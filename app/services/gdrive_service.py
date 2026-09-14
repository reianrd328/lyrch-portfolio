import os
import io
import re
import json
import base64
import logging
import urllib.request
import urllib.parse
from datetime import datetime
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials as UserCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/userinfo.email"
]

DEFAULT_SECRET_PATHS = [
    "service_account.json",
    "credentials.json",
    "/etc/secrets/service_account.json",
    "/etc/secrets/credentials.json",
    os.path.join("instance", "service_account.json"),
    os.path.join(os.getcwd(), "service_account.json")
]

def _parse_service_account_dict() -> dict | None:
    """Attempts to retrieve and parse service account credentials dictionary."""
    raw_env = os.getenv("GDRIVE_SERVICE_ACCOUNT_JSON", "").strip()
    if raw_env:
        if raw_env.startswith("{") and raw_env.endswith("}"):
            try:
                return json.loads(raw_env)
            except Exception as e:
                logger.warning(f"Error parsing raw GDRIVE_SERVICE_ACCOUNT_JSON: {e}")
        try:
            decoded = base64.b64decode(raw_env).decode("utf-8")
            return json.loads(decoded)
        except Exception:
            pass

    custom_path = os.getenv("GDRIVE_CREDENTIALS_FILE", "").strip()
    if custom_path and os.path.isfile(custom_path):
        try:
            with open(custom_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Error reading GDRIVE_CREDENTIALS_FILE at {custom_path}: {e}")

    for path in DEFAULT_SECRET_PATHS:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error reading credentials file at {path}: {e}")

    return None

def get_oauth_config(settings=None) -> tuple[str, str, str, str]:
    """Retrieves client_id, client_secret, refresh_token, and user_email."""
    cid = os.getenv("GDRIVE_CLIENT_ID", "").strip()
    csec = os.getenv("GDRIVE_CLIENT_SECRET", "").strip()
    rtoken = os.getenv("GDRIVE_REFRESH_TOKEN", "").strip()
    uemail = ""

    if settings:
        cid = getattr(settings, "gdrive_client_id", "") or cid
        csec = getattr(settings, "gdrive_client_secret", "") or csec
        rtoken = getattr(settings, "gdrive_refresh_token", "") or rtoken
        uemail = getattr(settings, "gdrive_user_email", "") or ""

    return cid.strip(), csec.strip(), rtoken.strip(), uemail.strip()

def is_oauth_configured(settings=None) -> bool:
    cid, csec, rtoken, _ = get_oauth_config(settings)
    return bool(cid and csec and rtoken)

def is_gdrive_configured(settings=None) -> bool:
    """Returns True if either OAuth 2.0 (User) or Service Account credentials are valid."""
    if is_oauth_configured(settings):
        return True
    data = _parse_service_account_dict()
    return bool(data and data.get("type") == "service_account" and data.get("client_email"))

def get_connected_account_email(settings=None) -> str | None:
    """Returns the email of the active Google connection (User account or Service Account)."""
    _, _, _, uemail = get_oauth_config(settings)
    if uemail:
        return uemail
    data = _parse_service_account_dict()
    if data and "client_email" in data:
        return data.get("client_email")
    return None

def get_service_account_email() -> str | None:
    data = _parse_service_account_dict()
    if data and "client_email" in data:
        return data.get("client_email")
    return None

def get_drive_service(settings=None):
    """
    Initializes and returns an authenticated Google Drive v3 resource.
    Prioritizes OAuth 2.0 (User Account) which owns 15 GB personal quota.
    """
    cid, csec, rtoken, _ = get_oauth_config(settings)
    if cid and csec and rtoken:
        user_creds = UserCredentials(
            token=None,
            refresh_token=rtoken,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=cid,
            client_secret=csec,
            scopes=SCOPES
        )
        return build("drive", "v3", credentials=user_creds, cache_discovery=False)

    data = _parse_service_account_dict()
    if data:
        creds = service_account.Credentials.from_service_account_info(data, scopes=SCOPES)
        return build("drive", "v3", credentials=creds, cache_discovery=False)

    raise ValueError("Google Drive credentials not configured. Please connect your Google account or add credentials.")

def build_google_oauth_url(client_id: str, redirect_uri: str) -> str:
    """Builds the authorization consent URL for Google OAuth 2.0."""
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/drive.file https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/userinfo.email",
        "access_type": "offline",
        "prompt": "consent"
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

def exchange_code_for_tokens(code: str, client_id: str, client_secret: str, redirect_uri: str) -> tuple[str | None, str | None, str | None]:
    """Exchanges an authorization code for refresh_token, access_token, and user email."""
    try:
        data = urllib.parse.urlencode({
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }).encode("utf-8")
        req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req) as resp:
            tokens = json.loads(resp.read().decode("utf-8"))

        refresh_token = tokens.get("refresh_token")
        access_token = tokens.get("access_token")

        user_email = ""
        if access_token:
            req_info = urllib.request.Request(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            try:
                with urllib.request.urlopen(req_info) as u_resp:
                    u_data = json.loads(u_resp.read().decode("utf-8"))
                    user_email = u_data.get("email", "")
            except Exception:
                pass

        return refresh_token, access_token, user_email
    except Exception as e:
        logger.error(f"Error exchanging OAuth code: {e}")
        return None, None, None

def clean_folder_id(raw_input: str) -> str:
    """
    Extracts the clean folder ID from a raw ID or any Google Drive URL format.
    Handles:
    - https://drive.google.com/drive/folders/1BxiMVs0XRA5nFMdKvBHKGo24xpVTk9-F?usp=sharing
    - https://drive.google.com/drive/u/0/folders/1BxiMVs0XRA5nFMdKvBHKGo24xpVTk9-F
    - https://drive.google.com/open?id=1BxiMVs0XRA5nFMdKvBHKGo24xpVTk9-F
    - 1BxiMVs0XRA5nFMdKvBHKGo24xpVTk9-F
    """
    if not raw_input:
        return ""
    val = raw_input.strip()
    m = re.search(r"/folders/([a-zA-Z0-9_-]+)", val)
    if m:
        return m.group(1)
    m = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", val)
    if m:
        return m.group(1)
    if "/" not in val and "?" not in val:
        return val
    return val

def upload_backup_to_gdrive(backup_json_str: str, filename: str = None, folder_id: str = None, settings=None) -> tuple[bool, str, str | None]:
    """
    Uploads a serialized database JSON string directly to a Google Drive folder.
    Returns: (success: bool, message: str, web_view_url: str | None)
    """
    try:
        if not is_gdrive_configured(settings):
            return False, "Google Drive is not connected. Please connect your Google account in Settings & Backup.", None

        target_folder = clean_folder_id(folder_id)
        if not target_folder:
            return False, "Google Drive Folder link/ID is missing. Please enter your Google Drive folder link in 'GOOGLE DRIVE FOLDER ID / URL' and save.", None

        service = get_drive_service(settings)

        if not filename:
            filename = f"lyrch_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

        file_metadata = {
            "name": filename,
            "mimeType": "application/json",
            "description": f"LYRCH Portfolio Database Backup archive generated on {datetime.utcnow().isoformat()} UTC",
            "parents": [target_folder]
        }

        media = MediaIoBaseUpload(
            io.BytesIO(backup_json_str.encode("utf-8")),
            mimetype="application/json",
            resumable=True
        )

        created_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, name, webViewLink, webContentLink, parents"
        ).execute()

        file_id = created_file.get("id")
        web_link = created_file.get("webViewLink") or f"https://drive.google.com/file/d/{file_id}/view"

        return True, f"Successfully uploaded {filename} to Google Drive (ID: {file_id})", web_link

    except HttpError as http_err:
        raw_reason = ""
        try:
            err_json = json.loads(http_err.content.decode("utf-8"))
            raw_reason = err_json.get("error", {}).get("message", "")
        except Exception:
            raw_reason = str(http_err)

        if "has not been used in project" in raw_reason or "is disabled" in raw_reason:
            err_msg = f"Google Drive API is disabled in your project. Please search 'Google Drive API' in Google Cloud Console and click ENABLE. ({raw_reason})"
        elif "storage quota" in raw_reason.lower():
            err_msg = "Google Drive storage quota error: Please connect your personal Google Account via OAuth 2.0 to use your 15 GB storage quota."
        elif http_err.resp.status == 404:
            err_msg = f"Google Drive Folder not found (404). Please verify your Google Drive Folder link / ID. ({raw_reason})"
        elif http_err.resp.status == 403:
            active_email = get_connected_account_email(settings) or "your account"
            err_msg = f"Google Drive Permission Denied (403): {raw_reason}. Ensure your account ({active_email}) has edit access to that folder."
        else:
            err_msg = f"Google Drive API error ({http_err.resp.status}): {raw_reason}"
        logger.error(f"Google Drive API HttpError: {err_msg}")
        return False, err_msg, None
    except Exception as e:
        logger.error(f"Google Drive upload exception: {e}")
        return False, f"Google Drive error: {str(e)}", None

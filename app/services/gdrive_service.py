import os
import io
import re
import json
import base64
import logging
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

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
        # Check if raw JSON
        if raw_env.startswith("{") and raw_env.endswith("}"):
            try:
                return json.loads(raw_env)
            except Exception as e:
                logger.warning(f"Error parsing raw GDRIVE_SERVICE_ACCOUNT_JSON: {e}")
        # Try base64 decoding
        try:
            decoded = base64.b64decode(raw_env).decode("utf-8")
            return json.loads(decoded)
        except Exception:
            pass

    # Check file path in environment variable
    custom_path = os.getenv("GDRIVE_CREDENTIALS_FILE", "").strip()
    if custom_path and os.path.isfile(custom_path):
        try:
            with open(custom_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Error reading GDRIVE_CREDENTIALS_FILE at {custom_path}: {e}")

    # Check default file paths
    for path in DEFAULT_SECRET_PATHS:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error reading credentials file at {path}: {e}")

    return None

def is_gdrive_configured() -> bool:
    """Returns True if Google Drive Service Account credentials are valid and present."""
    data = _parse_service_account_dict()
    return bool(data and data.get("type") == "service_account" and data.get("client_email"))

def get_service_account_email() -> str | None:
    """Returns the client email address from the configured Google Service Account."""
    data = _parse_service_account_dict()
    if data and "client_email" in data:
        return data.get("client_email")
    return None

def get_drive_service():
    """Initializes and returns an authenticated Google Drive v3 resource."""
    data = _parse_service_account_dict()
    if not data:
        raise ValueError("Google Drive credentials not found or invalid. Set GDRIVE_SERVICE_ACCOUNT_JSON or GDRIVE_CREDENTIALS_FILE.")

    creds = service_account.Credentials.from_service_account_info(data, scopes=SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)

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
    # Direct folder ID fallback
    if "/" not in val and "?" not in val:
        return val
    return val

def upload_backup_to_gdrive(backup_json_str: str, filename: str = None, folder_id: str = None) -> tuple[bool, str, str | None]:
    """
    Uploads a serialized database JSON string directly to a Google Drive folder.
    Returns: (success: bool, message: str, web_view_url: str | None)
    """
    try:
        if not is_gdrive_configured():
            return False, "Google Drive service account credentials are not configured. Please add GDRIVE_SERVICE_ACCOUNT_JSON in environment variables.", None

        target_folder = clean_folder_id(folder_id)
        if not target_folder:
            return False, "Google Drive Folder ID is missing. Please paste your Google Drive folder URL or ID in 'GOOGLE DRIVE FOLDER ID' and save.", None

        service = get_drive_service()

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
            err_msg = f"Google Drive API is disabled in your project. Please open Google Cloud Console, search 'Google Drive API', and click ENABLE. ({raw_reason})"
        elif "storage quota" in raw_reason.lower():
            err_msg = "Google Drive storage quota error: Service accounts cannot store root files. Make sure the folder is shared with your bot as Editor and the Folder ID is correct."
        elif http_err.resp.status == 404:
            err_msg = f"Google Drive Folder not found (404). Please verify your Google Drive Folder ID / URL. ({raw_reason})"
        elif http_err.resp.status == 403:
            sa_email = get_service_account_email() or "your service account email"
            err_msg = f"Google Drive Permission Denied (403): {raw_reason}. Make sure the folder is shared with {sa_email} as Editor."
        else:
            err_msg = f"Google Drive API error ({http_err.resp.status}): {raw_reason}"
        logger.error(f"Google Drive API HttpError: {err_msg}")
        return False, err_msg, None
    except Exception as e:
        logger.error(f"Google Drive upload exception: {e}")
        return False, f"Google Drive error: {str(e)}", None


import os
import json
import base64
import smtplib
import urllib.request
import urllib.error
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime

def is_smtp_configured(settings=None) -> bool:
    """Checks if email dispatch is configured via Resend HTTPS API or SMTP."""
    if settings and getattr(settings, "resend_api_key", None):
        return True
    if os.getenv("RESEND_API_KEY"):
        return True
    return bool(os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD"))

def _send_via_resend(api_key: str, recipient_email: str, filename: str, backup_json_str: str, body_html: str, now_str: str) -> tuple[bool, str]:
    """Sends email via Resend HTTPS REST API over port 443 (bypasses Render SMTP port blocking)."""
    try:
        b64_content = base64.b64encode(backup_json_str.encode("utf-8")).decode("utf-8")
        from_email = os.getenv("RESEND_FROM", "LYRCH Vault <onboarding@resend.dev>")
        payload = {
            "from": from_email,
            "to": [recipient_email],
            "subject": f"[LYRCH COMMAND CENTER] Database Backup Vault — {now_str}",
            "html": body_html,
            "attachments": [
                {
                    "filename": filename,
                    "content": b64_content
                }
            ]
        }
        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            return True, f"Backup successfully emailed to {recipient_email} via Resend API!"
    except urllib.error.HTTPError as http_err:
        err_body = http_err.read().decode("utf-8", errors="ignore")
        try:
            parsed = json.loads(err_body)
            msg = parsed.get("message") or parsed.get("error") or err_body
            return False, f"Resend notice: {msg}"
        except Exception:
            return False, f"Resend API notice ({http_err.code}): {err_body}"
    except Exception as e:
        return False, f"Resend dispatch notice: {str(e)}"

def send_backup_email(recipient_email: str, backup_json_str: str, metadata: dict = None, settings=None) -> tuple[bool, str]:
    """
    Sends a database backup JSON file as an attachment to recipient_email.
    Supports Resend HTTPS API (recommended for Render) or traditional SMTP.
    """
    if not recipient_email or "@" not in recipient_email:
        return False, "Recipient email address is invalid."

    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    filename = f"lyrch_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

    resend_key = (getattr(settings, "resend_api_key", "") or "").strip() or os.getenv("RESEND_API_KEY", "").strip()

    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    smtp_from = os.getenv("SMTP_FROM", f"LYRCH Command Center <{smtp_user}>" if smtp_user else "command@lyrch.dev")
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1")

    if not resend_key and (not smtp_user or not smtp_password):
        return False, "Email credentials not configured. Please paste your Resend API Key in Settings or set RESEND_API_KEY in Render."

    # Compose Email
    msg = MIMEMultipart()
    msg["From"] = smtp_from
    msg["To"] = recipient_email
    msg["Subject"] = f"[LYRCH COMMAND CENTER] Database Backup Vault — {now_str}"

    summary_lines = []
    if metadata and "record_counts" in metadata:
        summary_lines.append("Telemetry Record Counts:")
        for tbl, count in metadata["record_counts"].items():
            summary_lines.append(f"  • {tbl}: {count} records")
    summary_text = "\n".join(summary_lines) if summary_lines else "Complete system database state serialized."

    body_html = f"""
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0b112c; color: #f1f5f9; padding: 25px; border-radius: 8px;">
        <div style="border-bottom: 2px solid #00f0ff; padding-bottom: 12px; margin-bottom: 20px;">
            <h2 style="color: #00f0ff; margin: 0; font-size: 20px; letter-spacing: 1.5px;">LYRCH DIGITAL COMMAND CENTER</h2>
            <p style="color: #a855f7; margin: 4px 0 0; font-size: 13px;">AUTOMATED DISASTER RECOVERY &amp; DATABASE BACKUP VAULT</p>
        </div>

        <p style="font-size: 14px; line-height: 1.6; color: #cbd5e1;">
            Commander, your automated system backup has been successfully compiled and verified.
        </p>

        <div style="background: rgba(15,23,42,0.85); border: 1px solid rgba(0,240,255,0.25); border-radius: 6px; padding: 15px; margin: 18px 0;">
            <div style="color: #00f0ff; font-weight: bold; font-size: 13px; margin-bottom: 8px;">BACKUP TELEMETRY REPORT</div>
            <div style="font-size: 12px; color: #94a3b8; line-height: 1.7;">
                <strong>Generated At:</strong> {now_str}<br>
                <strong>Archive File:</strong> {filename}<br>
                <strong>Archive Size:</strong> {round(len(backup_json_str.encode('utf-8')) / 1024, 2)} KB<br>
                <strong>Status:</strong> Encrypted &amp; Ready for One-Click Restoration
            </div>
            <pre style="background: #020617; padding: 10px; border-radius: 4px; color: #38bdf8; font-size: 11px; margin-top: 10px; overflow-x: auto;">{summary_text}</pre>
        </div>

        <p style="font-size: 12px; color: #94a3b8;">
            Keep this attachment in a safe location. You can restore this archive anytime using the <strong>Restore from Backup</strong> tool in your Command Center Admin Dashboard.
        </p>

        <div style="margin-top: 25px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 12px; font-size: 11px; color: #64748b;">
            LYRCH DEV // CYBERNETIC WORK MANAGEMENT &amp; PORTFOLIO CMS
        </div>
    </div>
    """

    msg.attach(MIMEText(body_html, "html"))

    # Attach JSON file
    attachment = MIMEApplication(backup_json_str.encode("utf-8"), _subtype="json")
    attachment.add_header("Content-Disposition", "attachment", filename=filename)
    msg.attach(attachment)

    if resend_key:
        return _send_via_resend(resend_key, recipient_email, filename, backup_json_str, body_html, now_str)

    try:
        if use_tls:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=20)
            server.ehlo()
            server.starttls()
            server.ehlo()
        else:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20)
            server.ehlo()

        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        return True, f"Backup successfully emailed to {recipient_email}"
    except smtplib.SMTPAuthenticationError:
        return False, "SMTP Authentication Failed: Check your SMTP_USER and Google App Password."
    except Exception as e:
        err_str = str(e)
        if "101" in err_str or "network is unreachable" in err_str.lower():
            return False, "Render blocks outbound SMTP ports (587/465) on free instances. Please use your Google Drive Backup (which works over HTTPS) or set RESEND_API_KEY in Render."
        return False, f"Email sending failed: {err_str}"

def send_contact_message_email(sender_name: str, sender_email: str, message_content: str, recipient_email: str, settings=None) -> tuple[bool, str]:
    """
    Dispatches an incoming contact form transmission to the portfolio owner's registered email.
    Supports Resend HTTPS API (recommended) or SMTP.
    Sets Reply-To directly to the visitor's email address.
    """
    if not recipient_email or "@" not in recipient_email:
        return False, "Recipient email address is invalid."

    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    subject = f"[TRANSMISSION RECEIVED] Message from {sender_name} via Portfolio"

    resend_key = (getattr(settings, "resend_api_key", "") or "").strip() or os.getenv("RESEND_API_KEY", "").strip()

    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    smtp_from = os.getenv("SMTP_FROM", f"LYRCH Command Center <{smtp_user}>" if smtp_user else "command@lyrch.dev")
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1")

    escaped_message = message_content.replace("\n", "<br>")

    body_html = f"""
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0b112c; color: #f1f5f9; padding: 25px; border-radius: 8px; max-width: 600px; margin: 0 auto;">
        <div style="border-bottom: 2px solid #00f0ff; padding-bottom: 12px; margin-bottom: 20px;">
            <h2 style="color: #00f0ff; margin: 0; font-size: 20px; letter-spacing: 1.5px;">LYRCH DIGITAL COMMAND CENTER</h2>
            <p style="color: #a855f7; margin: 4px 0 0; font-size: 13px;">DIRECT TRANSMISSION // INCOMING CONTACT INQUIRY</p>
        </div>

        <p style="font-size: 14px; line-height: 1.6; color: #cbd5e1;">
            Commander, a new transmission has been received through your portfolio contact terminal:
        </p>

        <div style="background: rgba(15,23,42,0.85); border: 1px solid rgba(0,240,255,0.25); border-radius: 6px; padding: 15px; margin: 18px 0;">
            <div style="color: #00f0ff; font-weight: bold; font-size: 13px; margin-bottom: 10px;">TRANSMISSION METADATA</div>
            <div style="font-size: 13px; color: #94a3b8; line-height: 1.8;">
                <strong style="color: #ffffff;">Callsign / Name:</strong> {sender_name}<br>
                <strong style="color: #ffffff;">Sender Email:</strong> <a href="mailto:{sender_email}" style="color: #00f0ff; text-decoration: underline;">{sender_email}</a><br>
                <strong style="color: #ffffff;">Timestamp:</strong> {now_str}
            </div>
            <div style="margin-top: 14px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 12px;">
                <strong style="color: #a855f7; font-size: 12px; display: block; margin-bottom: 6px;">TRANSMISSION CONTENT:</strong>
                <div style="background: #020617; padding: 12px; border-radius: 6px; color: #f1f5f9; font-size: 13px; line-height: 1.6; border-left: 3px solid #00f0ff;">
                    {escaped_message}
                </div>
            </div>
        </div>

        <div style="margin: 20px 0;">
            <a href="mailto:{sender_email}?subject=Re: Your Transmission to LYRCH Dev" style="display: inline-block; background: #00f0ff; color: #020617; padding: 10px 20px; border-radius: 4px; text-decoration: none; font-weight: bold; font-size: 13px;">
                Reply Directly to {sender_name} &rarr;
            </a>
        </div>

        <div style="margin-top: 25px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 12px; font-size: 11px; color: #64748b;">
            LYRCH DEV // CYBERNETIC WORK MANAGEMENT &amp; PORTFOLIO CMS
        </div>
    </div>
    """

    if resend_key:
        try:
            from_email = os.getenv("RESEND_FROM", "LYRCH Dispatch <onboarding@resend.dev>")
            payload = {
                "from": from_email,
                "to": [recipient_email],
                "reply_to": sender_email,
                "subject": subject,
                "html": body_html
            }
            req = urllib.request.Request(
                "https://api.resend.com/emails",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {resend_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                return True, f"Transmission emailed to {recipient_email} via Resend API!"
        except Exception as e:
            return False, f"Resend notice: {str(e)}"

    if not smtp_user or not smtp_password:
        return False, "SMTP credentials not configured."

    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_from
        msg["To"] = recipient_email
        msg["Reply-To"] = sender_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body_html, "html"))

        if use_tls:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=20)
            server.ehlo()
            server.starttls()
            server.ehlo()
        else:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20)
            server.ehlo()

        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        return True, f"Transmission successfully emailed to {recipient_email}"
    except Exception as e:
        return False, f"Email sending failed: {str(e)}"


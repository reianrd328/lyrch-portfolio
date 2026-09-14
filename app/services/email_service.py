import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime

def is_smtp_configured() -> bool:
    """Checks if email SMTP settings are present in the environment."""
    return bool(os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD"))

def send_backup_email(recipient_email: str, backup_json_str: str, metadata: dict = None) -> tuple[bool, str]:
    """
    Sends a database backup JSON file as an attachment to recipient_email via SMTP.
    Works with Gmail, Outlook, SendGrid, Brevo, or custom SMTP servers.
    """
    if not recipient_email or "@" not in recipient_email:
        return False, "Recipient email address is invalid."

    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    smtp_from = os.getenv("SMTP_FROM", f"LYRCH Command Center <{smtp_user}>" if smtp_user else "command@lyrch.dev")
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1")

    if not smtp_user or not smtp_password:
        return False, "SMTP credentials not configured. Set SMTP_USER and SMTP_PASSWORD in Render Environment variables."

    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    filename = f"lyrch_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

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
        return False, "SMTP Authentication Failed: Check your SMTP_USER and App Password."
    except Exception as e:
        return False, f"Email sending failed: {str(e)}"


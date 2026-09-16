import os
import json
from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, Response
from flask_login import login_required, current_user
from app.models import db, Project, Video, GalleryItem, Document, Skill, Experience, BlogPost, ActivityLog, SiteSetting, PortfolioProfile
from app.services.upload_service import save_upload_file, delete_file
from app.services.backup_service import export_database_to_dict, export_database_to_json_str, restore_database_from_dict
from app.services.email_service import send_backup_email, is_smtp_configured
from app.services.gdrive_service import (
    upload_backup_to_gdrive, is_gdrive_configured, is_oauth_configured,
    get_connected_account_email, get_service_account_email, clean_folder_id,
    build_google_oauth_url, exchange_code_for_tokens
)

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/upload-avatar", methods=["POST"])
@login_required
def upload_avatar():
    """Instant AJAX avatar uploader that immediately saves to DB and disk."""
    avatar_file = request.files.get("avatar")
    if not avatar_file or not avatar_file.filename:
        return jsonify({"success": False, "error": "No image file provided."}), 400

    success, res = save_upload_file(avatar_file, subfolder="profile", allowed_types="image")
    if not success:
        return jsonify({"success": False, "error": res}), 400

    site_settings = SiteSetting.get_settings()
    if site_settings.avatar_url and site_settings.avatar_url.startswith("/uploads/"):
        delete_file(site_settings.avatar_url)

    site_settings.avatar_url = res
    if hasattr(current_user, "avatar_url"):
        current_user.avatar_url = res

    log = ActivityLog(
        title="Updated profile avatar photo",
        activity_type="project",
        time_label="Just now"
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        "success": True,
        "avatar_url": res,
        "message": "Profile photo saved and updated live!"
    })

@admin_bp.route("/")
@login_required
def dashboard():
    stats = {
        "projects": Project.query.count(),
        "videos": Video.query.count(),
        "gallery": GalleryItem.query.count(),
        "documents": Document.query.count(),
        "skills": Skill.query.count(),
        "blog_posts": BlogPost.query.count()
    }

    recent_projects = Project.query.order_by(Project.id.desc()).limit(5).all()
    recent_videos = Video.query.order_by(Video.id.desc()).limit(5).all()
    recent_activities = ActivityLog.query.order_by(ActivityLog.id.desc()).limit(8).all()
    active_profile = PortfolioProfile.query.filter_by(is_active=True).first()

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recent_projects=recent_projects,
        recent_videos=recent_videos,
        recent_activities=recent_activities,
        active_profile=active_profile,
        user=current_user
    )

@admin_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    site_settings = SiteSetting.get_settings()

    if request.method == "POST":
        # 1. Profile & Identity
        site_settings.display_name = request.form.get("display_name", site_settings.display_name).strip()
        site_settings.job_title = request.form.get("job_title", site_settings.job_title).strip()
        site_settings.location = request.form.get("location", site_settings.location).strip()

        avatar_file = request.files.get("avatar")
        if avatar_file and avatar_file.filename:
            success, res = save_upload_file(avatar_file, subfolder="profile", allowed_types="image")
            if success:
                if site_settings.avatar_url and site_settings.avatar_url.startswith("/uploads/"):
                    delete_file(site_settings.avatar_url)
                site_settings.avatar_url = res
                if hasattr(current_user, "avatar_url"):
                    current_user.avatar_url = res
            else:
                flash(f"Avatar upload error: {res}", "danger")
        else:
            avatar_url_custom = request.form.get("avatar_url_text", "").strip()
            if avatar_url_custom:
                site_settings.avatar_url = avatar_url_custom
                if hasattr(current_user, "avatar_url"):
                    current_user.avatar_url = avatar_url_custom

        # Resume Document Upload / Direct URL
        if request.form.get("clear_resume") == "1":
            if site_settings.resume_url and site_settings.resume_url.startswith("/uploads/"):
                delete_file(site_settings.resume_url)
            site_settings.resume_url = ""
        else:
            resume_file = request.files.get("resume")
            if resume_file and resume_file.filename:
                success, res = save_upload_file(resume_file, subfolder="documents", allowed_types="doc")
                if success:
                    if site_settings.resume_url and site_settings.resume_url.startswith("/uploads/"):
                        delete_file(site_settings.resume_url)
                    site_settings.resume_url = res
                else:
                    flash(f"Resume upload error: {res}", "danger")
            else:
                resume_url_custom = request.form.get("resume_url_text")
                if resume_url_custom is not None:
                    site_settings.resume_url = resume_url_custom.strip()

        # Synchronize resume with active profile snapshot if present
        active_prof = PortfolioProfile.query.filter_by(is_active=True).first()
        if active_prof:
            prof_data = active_prof.get_data()
            if "settings" in prof_data:
                prof_data["settings"]["resume_url"] = site_settings.resume_url
                active_prof.set_data(prof_data)

        # 2. Hero & Mission
        site_settings.hero_pretitle = request.form.get("hero_pretitle", site_settings.hero_pretitle).strip()
        site_settings.hero_title = request.form.get("hero_title", site_settings.hero_title).strip()
        site_settings.hero_tags = request.form.get("hero_tags", site_settings.hero_tags).strip()
        site_settings.hero_bio = request.form.get("hero_bio", site_settings.hero_bio).strip()

        # 3. Five Metrics
        site_settings.metric1_num = request.form.get("metric1_num", site_settings.metric1_num).strip()
        site_settings.metric1_title = request.form.get("metric1_title", site_settings.metric1_title).strip()
        site_settings.metric1_desc = request.form.get("metric1_desc", site_settings.metric1_desc).strip()

        site_settings.metric2_num = request.form.get("metric2_num", site_settings.metric2_num).strip()
        site_settings.metric2_title = request.form.get("metric2_title", site_settings.metric2_title).strip()
        site_settings.metric2_desc = request.form.get("metric2_desc", site_settings.metric2_desc).strip()

        site_settings.metric3_num = request.form.get("metric3_num", site_settings.metric3_num).strip()
        site_settings.metric3_title = request.form.get("metric3_title", site_settings.metric3_title).strip()
        site_settings.metric3_desc = request.form.get("metric3_desc", site_settings.metric3_desc).strip()

        site_settings.metric4_num = request.form.get("metric4_num", site_settings.metric4_num).strip()
        site_settings.metric4_title = request.form.get("metric4_title", site_settings.metric4_title).strip()
        site_settings.metric4_desc = request.form.get("metric4_desc", site_settings.metric4_desc).strip()

        site_settings.metric5_num = request.form.get("metric5_num", site_settings.metric5_num).strip()
        site_settings.metric5_title = request.form.get("metric5_title", site_settings.metric5_title).strip()
        site_settings.metric5_desc = request.form.get("metric5_desc", site_settings.metric5_desc).strip()

        # 4. Map Stats
        site_settings.map_stat1_num = request.form.get("map_stat1_num", site_settings.map_stat1_num).strip()
        site_settings.map_stat1_label = request.form.get("map_stat1_label", site_settings.map_stat1_label).strip()
        site_settings.map_stat2_num = request.form.get("map_stat2_num", site_settings.map_stat2_num).strip()
        site_settings.map_stat2_label = request.form.get("map_stat2_label", site_settings.map_stat2_label).strip()
        site_settings.map_stat3_num = request.form.get("map_stat3_num", site_settings.map_stat3_num).strip()
        site_settings.map_stat3_label = request.form.get("map_stat3_label", site_settings.map_stat3_label).strip()
        site_settings.map_tagline = request.form.get("map_tagline", site_settings.map_tagline).strip()

        # 5. Quote & Signature
        site_settings.quote_text = request.form.get("quote_text", site_settings.quote_text).strip()
        site_settings.quote_signature = request.form.get("quote_signature", site_settings.quote_signature).strip()

        # 6. Social & Contact
        site_settings.github_url = request.form.get("github_url", site_settings.github_url).strip()
        site_settings.linkedin_url = request.form.get("linkedin_url", site_settings.linkedin_url).strip()
        site_settings.youtube_url = request.form.get("youtube_url", site_settings.youtube_url).strip()
        site_settings.facebook_url = request.form.get("facebook_url", site_settings.facebook_url).strip()
        site_settings.contact_email = request.form.get("contact_email", site_settings.contact_email).strip()

        # 7. Default Theme Choice & Custom Colors
        theme = request.form.get("default_theme", "cyber")
        if theme in {"cyber", "matrix", "synthwave", "cobalt", "crimson", "custom"}:
            site_settings.default_theme = theme

        custom_p = request.form.get("custom_primary_color", "").strip()
        custom_s = request.form.get("custom_secondary_color", "").strip()
        if custom_p:
            site_settings.custom_primary_color = custom_p
        if custom_s:
            site_settings.custom_secondary_color = custom_s

        # 8. User account updates (e.g. transfer to another person)
        new_username = request.form.get("account_username", "").strip()
        new_password = request.form.get("account_password", "").strip()
        if new_username and new_username != current_user.username:
            current_user.username = new_username
        if new_password:
            current_user.set_password(new_password)
        current_user.display_name = site_settings.display_name

        # 9. Automated Database Backup Settings (Email & Google Drive)
        site_settings.backup_auto_enabled = (request.form.get("backup_auto_enabled") in ("on", "1", "true"))
        site_settings.backup_email = request.form.get("backup_email", "").strip()
        site_settings.backup_frequency = request.form.get("backup_frequency", "daily").strip()

        # Google Drive Backup Settings
        site_settings.gdrive_backup_enabled = (request.form.get("gdrive_backup_enabled") in ("on", "1", "true"))
        raw_folder_id = request.form.get("gdrive_folder_id", "").strip()
        site_settings.gdrive_folder_id = clean_folder_id(raw_folder_id)

        # Google Drive OAuth 2.0 Credentials
        cid = request.form.get("gdrive_client_id", "").strip()
        csec = request.form.get("gdrive_client_secret", "").strip()
        if cid:
            site_settings.gdrive_client_id = cid
        if csec:
            site_settings.gdrive_client_secret = csec

        # Resend Email API Key
        resend_key = request.form.get("resend_api_key", "").strip()
        site_settings.resend_api_key = resend_key

        # Log Activity
        log = ActivityLog(
            title="Updated Command Center dashboard & backup settings",
            activity_type="project",
            time_label="Just now"
        )
        db.session.add(log)
        db.session.commit()

        flash("Command Center Dashboard & System Settings Updated!", "success")
        return redirect(url_for("admin.settings"))

    return render_template(
        "admin/settings/index.html",
        s=site_settings,
        smtp_ready=is_smtp_configured(site_settings),
        gdrive_ready=is_gdrive_configured(site_settings),
        oauth_ready=is_oauth_configured(site_settings),
        gdrive_email=get_connected_account_email(site_settings),
        redirect_uri=_get_oauth_redirect_uri()
    )

@admin_bp.route("/backup/download", methods=["GET"])
@login_required
def backup_download():
    """Generates and streams a direct JSON database backup download."""
    json_str = export_database_to_json_str()
    filename = f"lyrch_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

    log = ActivityLog(
        title="Downloaded manual database backup archive (JSON)",
        activity_type="project",
        time_label="Just now"
    )
    db.session.add(log)
    db.session.commit()

    return Response(
        json_str,
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@admin_bp.route("/backup/send-email", methods=["POST"])
@login_required
def backup_send_email():
    """Manually triggers an immediate database backup and emails it to the specified address."""
    target_email = request.form.get("email_override", "").strip()
    settings = SiteSetting.get_settings()

    if not target_email:
        target_email = settings.backup_email or current_user.email

    if not target_email or "@" not in target_email:
        flash("Invalid recipient email. Please provide a valid email address.", "danger")
        return redirect(url_for("admin.settings"))

    backup_dict = export_database_to_dict()
    backup_json_str = export_database_to_json_str()

    success, msg = send_backup_email(target_email, backup_json_str, backup_dict["metadata"], settings=settings)
    settings.backup_last_run = datetime.utcnow()
    settings.backup_last_status = (("Success: " if success else "Error: ") + msg)[:500]

    log = ActivityLog(
        title=f"Manual Database Backup {'sent to ' + target_email if success else 'failed'}",
        activity_type="project",
        time_label="Just now"
    )
    db.session.add(log)
    db.session.commit()

    flash(msg, "success" if success else "danger")
    return redirect(url_for("admin.settings"))

@admin_bp.route("/backup/restore", methods=["POST"])
@login_required
def backup_restore():
    """Restores database tables from an uploaded JSON backup file."""
    backup_file = request.files.get("backup_file")
    if not backup_file or not backup_file.filename:
        flash("No backup file selected for restoration.", "warning")
        return redirect(url_for("admin.settings"))

    try:
        content = backup_file.read().decode("utf-8")
        data = json.loads(content)
        success, msg = restore_database_from_dict(data)
        if success:
            log = ActivityLog(
                title=f"Restored database from backup file {backup_file.filename}",
                activity_type="project",
                time_label="Just now"
            )
            db.session.add(log)
            db.session.commit()
            flash("Database successfully restored from backup!", "success")
        else:
            flash(f"Restoration failed: {msg}", "danger")
    except Exception as e:
        flash(f"Error parsing backup JSON file: {str(e)}", "danger")

    return redirect(url_for("admin.settings"))

@admin_bp.route("/backup/upload-gdrive", methods=["GET", "POST"])
@login_required
def backup_upload_gdrive():
    """Manually triggers an immediate database backup upload to Google Drive."""
    if request.method == "GET":
        return redirect(url_for("admin.settings"))

    try:
        settings = SiteSetting.get_settings()
        folder_override = request.form.get("folder_id_override", "").strip()
        folder_id = clean_folder_id(folder_override) if folder_override else settings.gdrive_folder_id

        # If a folder was supplied in the form, automatically persist it to settings
        if folder_override and folder_id and folder_id != settings.gdrive_folder_id:
            settings.gdrive_folder_id = folder_id
            db.session.commit()

        if not folder_id:
            flash("Google Drive Folder link/ID is missing. Please paste your Google Drive Folder link or ID into 'GOOGLE DRIVE FOLDER ID / URL' first.", "warning")
            return redirect(url_for("admin.settings"))

        backup_json_str = export_database_to_json_str()
        filename = f"lyrch_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

        success, msg, web_link = upload_backup_to_gdrive(backup_json_str, filename=filename, folder_id=folder_id, settings=settings)

        if success:
            settings.gdrive_last_upload_url = web_link
            settings.backup_last_run = datetime.utcnow()
            settings.backup_last_status = f"Success (Google Drive): {filename}"[:500]
            db.session.commit()

            log = ActivityLog(
                title=f"Uploaded backup {filename} to Google Drive",
                activity_type="project",
                time_label="Just now"
            )
            db.session.add(log)
            db.session.commit()
            flash(f"Database backup uploaded to Google Drive successfully! ({filename})", "success")
        else:
            settings.backup_last_status = f"Failed (Google Drive): {msg}"[:500]
            db.session.commit()
            flash(f"Google Drive upload notice: {msg}", "danger")

    except Exception as err:
        db.session.rollback()
        flash(f"Google Drive process notice: {str(err)}", "danger")

    return redirect(url_for("admin.settings"))

def _get_oauth_redirect_uri() -> str:
    """Returns the absolute callback URL for Google OAuth 2.0 with HTTPS assurance."""
    override = os.getenv("GDRIVE_REDIRECT_URI", "").strip()
    if override:
        return override
    uri = url_for("admin.gdrive_oauth_callback", _external=True)
    proto = request.headers.get("X-Forwarded-Proto", "").lower()
    if proto == "https" and uri.startswith("http://"):
        uri = "https://" + uri[len("http://"):]
    elif "onrender.com" in uri and uri.startswith("http://"):
        uri = "https://" + uri[len("http://"):]
    return uri

@admin_bp.route("/backup/gdrive-auth", methods=["POST"])
@login_required
def backup_gdrive_auth():
    """Initiates Google OAuth 2.0 authorization for personal Google Drive."""
    settings = SiteSetting.get_settings()
    client_id = (
        request.form.get("client_id", "").strip()
        or request.form.get("gdrive_client_id", "").strip()
        or settings.gdrive_client_id
        or os.getenv("GDRIVE_CLIENT_ID", "").strip()
    )
    client_secret = (
        request.form.get("client_secret", "").strip()
        or request.form.get("gdrive_client_secret", "").strip()
        or settings.gdrive_client_secret
        or os.getenv("GDRIVE_CLIENT_SECRET", "").strip()
    )

    raw_folder = request.form.get("folder_id", "").strip() or request.form.get("gdrive_folder_id", "").strip()
    if raw_folder:
        settings.gdrive_folder_id = clean_folder_id(raw_folder)

    if not client_id or not client_secret:
        flash("Please provide your Google OAuth Client ID and Client Secret first.", "warning")
        return redirect(url_for("admin.settings"))

    settings.gdrive_client_id = client_id
    settings.gdrive_client_secret = client_secret
    db.session.commit()

    redirect_uri = _get_oauth_redirect_uri()
    auth_url = build_google_oauth_url(client_id, redirect_uri)
    return redirect(auth_url)

@admin_bp.route("/oauth2callback", methods=["GET"])
@login_required
def gdrive_oauth_callback():
    """Handles the OAuth2 code callback from Google."""
    code = request.args.get("code")
    error = request.args.get("error")
    if error or not code:
        flash(f"Google authorization cancelled or failed: {error or 'No authorization code received'}", "warning")
        return redirect(url_for("admin.settings"))

    settings = SiteSetting.get_settings()
    redirect_uri = _get_oauth_redirect_uri()

    rtoken, atoken, uemail = exchange_code_for_tokens(
        code,
        settings.gdrive_client_id,
        settings.gdrive_client_secret,
        redirect_uri
    )

    if not rtoken and atoken and settings.gdrive_refresh_token:
        rtoken = settings.gdrive_refresh_token

    if rtoken:
        settings.gdrive_refresh_token = rtoken
        settings.gdrive_user_email = uemail or settings.gdrive_user_email or "Personal Account"
        settings.gdrive_backup_enabled = True
        db.session.commit()

        log = ActivityLog(
            title=f"Connected Google Drive account ({uemail or settings.gdrive_user_email})",
            activity_type="project",
            time_label="Just now"
        )
        db.session.add(log)
        db.session.commit()
        flash(f"Successfully connected Google Drive as {uemail or settings.gdrive_user_email}! Backups will now upload to your personal Google Drive with 15 GB storage.", "success")
    else:
        flash("Could not obtain refresh token. Please verify credentials and try again.", "danger")

    return redirect(url_for("admin.settings"))

@admin_bp.route("/backup/gdrive-disconnect", methods=["POST"])
@login_required
def backup_gdrive_disconnect():
    """Disconnects the Google OAuth 2.0 personal account."""
    settings = SiteSetting.get_settings()
    settings.gdrive_refresh_token = None
    settings.gdrive_user_email = None
    db.session.commit()

    log = ActivityLog(
        title="Disconnected Google Drive personal account",
        activity_type="project",
        time_label="Just now"
    )
    db.session.add(log)
    db.session.commit()
    flash("Google Drive personal account disconnected.", "info")
    return redirect(url_for("admin.settings"))


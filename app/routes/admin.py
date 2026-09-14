from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app.models import db, Project, Video, GalleryItem, Document, Skill, Experience, BlogPost, ActivityLog, SiteSetting
from app.services.upload_service import save_upload_file, delete_file

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

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recent_projects=recent_projects,
        recent_videos=recent_videos,
        recent_activities=recent_activities,
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

        # Log Activity
        log = ActivityLog(
            title="Updated Command Center dashboard settings",
            activity_type="project",
            time_label="Just now"
        )
        db.session.add(log)
        db.session.commit()

        flash("Command Center Dashboard & System Settings Updated!", "success")
        return redirect(url_for("admin.settings"))

    return render_template("admin/settings/index.html", s=site_settings)


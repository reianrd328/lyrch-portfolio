import json
import re
from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, Response, jsonify, abort
from flask_login import login_required, current_user
from app.models import db, PortfolioProfile, ActivityLog, SiteSetting, User
from app.services.profile_service import (
    capture_current_portfolio_dict,
    apply_portfolio_dict_to_database,
    get_starter_template_data,
    switch_active_profile,
    bootstrap_default_profile_if_needed
)
from app.services.upload_service import save_upload_file, delete_file

profiles_bp = Blueprint("admin_profiles", __name__)

def slugify(text: str) -> str:
    """Converts a title to a clean URL slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")

def get_unique_slug(base_slug: str, exclude_id: int = None) -> str:
    """Ensures slug is globally unique by appending counter if needed."""
    slug = base_slug or "portfolio"
    counter = 1
    query = PortfolioProfile.query.filter_by(slug=slug)
    if exclude_id:
        query = query.filter(PortfolioProfile.id != exclude_id)
    while query.first():
        slug = f"{base_slug}-{counter}"
        counter += 1
        query = PortfolioProfile.query.filter_by(slug=slug)
        if exclude_id:
            query = query.filter(PortfolioProfile.id != exclude_id)
    return slug

@profiles_bp.route("")
@profiles_bp.route("/")
@login_required
def index():
    bootstrap_default_profile_if_needed()
    profiles = PortfolioProfile.query.order_by(PortfolioProfile.is_active.desc(), PortfolioProfile.id.asc()).all()
    active_profile = PortfolioProfile.query.filter_by(is_active=True).first()
    return render_template("admin/profiles/index.html", profiles=profiles, active_profile=active_profile)

@profiles_bp.route("/create", methods=["POST"])
@login_required
def create():
    name = request.form.get("name", "").strip()
    client_name = request.form.get("client_name", "").strip()
    slug_raw = request.form.get("slug", "").strip()
    description = request.form.get("description", "").strip()
    theme_preset = request.form.get("theme_preset", "cyber").strip()
    template_type = request.form.get("template_type", "starter").strip()

    if not name:
        flash("Profile Name is required.", "danger")
        return redirect(url_for("admin_profiles.index"))

    slug = get_unique_slug(slugify(slug_raw if slug_raw else name))
    if "submitted_from_form" in request.form:
        is_published = bool(request.form.get("is_published") in ("1", "true", "True", True))
    else:
        is_published = request.form.get("is_published", "1") in ("1", "true", "True", True)

    if template_type == "clone":
        # Clone current active portfolio
        data = capture_current_portfolio_dict()
        if client_name:
            data.get("settings", {})["display_name"] = client_name
        data.get("settings", {})["default_theme"] = theme_preset
    else:
        # Generate clean starter template
        data = get_starter_template_data(name, client_name=client_name, theme_preset=theme_preset)

    # Optional avatar picture upload or URL
    avatar_file = request.files.get("avatar")
    avatar_url_text = request.form.get("avatar_url_text", "").strip()
    if avatar_file and avatar_file.filename:
        success, res = save_upload_file(avatar_file, subfolder="profile", allowed_types="image")
        if success:
            data.setdefault("settings", {})["avatar_url"] = res
    elif avatar_url_text:
        data.setdefault("settings", {})["avatar_url"] = avatar_url_text

    new_profile = PortfolioProfile(
        name=name,
        slug=slug,
        client_name=client_name,
        description=description,
        theme_preset=theme_preset,
        is_active=False,
        is_published=is_published
    )
    new_profile.set_data(data)
    db.session.add(new_profile)

    log = ActivityLog(
        title=f"Created new portfolio profile '{name}' ({'ONLINE' if is_published else 'DRAFT'})",
        activity_type="system",
        time_label="Just now"
    )
    db.session.add(log)
    db.session.commit()

    if data.get("gallery"):
        from app.models import GalleryItem
        from app.services.profile_service import filter_valid_columns
        for g_data in data["gallery"]:
            clean = filter_valid_columns(GalleryItem, dict(g_data))
            clean["profile_id"] = new_profile.id
            db.session.add(GalleryItem(**clean))
        db.session.commit()

    # Optional: Create initial login account if credentials provided
    account_username = request.form.get("account_username", "").strip()
    account_password = request.form.get("account_password", "").strip()
    if account_username and account_password:
        existing = User.query.filter((User.username == account_username) | (User.email == f"{account_username}@{slug}.local")).first()
        if not existing:
            user = User(
                username=account_username,
                email=f"{account_username}@{slug}.local",
                display_name=client_name or name,
                role="profile_user",
                is_active_account=True,
                profile_id=new_profile.id
            )
            user.set_password(account_password)
            db.session.add(user)
            db.session.commit()
            flash(f"Profile '{name}' created with login account '@{account_username}'!", "success")
        else:
            flash(f"Profile '{name}' created, but username '@{account_username}' is already taken.", "warning")
    else:
        flash(f"Profile '{name}' created! Dedicated public URL: /p/{slug}", "success")
    return redirect(url_for("admin_profiles.index"))

@profiles_bp.route("/<int:profile_id>/account", methods=["POST"])
@login_required
def manage_account(profile_id):
    """Super Admin route to create or update credentials for a profile."""
    if current_user.role != "admin":
        abort(403)
    profile = PortfolioProfile.query.get_or_404(profile_id)
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    display_name = request.form.get("display_name", "").strip() or profile.client_name or profile.name
    email = request.form.get("email", "").strip() or f"{username}@{profile.slug}.local"

    user = User.query.filter_by(profile_id=profile.id).first()

    if not user:
        if not username or not password:
            flash("Username and password are required to create a login account.", "danger")
            return redirect(url_for("admin_profiles.index"))
        
        existing = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing:
            flash(f"Username '{username}' or email '{email}' is already taken.", "danger")
            return redirect(url_for("admin_profiles.index"))

        user = User(
            username=username,
            email=email,
            display_name=display_name,
            role="profile_user",
            is_active_account=True,
            profile_id=profile.id
        )
        user.set_password(password)
        db.session.add(user)
        flash(f"Login account '@{username}' successfully created for '{profile.name}'!", "success")
    else:
        if username and username != user.username:
            existing = User.query.filter(User.username == username, User.id != user.id).first()
            if existing:
                flash(f"Username '{username}' is already in use by another account.", "danger")
                return redirect(url_for("admin_profiles.index"))
            user.username = username
        if display_name:
            user.display_name = display_name
        if email:
            user.email = email
        if password:
            user.set_password(password)
            user.active_session_token = None
            user.active_session_heartbeat = None
            flash(f"Credentials & password for '{profile.name}' updated!", "success")
        else:
            flash(f"Account details for '{profile.name}' updated.", "success")

    db.session.commit()
    return redirect(url_for("admin_profiles.index"))

@profiles_bp.route("/<int:profile_id>/toggle-account", methods=["POST"])
@login_required
def toggle_account(profile_id):
    """Super Admin route to activate or disable a profile's login account."""
    if current_user.role != "admin":
        abort(403)
    profile = PortfolioProfile.query.get_or_404(profile_id)
    user = User.query.filter_by(profile_id=profile.id).first()
    if not user:
        flash(f"No login account configured for '{profile.name}'. Please create an account first.", "warning")
        return redirect(url_for("admin_profiles.index"))

    user.is_active_account = not user.is_active_account
    if not user.is_active_account:
        # Invalidate active session immediately
        user.active_session_token = None
        user.active_session_heartbeat = None
    db.session.commit()

    status_label = "ACTIVE" if user.is_active_account else "DISABLED"
    flash(f"Login account '@{user.username}' for '{profile.name}' is now {status_label}.", "success" if user.is_active_account else "warning")
    return redirect(url_for("admin_profiles.index"))

@profiles_bp.route("/upload-avatar", methods=["POST"])
@login_required
def upload_profile_avatar():
    """Instant AJAX avatar uploader for profile workspace or admin desk."""
    avatar_file = request.files.get("avatar")
    if not avatar_file or not avatar_file.filename:
        return jsonify({"success": False, "error": "No image file provided."}), 400

    profile_id = request.form.get("profile_id")
    if current_user.role == "profile_user":
        if not current_user.profile_id:
            return jsonify({"success": False, "error": "No profile assigned."}), 403
        profile = PortfolioProfile.query.get_or_404(current_user.profile_id)
    else:
        if profile_id:
            profile = PortfolioProfile.query.get_or_404(profile_id)
        else:
            profile = PortfolioProfile.query.filter_by(is_active=True).first() or PortfolioProfile.query.first()
            if not profile:
                return jsonify({"success": False, "error": "No profile found."}), 404

    success, res = save_upload_file(avatar_file, subfolder="profile", allowed_types="image")
    if not success:
        return jsonify({"success": False, "error": res}), 400

    data = profile.get_data()
    if "settings" not in data:
        data["settings"] = {}

    old_avatar = data["settings"].get("avatar_url")
    if old_avatar and old_avatar.startswith("/uploads/"):
        delete_file(old_avatar)

    data["settings"]["avatar_url"] = res
    profile.set_data(data)
    profile.updated_at = datetime.utcnow()

    if profile.is_active:
        site_settings = SiteSetting.get_settings()
        site_settings.avatar_url = res

    db.session.commit()

    return jsonify({
        "success": True,
        "avatar_url": res,
        "message": "Profile picture updated and applied live!"
    })

@profiles_bp.route("/my-profile", methods=["GET", "POST"])
@login_required
def my_profile():
    """Scoped workspace for a profile user to view and edit their own portfolio."""
    if current_user.role == "profile_user":
        if not current_user.profile_id:
            flash("No portfolio profile assigned to this account. Please contact the administrator.", "danger")
            return redirect(url_for("auth.logout"))
        profile = PortfolioProfile.query.get_or_404(current_user.profile_id)
    else:
        # Superadmin viewing workspace
        profile = PortfolioProfile.query.filter_by(is_active=True).first() or PortfolioProfile.query.first()
        if not profile:
            return redirect(url_for("admin_profiles.index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        client_name = request.form.get("client_name", "").strip()
        description = request.form.get("description", "").strip()
        theme_preset = request.form.get("theme_preset", profile.theme_preset).strip()
        job_title = request.form.get("job_title", "").strip()
        location = request.form.get("location", "").strip()
        contact_email = request.form.get("contact_email", "").strip()
        hero_bio = request.form.get("hero_bio", "").strip()

        if name:
            profile.name = name
        profile.client_name = client_name
        profile.description = description
        profile.theme_preset = theme_preset
        profile.updated_at = datetime.utcnow()

        # Update snapshot data
        data = profile.get_data()
        if "settings" not in data:
            data["settings"] = {}

        display = client_name or name
        if display:
            data["settings"]["display_name"] = display
        data["settings"]["default_theme"] = theme_preset
        if job_title:
            data["settings"]["job_title"] = job_title
        if location:
            data["settings"]["location"] = location
        if contact_email:
            data["settings"]["contact_email"] = contact_email
        if hero_bio:
            data["settings"]["hero_bio"] = hero_bio

        # Check avatar file upload or direct URL
        avatar_file = request.files.get("avatar")
        avatar_url_text = request.form.get("avatar_url_text", "").strip()
        new_avatar = None
        if avatar_file and avatar_file.filename:
            success, res = save_upload_file(avatar_file, subfolder="profile", allowed_types="image")
            if success:
                new_avatar = res
            else:
                flash(f"Avatar upload notice: {res}", "warning")
        elif avatar_url_text:
            new_avatar = avatar_url_text

        if new_avatar:
            data["settings"]["avatar_url"] = new_avatar

        # Check password change
        new_pw = request.form.get("new_password", "").strip()
        if new_pw:
            current_user.set_password(new_pw)
            flash("Your login password has been updated.", "info")

        profile.set_data(data)

        # If this profile is active on root website, sync live SiteSetting as well
        if profile.is_active:
            site_settings = SiteSetting.get_settings()
            if display:
                site_settings.display_name = display
            site_settings.default_theme = theme_preset
            if job_title:
                site_settings.job_title = job_title
            if location:
                site_settings.location = location
            if contact_email:
                site_settings.contact_email = contact_email
            if hero_bio:
                site_settings.hero_bio = hero_bio
            if new_avatar:
                site_settings.avatar_url = new_avatar

        db.session.commit()
        flash(f"Your profile '{profile.name}' was successfully updated!", "success")
        return redirect(url_for("admin_profiles.my_profile"))

    data = profile.get_data()
    settings_dict = data.get("settings", {})
    return render_template("admin/profiles/workspace.html", profile=profile, settings_dict=settings_dict)

@profiles_bp.route("/<int:profile_id>/activate", methods=["POST"])
@login_required
def activate(profile_id):
    success, message = switch_active_profile(profile_id)
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")
    return redirect(url_for("admin_profiles.index"))

@profiles_bp.route("/<int:profile_id>/toggle-status", methods=["POST"])
@login_required
def toggle_status(profile_id):
    profile = PortfolioProfile.query.get_or_404(profile_id)
    profile.is_published = not profile.is_published
    profile.updated_at = datetime.utcnow()
    db.session.commit()
    status_label = "ONLINE & LIVE" if profile.is_published else "OFFLINE (DRAFT)"
    flash(f"Profile '{profile.name}' is now {status_label}.", "success" if profile.is_published else "info")
    return redirect(url_for("admin_profiles.index"))

@profiles_bp.route("/<int:profile_id>/save-current", methods=["POST"])
@login_required
def save_current(profile_id):
    profile = PortfolioProfile.query.get_or_404(profile_id)
    current_data = capture_current_portfolio_dict()
    profile.set_data(current_data)
    profile.updated_at = datetime.utcnow()
    db.session.commit()

    flash(f"Current live website state successfully saved to snapshot slot for '{profile.name}'!", "success")
    return redirect(url_for("admin_profiles.index"))

@profiles_bp.route("/<int:profile_id>/edit", methods=["POST"])
@login_required
def edit(profile_id):
    profile = PortfolioProfile.query.get_or_404(profile_id)
    name = request.form.get("name", "").strip()
    client_name = request.form.get("client_name", "").strip()
    slug_raw = request.form.get("slug", "").strip()
    description = request.form.get("description", "").strip()
    theme_preset = request.form.get("theme_preset", profile.theme_preset).strip()
    if "submitted_from_form" in request.form:
        is_published = bool(request.form.get("is_published") in ("1", "true", "True", True))
    else:
        is_published = request.form.get("is_published", "1" if profile.is_published else "0") in ("1", "true", "True", True)

    if not name:
        flash("Profile Name cannot be empty.", "danger")
        return redirect(url_for("admin_profiles.index"))

    slug = get_unique_slug(slugify(slug_raw if slug_raw else name), exclude_id=profile.id)

    profile.name = name
    profile.client_name = client_name
    profile.slug = slug
    profile.description = description
    profile.theme_preset = theme_preset
    profile.is_published = is_published
    profile.updated_at = datetime.utcnow()

    # Also update theme, display name & avatar in internal snapshot settings
    data = profile.get_data()
    if "settings" not in data:
        data["settings"] = {}

    avatar_file = request.files.get("avatar")
    avatar_url_text = request.form.get("avatar_url_text", "").strip()
    new_avatar = None
    if avatar_file and avatar_file.filename:
        success, res = save_upload_file(avatar_file, subfolder="profile", allowed_types="image")
        if success:
            new_avatar = res
        else:
            flash(f"Avatar upload notice: {res}", "warning")
    elif avatar_url_text:
        new_avatar = avatar_url_text

    if new_avatar:
        data["settings"]["avatar_url"] = new_avatar

    data["settings"]["default_theme"] = theme_preset
    display = client_name or name
    if display:
        data["settings"]["display_name"] = display
    profile.set_data(data)

    # If this profile is currently active on the main website, immediately apply to live SiteSetting
    if profile.is_active:
        site_settings = SiteSetting.get_settings()
        if new_avatar:
            site_settings.avatar_url = new_avatar
        display = client_name or name
        if display:
            site_settings.display_name = display
            user = User.query.first()
            if user:
                user.display_name = display
        if theme_preset:
            site_settings.default_theme = theme_preset

    db.session.commit()
    flash(f"Profile '{profile.name}' settings updated successfully.", "success")
    return redirect(url_for("admin_profiles.index"))

@profiles_bp.route("/<int:profile_id>/delete", methods=["POST"])
@login_required
def delete(profile_id):
    profile = PortfolioProfile.query.get_or_404(profile_id)
    if profile.is_active:
        flash("Cannot delete the currently active portfolio profile. Please switch to another profile first.", "warning")
        return redirect(url_for("admin_profiles.index"))

    name = profile.name
    db.session.delete(profile)
    db.session.commit()

    flash(f"Portfolio profile '{name}' deleted.", "info")
    return redirect(url_for("admin_profiles.index"))

@profiles_bp.route("/<int:profile_id>/export")
@login_required
def export(profile_id):
    profile = PortfolioProfile.query.get_or_404(profile_id)
    export_payload = {
        "metadata": {
            "app": "LYRCH Digital Command Center",
            "version": "1.0",
            "type": "portfolio_profile_export",
            "exported_at": datetime.utcnow().isoformat(),
        },
        "profile": {
            "name": profile.name,
            "slug": profile.slug,
            "client_name": profile.client_name,
            "description": profile.description,
            "theme_preset": profile.theme_preset,
            "is_published": profile.is_published,
        },
        "content": profile.get_data()
    }
    json_str = json.dumps(export_payload, indent=2, default=str)
    filename = f"portfolio_{profile.slug}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    
    response = Response(json_str, mimetype="application/json")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response

@profiles_bp.route("/import", methods=["POST"])
@login_required
def import_profile():
    file = request.files.get("profile_file")
    if not file or not file.filename:
        flash("Please choose a valid JSON profile file to import.", "warning")
        return redirect(url_for("admin_profiles.index"))

    try:
        content_dict = json.load(file)
        if "content" in content_dict:
            # Standalone profile export format
            prof_meta = content_dict.get("profile", {})
            name = prof_meta.get("name", "Imported Portfolio")
            client_name = prof_meta.get("client_name", "")
            description = prof_meta.get("description", "Imported from JSON")
            theme_preset = prof_meta.get("theme_preset", "cyber")
            is_published = prof_meta.get("is_published", True)
            data = content_dict.get("content", {})
        elif "tables" in content_dict:
            # Full database backup format
            name = "Imported Backup Profile"
            client_name = ""
            description = "Imported from full database backup archive"
            theme_preset = "cyber"
            is_published = True
            # Format into portfolio dict
            tables = content_dict.get("tables", {})
            data = {
                "settings": tables.get("site_settings", [{}])[0] if tables.get("site_settings") else {},
                "categories": tables.get("categories", []),
                "projects": tables.get("projects", []),
                "videos": tables.get("videos", []),
                "gallery": tables.get("gallery", []),
                "documents": tables.get("documents", []),
                "skills": tables.get("skills", []),
                "experiences": tables.get("experiences", []),
                "blog_posts": tables.get("blog_posts", []),
            }
        else:
            flash("Unrecognized file format. Please upload a valid LYRCH portfolio JSON export.", "danger")
            return redirect(url_for("admin_profiles.index"))

        slug = get_unique_slug(slugify(name))
        new_profile = PortfolioProfile(
            name=name,
            slug=slug,
            client_name=client_name,
            description=description,
            theme_preset=theme_preset,
            is_active=False,
            is_published=is_published
        )
        new_profile.set_data(data)
        db.session.add(new_profile)
        db.session.commit()

        flash(f"Profile '{name}' successfully imported! Dedicated link: /p/{slug}", "success")
    except Exception as e:
        flash(f"Failed to import profile: {str(e)}", "danger")

    return redirect(url_for("admin_profiles.index"))

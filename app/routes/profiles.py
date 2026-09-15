import json
import re
from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, Response, jsonify
from flask_login import login_required
from app.models import db, PortfolioProfile, ActivityLog, SiteSetting
from app.services.profile_service import (
    capture_current_portfolio_dict,
    apply_portfolio_dict_to_database,
    get_starter_template_data,
    switch_active_profile,
    bootstrap_default_profile_if_needed
)

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

    flash(f"Profile '{name}' created! Dedicated public URL: /p/{slug}", "success")
    return redirect(url_for("admin_profiles.index"))

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

    # Also update theme in internal snapshot settings
    data = profile.get_data()
    if "settings" in data:
        data["settings"]["default_theme"] = theme_preset
        if client_name:
            data["settings"]["display_name"] = client_name
        profile.set_data(data)

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

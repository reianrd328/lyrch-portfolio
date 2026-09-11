from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.models import db, Project, ActivityLog
from app.services.upload_service import save_upload_file, delete_file
import re

projects_bp = Blueprint("admin_projects", __name__)

def slugify(text):
    text = text.lower().strip()
    return re.sub(r'[\s\W-]+', '-', text)

@projects_bp.route("/")
@login_required
def index():
    projects = Project.query.order_by(Project.order_index.asc(), Project.id.desc()).all()
    return render_template("admin/projects/index.html", projects=projects)

@projects_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("Project title is required", "danger")
            return redirect(request.url)

        slug = slugify(title)
        # Check collision
        existing = Project.query.filter_by(slug=slug).first()
        if existing:
            slug = f"{slug}-{Project.query.count() + 1}"

        subtitle = request.form.get("subtitle")
        category = request.form.get("category", "Software Project")
        status_badge = request.form.get("status_badge", "Live")
        featured = bool(request.form.get("featured"))
        visibility = request.form.get("visibility", "published")
        technologies = request.form.get("technologies", "")
        short_description = request.form.get("short_description")
        full_description = request.form.get("full_description")
        github_url = request.form.get("github_url")
        demo_url = request.form.get("demo_url")

        # Thumbnail upload
        thumbnail_file = request.files.get("thumbnail")
        thumbnail_url = None
        if thumbnail_file and thumbnail_file.filename:
            success, res = save_upload_file(thumbnail_file, subfolder="projects", allowed_types="image")
            if success:
                thumbnail_url = res

        project = Project(
            title=title,
            slug=slug,
            subtitle=subtitle,
            category=category,
            status_badge=status_badge,
            featured=featured,
            visibility=visibility,
            technologies=technologies,
            short_description=short_description,
            full_description=full_description,
            github_url=github_url,
            demo_url=demo_url,
            thumbnail_url=thumbnail_url
        )
        db.session.add(project)

        # Log activity
        log = ActivityLog(
            title=f"Created project: {title}",
            activity_type="project",
            time_label="Just now"
        )
        db.session.add(log)
        db.session.commit()

        flash(f"Project '{title}' has been successfully created!", "success")
        return redirect(url_for("admin_projects.index"))

    return render_template("admin/projects/create.html")

@projects_bp.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit(id):
    project = Project.query.get_or_404(id)

    if request.method == "POST":
        project.title = request.form.get("title", project.title).strip()
        project.subtitle = request.form.get("subtitle", project.subtitle)
        project.category = request.form.get("category", project.category)
        project.status_badge = request.form.get("status_badge", project.status_badge)
        project.featured = bool(request.form.get("featured"))
        project.visibility = request.form.get("visibility", project.visibility)
        project.technologies = request.form.get("technologies", project.technologies)
        project.short_description = request.form.get("short_description", project.short_description)
        project.full_description = request.form.get("full_description", project.full_description)
        project.github_url = request.form.get("github_url", project.github_url)
        project.demo_url = request.form.get("demo_url", project.demo_url)

        # Thumbnail update
        thumbnail_file = request.files.get("thumbnail")
        if thumbnail_file and thumbnail_file.filename:
            success, res = save_upload_file(thumbnail_file, subfolder="projects", allowed_types="image")
            if success:
                if project.thumbnail_url:
                    delete_file(project.thumbnail_url)
                project.thumbnail_url = res

        db.session.commit()
        flash(f"Project '{project.title}' updated successfully.", "success")
        return redirect(url_for("admin_projects.index"))

    return render_template("admin/projects/edit.html", project=project)

@projects_bp.route("/delete/<int:id>", methods=["POST"])
@login_required
def delete(id):
    project = Project.query.get_or_404(id)
    if project.thumbnail_url:
        delete_file(project.thumbnail_url)
    title = project.title
    db.session.delete(project)
    db.session.commit()
    flash(f"Project '{title}' deleted.", "info")
    return redirect(url_for("admin_projects.index"))


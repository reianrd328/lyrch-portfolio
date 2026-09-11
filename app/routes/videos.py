from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.models import db, Video, ActivityLog
from app.services.upload_service import save_upload_file, delete_file
import re

videos_bp = Blueprint("admin_videos", __name__)

def slugify(text):
    text = text.lower().strip()
    return re.sub(r'[\s\W-]+', '-', text)

@videos_bp.route("/")
@login_required
def index():
    videos = Video.query.order_by(Video.id.desc()).all()
    return render_template("admin/videos/index.html", videos=videos)

@videos_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("Video title is required", "danger")
            return redirect(request.url)

        slug = slugify(title)
        existing = Video.query.filter_by(slug=slug).first()
        if existing:
            slug = f"{slug}-{Video.query.count() + 1}"

        category = request.form.get("category", "AI Creative")
        tools_used = request.form.get("tools_used", "Gemini, Video Edit")
        platforms = request.form.get("platforms", "Facebook Reels, TikTok")
        duration = request.form.get("duration", "00:10")
        aspect_ratio = request.form.get("aspect_ratio", "9:16")
        prompt_text = request.form.get("prompt_text")
        workflow_notes = request.form.get("workflow_notes")
        description = request.form.get("description")
        featured = bool(request.form.get("featured"))
        visibility = request.form.get("visibility", "published")

        # Media files
        thumbnail_file = request.files.get("thumbnail")
        thumbnail_url = None
        if thumbnail_file and thumbnail_file.filename:
            success, res = save_upload_file(thumbnail_file, subfolder="videos", allowed_types="image")
            if success:
                thumbnail_url = res

        video_file = request.files.get("video")
        video_url = None
        if video_file and video_file.filename:
            success, res = save_upload_file(video_file, subfolder="videos", allowed_types="video")
            if success:
                video_url = res
        elif request.form.get("video_external_url"):
            video_url = request.form.get("video_external_url")

        video = Video(
            title=title,
            slug=slug,
            category=category,
            tools_used=tools_used,
            platforms=platforms,
            duration=duration,
            aspect_ratio=aspect_ratio,
            prompt_text=prompt_text,
            workflow_notes=workflow_notes,
            description=description,
            featured=featured,
            visibility=visibility,
            thumbnail_url=thumbnail_url,
            video_url=video_url
        )
        db.session.add(video)

        log = ActivityLog(
            title=f"Published AI Video: {title}",
            activity_type="video",
            time_label="Just now"
        )
        db.session.add(log)
        db.session.commit()

        flash(f"AI Video '{title}' created successfully!", "success")
        return redirect(url_for("admin_videos.index"))

    return render_template("admin/videos/create.html")

@videos_bp.route("/delete/<int:id>", methods=["POST"])
@login_required
def delete(id):
    video = Video.query.get_or_404(id)
    if video.thumbnail_url:
        delete_file(video.thumbnail_url)
    if video.video_url and video.video_url.startswith("/uploads/"):
        delete_file(video.video_url)
    title = video.title
    db.session.delete(video)
    db.session.commit()
    flash(f"Video '{title}' removed.", "info")
    return redirect(url_for("admin_videos.index"))


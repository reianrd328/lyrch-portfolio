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
    selected_album = request.args.get("album", "").strip()
    active_tab = request.args.get("tab", "all").strip()
    all_videos = Video.query.order_by(Video.id.desc()).all()
    
    albums = sorted(list({v.album for v in all_videos if v.album}))
    
    # Calculate stats for each album
    album_stats = []
    for alb in albums:
        alb_videos = [v for v in all_videos if v.album == alb]
        cover_thumb = next((v.thumbnail_url for v in alb_videos if v.thumbnail_url), None)
        tools = sorted(list({t for v in alb_videos for t in v.tools_list}))
        pub_count = sum(1 for v in alb_videos if v.visibility == "published")
        if pub_count == len(alb_videos):
            status_badge = "Published"
            status_class = "live"
        elif pub_count == 0:
            status_badge = "Draft"
            status_class = "draft"
        else:
            status_badge = f"{pub_count}/{len(alb_videos)} Published"
            status_class = "live"

        album_stats.append({
            "name": alb,
            "count": len(alb_videos),
            "cover_url": cover_thumb,
            "tools_label": ", ".join(tools[:2]) if tools else "AI Studio",
            "status_badge": status_badge,
            "status_class": status_class,
            "latest_video": alb_videos[0] if alb_videos else None
        })

    standalone_videos = [v for v in all_videos if not v.album]
    draft_videos = [v for v in all_videos if v.visibility == "draft"]
    
    # Filter videos if an album is selected
    if selected_album:
        if selected_album == "__standalone__":
            videos = standalone_videos
        else:
            videos = [v for v in all_videos if v.album == selected_album]
    elif active_tab == "drafts":
        videos = draft_videos
    elif active_tab == "standalone":
        videos = standalone_videos
    else:
        videos = all_videos

    return render_template(
        "admin/videos/index.html",
        videos=videos,
        albums=albums,
        album_stats=album_stats,
        standalone_videos=standalone_videos,
        standalone_count=len(standalone_videos),
        drafts_count=len(draft_videos),
        total_videos_count=len(all_videos),
        selected_album=selected_album,
        active_tab=active_tab
    )

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

        album_select = request.form.get("album_select", "").strip()
        album_custom = request.form.get("album_custom", "").strip()
        album_raw = request.form.get("album", "").strip()

        if album_select == "__new__":
            album = album_custom or None
        elif album_select:
            album = album_select
        else:
            album = album_custom or album_raw or None

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
            album=album,
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
            title=f"Published AI Video: {title}" + (f" (Album: {album})" if album else ""),
            activity_type="video",
            time_label="Just now"
        )
        db.session.add(log)
        db.session.commit()

        flash(f"AI Video '{title}' created successfully!", "success")
        return redirect(url_for("admin_videos.index"))

    preselected_album = request.args.get("album", "").strip()
    existing_albums = sorted(list({v.album for v in Video.query.all() if v.album}))
    return render_template("admin/videos/create.html", existing_albums=existing_albums, preselected_album=preselected_album)

@videos_bp.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit(id):
    video = Video.query.get_or_404(id)
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("Video title is required", "danger")
            return redirect(request.url)

        video.title = title
        album_select = request.form.get("album_select", "").strip()
        album_custom = request.form.get("album_custom", "").strip()
        album_raw = request.form.get("album", "").strip()

        if album_select == "__new__":
            album = album_custom or None
        elif album_select:
            album = album_select
        else:
            album = album_custom or album_raw or None

        video.album = album
        video.category = request.form.get("category", "AI Creative")
        video.tools_used = request.form.get("tools_used", "Gemini, Video Edit")
        video.platforms = request.form.get("platforms", "Facebook Reels, TikTok")
        video.duration = request.form.get("duration", "00:10")
        video.aspect_ratio = request.form.get("aspect_ratio", "9:16")
        video.prompt_text = request.form.get("prompt_text")
        video.workflow_notes = request.form.get("workflow_notes")
        video.description = request.form.get("description")
        video.featured = bool(request.form.get("featured"))
        video.visibility = request.form.get("visibility", "published")

        thumbnail_file = request.files.get("thumbnail")
        if thumbnail_file and thumbnail_file.filename:
            success, res = save_upload_file(thumbnail_file, subfolder="videos", allowed_types="image")
            if success:
                if video.thumbnail_url:
                    delete_file(video.thumbnail_url)
                video.thumbnail_url = res

        video_file = request.files.get("video")
        if video_file and video_file.filename:
            success, res = save_upload_file(video_file, subfolder="videos", allowed_types="video")
            if success:
                if video.video_url and video.video_url.startswith("/uploads/"):
                    delete_file(video.video_url)
                video.video_url = res
        elif request.form.get("video_external_url"):
            video.video_url = request.form.get("video_external_url")

        db.session.commit()
        flash(f"AI Video '{video.title}' updated successfully!", "success")
        return redirect(url_for("admin_videos.index"))

    existing_albums = sorted(list({v.album for v in Video.query.all() if v.album}))
    return render_template("admin/videos/edit.html", video=video, existing_albums=existing_albums)

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


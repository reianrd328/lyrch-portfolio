from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, abort
from flask_login import login_required, current_user
from app.models import db, Video, ActivityLog, PortfolioProfile
from app.services.upload_service import save_upload_file, delete_file
import re
from pathlib import Path

videos_bp = Blueprint("admin_videos", __name__)

def sync_profile_videos_json(profile_id):
    """Keep portfolio_profile.data_json['videos'] in sync with SQL video entries."""
    if not profile_id:
        return
    try:
        profile = db.session.get(PortfolioProfile, profile_id)
        if not profile:
            return
        videos = Video.query.filter_by(profile_id=profile_id).order_by(Video.id.desc()).all()
        data = profile.get_data()
        data["videos"] = [v.to_dict() for v in videos]
        profile.set_data(data)
        db.session.commit()
    except Exception as e:
        current_app.logger.warning(f"Error syncing profile videos JSON: {e}")

def slugify(text):
    text = text.lower().strip()
    return re.sub(r'[\s\W-]+', '-', text)

@videos_bp.route("/")
@login_required
def index():
    selected_album = request.args.get("album", "").strip()
    active_tab = request.args.get("tab", "all").strip()
    selected_profile_raw = request.args.get("profile_id", "").strip()

    is_profile_user = (getattr(current_user, "role", "") == "profile_user")
    all_profiles = PortfolioProfile.query.order_by(PortfolioProfile.is_active.desc(), PortfolioProfile.name.asc()).all()
    active_profile = PortfolioProfile.query.filter_by(is_active=True).first()

    if is_profile_user:
        target_profile_id = current_user.profile_id
        scoped_profile = PortfolioProfile.query.get(target_profile_id) if target_profile_id else None
        selected_profile = str(target_profile_id) if target_profile_id else ""
    else:
        if selected_profile_raw and selected_profile_raw.isdigit():
            target_profile_id = int(selected_profile_raw)
            scoped_profile = PortfolioProfile.query.get(target_profile_id)
            selected_profile = str(target_profile_id)
        elif selected_profile_raw == "all":
            target_profile_id = None
            scoped_profile = None
            selected_profile = "all"
        else:
            target_profile_id = None
            scoped_profile = None
            selected_profile = "all"

    if target_profile_id:
        all_videos = Video.query.filter(Video.profile_id == target_profile_id).order_by(Video.id.desc()).all()
    else:
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
        active_tab=active_tab,
        all_profiles=all_profiles,
        scoped_profile=scoped_profile,
        selected_profile=selected_profile,
        is_profile_user=is_profile_user,
        active_profile=active_profile
    )

@videos_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    is_profile_user = (getattr(current_user, "role", "") == "profile_user")
    all_profiles = PortfolioProfile.query.order_by(PortfolioProfile.is_active.desc(), PortfolioProfile.name.asc()).all()
    active_profile = PortfolioProfile.query.filter_by(is_active=True).first()

    if request.method == "POST":
        title = request.form.get("title", "").strip()

        # Profile ID scoping
        if is_profile_user:
            target_profile_id = current_user.profile_id
        else:
            profile_id_raw = (request.form.get("profile_id", "") or request.args.get("profile_id", "")).strip()
            if profile_id_raw and profile_id_raw.isdigit():
                target_profile_id = int(profile_id_raw)
            else:
                target_profile_id = active_profile.id if active_profile else None

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

        # Media files - Thumbnail if provided
        thumbnail_file = request.files.get("thumbnail")
        thumbnail_url = None
        if thumbnail_file and thumbnail_file.filename:
            success, res = save_upload_file(thumbnail_file, subfolder="videos", allowed_types="image")
            if success:
                thumbnail_url = res

        # Collect uploaded video files (supports 'videos' and 'video', single or multiple)
        raw_video_files = request.files.getlist("videos")
        if not raw_video_files or (len(raw_video_files) == 1 and not raw_video_files[0].filename):
            raw_video_files = request.files.getlist("video")

        valid_video_files = [f for f in raw_video_files if f and f.filename]
        external_url = request.form.get("video_external_url", "").strip()

        if not valid_video_files and not external_url and not title:
            flash("Please enter a video title, upload video file(s), or provide an external video URL.", "danger")
            return redirect(request.url)

        created_videos = []
        failed_files = []

        if valid_video_files:
            total_files = len(valid_video_files)
            for idx, vf in enumerate(valid_video_files):
                success, res = save_upload_file(vf, subfolder="videos", allowed_types="video")
                if not success:
                    failed_files.append((vf.filename, res))
                    continue

                # Smart titling:
                # 1. Title given: "Title" (if 1 file) or "Title - Part 1", "Title - Part 2", ...
                # 2. No title: clean formatted filename (e.g. "cyberpunk_scene_01.mp4" -> "Cyberpunk Scene 01")
                if title:
                    vid_title = title if total_files == 1 else f"{title} - Part {idx + 1}"
                else:
                    stem = Path(vf.filename).stem
                    clean_name = re.sub(r'[\-_]+', ' ', stem).strip()
                    vid_title = clean_name.title() if clean_name else f"Video {idx + 1}"

                base_slug = slugify(vid_title)
                slug = base_slug
                counter = 1
                while Video.query.filter_by(slug=slug).first():
                    slug = f"{base_slug}-{counter}"
                    counter += 1

                video = Video(
                    title=vid_title,
                    slug=slug,
                    album=album,
                    profile_id=target_profile_id,
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
                    video_url=res
                )
                db.session.add(video)
                created_videos.append(video)
        else:
            # Fallback for external URL only
            vid_title = title or "AI Creative Video"
            base_slug = slugify(vid_title)
            slug = base_slug
            counter = 1
            while Video.query.filter_by(slug=slug).first():
                slug = f"{base_slug}-{counter}"
                counter += 1

            video = Video(
                title=vid_title,
                slug=slug,
                album=album,
                profile_id=target_profile_id,
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
                video_url=external_url
            )
            db.session.add(video)
            created_videos.append(video)

        if not created_videos and failed_files:
            err_msg = ", ".join([f"{fn}: {err}" for fn, err in failed_files])
            flash(f"Video upload failed: {err_msg}", "danger")
            return redirect(request.url)

        db.session.commit()

        if target_profile_id:
            sync_profile_videos_json(target_profile_id)

        if len(created_videos) == 1:
            log_title = f"Published AI Video: {created_videos[0].title}" + (f" (Album: {album})" if album else "")
            flash_msg = f"AI Video '{created_videos[0].title}' created successfully!"
        else:
            log_title = f"Batch uploaded {len(created_videos)} AI Videos" + (f" (Album: {album})" if album else "")
            flash_msg = f"Successfully uploaded {len(created_videos)} AI videos" + (f" to album '{album}'" if album else "") + "!"

        log = ActivityLog(
            title=log_title,
            activity_type="video",
            time_label="Just now"
        )
        db.session.add(log)
        db.session.commit()

        flash(flash_msg, "success")
        if failed_files:
            flash(f"Note: {len(failed_files)} file(s) could not be uploaded due to invalid formats.", "warning")

        if album:
            return redirect(url_for("admin_videos.index", album=album))
        return redirect(url_for("admin_videos.index"))

    preselected_album = request.args.get("album", "").strip()
    selected_profile_raw = request.args.get("profile_id", "").strip()
    target_profile_id = current_user.profile_id if is_profile_user else (int(selected_profile_raw) if selected_profile_raw.isdigit() else (active_profile.id if active_profile else None))

    albums_query = Video.query
    if target_profile_id:
        albums_query = albums_query.filter(Video.profile_id == target_profile_id)
    existing_albums = sorted(list({v.album for v in albums_query.all() if v.album}))

    return render_template(
        "admin/videos/create.html",
        existing_albums=existing_albums,
        preselected_album=preselected_album,
        all_profiles=all_profiles,
        target_profile_id=target_profile_id,
        is_profile_user=is_profile_user
    )

@videos_bp.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit(id):
    video = Video.query.get_or_404(id)
    is_profile_user = (getattr(current_user, "role", "") == "profile_user")
    all_profiles = PortfolioProfile.query.order_by(PortfolioProfile.is_active.desc(), PortfolioProfile.name.asc()).all()

    if is_profile_user and video.profile_id != current_user.profile_id:
        abort(403)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("Video title is required", "danger")
            return redirect(request.url)

        old_profile_id = video.profile_id
        if not is_profile_user:
            profile_id_raw = request.form.get("profile_id", "").strip()
            if profile_id_raw and profile_id_raw.isdigit():
                video.profile_id = int(profile_id_raw)
            elif profile_id_raw == "":
                video.profile_id = None

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

        old_thumb = video.thumbnail_url
        old_vid = video.video_url

        thumbnail_file = request.files.get("thumbnail")
        if thumbnail_file and thumbnail_file.filename:
            success, res = save_upload_file(thumbnail_file, subfolder="videos", allowed_types="image")
            if success:
                video.thumbnail_url = res

        video_file = request.files.get("video")
        if video_file and video_file.filename:
            success, res = save_upload_file(video_file, subfolder="videos", allowed_types="video")
            if success:
                video.video_url = res
        elif request.form.get("video_external_url"):
            video.video_url = request.form.get("video_external_url")

        db.session.commit()

        if old_thumb and old_thumb != video.thumbnail_url:
            delete_file(old_thumb)
        if old_vid and old_vid != video.video_url and old_vid.startswith("/uploads/"):
            delete_file(old_vid)

        if video.profile_id:
            sync_profile_videos_json(video.profile_id)
        if old_profile_id and old_profile_id != video.profile_id:
            sync_profile_videos_json(old_profile_id)

        flash(f"AI Video '{video.title}' updated successfully!", "success")
        return redirect(url_for("admin_videos.index"))

    albums_query = Video.query
    if video.profile_id:
        albums_query = albums_query.filter(Video.profile_id == video.profile_id)
    existing_albums = sorted(list({v.album for v in albums_query.all() if v.album}))

    return render_template(
        "admin/videos/edit.html",
        video=video,
        existing_albums=existing_albums,
        all_profiles=all_profiles,
        is_profile_user=is_profile_user
    )

@videos_bp.route("/delete/<int:id>", methods=["POST"])
@login_required
def delete(id):
    video = Video.query.get_or_404(id)
    is_profile_user = (getattr(current_user, "role", "") == "profile_user")
    if is_profile_user and video.profile_id != current_user.profile_id:
        abort(403)

    target_profile_id = video.profile_id
    thumb_to_delete = video.thumbnail_url
    vid_to_delete = video.video_url
    title = video.title

    db.session.delete(video)
    db.session.commit()

    if thumb_to_delete:
        delete_file(thumb_to_delete)
    if vid_to_delete and vid_to_delete.startswith("/uploads/"):
        delete_file(vid_to_delete)

    if target_profile_id:
        sync_profile_videos_json(target_profile_id)

    flash(f"Video '{title}' removed.", "info")
    return redirect(url_for("admin_videos.index"))


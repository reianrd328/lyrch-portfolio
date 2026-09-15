import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required
from app.models import db, GalleryItem, Project
from app.services.upload_service import save_upload_file, delete_file

gallery_bp = Blueprint("admin_gallery", __name__)

@gallery_bp.route("/")
@login_required
def index():
    query_text = request.args.get("q", "").strip()
    selected_cat = request.args.get("cat", "All").strip()
    selected_project = request.args.get("project_id", "").strip()
    selected_status = request.args.get("status", "all").strip()
    sort_by = request.args.get("sort", "newest").strip()

    all_items = GalleryItem.query.all()
    projects = Project.query.order_by(Project.title.asc()).all()

    # Telemetry Stats
    total_assets = len(all_items)
    ui_projects_count = sum(1 for i in all_items if i.category == "UI / UX" or i.project_id)
    screenshots_count = sum(1 for i in all_items if i.category == "Screenshots")
    graphics_count = sum(1 for i in all_items if i.category in ("Graphics", "Branding"))
    drafts_count = sum(1 for i in all_items if i.visibility == "draft")

    # Base query for filtered results
    query = GalleryItem.query

    # Search filter
    if query_text:
        search_pattern = f"%{query_text}%"
        query = query.filter(
            (GalleryItem.title.ilike(search_pattern)) |
            (GalleryItem.tags.ilike(search_pattern)) |
            (GalleryItem.description.ilike(search_pattern))
        )

    # Category filter
    if selected_cat and selected_cat != "All":
        if selected_cat == "Projects":
            query = query.filter(GalleryItem.project_id.isnot(None))
        else:
            query = query.filter(GalleryItem.category == selected_cat)

    # Project filter
    if selected_project and selected_project.isdigit():
        query = query.filter(GalleryItem.project_id == int(selected_project))

    # Status filter
    if selected_status and selected_status != "all":
        query = query.filter(GalleryItem.visibility == selected_status)

    # Sort
    if sort_by == "oldest":
        query = query.order_by(GalleryItem.id.asc())
    elif sort_by == "title_asc":
        query = query.order_by(GalleryItem.title.asc())
    elif sort_by == "title_desc":
        query = query.order_by(GalleryItem.title.desc())
    else:
        query = query.order_by(GalleryItem.id.desc())

    items = query.all()

    return render_template(
        "admin/gallery/index.html",
        items=items,
        projects=projects,
        total_assets=total_assets,
        ui_projects_count=ui_projects_count,
        screenshots_count=screenshots_count,
        graphics_count=graphics_count,
        drafts_count=drafts_count,
        query_text=query_text,
        selected_cat=selected_cat,
        selected_project=selected_project,
        selected_status=selected_status,
        sort_by=sort_by
    )

@gallery_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "UI / UX")
        project_id_raw = request.form.get("project_id", "").strip()
        project_id = int(project_id_raw) if project_id_raw and project_id_raw.isdigit() else None
        description = request.form.get("description", "").strip()
        tags = request.form.get("tags", "").strip()
        visibility = request.form.get("visibility", "published").strip()
        featured = bool(request.form.get("featured"))

        img_file = request.files.get("image")
        if not img_file or not img_file.filename:
            if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "error": "Image file is required"}), 400
            flash("Image file is required", "danger")
            return redirect(request.url)

        success, res = save_upload_file(img_file, subfolder="gallery", allowed_types="image")
        if not success:
            if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "error": res}), 400
            flash(f"Upload failed: {res}", "danger")
            return redirect(request.url)

        # File size calculation
        file_size_bytes = 0
        try:
            full_path = os.path.join(current_app.config["UPLOAD_FOLDER"], "gallery", os.path.basename(res))
            if os.path.exists(full_path):
                file_size_bytes = os.path.getsize(full_path)
        except Exception:
            pass

        item = GalleryItem(
            title=title or "Creative Asset",
            category=category,
            project_id=project_id,
            description=description,
            tags=tags,
            visibility=visibility,
            featured=featured,
            image_url=res,
            file_size_bytes=file_size_bytes
        )
        db.session.add(item)
        db.session.commit()

        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": True, "item": item.to_dict()})

        flash(f"Creative asset '{item.title}' uploaded successfully!", "success")
        return redirect(url_for("admin_gallery.index"))

    projects = Project.query.order_by(Project.title.asc()).all()
    return render_template("admin/gallery/create.html", projects=projects)

@gallery_bp.route("/api/item/<int:id>", methods=["GET"])
@login_required
def api_item(id):
    item = GalleryItem.query.get_or_404(id)
    return jsonify({"success": True, "item": item.to_dict()})

@gallery_bp.route("/edit/<int:id>", methods=["POST"])
@login_required
def edit(id):
    item = GalleryItem.query.get_or_404(id)

    # Handle form or JSON body
    if request.is_json:
        data = request.get_json() or {}
        title = data.get("title", "").strip()
        category = data.get("category", item.category)
        project_id = data.get("project_id")
        description = data.get("description", item.description)
        tags = data.get("tags", item.tags)
        visibility = data.get("visibility", item.visibility)
        featured = bool(data.get("featured", item.featured))
    else:
        title = request.form.get("title", "").strip()
        category = request.form.get("category", item.category)
        project_id_raw = request.form.get("project_id", "").strip()
        project_id = int(project_id_raw) if project_id_raw and project_id_raw.isdigit() else None
        description = request.form.get("description", item.description)
        tags = request.form.get("tags", item.tags)
        visibility = request.form.get("visibility", item.visibility)
        featured = bool(request.form.get("featured"))

    if title:
        item.title = title
    item.category = category
    item.project_id = project_id
    item.description = description
    item.tags = tags
    item.visibility = visibility
    item.featured = featured

    # Optional image replacement
    img_file = request.files.get("image")
    if img_file and img_file.filename:
        success, res = save_upload_file(img_file, subfolder="gallery", allowed_types="image")
        if success:
            if item.image_url:
                delete_file(item.image_url)
            item.image_url = res

    db.session.commit()

    if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": True, "item": item.to_dict(), "message": "Asset metadata updated successfully."})

    flash(f"Asset '{item.title}' updated successfully.", "success")
    return redirect(url_for("admin_gallery.index"))

@gallery_bp.route("/bulk-action", methods=["POST"])
@login_required
def bulk_action():
    action = request.form.get("action") or (request.json.get("action") if request.is_json else None)
    
    if request.is_json:
        ids = request.json.get("ids", [])
    else:
        ids_raw = request.form.getlist("selected_ids") or request.form.get("ids", "").split(",")
        ids = [int(i) for i in ids_raw if str(i).strip().isdigit()]

    if not ids:
        flash("No assets selected for bulk action.", "warning")
        return redirect(url_for("admin_gallery.index"))

    items = GalleryItem.query.filter(GalleryItem.id.in_(ids)).all()
    count = len(items)

    if action == "delete":
        for item in items:
            delete_file(item.image_url)
            db.session.delete(item)
        db.session.commit()
        msg = f"Successfully deleted {count} creative assets."
    elif action == "change_category":
        new_cat = request.form.get("new_category") or (request.json.get("new_category") if request.is_json else "UI / UX")
        for item in items:
            item.category = new_cat
        db.session.commit()
        msg = f"Updated category of {count} assets to '{new_cat}'."
    elif action == "change_visibility":
        new_vis = request.form.get("new_visibility") or (request.json.get("new_visibility") if request.is_json else "published")
        for item in items:
            item.visibility = new_vis
        db.session.commit()
        msg = f"Updated status of {count} assets to '{new_vis.upper()}'."
    elif action == "move_to_project":
        new_proj_raw = request.form.get("new_project_id") or (request.json.get("new_project_id") if request.is_json else None)
        new_proj_id = int(new_proj_raw) if new_proj_raw and str(new_proj_raw).isdigit() else None
        for item in items:
            item.project_id = new_proj_id
        db.session.commit()
        msg = f"Assigned {count} assets to project."
    else:
        msg = "Unknown bulk action."

    if request.is_json:
        return jsonify({"success": True, "message": msg, "count": count})

    flash(msg, "success")
    return redirect(url_for("admin_gallery.index"))

@gallery_bp.route("/delete/<int:id>", methods=["POST"])
@login_required
def delete(id):
    item = GalleryItem.query.get_or_404(id)
    delete_file(item.image_url)
    db.session.delete(item)
    db.session.commit()
    flash(f"Asset '{item.title}' deleted.", "info")
    return redirect(url_for("admin_gallery.index"))

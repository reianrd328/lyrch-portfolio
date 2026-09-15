import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required
from app.models import db, GalleryItem, Project
from app.services.upload_service import save_upload_file, delete_file

import re
from pathlib import Path

def slugify(text):
    text = (text or "").lower().strip()
    slug = re.sub(r'[\s\W-]+', '-', text)
    return slug.strip('-') or 'project'

def resolve_or_create_project(project_id_raw, custom_project_title, default_category="UI / UX"):
    """
    Returns Project ID. If custom_project_title is provided or project_id_raw is '__new__',
    finds an existing project with that title or creates a new one automatically.
    """
    custom_title = (custom_project_title or "").strip()
    if (project_id_raw == "__new__" or not project_id_raw) and custom_title:
        existing = Project.query.filter(Project.title.ilike(custom_title)).first()
        if existing:
            return existing.id
        base_slug = slugify(custom_title)
        slug = base_slug
        counter = 1
        while Project.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1
        new_proj = Project(
            title=custom_title,
            slug=slug,
            category=default_category or "Project",
            visibility="published",
            status_badge="Live"
        )
        db.session.add(new_proj)
        db.session.flush()
        return new_proj.id

    if project_id_raw and str(project_id_raw).isdigit():
        return int(project_id_raw)
    return None

def get_gallery_categories():
    """Returns configured gallery categories, merged with any categories from database."""
    from app.models.settings import SiteSetting
    try:
        settings = SiteSetting.get_settings()
        configured_raw = getattr(settings, "gallery_categories", None) or "UI / UX, Projects, AI, Branding, Screenshots, Graphics, Other"
    except Exception:
        configured_raw = "UI / UX, Projects, AI, Branding, Screenshots, Graphics, Other"

    cats = []
    for c in configured_raw.split(","):
        cleaned = c.strip()
        if cleaned and cleaned not in cats and cleaned != "All":
            cats.append(cleaned)

    # Include existing categories in DB
    try:
        used_cats = db.session.query(GalleryItem.category).distinct().all()
        for (uc,) in used_cats:
            if uc and uc.strip() and uc.strip() not in cats and uc.strip() != "All":
                cats.append(uc.strip())
    except Exception:
        pass

    return cats or ["UI / UX", "Projects", "AI", "Branding", "Screenshots", "Graphics", "Other"]

def resolve_category(category_raw, custom_category_raw):
    cat = (category_raw or "").strip()
    custom_cat = (custom_category_raw or "").strip()
    if cat == "__custom__" and custom_cat:
        # Also persist to SiteSetting gallery_categories if not present
        try:
            from app.models.settings import SiteSetting
            settings = SiteSetting.get_settings()
            configured = [c.strip() for c in (settings.gallery_categories or "").split(",") if c.strip()]
            if custom_cat not in configured:
                configured.append(custom_cat)
                settings.gallery_categories = ", ".join(configured)
                db.session.commit()
        except Exception:
            pass
        return custom_cat
    return cat or "General"

gallery_bp = Blueprint("admin_gallery", __name__)

@gallery_bp.route("/")
@login_required
def index():
    query_text = request.args.get("q", "").strip()
    selected_cat = request.args.get("cat", "All").strip()
    selected_project = request.args.get("project_id", "").strip()
    selected_status = request.args.get("status", "all").strip()
    sort_by = request.args.get("sort", "newest").strip()
    view_mode = request.args.get("view", "").strip()

    all_items = GalleryItem.query.all()
    projects = Project.query.order_by(Project.title.asc()).all()
    categories = get_gallery_categories()

    current_project = None
    if selected_project and selected_project.isdigit():
        current_project = db.session.get(Project, int(selected_project))

    # Compute Project Album statistics
    project_stats = []
    for p in projects:
        p_items = [i for i in all_items if i.project_id == p.id]
        if not p_items:
            continue
        cover_item = next((i for i in reversed(p_items) if i.image_url), p_items[-1] if p_items else None)
        cover_url = cover_item.image_url if cover_item else None
        
        cats = sorted(list({i.category for i in p_items if i.category}))
        category_label = ", ".join(cats[:2]) if cats else (p.category or "Project")
        
        pub_count = sum(1 for i in p_items if i.visibility == "published")
        if pub_count == len(p_items):
            status_badge = "Published"
            status_class = "live"
        elif pub_count == 0:
            status_badge = "Draft"
            status_class = "draft"
        else:
            status_badge = f"{pub_count}/{len(p_items)} Live"
            status_class = "live"
            
        project_stats.append({
            "id": p.id,
            "title": p.title,
            "slug": p.slug,
            "category_label": category_label,
            "count": len(p_items),
            "cover_url": cover_url,
            "status_badge": status_badge,
            "status_class": status_class,
            "items": p_items
        })

    # Apply search filter to project stats if searching in albums mode
    if query_text:
        project_stats = [
            ps for ps in project_stats
            if query_text.lower() in ps["title"].lower() or query_text.lower() in ps["category_label"].lower()
        ]

    # Sort project_stats
    if sort_by == "title_asc":
        project_stats.sort(key=lambda x: x["title"].lower())
    elif sort_by == "title_desc":
        project_stats.sort(key=lambda x: x["title"].lower(), reverse=True)
    elif sort_by == "oldest":
        project_stats.sort(key=lambda x: x["id"])
    else:
        project_stats.sort(key=lambda x: x["id"], reverse=True)

    # Compute Category Folder statistics
    category_stats = []
    for c in categories:
        if c == "Projects":
            c_items = [i for i in all_items if i.project_id]
        else:
            c_items = [i for i in all_items if i.category == c]
        
        cover_item = next((i for i in reversed(c_items) if i.image_url), c_items[-1] if c_items else None)
        cover_url = cover_item.image_url if cover_item else None
        
        pub_count = sum(1 for i in c_items if i.visibility == "published")
        if len(c_items) > 0:
            if pub_count == len(c_items):
                status_badge = "Published"
                status_class = "live"
            elif pub_count == 0:
                status_badge = "Draft"
                status_class = "draft"
            else:
                status_badge = f"{pub_count}/{len(c_items)} Live"
                status_class = "live"
        else:
            status_badge = "Empty"
            status_class = "draft"
            
        category_stats.append({
            "name": c,
            "count": len(c_items),
            "cover_url": cover_url,
            "status_badge": status_badge,
            "status_class": status_class,
            "items": c_items
        })

    # Sort category_stats so folders with assets appear first
    category_stats.sort(key=lambda x: (x["count"] == 0, -x["count"]))

    # Determine default view_mode
    if not view_mode:
        if selected_cat == "Projects" and not selected_project:
            view_mode = "albums"
        elif (not selected_cat or selected_cat == "All") and not query_text and (not selected_status or selected_status == "all") and not selected_project:
            view_mode = "folders"
        else:
            view_mode = "flat"

    standalone_count = sum(1 for i in all_items if not i.project_id)

    # Telemetry Stats
    total_assets = len(all_items)
    ui_projects_count = sum(1 for i in all_items if i.category == "UI / UX" or i.project_id)
    screenshots_count = sum(1 for i in all_items if i.category == "Screenshots")
    graphics_count = sum(1 for i in all_items if i.category in ("Graphics", "Branding"))
    drafts_count = sum(1 for i in all_items if i.visibility == "draft")

    # Dynamic telemetry list for all user-defined categories
    telemetry_cats = []
    for c in categories:
        if c == "Projects":
            cnt = sum(1 for i in all_items if i.project_id)
        else:
            cnt = sum(1 for i in all_items if i.category == c)
        telemetry_cats.append({"name": c, "count": cnt})

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
        project_stats=project_stats,
        category_stats=category_stats,
        current_project=current_project,
        view_mode=view_mode,
        standalone_count=standalone_count,
        categories=categories,
        telemetry_cats=telemetry_cats,
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

@gallery_bp.route("/categories/update", methods=["POST"])
@login_required
def update_categories():
    new_categories_raw = request.form.get("categories", "") or (request.json.get("categories", "") if request.is_json else "")
    from app.models.settings import SiteSetting
    settings = SiteSetting.get_settings()

    cats = []
    for c in new_categories_raw.split(","):
        cleaned = c.strip()
        if cleaned and cleaned not in cats and cleaned != "All":
            cats.append(cleaned)

    if not cats:
        cats = ["UI / UX", "Projects", "AI", "Branding", "Screenshots", "Graphics", "Other"]

    settings.gallery_categories = ", ".join(cats)
    db.session.commit()

    if request.is_json:
        return jsonify({"success": True, "categories": cats, "message": "Categories updated successfully."})

    flash("Creative asset categories updated successfully!", "success")
    return redirect(url_for("admin_gallery.index"))

@gallery_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category_raw = request.form.get("category", "UI / UX")
        custom_category_raw = request.form.get("custom_category", "")
        category = resolve_category(category_raw, custom_category_raw)
        project_id_raw = request.form.get("project_id", "").strip()
        new_project_title = request.form.get("new_project_title", "").strip()
        project_id = resolve_or_create_project(project_id_raw, new_project_title, default_category=category)
        description = request.form.get("description", "").strip()
        tags = request.form.get("tags", "").strip()
        visibility = request.form.get("visibility", "published").strip()
        featured = bool(request.form.get("featured"))

        # Collect uploaded image files (supports 'images' and 'image' input names, single or multiple)
        raw_files = request.files.getlist("images")
        if not raw_files or (len(raw_files) == 1 and not raw_files[0].filename):
            raw_files = request.files.getlist("image")

        valid_files = [f for f in raw_files if f and f.filename]
        if not valid_files:
            if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "error": "Please select at least one image file to upload"}), 400
            flash("Please select at least one image file to upload.", "danger")
            return redirect(request.url)

        created_items = []
        failed_files = []
        total_files = len(valid_files)

        for idx, img_file in enumerate(valid_files):
            success, res = save_upload_file(img_file, subfolder="gallery", allowed_types="image")
            if not success:
                failed_files.append((img_file.filename, res))
                continue

            # File size calculation
            file_size_bytes = 0
            try:
                full_path = os.path.join(current_app.config["UPLOAD_FOLDER"], "gallery", os.path.basename(res))
                if os.path.exists(full_path):
                    file_size_bytes = os.path.getsize(full_path)
            except Exception:
                pass

            # Smart titling:
            # 1. Custom title given: "Title" (if 1 file) or "Title (1)", "Title (2)", ...
            # 2. No title: clean human title from filename (e.g. "ui_dashboard.png" -> "Ui Dashboard")
            if title:
                item_title = title if total_files == 1 else f"{title} ({idx + 1})"
            else:
                stem = Path(img_file.filename).stem
                clean_name = re.sub(r'[\-_]+', ' ', stem).strip()
                item_title = clean_name.title() if clean_name else f"Asset {idx + 1}"

            item = GalleryItem(
                title=item_title,
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
            created_items.append(item)

        if not created_items and failed_files:
            err_msg = ", ".join([f"{fn}: {err}" for fn, err in failed_files])
            if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "error": f"Upload failed: {err_msg}"}), 400
            flash(f"Upload failed: {err_msg}", "danger")
            return redirect(request.url)

        db.session.commit()

        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({
                "success": True,
                "count": len(created_items),
                "items": [item.to_dict() for item in created_items],
                "item": created_items[0].to_dict() if created_items else None,
                "message": f"Successfully uploaded {len(created_items)} creative asset(s)!"
            })

        if len(created_items) == 1:
            flash(f"Creative asset '{created_items[0].title}' uploaded successfully!", "success")
        else:
            flash(f"Successfully uploaded {len(created_items)} creative assets to the library!", "success")

        if failed_files:
            flash(f"Note: {len(failed_files)} file(s) could not be uploaded due to invalid formats.", "warning")

        return redirect(url_for("admin_gallery.index"))

    projects = Project.query.order_by(Project.title.asc()).all()
    categories = get_gallery_categories()
    return render_template("admin/gallery/create.html", projects=projects, categories=categories)

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
        category_raw = data.get("category", item.category)
        custom_category_raw = data.get("custom_category", "")
        category = resolve_category(category_raw, custom_category_raw)
        project_id_raw = data.get("project_id")
        new_project_title = data.get("new_project_title", "")
        project_id = resolve_or_create_project(project_id_raw, new_project_title, default_category=category)
        description = data.get("description", item.description)
        tags = data.get("tags", item.tags)
        visibility = data.get("visibility", item.visibility)
        featured = bool(data.get("featured", item.featured))
    else:
        title = request.form.get("title", "").strip()
        category_raw = request.form.get("category", item.category)
        custom_category_raw = request.form.get("custom_category", "").strip()
        category = resolve_category(category_raw, custom_category_raw)
        project_id_raw = request.form.get("project_id", "").strip()
        new_project_title = request.form.get("new_project_title", "").strip()
        project_id = resolve_or_create_project(project_id_raw, new_project_title, default_category=category)
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

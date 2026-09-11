from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.models import db, GalleryItem
from app.services.upload_service import save_upload_file, delete_file

gallery_bp = Blueprint("admin_gallery", __name__)

@gallery_bp.route("/")
@login_required
def index():
    items = GalleryItem.query.order_by(GalleryItem.order_index.asc(), GalleryItem.id.desc()).all()
    return render_template("admin/gallery/index.html", items=items)

@gallery_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "UI / UX")
        description = request.form.get("description")
        featured = bool(request.form.get("featured"))

        img_file = request.files.get("image")
        if not img_file or not img_file.filename:
            flash("Image file is required", "danger")
            return redirect(request.url)

        success, res = save_upload_file(img_file, subfolder="gallery", allowed_types="image")
        if not success:
            flash(f"Upload failed: {res}", "danger")
            return redirect(request.url)

        item = GalleryItem(
            title=title or "Gallery Image",
            category=category,
            description=description,
            featured=featured,
            image_url=res
        )
        db.session.add(item)
        db.session.commit()

        flash("Gallery asset uploaded successfully!", "success")
        return redirect(url_for("admin_gallery.index"))

    return render_template("admin/gallery/create.html")

@gallery_bp.route("/delete/<int:id>", methods=["POST"])
@login_required
def delete(id):
    item = GalleryItem.query.get_or_404(id)
    delete_file(item.image_url)
    db.session.delete(item)
    db.session.commit()
    flash("Gallery item deleted.", "info")
    return redirect(url_for("admin_gallery.index"))


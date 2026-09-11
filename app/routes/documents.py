import os
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.models import db, Document
from app.services.upload_service import save_upload_file, delete_file

documents_bp = Blueprint("admin_documents", __name__)

@documents_bp.route("/")
@login_required
def index():
    docs = Document.query.order_by(Document.id.desc()).all()
    return render_template("admin/documents/index.html", documents=docs)

@documents_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "Project Documentation")
        description = request.form.get("description")
        allow_download = bool(request.form.get("allow_download"))
        is_public = bool(request.form.get("is_public"))

        doc_file = request.files.get("document")
        if not doc_file or not doc_file.filename:
            flash("Document file is required", "danger")
            return redirect(request.url)

        file_type = doc_file.filename.rsplit(".", 1)[-1].upper() if "." in doc_file.filename else "FILE"
        success, res = save_upload_file(doc_file, subfolder="documents", allowed_types="doc")
        if not success:
            flash(f"Upload failed: {res}", "danger")
            return redirect(request.url)

        doc = Document(
            title=title or doc_file.filename,
            category=category,
            description=description,
            file_path=res,
            file_type=file_type,
            allow_download=allow_download,
            is_public=is_public
        )
        db.session.add(doc)
        db.session.commit()

        flash("Document stored in repository successfully!", "success")
        return redirect(url_for("admin_documents.index"))

    return render_template("admin/documents/upload.html")

@documents_bp.route("/delete/<int:id>", methods=["POST"])
@login_required
def delete(id):
    doc = Document.query.get_or_404(id)
    delete_file(doc.file_path)
    db.session.delete(doc)
    db.session.commit()
    flash("Document deleted.", "info")
    return redirect(url_for("admin_documents.index"))


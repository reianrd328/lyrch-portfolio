import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, abort
from flask_login import login_required, current_user
from app.models import db, Document, PortfolioProfile
from app.services.upload_service import save_upload_file, delete_file

documents_bp = Blueprint("admin_documents", __name__)

def sync_profile_documents_json(profile_id):
    """Keep portfolio_profile.data_json['documents'] in sync with SQL document entries."""
    if not profile_id:
        return
    try:
        profile = db.session.get(PortfolioProfile, profile_id)
        if not profile:
            return
        docs = Document.query.filter_by(profile_id=profile_id).order_by(Document.id.desc()).all()
        data = profile.get_data()
        data["documents"] = [d.to_dict() for d in docs]
        profile.set_data(data)
        db.session.commit()
    except Exception as e:
        current_app.logger.warning(f"Error syncing profile documents JSON: {e}")

@documents_bp.route("/")
@login_required
def index():
    is_profile_user = (getattr(current_user, "role", "") == "profile_user")
    all_profiles = PortfolioProfile.query.order_by(PortfolioProfile.is_active.desc(), PortfolioProfile.name.asc()).all()
    active_profile = PortfolioProfile.query.filter_by(is_active=True).first()

    selected_profile_raw = request.args.get("profile_id", "").strip()
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
        docs = Document.query.filter(Document.profile_id == target_profile_id).order_by(Document.id.desc()).all()
    else:
        docs = Document.query.order_by(Document.id.desc()).all()

    return render_template(
        "admin/documents/index.html",
        documents=docs,
        all_profiles=all_profiles,
        scoped_profile=scoped_profile,
        selected_profile=selected_profile,
        is_profile_user=is_profile_user,
        active_profile=active_profile
    )

@documents_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    is_profile_user = (getattr(current_user, "role", "") == "profile_user")
    all_profiles = PortfolioProfile.query.order_by(PortfolioProfile.is_active.desc(), PortfolioProfile.name.asc()).all()
    active_profile = PortfolioProfile.query.filter_by(is_active=True).first()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "Project Documentation")
        description = request.form.get("description")
        allow_download = bool(request.form.get("allow_download"))
        is_public = bool(request.form.get("is_public"))

        if is_profile_user:
            target_profile_id = current_user.profile_id
        else:
            profile_id_raw = (request.form.get("profile_id", "") or request.args.get("profile_id", "")).strip()
            if profile_id_raw and profile_id_raw.isdigit():
                target_profile_id = int(profile_id_raw)
            else:
                target_profile_id = active_profile.id if active_profile else None

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
            is_public=is_public,
            profile_id=target_profile_id
        )
        db.session.add(doc)
        db.session.commit()

        if target_profile_id:
            sync_profile_documents_json(target_profile_id)

        flash("Document stored in repository successfully!", "success")
        return redirect(url_for("admin_documents.index"))

    return render_template(
        "admin/documents/upload.html",
        all_profiles=all_profiles,
        is_profile_user=is_profile_user,
        active_profile=active_profile
    )

@documents_bp.route("/delete/<int:id>", methods=["POST"])
@login_required
def delete(id):
    doc = Document.query.get_or_404(id)
    is_profile_user = (getattr(current_user, "role", "") == "profile_user")
    if is_profile_user and doc.profile_id != current_user.profile_id:
        abort(403)

    target_profile_id = doc.profile_id
    file_to_delete = doc.file_path
    db.session.delete(doc)
    db.session.commit()

    if file_to_delete:
        delete_file(file_to_delete)

    if target_profile_id:
        sync_profile_documents_json(target_profile_id)

    flash("Document deleted.", "info")
    return redirect(url_for("admin_documents.index"))



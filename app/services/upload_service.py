import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app

def allowed_file(filename: str, allowed_extensions: set) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions

def save_upload_file(file_storage, subfolder: str = "projects", allowed_types: str = "image") -> tuple[bool, str]:
    """
    Saves an uploaded file to uploads/<subfolder>/ with a secure unique filename.
    Returns (success, filename_or_error)
    """
    if not file_storage or file_storage.filename == "":
        return False, "No file provided"

    filename = secure_filename(file_storage.filename)
    ext = filename.rsplit(".", 1)[1].lower() if "." in filename else ""

    config = current_app.config
    if allowed_types == "image":
        allowed = config.get("ALLOWED_IMAGE_EXTENSIONS", {"png", "jpg", "jpeg", "webp", "gif", "svg", "jfif", "bmp"})
    elif allowed_types == "video":
        allowed = config.get("ALLOWED_VIDEO_EXTENSIONS", {"mp4", "webm", "mov"})
    elif allowed_types == "doc":
        allowed = config.get("ALLOWED_DOC_EXTENSIONS", {"pdf", "docx", "doc", "zip"})
    else:
        allowed = {"png", "jpg", "jpeg", "webp", "pdf", "mp4"}

    if ext not in allowed:
        return False, f"File extension .{ext} is not supported"

    # Create unique filename
    unique_name = f"{uuid.uuid4().hex[:12]}_{filename}"
    target_dir = os.path.join(config["UPLOAD_FOLDER"], subfolder)
    os.makedirs(target_dir, exist_ok=True)

    file_path = os.path.join(target_dir, unique_name)
    file_storage.save(file_path)

    # Return relative URL path for storage in DB
    relative_url = f"/uploads/{subfolder}/{unique_name}"
    return True, relative_url

def count_file_references(relative_url: str) -> int:
    """
    Counts how many database records currently reference this uploaded file.
    Protects shared media (e.g. batch-uploaded videos sharing one thumbnail)
    from being deleted when only one item is removed.
    """
    if not relative_url or not relative_url.startswith("/uploads/"):
        return 0
    total = 0
    try:
        from app.models.video import Video
        from app.models.gallery import GalleryItem
        from app.models.document import Document
        from app.models.project import Project
        from app.models.profile import PortfolioProfile
        from app.models.settings import SiteSetting

        total += Video.query.filter(
            (Video.thumbnail_url == relative_url) | (Video.video_url == relative_url)
        ).count()
        total += GalleryItem.query.filter(GalleryItem.image_url == relative_url).count()
        total += Document.query.filter(Document.file_path == relative_url).count()
        total += Project.query.filter(
            (Project.thumbnail_url == relative_url) | (Project.banner_url == relative_url)
        ).count()
        total += PortfolioProfile.query.filter(PortfolioProfile.avatar_url == relative_url).count()
        total += SiteSetting.query.filter(
            (SiteSetting.avatar_url == relative_url) | (SiteSetting.resume_url == relative_url)
        ).count()
    except Exception:
        pass
    return total

def delete_file(relative_url: str, check_references: bool = True) -> bool:
    """Deletes a file given its relative URL e.g. /uploads/projects/xyz.png"""
    if not relative_url or not relative_url.startswith("/uploads/"):
        return False
    
    if check_references:
        # If any record in DB still references this file, do not delete from disk
        if count_file_references(relative_url) > 0:
            return False

    clean_path = relative_url.replace("/uploads/", "")
    full_path = os.path.join(current_app.config["UPLOAD_FOLDER"], clean_path)
    if os.path.exists(full_path):
        try:
            os.remove(full_path)
            return True
        except OSError:
            return False
    return False


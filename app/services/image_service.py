import os
from PIL import Image
from flask import current_app

def create_thumbnail(image_rel_path: str, max_size=(600, 400)) -> str:
    """Generates an optimized thumbnail for an uploaded image"""
    if not image_rel_path or not image_rel_path.startswith("/uploads/"):
        return image_rel_path

    clean_path = image_rel_path.replace("/uploads/", "")
    full_path = os.path.join(current_app.config["UPLOAD_FOLDER"], clean_path)

    if not os.path.exists(full_path):
        return image_rel_path

    try:
        dir_name, base_name = os.path.split(full_path)
        thumb_name = f"thumb_{base_name}"
        thumb_path = os.path.join(dir_name, thumb_name)

        with Image.open(full_path) as img:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(thumb_path, "JPEG", quality=85)

        thumb_rel_dir = os.path.dirname(image_rel_path)
        return f"{thumb_rel_dir}/{thumb_name}"
    except Exception:
        return image_rel_path

def optimize_image(image_path: str, max_width=1920) -> bool:
    """Optimizes oversized images in place"""
    try:
        with Image.open(image_path) as img:
            if img.width > max_width:
                w_percent = (max_width / float(img.width))
                h_size = int((float(img.height) * float(w_percent)))
                resized = img.resize((max_width, h_size), Image.Resampling.LANCZOS)
                resized.save(image_path, optimize=True, quality=88)
        return True
    except Exception:
        return False


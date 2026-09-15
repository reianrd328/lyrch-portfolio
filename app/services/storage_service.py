import os
from flask import current_app

def format_bytes(size_bytes: int) -> str:
    """Formats bytes into human readable string (KB, MB, GB)."""
    if size_bytes <= 0:
        return "0 MB"
    if size_bytes < 1024 * 1024:
        return f"{round(size_bytes / 1024, 1)} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{round(size_bytes / (1024 * 1024), 1)} MB"
    else:
        return f"{round(size_bytes / (1024 * 1024 * 1024), 2)} GB"

def get_directory_size(path: str) -> int:
    """Recursively computes size in bytes of a directory."""
    if not os.path.exists(path):
        return 0
    total = 0
    try:
        for root, _, files in os.walk(path):
            for f in files:
                fp = os.path.join(root, f)
                if os.path.isfile(fp) and not os.path.islink(fp):
                    total += os.path.getsize(fp)
    except Exception:
        pass
    return total

def get_storage_stats() -> dict:
    """
    Computes storage breakdown across uploads:
    Images (gallery, projects, profile), Videos (videos), Documents (documents).
    """
    upload_root = current_app.config.get("UPLOAD_FOLDER", "uploads")
    
    img_folders = ["gallery", "projects", "profile"]
    images_bytes = sum(get_directory_size(os.path.join(upload_root, sub)) for sub in img_folders)
    videos_bytes = get_directory_size(os.path.join(upload_root, "videos"))
    docs_bytes = get_directory_size(os.path.join(upload_root, "documents"))
    
    total_bytes = images_bytes + videos_bytes + docs_bytes
    # Base storage limit default: 10 GB
    max_bytes = int(os.getenv("STORAGE_LIMIT_BYTES", 10 * 1024 * 1024 * 1024))
    used_pct = min(100, max(1, round((total_bytes / max_bytes) * 100, 1))) if total_bytes > 0 else 0

    return {
        "images_bytes": images_bytes,
        "images_formatted": format_bytes(images_bytes),
        "videos_bytes": videos_bytes,
        "videos_formatted": format_bytes(videos_bytes),
        "docs_bytes": docs_bytes,
        "docs_formatted": format_bytes(docs_bytes),
        "total_bytes": total_bytes,
        "total_formatted": format_bytes(total_bytes),
        "max_formatted": format_bytes(max_bytes),
        "used_pct": used_pct
    }

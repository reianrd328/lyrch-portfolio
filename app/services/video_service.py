def validate_video_file(filename: str) -> bool:
    """Basic validation for video extensions"""
    if not filename:
        return False
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in {"mp4", "webm", "mov", "m4v"}


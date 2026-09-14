import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

class Config:
    """Base Configuration"""
    SECRET_KEY = os.getenv("SECRET_KEY", "lyrch-command-center-default-key-3026")
    SESSION_PERMANENT = False
    
    # Upload configuration (supports Render Persistent Disk or local folder)
    upload_env = os.getenv("UPLOAD_FOLDER", "uploads")
    if os.path.isabs(upload_env):
        UPLOAD_FOLDER = upload_env
    else:
        UPLOAD_FOLDER = os.path.join(BASE_DIR, upload_env)

    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 50 * 1024 * 1024))  # 50MB
    
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "svg", "jfif", "bmp"}
    ALLOWED_VIDEO_EXTENSIONS = {"mp4", "webm", "mov", "avi"}
    ALLOWED_DOC_EXTENSIONS = {"pdf", "docx", "doc", "txt", "zip"}
    
    # Database configuration (TiDB, MySQL, PostgreSQL, or zero-config SQLite)
    raw_db_url = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI")
    if raw_db_url:
        # Standardize prefixes for SQL drivers
        if raw_db_url.startswith("mysql://"):
            raw_db_url = raw_db_url.replace("mysql://", "mysql+pymysql://", 1)
        elif raw_db_url.startswith("postgres://"):
            raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)
        DB_URI = raw_db_url
    elif os.getenv("DB_HOST"):
        db_user = os.getenv("DB_USER", "root")
        db_pass = os.getenv("DB_PASSWORD", "")
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "3306")
        db_name = os.getenv("DB_NAME", "lyrch_portfolio")
        DB_URI = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"
    else:
        # Zero-config SQLite: Enables 1-click deployment on Render without external databases!
        instance_dir = os.path.join(BASE_DIR, "instance")
        os.makedirs(instance_dir, exist_ok=True)
        DB_URI = f"sqlite:///{os.path.join(instance_dir, 'portfolio.db')}"

    SQLALCHEMY_DATABASE_URI = DB_URI
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Engine options & SSL handling
    is_sqlite = SQLALCHEMY_DATABASE_URI.startswith("sqlite")
    if is_sqlite:
        engine_opts = {}
    else:
        engine_opts = {
            "pool_recycle": 280,
            "pool_pre_ping": True,
        }
        
        # Automatically configure secure SSL for TiDB Cloud Serverless
        is_tidb = "tidbcloud.com" in SQLALCHEMY_DATABASE_URI
        use_ssl = os.getenv("TIDB_SSL", "false").lower() in ("true", "1") or is_tidb
        
        if use_ssl:
            try:
                import certifi
                engine_opts["connect_args"] = {"ssl": {"ca": certifi.where()}}
            except Exception:
                ca_path = os.getenv("TIDB_CA_PATH", "/etc/ssl/certs/ca-certificates.crt")
                if os.path.exists(ca_path):
                    engine_opts["connect_args"] = {"ssl": {"ca": ca_path}}
                else:
                    engine_opts["connect_args"] = {"ssl": {"ssl_mode": "VERIFY_IDENTITY"}}

    SQLALCHEMY_ENGINE_OPTIONS = engine_opts


class DevelopmentConfig(Config):
    """Development Configuration"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production Configuration"""
    DEBUG = False
    TESTING = False


class TestingConfig(Config):
    """Testing Configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{BASE_DIR}/instance/test_portfolio.db"
    SQLALCHEMY_ENGINE_OPTIONS = {}


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig
}


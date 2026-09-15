import json
from datetime import datetime
from app.models import (
    db, Project, ProjectImage, Category, Video, GalleryItem, Document,
    Skill, Experience, BlogPost, ActivityLog, SiteSetting, PortfolioProfile
)

# Attributes of SiteSetting that belong to the portfolio presentation
# (strictly excluding server-wide secrets like resend_api_key, gdrive tokens, backup cron, etc.)
PRESENTATION_SETTING_KEYS = [
    "display_name", "job_title", "location", "avatar_url",
    "hero_pretitle", "hero_title", "hero_tags", "hero_bio",
    "metric1_num", "metric1_title", "metric1_desc",
    "metric2_num", "metric2_title", "metric2_desc",
    "metric3_num", "metric3_title", "metric3_desc",
    "metric4_num", "metric4_title", "metric4_desc",
    "metric5_num", "metric5_title", "metric5_desc",
    "map_stat1_num", "map_stat1_label",
    "map_stat2_num", "map_stat2_label",
    "map_stat3_num", "map_stat3_label",
    "map_tagline",
    "quote_text", "quote_signature",
    "footer_motto", "footer_sub", "copyright_text",
    "github_url", "linkedin_url", "youtube_url", "facebook_url", "contact_email",
    "default_theme", "custom_primary_color", "custom_secondary_color"
]

def serialize_row(instance, exclude_cols=None) -> dict:
    """Serializes a SQLAlchemy model row to a plain dict."""
    if not instance:
        return {}
    exclude_cols = exclude_cols or []
    data = {}
    for col in instance.__table__.columns:
        if col.name in exclude_cols:
            continue
        val = getattr(instance, col.name)
        if isinstance(val, datetime):
            val = val.isoformat()
        data[col.name] = val
    return data

def capture_current_portfolio_dict() -> dict:
    """
    Serializes all portfolio-specific data currently live in the database.
    Does NOT include users or sensitive server/backup credentials.
    """
    settings = SiteSetting.get_settings()
    settings_dict = {k: getattr(settings, k, None) for k in PRESENTATION_SETTING_KEYS}

    # Projects with their images
    projects_list = []
    for p in Project.query.order_by(Project.order_index.asc(), Project.id.asc()).all():
        p_data = serialize_row(p, exclude_cols=["id", "created_at", "updated_at"])
        p_data["images"] = [
            serialize_row(img, exclude_cols=["id", "project_id"])
            for img in p.images.order_by(ProjectImage.order_index.asc()).all()
        ]
        projects_list.append(p_data)

    return {
        "metadata": {
            "version": "1.0",
            "exported_at": datetime.utcnow().isoformat(),
        },
        "settings": settings_dict,
        "categories": [serialize_row(c, exclude_cols=["id"]) for c in Category.query.all()],
        "projects": projects_list,
        "videos": [serialize_row(v, exclude_cols=["id", "created_at"]) for v in Video.query.all()],
        "gallery": [serialize_row(g, exclude_cols=["id", "created_at"]) for g in GalleryItem.query.all()],
        "documents": [serialize_row(d, exclude_cols=["id", "created_at"]) for d in Document.query.all()],
        "skills": [serialize_row(s, exclude_cols=["id"]) for s in Skill.query.all()],
        "experiences": [serialize_row(e, exclude_cols=["id"]) for e in Experience.query.all()],
        "blog_posts": [serialize_row(b, exclude_cols=["id", "created_at", "updated_at"]) for b in BlogPost.query.all()],
    }

def filter_valid_columns(model_cls, data_dict: dict) -> dict:
    """Filters dictionary so it only contains valid table column names, excluding primary key 'id'."""
    col_names = {c.name for c in model_cls.__table__.columns}
    return {k: v for k, v in data_dict.items() if k in col_names and k != "id"}

def apply_portfolio_dict_to_database(data: dict) -> tuple[bool, str]:
    """
    Replaces the current active portfolio content in the database with the given data.
    Safely preserves system credentials and user accounts.
    """
    try:
        # 1. Update presentation settings
        settings_data = data.get("settings", {})
        if settings_data:
            current_settings = SiteSetting.get_settings()
            for key in PRESENTATION_SETTING_KEYS:
                if key in settings_data and settings_data[key] is not None:
                    setattr(current_settings, key, settings_data[key])

        # 2. Clear content tables safely (child items first to respect foreign keys)
        ProjectImage.query.delete()
        Project.query.delete()
        Video.query.delete()
        GalleryItem.query.delete()
        Document.query.delete()
        Skill.query.delete()
        Experience.query.delete()
        BlogPost.query.delete()
        Category.query.delete()

        # 3. Populate Categories
        for cat_data in data.get("categories", []):
            db.session.add(Category(**filter_valid_columns(Category, cat_data)))

        # 4. Populate Projects and child Images
        for p_data in data.get("projects", []):
            images_data = p_data.pop("images", [])
            project = Project(**filter_valid_columns(Project, p_data))
            db.session.add(project)
            db.session.flush()  # obtain project.id
            for img_data in images_data:
                db.session.add(ProjectImage(project_id=project.id, **filter_valid_columns(ProjectImage, img_data)))

        # 5. Populate Skills
        for s_data in data.get("skills", []):
            db.session.add(Skill(**filter_valid_columns(Skill, s_data)))

        # 6. Populate Experiences
        for e_data in data.get("experiences", []):
            if "role" in e_data and "role_title" not in e_data:
                e_data["role_title"] = e_data["role"]
            if "achievements" in e_data and "highlights" not in e_data:
                e_data["highlights"] = e_data["achievements"]
            db.session.add(Experience(**filter_valid_columns(Experience, e_data)))

        # 7. Populate Videos
        for v_data in data.get("videos", []):
            db.session.add(Video(**filter_valid_columns(Video, v_data)))

        # 8. Populate Gallery
        for g_data in data.get("gallery", []):
            db.session.add(GalleryItem(**filter_valid_columns(GalleryItem, g_data)))

        # 9. Populate Documents
        for d_data in data.get("documents", []):
            db.session.add(Document(**filter_valid_columns(Document, d_data)))

        # 10. Populate Blog Posts
        for b_data in data.get("blog_posts", []):
            db.session.add(BlogPost(**filter_valid_columns(BlogPost, b_data)))

        db.session.commit()
        return True, "Portfolio content applied successfully!"
    except Exception as e:
        db.session.rollback()
        return False, f"Failed to apply portfolio content: {str(e)}"

def get_starter_template_data(profile_name: str, client_name: str = "", theme_preset: str = "cyber") -> dict:
    """
    Generates a clean starter template data dictionary for a new client portfolio.
    """
    display = client_name if client_name else profile_name
    return {
        "metadata": {
            "version": "1.0",
            "template": "starter_clean",
            "created_at": datetime.utcnow().isoformat(),
        },
        "settings": {
            "display_name": display,
            "job_title": "PORTFOLIO & DIGITAL SHOWCASE",
            "location": "Global",
            "avatar_url": "/static/images/profile/avatar.jpg",
            "hero_pretitle": "WELCOME TO",
            "hero_title": f"{display.upper()} PORTFOLIO",
            "hero_tags": "DESIGN • ENGINEERING • INNOVATION",
            "hero_bio": f"Welcome to the official portfolio showcase for {display}. Explore featured projects, specialized skills, and professional accomplishments.",
            "metric1_num": "5+",
            "metric1_title": "Years Experience",
            "metric1_desc": "Industry Expertise",
            "metric2_num": "50+",
            "metric2_title": "Projects Completed",
            "metric2_desc": "Client Deliverables",
            "metric3_num": "100%",
            "metric3_title": "Satisfaction Rate",
            "metric3_desc": "Quality Delivery",
            "metric4_num": "24/7",
            "metric4_title": "Support Availability",
            "metric4_desc": "Reliable Operations",
            "metric5_num": "Forward Thinking",
            "metric5_title": "",
            "metric5_desc": "Continuous Evolution",
            "map_stat1_num": "50+",
            "map_stat1_label": "DEPLOYED PROJECTS",
            "map_stat2_num": "100%",
            "map_stat2_label": "UPTIME COMMITMENT",
            "map_stat3_num": "5+",
            "map_stat3_label": "YEARS EXCELLENCE",
            "map_tagline": "Delivering Exceptional Digital Experiences",
            "quote_text": "Great systems are built with clarity, precision, and purpose.",
            "quote_signature": display,
            "footer_motto": "INNOVATE → ARCHITECT → DELIVER",
            "footer_sub": "TURNING VISIONS INTO REALITY",
            "copyright_text": f"© {datetime.utcnow().year} {display}. All rights reserved.",
            "github_url": "https://github.com",
            "linkedin_url": "https://linkedin.com",
            "youtube_url": "https://youtube.com",
            "facebook_url": "https://facebook.com",
            "contact_email": "hello@example.com",
            "default_theme": theme_preset,
            "custom_primary_color": "#00f0ff",
            "custom_secondary_color": "#a855f7"
        },
        "categories": [
            {"name": "Web Applications", "slug": "web-apps", "icon": "fa-globe", "description": "Web apps and portals"},
            {"name": "Mobile Solutions", "slug": "mobile-apps", "icon": "fa-mobile-screen", "description": "Mobile app solutions"},
            {"name": "Systems & Cloud", "slug": "systems-cloud", "icon": "fa-cloud", "description": "Cloud architectures"}
        ],
        "projects": [
            {
                "title": f"{display} Core Platform",
                "slug": "core-platform",
                "subtitle": "High-performance enterprise software solution",
                "category": "Web Applications",
                "status_badge": "Live",
                "featured": True,
                "order_index": 1,
                "short_description": "A high-performance modern web application built with responsive UI, secure authentication, and real-time data sync.",
                "full_description": "Comprehensive full-stack application built to streamline operations and deliver interactive user experiences.",
                "problem": "Legacy tools were fragmented and slow, hindering operational efficiency.",
                "solution": "Architected a unified digital platform with lightning-fast response times.",
                "challenges": "Integrating heterogeneous systems while maintaining sub-second latency.",
                "results": "Improved workflow productivity by over 40% in initial benchmarks.",
                "technologies": "Python, Flask, React, TailwindCSS, PostgreSQL",
                "key_features": "Real-time Telemetry\nRole-based Clearance\nAutomated Backup Sync",
                "thumbnail_url": "/static/images/portfolio/project1.jpg",
                "banner_url": "",
                "github_url": "https://github.com",
                "demo_url": "https://example.com",
                "visibility": "published",
                "images": []
            },
            {
                "title": "Cloud Analytics Dashboard",
                "slug": "analytics-dashboard",
                "subtitle": "Interactive telemetry and metric visualization",
                "category": "Systems & Cloud",
                "status_badge": "Live",
                "featured": True,
                "order_index": 2,
                "short_description": "Real-time interactive dashboard monitoring key business KPIs and operational metrics.",
                "full_description": "Data processing and reporting interface featuring automated chart rendering and alerts.",
                "technologies": "JavaScript, Chart.js, Python, REST API",
                "key_features": "Real-time Streaming\nCustom Filters\nExportable Reports",
                "thumbnail_url": "/static/images/portfolio/project2.jpg",
                "visibility": "published",
                "images": []
            }
        ],
        "skills": [
            {"name": "Full-Stack Development", "category": "Development", "proficiency": 95, "icon": "fa-code", "order_index": 1},
            {"name": "Cloud Infrastructure", "category": "DevOps", "proficiency": 90, "icon": "fa-cloud", "order_index": 2},
            {"name": "UI / UX Architecture", "category": "Design", "proficiency": 88, "icon": "fa-palette", "order_index": 3},
            {"name": "Database Engineering", "category": "Data", "proficiency": 92, "icon": "fa-database", "order_index": 4}
        ],
        "experiences": [
            {
                "company": f"{display} Studio",
                "role_title": "Lead Architect & Developer",
                "period": "2022 — Present",
                "location": "Remote",
                "description": "Leading product architecture, client engineering, and technical solution delivery.",
                "highlights": "Spearheaded successful delivery of 30+ client projects with 99.9% uptime.",
                "order_index": 1
            }
        ],
        "videos": [],
        "gallery": [],
        "documents": [],
        "blog_posts": []
    }

def switch_active_profile(target_profile_id: int) -> tuple[bool, str]:
    """
    Switches the live website to the specified profile.
    1. First auto-saves current live site into current active profile so no data is lost.
    2. Applies target profile data to live tables.
    3. Toggles is_active flags.
    """
    target = db.session.get(PortfolioProfile, target_profile_id)
    if not target:
        return False, "Target profile not found."

    # 1. Auto-save current active state
    current_active = PortfolioProfile.query.filter_by(is_active=True).first()
    if current_active:
        current_active.set_data(capture_current_portfolio_dict())
        current_active.updated_at = datetime.utcnow()
        db.session.commit()

    # 2. Apply target profile data
    target_data = target.get_data()
    success, msg = apply_portfolio_dict_to_database(target_data)
    if not success:
        return False, msg

    # 3. Update active flags
    PortfolioProfile.query.update({PortfolioProfile.is_active: False})
    target.is_active = True
    target.updated_at = datetime.utcnow()

    # 4. Log activity
    log = ActivityLog(
        title=f"Switched active portfolio to '{target.name}'",
        activity_type="system",
        time_label="Just now"
    )
    db.session.add(log)
    db.session.commit()

    return True, f"Portfolio successfully switched to '{target.name}'!"

def bootstrap_default_profile_if_needed():
    """
    Ensures that if no PortfolioProfile exists yet, the current live database
    state is automatically captured as the initial Master Profile ('DROP FARMD').
    This guarantees 100% safety and zero data loss on existing systems.
    """
    try:
        count = PortfolioProfile.query.count()
        if count == 0:
            settings = SiteSetting.get_settings()
            current_dict = capture_current_portfolio_dict()
            master = PortfolioProfile(
                name="DROP FARMD (Master Portfolio)",
                slug="drop-farmd",
                client_name=settings.display_name or "Lyrch",
                description="Primary master portfolio containing all personal IT technical support, systems, and AI creator showcases.",
                theme_preset=settings.default_theme or "cyber",
                is_active=True,
                is_published=True
            )
            master.set_data(current_dict)
            db.session.add(master)
            db.session.commit()
            return master
    except Exception as e:
        db.session.rollback()
        # Non-fatal if table doesn't exist yet before migration
        pass
    return None

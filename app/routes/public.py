from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import current_user
from app.models import Project, Video, GalleryItem, Document, Skill, Experience, BlogPost, ActivityLog, PortfolioProfile

public_bp = Blueprint("public", __name__)

class ProfileProxy:
    """Helper wrapper that allows dictionary data to be accessed via attributes in Jinja templates."""
    def __init__(self, d):
        self._d = d or {}
        for k, v in self._d.items():
            if isinstance(v, dict):
                setattr(self, k, ProfileProxy(v))
            elif isinstance(v, list):
                setattr(self, k, [ProfileProxy(item) if isinstance(item, dict) else item for item in v])
            else:
                setattr(self, k, v)

    @property
    def tech_list(self):
        val = getattr(self, "technologies", "") or ""
        return [t.strip() for t in val.split(",") if t.strip()]

    @property
    def features_list(self):
        val = getattr(self, "key_features", "") or ""
        import json
        try:
            return json.loads(val)
        except Exception:
            return [f.strip() for f in val.split("\n") if f.strip()]

    def __getattr__(self, name):
        return None

@public_bp.route("/")
def home():
    # Featured Projects for the 4-column showcase
    featured_projects = Project.query.filter(
        Project.visibility == "published"
    ).order_by(Project.featured.desc(), Project.order_index.asc(), Project.id.asc()).limit(4).all()

    # Featured AI Video for Creative Studio card
    featured_video = Video.query.filter(
        Video.visibility == "published"
    ).order_by(Video.featured.desc(), Video.id.desc()).first()

    # Recent activities for telemetry feed
    recent_activities = ActivityLog.query.order_by(ActivityLog.id.desc()).limit(6).all()

    # Metrics
    metrics = {
        "branches": "100+",
        "users": "1000+",
        "experience": "18+",
        "support": "24/7",
        "growth": "Always Learning"
    }

    return render_template(
        "public/home.html",
        featured_projects=featured_projects,
        featured_video=featured_video,
        recent_activities=recent_activities,
        metrics=metrics
    )

@public_bp.route("/about")
def about():
    skills = Skill.query.order_by(Skill.order_index.asc()).all()
    return render_template("public/about.html", skills=skills)

@public_bp.route("/experience")
def experience():
    experiences = Experience.query.order_by(Experience.order_index.asc()).all()
    return render_template("public/experience.html", experiences=experiences)

@public_bp.route("/projects")
def projects():
    category = request.args.get("category", "")
    query = Project.query.filter(Project.visibility == "published")
    if category:
        query = query.filter(Project.category == category)
    all_projects = query.order_by(Project.order_index.asc(), Project.id.asc()).all()
    return render_template("public/projects.html", projects=all_projects, selected_category=category)

@public_bp.route("/projects/<slug>")
def project_detail(slug):
    project = Project.query.filter_by(slug=slug, visibility="published").first_or_404()
    return render_template("public/project_detail.html", project=project)

@public_bp.route("/ai-lab")
def ai_lab():
    return render_template("public/ai_lab.html")

@public_bp.route("/video-studio")
def video_studio():
    videos = Video.query.filter(Video.visibility == "published").order_by(Video.id.desc()).all()
    albums = sorted(list({v.album for v in videos if v.album}))
    has_standalone = any(not v.album for v in videos)
    return render_template("public/video_studio.html", videos=videos, albums=albums, has_standalone=has_standalone)

@public_bp.route("/gallery")
def gallery():
    items = GalleryItem.query.filter(GalleryItem.visibility == "published").order_by(GalleryItem.order_index.asc(), GalleryItem.id.desc()).all()
    return render_template("public/gallery.html", items=items)

@public_bp.route("/files")
def files():
    documents = Document.query.filter_by(is_public=True).order_by(Document.id.desc()).all()
    return render_template("public/files.html", documents=documents)

@public_bp.route("/blog")
def blog():
    posts = BlogPost.query.filter_by(is_published=True).order_by(BlogPost.id.desc()).all()
    return render_template("public/blog.html", posts=posts)

@public_bp.route("/blog/<slug>")
def blog_detail(slug):
    post = BlogPost.query.filter_by(slug=slug, is_published=True).first_or_404()
    post.views_count += 1
    from app.models import db
    db.session.commit()
    return render_template("public/blog_detail.html", post=post)

@public_bp.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        flash("Signal received! Your transmission has reached the Command Center.", "success")
        return redirect(url_for("public.contact"))
    return render_template("public/contact.html")

# --- STANDALONE CLIENT PROFILE DEDICATED ROUTES (/p/<slug>) ---

@public_bp.route("/p/<slug>")
def profile_preview(slug):
    profile = PortfolioProfile.query.filter_by(slug=slug).first_or_404()
    if not profile.is_published and not current_user.is_authenticated:
        abort(404)

    if profile.is_active:
        return home()

    data = profile.get_data()
    preview_settings = ProfileProxy(data.get("settings", {}))
    
    projects_data = data.get("projects", [])
    featured = [ProfileProxy(p) for p in projects_data if p.get("featured") and p.get("visibility") == "published"][:4]
    if not featured:
        featured = [ProfileProxy(p) for p in projects_data if p.get("visibility") != "draft"][:4]

    videos_data = data.get("videos", [])
    featured_video = ProfileProxy(videos_data[0]) if videos_data else None

    metrics = {
        "branches": getattr(preview_settings, "metric2_num", "100+"),
        "users": getattr(preview_settings, "metric3_num", "1000+"),
        "experience": getattr(preview_settings, "metric1_num", "5+"),
        "support": getattr(preview_settings, "metric4_num", "24/7"),
        "growth": getattr(preview_settings, "metric5_num", "Always Learning")
    }

    return render_template(
        "public/home.html",
        featured_projects=featured,
        featured_video=featured_video,
        recent_activities=[],
        metrics=metrics,
        preview_profile=profile,
        settings=preview_settings
    )

@public_bp.route("/p/<slug>/about")
def profile_about(slug):
    profile = PortfolioProfile.query.filter_by(slug=slug).first_or_404()
    if not profile.is_published and not current_user.is_authenticated:
        abort(404)

    if profile.is_active:
        return about()
    data = profile.get_data()
    preview_settings = ProfileProxy(data.get("settings", {}))
    skills = [ProfileProxy(s) for s in data.get("skills", [])]
    return render_template("public/about.html", skills=skills, preview_profile=profile, settings=preview_settings)

@public_bp.route("/p/<slug>/experience")
def profile_experience(slug):
    profile = PortfolioProfile.query.filter_by(slug=slug).first_or_404()
    if not profile.is_published and not current_user.is_authenticated:
        abort(404)

    if profile.is_active:
        return experience()
    data = profile.get_data()
    preview_settings = ProfileProxy(data.get("settings", {}))
    experiences = [ProfileProxy(e) for e in data.get("experiences", [])]
    return render_template("public/experience.html", experiences=experiences, preview_profile=profile, settings=preview_settings)

@public_bp.route("/p/<slug>/projects")
def profile_projects(slug):
    profile = PortfolioProfile.query.filter_by(slug=slug).first_or_404()
    if not profile.is_published and not current_user.is_authenticated:
        abort(404)

    if profile.is_active:
        return projects()
    data = profile.get_data()
    preview_settings = ProfileProxy(data.get("settings", {}))
    category = request.args.get("category", "")
    projects_list = [ProfileProxy(p) for p in data.get("projects", []) if p.get("visibility") == "published"]
    if category:
        projects_list = [p for p in projects_list if getattr(p, "category", "") == category]
    return render_template("public/projects.html", projects=projects_list, selected_category=category, preview_profile=profile, settings=preview_settings)

@public_bp.route("/p/<slug>/projects/<project_slug>")
def profile_project_detail(slug, project_slug):
    profile = PortfolioProfile.query.filter_by(slug=slug).first_or_404()
    if not profile.is_published and not current_user.is_authenticated:
        abort(404)

    if profile.is_active:
        return project_detail(project_slug)
    data = profile.get_data()
    preview_settings = ProfileProxy(data.get("settings", {}))
    match = None
    for p in data.get("projects", []):
        if p.get("slug") == project_slug:
            match = ProfileProxy(p)
            break
    if not match:
        abort(404)
    return render_template("public/project_detail.html", project=match, preview_profile=profile, settings=preview_settings)

@public_bp.route("/p/<slug>/video-studio")
def profile_video_studio(slug):
    profile = PortfolioProfile.query.filter_by(slug=slug).first_or_404()
    if not profile.is_published and not current_user.is_authenticated:
        abort(404)

    if profile.is_active:
        return video_studio()
    data = profile.get_data()
    preview_settings = ProfileProxy(data.get("settings", {}))
    videos = [ProfileProxy(v) for v in data.get("videos", []) if v.get("visibility") == "published"]
    albums = sorted(list({v.album for v in videos if getattr(v, "album", None)}))
    has_standalone = any(not getattr(v, "album", None) for v in videos)
    return render_template("public/video_studio.html", videos=videos, albums=albums, has_standalone=has_standalone, preview_profile=profile, settings=preview_settings)

@public_bp.route("/p/<slug>/gallery")
def profile_gallery(slug):
    profile = PortfolioProfile.query.filter_by(slug=slug).first_or_404()
    if not profile.is_published and not current_user.is_authenticated:
        abort(404)

    if profile.is_active:
        return gallery()
    data = profile.get_data()
    preview_settings = ProfileProxy(data.get("settings", {}))
    items = [ProfileProxy(g) for g in data.get("gallery", [])]
    return render_template("public/gallery.html", items=items, preview_profile=profile, settings=preview_settings)

@public_bp.route("/p/<slug>/contact", methods=["GET", "POST"])
def profile_contact(slug):
    profile = PortfolioProfile.query.filter_by(slug=slug).first_or_404()
    if not profile.is_published and not current_user.is_authenticated:
        abort(404)

    data = profile.get_data()
    preview_settings = ProfileProxy(data.get("settings", {}))
    if request.method == "POST":
        flash("Signal received! Your transmission has reached the Command Center.", "success")
        return redirect(url_for("public.profile_contact", slug=slug))
    return render_template("public/contact.html", preview_profile=profile, settings=preview_settings)



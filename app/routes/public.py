from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.models import Project, Video, GalleryItem, Document, Skill, Experience, BlogPost, ActivityLog

public_bp = Blueprint("public", __name__)

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
    return render_template("public/video_studio.html", videos=videos)

@public_bp.route("/gallery")
def gallery():
    items = GalleryItem.query.order_by(GalleryItem.order_index.asc(), GalleryItem.id.desc()).all()
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


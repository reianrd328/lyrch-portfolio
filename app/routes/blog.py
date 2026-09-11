from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.models import db, BlogPost
import re

blog_bp = Blueprint("admin_blog", __name__)

def slugify(text):
    text = text.lower().strip()
    return re.sub(r'[\s\W-]+', '-', text)

@blog_bp.route("/")
@login_required
def index():
    posts = BlogPost.query.order_by(BlogPost.id.desc()).all()
    return render_template("admin/blog/index.html", posts=posts)

@blog_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("Title is required", "danger")
            return redirect(request.url)

        slug = slugify(title)
        existing = BlogPost.query.filter_by(slug=slug).first()
        if existing:
            slug = f"{slug}-{BlogPost.query.count() + 1}"

        excerpt = request.form.get("excerpt")
        content = request.form.get("content", "")
        tags = request.form.get("tags", "")
        is_published = bool(request.form.get("is_published"))

        post = BlogPost(
            title=title,
            slug=slug,
            excerpt=excerpt,
            content=content,
            tags=tags,
            is_published=is_published
        )
        db.session.add(post)
        db.session.commit()
        flash("Blog log created!", "success")
        return redirect(url_for("admin_blog.index"))

    return render_template("admin/blog/create.html")


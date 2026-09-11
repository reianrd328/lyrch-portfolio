from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.models import db, Experience

experience_bp = Blueprint("admin_experience", __name__)

@experience_bp.route("/")
@login_required
def index():
    experiences = Experience.query.order_by(Experience.order_index.asc(), Experience.id.desc()).all()
    return render_template("admin/experience/index.html", experiences=experiences)

@experience_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        role_title = request.form.get("role_title", "").strip()
        company = request.form.get("company", "").strip()
        location = request.form.get("location", "Philippines")
        period = request.form.get("period", "").strip()
        description = request.form.get("description")
        highlights = request.form.get("highlights")

        if not role_title or not company:
            flash("Role and Company are required", "danger")
            return redirect(request.url)

        exp = Experience(
            role_title=role_title,
            company=company,
            location=location,
            period=period,
            description=description,
            highlights=highlights
        )
        db.session.add(exp)
        db.session.commit()
        flash("Experience logged to timeline.", "success")
        return redirect(url_for("admin_experience.index"))

    return render_template("admin/experience/create.html")

@experience_bp.route("/delete/<int:id>", methods=["POST"])
@login_required
def delete(id):
    exp = Experience.query.get_or_404(id)
    db.session.delete(exp)
    db.session.commit()
    flash("Experience entry deleted.", "info")
    return redirect(url_for("admin_experience.index"))


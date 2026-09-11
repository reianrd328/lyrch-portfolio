from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.models import db, Skill

skills_bp = Blueprint("admin_skills", __name__)

@skills_bp.route("/")
@login_required
def index():
    skills = Skill.query.order_by(Skill.order_index.asc(), Skill.id.desc()).all()
    return render_template("admin/skills/index.html", skills=skills)

@skills_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "IT Operations")
        level = int(request.form.get("level", 90))
        icon = request.form.get("icon", "terminal")

        if not name:
            flash("Skill name is required", "danger")
            return redirect(request.url)

        skill = Skill(name=name, category=category, level=level, icon=icon)
        db.session.add(skill)
        db.session.commit()
        flash(f"Skill '{name}' registered in command matrix.", "success")
        return redirect(url_for("admin_skills.index"))

    return render_template("admin/skills/create.html")

@skills_bp.route("/delete/<int:id>", methods=["POST"])
@login_required
def delete(id):
    skill = Skill.query.get_or_404(id)
    db.session.delete(skill)
    db.session.commit()
    flash("Skill removed.", "info")
    return redirect(url_for("admin_skills.index"))


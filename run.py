import os
import click
from app import create_app
from app.models import (
    db, User, Project, Video, ActivityLog, Skill, Experience, Category, SiteSetting
)

env_name = os.getenv("FLASK_ENV", "production" if os.getenv("RENDER") else "development")
app = create_app(env_name)

@app.cli.command("init-db")
def init_db():
    """Initializes all database tables in MySQL."""
    with app.app_context():
        db.create_all()
        click.echo("✓ Database tables initialized in MySQL.")

@app.cli.command("seed-demo")
def seed_demo():
    """Seeds the initial Command Center data matching the target UI design."""
    with app.app_context():
        db.create_all()

        # 1. Admin User
        admin = User.query.filter_by(username="admin").first()
        if not admin:
            admin = User(
                username="admin",
                email="admin@lyrch.dev",
                display_name="DROP FARMD",
                role="admin"
            )
            admin.set_password("admin123")
            db.session.add(admin)
            click.echo("[OK] Created default admin (admin / admin123)")

        # 2. Featured Projects (Matching the UI reference)
        projects_data = [
            {
                "title": "PAWSHOP Command Center",
                "slug": "pawshop-command-center",
                "subtitle": "IT Helpdesk & Ticketing System",
                "category": "IT Operations",
                "status_badge": "Live",
                "featured": True,
                "order_index": 1,
                "technologies": "Python, Flask, MySQL, HTML, CSS, JavaScript",
                "short_description": "A complete helpdesk system for branches, helpdesk and technical support.",
                "thumbnail_url": "/static/images/projects/pawshop_thumb.jpg",
                "github_url": "https://github.com",
                "demo_url": "https://demo.pawshop.lyrch.dev"
            },
            {
                "title": "TobiasConnect",
                "slug": "tobias-connect",
                "subtitle": "Remote PC Support System",
                "category": "IT Operations",
                "status_badge": "Beta",
                "featured": True,
                "order_index": 2,
                "technologies": "Python, PySide6, Remote, Security, Authentication",
                "short_description": "Secure remote access with authentication and user management.",
                "thumbnail_url": "/static/images/projects/tobias_thumb.jpg",
                "github_url": "https://github.com",
                "demo_url": "https://demo.tobias.lyrch.dev"
            },
            {
                "title": "Lyrch AI",
                "slug": "lyrch-ai",
                "subtitle": "AI Assistant / AI Platform",
                "category": "AI Lab",
                "status_badge": "Online",
                "featured": True,
                "order_index": 3,
                "technologies": "Python, OpenAI, Gemini, AI API, Prompting, Web",
                "short_description": "AI-powered assistant and experiments using modern AI models.",
                "thumbnail_url": "/static/images/projects/lyrch_ai_thumb.jpg",
                "github_url": "https://github.com",
                "demo_url": "https://ai.lyrch.dev"
            },
            {
                "title": "FoodCart Manager",
                "slug": "foodcart-manager",
                "subtitle": "Food Cart Management System",
                "category": "Software Projects",
                "status_badge": "Demo",
                "featured": True,
                "order_index": 4,
                "technologies": "Python, Flask, MySQL, Inventory, Sales, Reports",
                "short_description": "Manage products, sales, inventory and reports.",
                "thumbnail_url": "/static/images/projects/foodcart_thumb.jpg",
                "github_url": "https://github.com",
                "demo_url": "https://demo.foodcart.lyrch.dev"
            },
        ]

        for p_data in projects_data:
            existing = Project.query.filter_by(slug=p_data["slug"]).first()
            if not existing:
                p = Project(**p_data)
                db.session.add(p)
                click.echo(f"[OK] Added project: {p_data['title']}")

        # 3. AI Creative Studio Video
        video = Video.query.filter_by(slug="ai-kung-fu-scene").first()
        if not video:
            v = Video(
                title="AI Kung Fu Scene",
                slug="ai-kung-fu-scene",
                description="Cinematic martial arts duel sequence generated using Gemini image-to-video workflow and enhanced in post-production.",
                category="AI Creative",
                tools_used="Gemini, Video Edit",
                platforms="Facebook Reels, TikTok",
                duration="0:10",
                aspect_ratio="16:9",
                featured=True,
                visibility="published",
                thumbnail_url="/static/images/projects/kungfu_thumb.jpg"
            )
            db.session.add(v)
            click.echo("[OK] Added AI Video: AI Kung Fu Scene")

        # 4. Recent Activities
        if ActivityLog.query.count() == 0:
            activities = [
                {"title": "Updated PAWSHOP dashboard", "activity_type": "project", "time_label": "2 hours ago"},
                {"title": "Generated AI video (Diaper Ad)", "activity_type": "video", "time_label": "4 hours ago"},
                {"title": "Improved Lyrch AI prompt", "activity_type": "ai", "time_label": "6 hours ago"},
                {"title": "Fixed network issue (Branch 032)", "activity_type": "network", "time_label": "1 day ago"},
                {"title": "Pushed code to GitHub", "activity_type": "git", "time_label": "1 day ago"}
            ]
            for a in activities:
                db.session.add(ActivityLog(**a))
            click.echo("[OK] Added Telemetry Activities")

        # 5. Skills
        if Skill.query.count() == 0:
            skills = [
                {"name": "IT Helpdesk & Systems Administration", "category": "IT Operations", "level": 95, "icon": "server"},
                {"name": "Branch Network & Infrastructure Support", "category": "IT Operations", "level": 92, "icon": "network"},
                {"name": "Python & Flask Backend Development", "category": "Development", "level": 90, "icon": "python"},
                {"name": "MySQL Database Architecture", "category": "Development", "level": 88, "icon": "database"},
                {"name": "Prompt Engineering & Generative AI", "category": "AI & Media", "level": 94, "icon": "cpu"},
                {"name": "AI Video Generation & Post-Production", "category": "AI & Media", "level": 90, "icon": "video"},
            ]
            for idx, s in enumerate(skills):
                db.session.add(Skill(order_index=idx, **s))
            click.echo("[OK] Added Skills Matrix")

        # 6. Default Site Settings
        SiteSetting.get_settings()
        click.echo("[OK] Initialized Site Settings record")

        db.session.commit()
        click.echo("[OK] Seed complete! Ready for Command Center launch.")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

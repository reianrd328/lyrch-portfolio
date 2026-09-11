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
    """Initializes all database tables."""
    with app.app_context():
        db.create_all()
        click.echo("✓ Database tables initialized.")

@app.cli.command("seed-demo")
def seed_demo():
    """Seeds the initial Command Center data matching the target UI design."""
    with app.app_context():
        from app.seed import seed_initial_data
        seed_initial_data()
        click.echo("[OK] Seed complete! Ready for Command Center launch.")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

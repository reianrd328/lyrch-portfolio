from . import db

class SiteSetting(db.Model):
    __tablename__ = "site_settings"

    id = db.Column(db.Integer, primary_key=True)

    # 1. Profile & Identity
    display_name = db.Column(db.String(120), default="DROP FARMD")
    job_title = db.Column(db.String(150), default="IT SUPPORT SPECIALIST & DEVELOPER")
    location = db.Column(db.String(100), default="Philippines")
    avatar_url = db.Column(db.String(255), default="/static/images/profile/avatar.jpg")

    # 2. Hero & Mission
    hero_pretitle = db.Column(db.String(100), default="WELCOME TO MY")
    hero_title = db.Column(db.String(150), default="DIGITAL COMMAND CENTER")
    hero_tags = db.Column(db.String(200), default="IT SUPPORT • DEVELOPER • AI CREATOR")
    hero_bio = db.Column(db.Text, default="18 years of technical support experience, supporting 100+ branches. Building systems, solving problems, and creating with AI.")

    # 3. Five Metrics Cards
    metric1_num = db.Column(db.String(40), default="18+")
    metric1_title = db.Column(db.String(80), default="Years Experience")
    metric1_desc = db.Column(db.String(100), default="IT Technical Support")

    metric2_num = db.Column(db.String(40), default="100+")
    metric2_title = db.Column(db.String(80), default="Branches Supported")
    metric2_desc = db.Column(db.String(100), default="Nationwide")

    metric3_num = db.Column(db.String(40), default="1000+")
    metric3_title = db.Column(db.String(80), default="Users Potential")
    metric3_desc = db.Column(db.String(100), default="System Ready")

    metric4_num = db.Column(db.String(40), default="24/7")
    metric4_title = db.Column(db.String(80), default="Problem Solving")
    metric4_desc = db.Column(db.String(100), default="IT Operations")

    metric5_num = db.Column(db.String(40), default="Always Learning")
    metric5_title = db.Column(db.String(80), default="")
    metric5_desc = db.Column(db.String(100), default="Growing with AI")

    # 4. Regional Constellation Map
    map_stat1_num = db.Column(db.String(40), default="100+")
    map_stat1_label = db.Column(db.String(80), default="BRANCHES SUPPORTED")
    map_stat2_num = db.Column(db.String(40), default="1000+")
    map_stat2_label = db.Column(db.String(80), default="USERS POTENTIAL")
    map_stat3_num = db.Column(db.String(40), default="18+")
    map_stat3_label = db.Column(db.String(80), default="YEARS EXPERIENCE")
    map_tagline = db.Column(db.String(150), default="Stronger Together Through Technology")

    # 5. Inspiration & Footer
    quote_text = db.Column(db.Text, default="Technology makes work easier. Creativity makes life better.")
    quote_signature = db.Column(db.String(80), default="Lyrch")
    footer_motto = db.Column(db.String(150), default="THINK → SOLVE → BUILD → CREATE")
    footer_sub = db.Column(db.String(150), default="IDEAS INTO REAL SOLUTIONS")
    copyright_text = db.Column(db.String(120), default="© 2026 LYRCH DEV All rights reserved.")

    # 6. Social Links & Contact
    github_url = db.Column(db.String(255), default="https://github.com")
    linkedin_url = db.Column(db.String(255), default="https://linkedin.com")
    youtube_url = db.Column(db.String(255), default="https://youtube.com")
    facebook_url = db.Column(db.String(255), default="https://facebook.com")
    contact_email = db.Column(db.String(120), default="contact@lyrch.dev")

    # 7. Theme Engine Default ("cyber", "matrix", "synthwave", "cobalt", "crimson", "custom")
    default_theme = db.Column(db.String(30), default="cyber")
    custom_primary_color = db.Column(db.String(20), default="#00f0ff")
    custom_secondary_color = db.Column(db.String(20), default="#a855f7")

    # 8. Automated Database Backup & Email Dispatch
    backup_auto_enabled = db.Column(db.Boolean, default=False)
    backup_email = db.Column(db.String(120), default="")
    backup_frequency = db.Column(db.String(20), default="daily")
    backup_last_run = db.Column(db.DateTime, nullable=True)
    backup_last_status = db.Column(db.String(150), default="Never run")

    @classmethod
    def get_settings(cls):
        """Retrieves or creates the primary site settings record."""
        settings = cls.query.first()
        if not settings:
            settings = cls()
            db.session.add(settings)
            db.session.commit()
        return settings

    def __repr__(self):
        return f"<SiteSetting {self.display_name} - {self.default_theme}>"


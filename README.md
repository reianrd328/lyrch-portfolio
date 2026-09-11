# LYRCH / DEV — Digital Command Center & Portfolio CMS

> **"THINK → SOLVE → BUILD → CREATE"** — Ideas into Real Solutions.

A futuristic, cybernetic command center portfolio and personal Content Management System (CMS) designed for **DROP FARMD** (IT Support Specialist & Developer, Philippines).

---

## ⚡ Key Highlights
- **Futuristic Cybernetic UI**: Deep space dark navy theme, electric cyan (`#00f0ff`) and neon purple (`#a855f7`) glowing accents, glassmorphic telemetry cards, and a real-time command clock.
- **Personal Work CMS (`/admin`)**: Private administrative workspace where you control what gets published—add projects, AI videos, design assets, and documentation with zero HTML editing required.
- **Multi-Work Portfolio**: First-class support for Software Projects, IT Systems, AI Video Productions (Gemini workflows), and Case Studies.
- **MySQL Architecture**: Powered by Python, Flask, Flask-SQLAlchemy, and MySQL 8.0 with PyMySQL.

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.10+ (Verified on Python 3.14)
- MySQL 8.0 running on `localhost:3306`

### 2. Environment Setup
```powershell
# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 3. Initialize Database & Seed Blueprint Data
```powershell
# Initializes MySQL tables and seeds the demo command center data
python -m flask --app run.py seed-demo
```

### 4. Run the Digital Command Center
```powershell
python run.py
```
- **Public Portal**: Open [http://127.0.0.1:5000](http://127.0.0.1:5000)
- **Admin CMS**: Open [http://127.0.0.1:5000/auth/login](http://127.0.0.1:5000/auth/login)
  - *Default Username*: `admin`
  - *Default Password*: `admin123`

---

## 📁 Project Architecture
```
LYRCH-PORTFOLIO/
├── run.py                     # Entry point & CLI seed helpers
├── config.py                  # Multi-environment configuration
├── requirements.txt           # Production & dev dependencies
├── .env                       # Environment secrets & database URI
│
├── app/
│   ├── models/                # User, Project, Video, Gallery, Document, Skill, etc.
│   ├── routes/                # Public portal, Auth, Admin & CRUD blueprints
│   ├── services/              # Uploads, image optimization, video handling
│   ├── templates/             # Jinja2 templates (Public, Admin, Auth)
│   └── static/                # CSS, JS, Branding & Cropped mockup assets
│
├── uploads/                   # Managed media storage
├── docs/                      # Master design docs & database schemas
└── tests/                     # Unit tests
```

---

## 🛡️ License
Proprietary © 2026 LYRCH DEV. All rights reserved.


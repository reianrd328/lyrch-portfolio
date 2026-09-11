# Production Deployment Guide: GitHub + TiDB Cloud + Render

This guide outlines the step-by-step process to deploy your **LYRCH Digital Command Center Portfolio & CMS** live to the internet for free using:
1. **GitHub**: Cloud code repository with continuous deployment.
2. **TiDB Cloud (Serverless)**: 100% MySQL-compatible cloud database with a generous free tier (no credit card needed).
3. **Render**: Cloud web app hosting with automatic HTTPS, custom domains, and auto-deploy from GitHub.

---

## Architecture Overview

```
[ Developer / Local Machine ]
             │
             ├── git push ──► [ GitHub Repository ]
             │                         │
             │                   auto-deploy webhook
             │                         ▼
             │               [ Render Web Service ] (Flask + Gunicorn)
             │                         │
             │                    SSL / MySQL
             │                         ▼
             └──────────────► [ TiDB Cloud Serverless ] (MySQL 8.0 Compatible)
```

---

## Step 1: Initialize Git & Push to GitHub

1. Open PowerShell in your project folder:
   ```powershell
   cd c:\Users\ITD-Chad\Desktop\PythonProjects\portfolio
   ```

2. Initialize git and create the initial commit:
   ```powershell
   git init
   git add .
   git commit -m "feat: digital command center portfolio & CMS ready for live deployment"
   git branch -M main
   ```

3. Create a new repository on [GitHub](https://github.com/new):
   - Repository name: `lyrch-portfolio` (or your choice)
   - Visibility: **Public** or **Private**
   - Do **NOT** initialize with README or .gitignore (we already have them)

4. Link your local repository and push:
   ```powershell
   git remote add origin https://github.com/<your-username>/lyrch-portfolio.git
   git push -u origin main
   ```

---

## Step 2: Set Up Free TiDB Cloud (Serverless MySQL)

1. Sign up for free at [TiDB Cloud](https://tidbcloud.com) (Log in with GitHub or Google).
2. Click **Create Cluster**:
   - Choose **Serverless** (Free forever).
   - Region: Select closest to you (e.g. `ap-southeast-1` Singapore or `us-east-1` Oregon).
   - Click **Create**.
3. Once created (takes ~15 seconds), click **Connect**:
   - Select **Connection Type**: `General` or `Python` (with PyMySQL).
   - Generate a password and save it securely.
4. Note your connection details or connection string:
   - **Host**: e.g. `gateway01.us-east-1.prod.aws.tidbcloud.com`
   - **Port**: `4000`
   - **User**: e.g. `24abcde.root`
   - **Password**: `your-generated-password`
   - **Database**: `test` or create `lyrch_portfolio`

Your full `DATABASE_URL` format:
```text
mysql+pymysql://<user>:<password>@<host>:4000/<dbname>?charset=utf8mb4
```

> **Note**: Our application automatically uses `certifi` to handle the required SSL certificate for TiDB Cloud on Render and Windows.

---

## Step 3: Deploy to Render.com

1. Sign up or log in at [Render.com](https://render.com) (Log in with GitHub).
2. Click **New +** in the top right &rarr; select **Web Service**.
3. Choose **Build and deploy from a Git repository** &rarr; connect your GitHub repo `lyrch-portfolio`.
4. Configure your Web Service:
   - **Name**: `lyrch-portfolio` (or your custom name)
   - **Region**: Oregon (US West) or Singapore
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn run:app`
   - **Instance Type**: `Free`

5. Under **Environment Variables**, add the following keys:
   | Key | Value | Description |
   |---|---|---|
   | `FLASK_ENV` | `production` | Enables production configuration |
   | `SECRET_KEY` | *(Click "Generate" or type a random string)* | Encrypts session cookies |
   | `DATABASE_URL` | `mysql+pymysql://<user>:<password>@<host>:4000/<dbname>?charset=utf8mb4` | Your TiDB Cloud connection string |
   | `TIDB_SSL` | `true` | Enforces SSL verification for TiDB |

6. Click **Deploy Web Service**!
   - Render will pull your GitHub repository, install dependencies, and start `gunicorn`.

---

## Step 4: Seed Database Tables on TiDB Cloud

You can initialize and seed the demo data on your live TiDB database using either of these two easy methods:

### Method A: Seed from your Local Terminal (Easiest)
From your local PowerShell, run `seed-demo` targeting your TiDB Cloud database:

```powershell
$env:DATABASE_URL="mysql+pymysql://<user>:<password>@<host>:4000/<dbname>?charset=utf8mb4"
$env:TIDB_SSL="true"
.\.venv\Scripts\python.exe run.py seed-demo
```
This connects to your TiDB Cloud database, creates all tables, seeds the default admin (`admin` / `admin123`), project case studies, and site settings in ~5 seconds!

### Method B: Seed using Render Shell
1. In your Render Dashboard, click your `lyrch-portfolio` service.
2. Click the **Shell** tab on the left.
3. Run:
   ```bash
   flask seed-demo
   ```

---

## Step 5: Verify Your Live Site

Visit your Render web service URL (e.g. `https://lyrch-portfolio.onrender.com`):
* **Public Command Center**: `https://<your-subdomain>.onrender.com`
* **Admin Login**: `https://<your-subdomain>.onrender.com/auth/login`
  - **Username**: `admin`
  - **Password**: `admin123`
* **Dashboard Customizer**: `https://<your-subdomain>.onrender.com/admin/settings`

---

## Continuous Deployment (Auto-Deploy)
Whenever you make changes to your code locally:
```powershell
git add .
git commit -m "update: tweaks to portfolio"
git push origin main
```
Render will automatically detect the new commit on GitHub, rebuild, and redeploy your live website with zero downtime!

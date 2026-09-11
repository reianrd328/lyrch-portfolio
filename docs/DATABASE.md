# Database Schema & Entity Relationships

The LYRCH Command Center utilizes MySQL (with SQLite fallback) managed through Flask-SQLAlchemy.

## Tables Overview

### 1. `users`
- `id` (INTEGER, Primary Key)
- `username` (VARCHAR 64, Unique)
- `email` (VARCHAR 120, Unique)
- `password_hash` (VARCHAR 255)
- `display_name` (VARCHAR 100)
- `role` (VARCHAR 20, default: 'admin')
- `created_at` (DATETIME)

### 2. `projects`
- `id` (INTEGER, Primary Key)
- `title` (VARCHAR 150)
- `slug` (VARCHAR 180, Unique)
- `subtitle` (VARCHAR 255)
- `category` (VARCHAR 50)  # IT System, Web App, Desktop, AI
- `status_badge` (VARCHAR 30) # Live, Beta, Demo, In Progress
- `featured` (BOOLEAN, default: False)
- `order_index` (INTEGER, default: 0)
- `short_description` (TEXT)
- `full_description` (TEXT)
- `technologies` (VARCHAR 255) # Comma-separated or JSON list
- `features` (TEXT) # JSON list or bullet points
- `thumbnail_url` (VARCHAR 255)
- `banner_url` (VARCHAR 255)
- `github_url` (VARCHAR 255)
- `demo_url` (VARCHAR 255)
- `documentation_url` (VARCHAR 255)
- `visibility` (VARCHAR 20) # published, draft, private
- `created_at` (DATETIME)
- `updated_at` (DATETIME)

### 3. `videos` (AI Video Studio)
- `id` (INTEGER, Primary Key)
- `title` (VARCHAR 150)
- `slug` (VARCHAR 180, Unique)
- `description` (TEXT)
- `video_url` (VARCHAR 255)
- `thumbnail_url` (VARCHAR 255)
- `category` (VARCHAR 50) # Commercial, Reel, TikTok, Experiment
- `tools_used` (VARCHAR 255) # e.g. Gemini, Midjourney, Premiere
- `platforms` (VARCHAR 255) # Facebook, TikTok, YouTube
- `duration` (VARCHAR 20) # e.g. 00:10
- `aspect_ratio` (VARCHAR 20) # e.g. 9:16, 16:9
- `prompt_text` (TEXT)
- `workflow_notes` (TEXT)
- `featured` (BOOLEAN, default: False)
- `visibility` (VARCHAR 20) # published, draft, private
- `created_at` (DATETIME)

### 4. `gallery`
- `id` (INTEGER, Primary Key)
- `title` (VARCHAR 150)
- `category` (VARCHAR 50)
- `image_url` (VARCHAR 255)
- `thumbnail_url` (VARCHAR 255)
- `description` (TEXT)
- `featured` (BOOLEAN, default: False)
- `created_at` (DATETIME)

### 5. `documents`
- `id` (INTEGER, Primary Key)
- `title` (VARCHAR 150)
- `file_path` (VARCHAR 255)
- `file_type` (VARCHAR 20)
- `file_size` (INTEGER)
- `category` (VARCHAR 50)
- `description` (TEXT)
- `allow_download` (BOOLEAN, default: True)
- `is_public` (BOOLEAN, default: True)
- `created_at` (DATETIME)

### 6. `skills`
- `id` (INTEGER, Primary Key)
- `name` (VARCHAR 100)
- `category` (VARCHAR 50) # IT Operations, Development, AI & Media
- `level` (INTEGER) # 1-100 percentage
- `icon_name` (VARCHAR 50)
- `order_index` (INTEGER, default: 0)

### 7. `experiences`
- `id` (INTEGER, Primary Key)
- `role_title` (VARCHAR 150)
- `company` (VARCHAR 150)
- `location` (VARCHAR 100)
- `period` (VARCHAR 50) # e.g. 2008 - Present
- `description` (TEXT)
- `highlights` (TEXT)
- `order_index` (INTEGER, default: 0)

### 8. `activity_logs`
- `id` (INTEGER, Primary Key)
- `action_text` (VARCHAR 255)
- `action_type` (VARCHAR 50) # project, video, network, git
- `time_ago_label` (VARCHAR 50)
- `created_at` (DATETIME)


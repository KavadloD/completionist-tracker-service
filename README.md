Completionist Tracker - Service (Backend)

Overview
This repository contains the backend service for Completionist Tracker. It exposes a simple REST API for user accounts, games, checklists, progress, and community templates. The service stores data in PostgreSQL and ships with database migrations.

Tech stack
- Python, Flask, Flask-SQLAlchemy, Flask-Migrate
- PostgreSQL
- Gunicorn for production serving
- CORS support

Requirements
- Python 3.12+
- PostgreSQL running locally or in the cloud
- pip and virtualenv (optional but recommended)

Environment variables
- DATABASE_URL  Postgres connection string. Default if unset:
  postgresql://postgres:postgres123@localhost/completionist_db
  Note: postgres:// is also accepted and normalized to postgresql://
- CORS_ORIGINS  Allowed origins for the API. Comma-separated. Default: *

Quick start (local)
1) Create a virtual environment and install dependencies
   python -m venv .venv
   .venv\Scripts\Activate.ps1     (PowerShell)
   pip install -r requirements.txt

2) Set environment variables
   PowerShell:
     $env:DATABASE_URL = "postgresql://postgres:postgres123@localhost/completionist_db"
     $env:CORS_ORIGINS = "http://localhost:8000"
   macOS/Linux (bash):
     export DATABASE_URL=postgresql://postgres:postgres123@localhost/completionist_db
     export CORS_ORIGINS=http://localhost:8000

3) Initialize the database
   set FLASK_APP=app.py; flask db upgrade      (PowerShell)
   FLASK_APP=app.py flask db upgrade           (macOS/Linux)

4) Run the server
   flask run            (development)
   gunicorn app:app     (production-style run)

API summary
Auth
- POST /api/register
  Body: { "username": "...", "email": "...", "password": "..." }
  201 on success
- POST /api/login
  Body: { "email": "...", "password": "..." } OR { "username": "...", "password": "..." }
  200 on success

Games
- POST   /api/games
- GET    /api/games?user_id=:id
- GET    /api/games/:game_id
- PATCH  /api/games/:game_id
- DELETE /api/games/:game_id
- GET    /api/games/:game_id/progress

Checklist
- GET    /api/games/:game_id/checklist
- POST   /api/games/:game_id/checklist
- PUT    /api/checklist/:item_id
- DELETE /api/checklist/:item_id

Community
- GET    /api/community
- POST   /api/community
- GET    /api/community/:template_id
- POST   /api/community/import/:template_id

Thumbnails
- PATCH  /api/games/:game_id/thumbnail
- GET    /api/games/:game_id/thumbnail
- GET    /api/games/thumbnails?user_id=:id
- GET    /api/games/with-thumbnails
- POST   /api/admin/thumbnails/backfill[?user_id]

Data model (tables)
- users                (user_id, username, email unique, password_hash)
- games                (game_id, user_id, title, platform, genre, run_type, tags, cover_url, thumbnail_url)
- checklist_items      (checklist_item_id, game_id, description, completed, order) with unique (game_id, order)
- community_checklist  (community_checklist_id, title, description, platform, genre, run_type, tags, thumbnail_url, created_by_user_id)
- community_items      (community_item_id, community_checklist_id, description, order) with unique (community_checklist_id, order)

Migrations
- Upgrade to the latest:
  FLASK_APP=app.py flask db upgrade
- Create a new migration after model changes:
  FLASK_APP=app.py flask db migrate -m "describe change"
- If your DB is out of sync and empty, you can stamp and then upgrade:
  FLASK_APP=app.py flask db stamp head && FLASK_APP=app.py flask db upgrade

Deployment
- Procfile (Heroku/Fly):
    release: flask db upgrade
    web: gunicorn app:app
- Render:
  - Start command: gunicorn app:app
  - Pre-deploy or post-deploy hook: flask db upgrade
- Set DATABASE_URL and CORS_ORIGINS in your host’s dashboard.

Troubleshooting
- CORS errors: ensure CORS_ORIGINS includes your frontend origin.
- Connection refused: verify DATABASE_URL and that Postgres is running.
- 500 errors on list endpoints: run migrations (flask db upgrade).
- Alembic head mismatch: flask db heads, flask db current, then migrate/upgrade as needed.

Project structure (common files)
app.py               Flask app and routes
models.py            SQLAlchemy models
users.py             Auth handlers
checklist.py         Checklist handlers
migrations/          Alembic migration scripts
requirements.txt     Pinned dependencies
Procfile             Process types for deploy

Contact
Maintainer: Dorian Kavadlo
Email: dkavadlo@gmail.com
GitHub: https://github.com/KavadloD
LinkedIn: https://www.linkedin.com/in/dorian-kavadlo/

License
MIT for the service code. Any third-party assets may carry their own terms.

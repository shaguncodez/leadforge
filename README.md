# LeadForge ⚡

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0.35-red.svg?style=flat)](https://www.sqlalchemy.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Ruff/Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

> **AI-Assisted Lead Management & Scoring Platform** with deterministic explainable intelligence, real-time analytics, interaction logging, and follow-up tracking.

---

## 🌟 Key Features

- **⚡ High-Performance Async Backend**: Built with FastAPI and SQLAlchemy 2.0 async engine (`aiosqlite`/PostgreSQL).
- **🎯 Deterministic Lead Scoring (0–100)**:
  - **Purchase Intent (max 35 pts)**: Pipeline stage evaluation (`new`=5, `contacted`=15, `qualified`=25, `proposal`=35, `won`=35).
  - **Engagement Frequency (max 25 pts)**: Tiered interaction count evaluation (1=5pts, 2-3=10pts, 4-5=15pts, 6+=25pts).
  - **Profile Completeness (max 20 pts)**: Contact data readiness (Email=7pts, Company=7pts, Phone=6pts).
  - **Recency Boost (max 20 pts)**: Active touchpoint verified within the past 7 days.
  - **Full Explainability**: Breakdown and reasoning dict explaining every single point award.
- **🔐 Multi-Tenant Role-Based Access Control**:
  - Secure bcrypt password hashing and signed JWT bearer tokens.
  - `admin` role with global visibility and lead reassignment.
  - `member` role isolated to owned leads and assigned tasks.
- **📊 Real-Time Pipeline Analytics**:
  - Conversion rate calculation, deal stage breakdown, source attribution, and average lead scores.
- **📝 Interaction History & Follow-Up Tasks**:
  - Log calls, emails, meetings, and internal notes.
  - Automated lead score recalculation upon every new activity log.
  - Follow-up task management with due dates and completion tracking.
- **🎨 Modern Responsive SPA Dashboard**:
  - Hosted directly via FastAPI `/static` or deployable standalone to **GitHub Pages**.
  - Tailwind CSS, clean dark/light mode toggle, filter bar, search, detail drawer, and score gauges.
  - Configurable backend endpoint for cross-origin deployments.
- **🛡️ Production Ready**:
  - Full async Alembic database migrations.
  - Docker, Docker Compose, Render.com, and Railway deployment specifications.
  - 100% test pass rate with in-memory SQLite async test suite.

---

## 🏗️ Project Architecture

```
leadforge/
├── alembic/                  # Alembic async migration environment
│   ├── versions/             # Auto-generated database migration revisions
│   ├── env.py                # Async engine runner for Alembic
│   └── script.py.mako        # Migration template
├── app/
│   ├── models/               # SQLAlchemy 2.x declarative models
│   │   ├── user.py           # User & RoleEnum models
│   │   ├── lead.py           # Lead, LeadStatus, LeadSource models
│   │   ├── activity.py       # Activity model & ActivityType enum
│   │   ├── task.py           # FollowUpTask & TaskStatus enum
│   │   └── audit_log.py      # AuditLog model with JSON payload
│   ├── schemas/              # Pydantic v2 schemas
│   │   ├── common.py         # Pagination & response wrappers
│   │   ├── user.py           # UserCreate, UserLogin, Token
│   │   ├── lead.py           # LeadCreate, LeadUpdate, LeadScoreResponse
│   │   ├── activity.py       # ActivityCreate, ActivityResponse
│   │   └── task.py           # TaskCreate, TaskUpdate, TaskResponse
│   ├── services/             # Core business logic & scoring
│   │   ├── auth_service.py   # JWT, password hashing, get_current_user
│   │   ├── scoring_service.py# Lead scoring calculation & explanations
│   │   ├── lead_service.py   # Lead CRUD & ownership enforcement
│   │   └── analytics_service.py# Dashboard KPIs & conversion rate calculations
│   ├── routers/              # FastAPI route endpoints
│   │   ├── auth.py           # /api/v1/auth (register, login, me)
│   │   ├── leads.py          # /api/v1/leads (CRUD, search, score breakdown)
│   │   ├── activities.py     # /api/v1/leads/{id}/activities
│   │   ├── tasks.py          # /api/v1/tasks (CRUD, filter by lead/status)
│   │   └── analytics.py      # /api/v1/analytics/summary
│   ├── config.py             # Pydantic settings from .env
│   ├── database.py           # Async SQLAlchemy session and engine
│   ├── middleware.py         # Request logging and execution timing
│   └── main.py               # FastAPI application entrypoint & static mount
├── static/                   # SPA Single Page Application for GitHub Pages
│   ├── index.html            # Responsive Tailwind CSS dashboard
│   └── 404.html              # GitHub Pages fallback router
├── tests/                    # Pytest test suite
│   ├── conftest.py           # In-memory DB, async client & auth fixtures
│   ├── test_auth.py          # Authentication tests
│   ├── test_leads.py         # Lead CRUD, pagination, filtering, ownership tests
│   └── test_scoring.py       # Deterministic scoring tests
├── Dockerfile                # Production container specification
├── docker-compose.yml        # Multi-container orchestration
├── render.yaml               # Render.com deployment manifest
├── Procfile                  # Railway / Heroku deployment process
├── requirements.txt          # Python dependencies
└── pytest.ini                # Pytest configuration
```

---

## 🚀 Quick Start (Local Setup)

### 1. Prerequisites
- Python 3.11, 3.12, or 3.13
- Git

### 2. Clone and Setup Environment

```bash
git clone https://github.com/your-username/leadforge.git
cd leadforge

# Create a virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

Copy the example configuration:
```bash
cp .env.example .env
```

Default `.env` settings:
```env
DATABASE_URL=sqlite+aiosqlite:///./leadforge.db
SECRET_KEY=leadforge-dev-secret-key-32bytes-secure-random-token-2026
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

### 4. Run Database Migrations

```bash
alembic upgrade head
```

### 5. Launch the Server

```bash
uvicorn app.main:app --reload --port 8000
```

Once running:
- **Interactive API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Built-in Web Dashboard**: [http://localhost:8000/static/index.html](http://localhost:8000/static/index.html)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 🧪 Running Automated Tests

Run the complete test suite with pytest:

```bash
pytest -v
```

All 19 test cases run asynchronously against an isolated in-memory SQLite database instance:
- `tests/test_auth.py`: Registration, duplicate check, JSON/form login, JWT validation.
- `tests/test_leads.py`: Lead CRUD, ownership isolation, pagination, status & source filters, text search.
- `tests/test_scoring.py`: Purchase intent tiers, profile completeness, activity engagement, recency window, and live API score recalculation.

---

## 🧠 Lead Scoring Algorithm Explained

LeadForge uses a transparent, deterministic mathematical scoring algorithm that computes an overall score from **0 to 100**:

$$\text{Total Score} = \min(100, S_{\text{intent}} + S_{\text{engagement}} + S_{\text{profile}} + S_{\text{recency}})$$

| Component | Max Points | Evaluation Logic |
| :--- | :---: | :--- |
| **Purchase Intent** | **35 pts** | Evaluates sales pipeline stage:<br>• `new`: 5 pts<br>• `contacted`: 15 pts<br>• `qualified`: 25 pts<br>• `proposal`: 35 pts<br>• `won`: 35 pts<br>• `lost`: 0 pts |
| **Engagement** | **25 pts** | Based on number of logged touchpoints:<br>• 0 activities: 0 pts<br>• 1 activity: 5 pts<br>• 2–3 activities: 10 pts<br>• 4–5 activities: 15 pts<br>• 6+ activities: 25 pts |
| **Profile Completeness** | **20 pts** | Contact readiness:<br>• Email present: +7 pts<br>• Company present: +7 pts<br>• Phone present: +6 pts |
| **Recency** | **20 pts** | Velocity factor:<br>• Interaction logged within the past 7 days: +20 pts<br>• No interaction within last 7 days: 0 pts |

### Example Score Breakdown Response

```json
{
  "lead_id": "c62043e0-bf4d-4df8-8687-f8232c4df2fa",
  "score": 75,
  "breakdown": {
    "purchase_intent": 25,
    "engagement": 10,
    "profile_completeness": 20,
    "recency": 20,
    "total": 75
  },
  "explanation": {
    "purchase_intent": {
      "score": 25,
      "max": 35,
      "status": "qualified",
      "description": "Status 'qualified' contributes 25/35 points based on sales pipeline stage."
    },
    "engagement": {
      "score": 10,
      "max": 25,
      "activity_count": 2,
      "description": "2 logged interaction(s) contribute 10/25 points."
    },
    "profile_completeness": {
      "score": 20,
      "max": 20,
      "fields": ["email", "company", "phone"],
      "description": "Profile completeness (3/3 fields present: email, company, phone) contributes 20/20 points."
    },
    "recency": {
      "score": 20,
      "max": 20,
      "has_recent_activity": true,
      "description": "Active in last 7 days (+20 points)"
    },
    "summary": "Calculated LeadForge AI Score: 75/100."
  }
}
```

---

## 🌐 Deploying Frontend to GitHub Pages

The `static/` folder contains a standalone, zero-build Single Page Application using Tailwind CSS via CDN:

1. Push your repository to GitHub.
2. In your repository settings, go to **Settings > Pages**.
3. Under **Build and deployment**, select **Deploy from a branch**.
4. Set Branch to `main` (or `gh-pages`) and folder to `/static` (or use GitHub Actions).
5. Open your deployed GitHub Pages URL (e.g. `https://your-user.github.io/leadforge/`).
6. Click the API indicator pill in the top header and configure your deployed backend API URL (e.g. `https://leadforge-api.onrender.com`).

---

## ☁️ Backend Deployment Guide

### Deploying to Render.com (Free Tier)

This repository includes a preconfigured `render.yaml` blueprint:

1. Create a free account on [Render.com](https://render.com).
2. Connect your GitHub repository.
3. Click **New + > Blueprint** and select this repository.
4. Render will automatically read `render.yaml` and configure the web service with:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Health check: `/health`

### Deploying with Docker / Docker Compose

```bash
# Build and run container
docker compose up -d --build

# Verify container logs
docker compose logs -f leadforge-api
```

---

## 📷 Screenshots

| Dashboard & Pipeline KPIs | AI Score Explanation Breakdown |
| :---: | :---: |
| *(Dashboard with KPIs, search, filtering, and lead table)* | *(Drawer showing score progress bars and activity timeline)* |

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

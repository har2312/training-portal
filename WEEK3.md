# Week 3 — Progress Report

**Project:** Smart Training Allotment & Management System
**Organization:** Prasar Bharati / NABM (government broadcasting)
**Stack:** FastAPI · SQLAlchemy · scikit-learn (backend) · React + Vite + Tailwind CSS (frontend) · **PostgreSQL in production** (SQLite for local dev)

> Weeks 1–2 built the full-stack app + the advanced AI (topic-aware ML, The Oracle, chatbot). Week 3 took it **live on the internet** with a proper production database, and refined the workshop-creation UX. See [WEEK1.md](WEEK1.md) and [WEEK2.md](WEEK2.md).

---

## 1. Goals for Week 3
1. Deploy the whole system publicly on free infrastructure (frontend + backend + a real database).
2. Redesign the database for production and future needs (more tables, proper separation).
3. Improve the "Add Workshop" form: selectable designation sets + title autocomplete.

---

## 2. Live Deployment (free stack)

| Layer | Platform | Notes |
|-------|----------|-------|
| Database | **Neon** (PostgreSQL) | Free & **persistent** (unlike Render's expiring free DB) |
| Backend API | **Render** (Web Service) | `https://training-portal-api-7q4a.onrender.com` |
| Frontend | **Vercel** | Auto-built Vite/React static site |

- Full click-by-click instructions live in [DEPLOYMENT.md](DEPLOYMENT.md).
- **Auto-deploy pipeline:** every `git push` to `main` rebuilds both Render and Vercel automatically.
- Repo initialized and pushed to GitHub (`har2312/training-portal`).

### Made deployment-ready
- **[database.py](backend/app/database.py)** auto-normalizes managed-Postgres URLs (`postgres://…` → psycopg v3 driver) and adds connection pooling (`pool_pre_ping`, `pool_recycle`) so free-tier idle connections don't error. Also enforces `PRAGMA foreign_keys=ON` on SQLite so local dev matches Postgres.
- **Self-contained seeding:** CSVs moved into `backend/data/`; `seed_if_empty()` populates a fresh DB on first boot **without** wiping existing data (destructive `seed()` remains for local resets).
- **Env-driven CORS** (`FRONTEND_ORIGIN` + a default `*.vercel.app` regex) and a **`/health`** probe.
- **Startup auto-migration** (`_ensure_schema`) runs `ALTER TABLE … ADD COLUMN` for new additive columns, so schema changes deploy without dropping the production DB.
- Deploy config: `render.yaml`, `backend/.python-version` (3.11.9), root `.gitignore`, `frontend/.env.example`; frontend reads `VITE_API_URL`.

---

## 3. Database Redesign — 10 Tables

The 5 core tables gained 5 future-proof ones ([models.py](backend/app/models.py)):

| Table | Purpose |
|-------|---------|
| `personnel` | People + auth + specialization |
| `workshops` | Programs (topic, min_designation, **allowed_designations**, dates, capacity) |
| `allotments` | Live assignments (Pending/Accepted/Rejected) |
| `historical_allotments` | ML training seed |
| `training_history` | Topic-wise completed trainings |
| **`allotment_events`** | **Audit trail** — every status change (from/to, actor, timestamp) |
| **`notifications`** | In-app alerts (invitations, updates) |
| **`workshop_feedback`** | Post-training ratings/comments (future feedback loop) |
| **`topics`** | Reference/lookup list of training topics |
| **`designations`** | Reference designation hierarchy (with rank) |

- **Audit + notifications are wired into every allotment write path** (commit, manual add, replacement, admin accept/reject, personnel accept/decline) via [services.py](backend/app/services.py).
- New endpoints: `GET /api/me/{id}/notifications`, `POST /api/notifications/{id}/read`.
- Reference tables (`topics`, `designations`) are seeded so topics/hierarchy are data-driven and extensible.

---

## 4. Workshop Form Upgrades

### 4.1 Selectable eligible designations (not a threshold)
- Admin now **picks specific grades** for a workshop (e.g. *DDG + EA only*) instead of a rigid "X & above" order. Selections show as removable **chips (× to remove)**.
- New `Workshop.allowed_designations` column (CSV) drives **membership-based** eligibility; the legacy `min_designation` threshold is kept as a **fallback** so pre-existing workshops keep working.
- Backend: `designation_allowed()` in [constants.py](backend/app/constants.py); `/api/workshops` create handles the list→CSV and derives `min_designation` (most senior selected) for display.
- XAI reason adapts: *"…EA (eligible grade)…"*.

### 4.2 Title autocomplete
- As the admin types a title, a dropdown suggests **existing workshop titles** (reuse allowed); free-typing a new title still works.
- New `GET /api/workshop-titles` endpoint (distinct titles); [WorkshopForm.jsx](frontend/src/components/admin/WorkshopForm.jsx) filters client-side.

---

## 5. Production Bugs Found & Fixed

1. **Postgres FK-ordering failure on first boot** — SQLite silently ignores foreign keys, so the single big seed `commit()` "worked" locally but Postgres rejected `historical_allotments` inserted before their parent `workshops`. **Fix:** commit parent tables first; enforce FK on SQLite so it can never hide again.
2. **Login blocked in production (`OPTIONS //api/login 400`)** — two causes:
   - CORS preflight rejected because the backend didn't recognize the Vercel origin → **fix:** allow any `*.vercel.app` origin via `allow_origin_regex`.
   - A trailing slash in `VITE_API_URL` produced `//api/login` → **fix:** frontend strips trailing slashes from the base URL.
3. **Schema change vs. live DB** — adding `allowed_designations` to an existing production DB → **fix:** startup auto-migration adds the column in place (no data loss, no manual reset).

---

## 6. New / Changed Endpoints (Week 3)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | Liveness probe for the host |
| GET | `/api/workshop-titles` | Distinct titles for autocomplete |
| GET | `/api/me/{id}/notifications` | Personnel notifications |
| POST | `/api/notifications/{id}/read` | Mark a notification read |

Plus updated `POST /api/workshops` (accepts `allowed_designations` list) and audit/notification side-effects on all allotment writes.

---

## 7. Verified Working
- Fresh-boot flow (empty DB → auto-create tables → seed → train → serve) confirmed locally with FK enforcement (Postgres parity).
- Live on Render: `Application startup complete`, `/health` → `{"status":"ok"}`.
- Login works end-to-end from the Vercel frontend after the CORS + trailing-slash fixes.
- Hand-picked non-contiguous designation set (`DDG + EA`) restricts eligibility to exactly those grades; legacy workshops still allot via fallback.
- Title autocomplete returns 16 distinct titles; audit trail + notifications populate on allotment actions.
- Frontend builds clean.

---

## 8. How to Run

**Local dev:**
```powershell
cd c:\Users\itsha\training-portal\backend
C:\python310\python.exe -m app.seed
C:\python310\python.exe -m uvicorn app.main:app --reload
# separate terminal
cd c:\Users\itsha\training-portal\frontend
npm run dev
```

**Production:** just `git push` — Render + Vercel auto-redeploy. Reset the prod DB only if needed (Neon SQL editor: `DROP SCHEMA public CASCADE; CREATE SCHEMA public;` then restart Render).

**Demo logins:** admin `admin`/`admin` · personnel `pb001`/`password`.

---

## 9. Known Gaps / Planned for Next Week
- **Auth is still a demo token, not signed JWT**, and endpoints don't enforce the caller's role. **This is the top priority before the system handles real personnel data.**
- Render free tier **cold-starts** (~50s) after ~15 min idle — acceptable for a demo; a paid tier or a keep-alive ping removes it.
- Notifications exist in the DB + API but aren't yet surfaced in the UI (a notification bell is the natural next feature).
- Consider Alembic for versioned migrations instead of the lightweight startup auto-migration.
- Move the deterministic data generator into the repo (still a scratch script).

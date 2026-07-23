# Week 1 — Progress Report

**Project:** Smart Training Allotment & Management System
**Organization:** Prasar Bharati / NABM (government broadcasting)
**Stack:** FastAPI · SQLAlchemy · scikit-learn (backend) · React + Vite + Tailwind CSS (frontend) · SQLite (dev) → PostgreSQL (prod)

---

## 1. Goal for Week 1

Take the existing CSV-based AI allotment prototype and turn it into a runnable full-stack
application: a real database, a proper API, advanced AI features, and two role-based
dashboards (Admin + Personnel) — plus a realistic dataset so the whole thing demos smoothly.

---

## 2. What We Started With

- A single `main.py` FastAPI file reading three CSVs (`personnel_dataset.csv`,
  `training_workshops.csv`, `historical_allotments.csv`) with pandas.
- Two endpoints: `GET /api/workshops` and `GET /api/allot/{program_id}`.
- Allotment logic: hard rules (retirement filter, stream/designation match) + a Random
  Forest ML ranking + "local-first" zone cost optimization.
- No database, no frontend, no persistence, no auth.

---

## 3. What We Built This Week

### 3.1 Database Migration (CSV → SQLAlchemy)
- Moved from pandas CSVs to a real relational DB via SQLAlchemy ORM.
- **SQLite for development**, switchable to **PostgreSQL in production** by setting the
  `DATABASE_URL` env var — no code changes required.
- Four models in [backend/app/models.py](backend/app/models.py):
  - `Personnel` — incl. admin-only `performance_score` and added auth fields
    (`username`, `password_hash`, `role`).
  - `Workshop` — training programs.
  - `Allotment` — **live** allotments (Pending/Accepted/Rejected) created by Auto-Allot.
  - `HistoricalAllotment` — past outcomes used **only** to train the ML model.
- **Key design decision:** live allotments and historical training data are **two separate
  tables**. Mixing them would corrupt either the model or the live workflow.
- [backend/app/seed.py](backend/app/seed.py) loads the CSVs into the DB and creates demo
  logins.

### 3.2 API Rebuild (DB-backed FastAPI)
- All endpoints now read/write the database instead of CSVs — see
  [backend/app/main.py](backend/app/main.py).
- Pydantic schemas ([backend/app/schemas.py](backend/app/schemas.py)) act as the API
  contract and are the **enforcement point for hiding `Performance_Score`**:
  personnel-facing responses use `PersonnelPublic` (no score); admin responses use
  `PersonnelAdmin`. The score never leaves the server for personnel — it can't be read
  from the browser network tab.
- **Auth:** simple role-based login (`POST /api/login`) using bcrypt password hashing
  ([backend/app/security.py](backend/app/security.py)). Returns a demo token
  (JWT is a planned upgrade).

### 3.3 Advanced AI Features
1. **Explainable AI (XAI)** — `build_reason()` in [backend/app/ml.py](backend/app/ml.py)
   turns the numeric decision into a human-readable string, e.g.
   *"Local zone (saves travel) | No prior trainings (top priority) | High performance"*.
   Returned alongside the match probability. **Admin-only** (it references performance).
2. **Auto-Replacement / Smart Waitlist** — `POST /api/admin/allotments/{id}/reject`:
   rejecting frees the seat, re-runs the AI on the remaining pool (excluding everyone
   already allotted so rejected people never reappear), and returns the next-best
   candidate to instantly replace them.
3. **Continuous Learning** — `POST /api/ai/retrain`: retrains the Random Forest on the
   historical data **plus** live Accepted(→1)/Rejected(→0) allotments, so the model learns
   from human decisions over time. Returns sample count + a confidence score.
4. **Dashboard Metrics** — `GET /api/admin/metrics`: total workshops, personnel trained,
   AI confidence, and zone distribution for the charts.

### 3.4 Frontend (React + Vite + Tailwind)
Government-enterprise styling (slate / navy / emerald), clean and accessible.

- **Login** with role-based routing ([frontend/src/App.jsx](frontend/src/App.jsx)).
- **Admin — Command Center** ([frontend/src/pages/AdminDashboard.jsx](frontend/src/pages/AdminDashboard.jsx)):
  - KPI metric cards (Total Workshops, Personnel Trained, AI Confidence).
  - Recharts **"Training Distribution by Zone"** bar chart.
  - **Smart Allotment Table**: match-score progress bars, hover **"AI ⓘ"** tooltip
    showing the XAI reason, Accept/Reject buttons.
  - **Auto-Replacement animation**: rejected row slides out, next-best candidate slides in
    (Framer Motion).
  - **Retrain AI** button with loading state + success toast (react-hot-toast).
  - Add-Workshop form + Personnel Directory (admin sees performance scores).
- **Personnel Dashboard** ([frontend/src/pages/PersonnelDashboard.jsx](frontend/src/pages/PersonnelDashboard.jsx)):
  - **"Action Required"** card — Accept / Decline invitations (Decline silently triggers
    the backend replacement; **no AI metadata is ever shown to personnel**).
  - **My Profile** and **Training History** — performance score + AI metadata strictly hidden.

### 3.5 One-Command Setup
- Full Vite scaffold generated ([frontend/package.json](frontend/package.json),
  `vite.config.js`, `tailwind.config.js`, etc.) so the frontend runs with a single command
  — no manual `npm create vite` step.

### 3.6 Expanded Demo Dataset
Grew the seed data so pools exceed capacity and the AI features trigger naturally:

| Data | Before | After |
|------|--------|-------|
| Personnel | 30 | **95** (Engineering / Programme / Administration across 6 zones, incl. `EA` designation + near-retirement cases) |
| Workshops | 7 | **16** (several small capacities 4–8 to force waitlists) |
| Historical allotments | 12 | **84** (richer ML training) |

- **15 of 16 workshops** now have more eligible candidates than seats → the Smart Waitlist
  replacement triggers naturally.
- Pre-seeded ~25 live allotments (mix of Accepted/Pending/Rejected) so the dashboards are
  populated on first load.
- Original CSVs backed up as `*_original.csv`.

---

## 4. Bugs Found & Fixed This Week

1. **Two Python installs collision** — packages were in `C:\python310` but `python` on PATH
   was empty `C:\Python313`. Resolved by running everything with `C:\python310\python.exe`.
2. **passlib incompatible with bcrypt 5.0** — dropped passlib, switched to the `bcrypt`
   library directly ([backend/app/security.py](backend/app/security.py)).
3. **Administration courses matched zero personnel** — the stream filter blocked them
   (no one has `Stream = Administration`). Fixed: **"All Officers" courses now bypass the
   stream/designation filter** (they're genuinely open to all), matching the historical data.
4. **Admin account became a training candidate** — the "All Officers" change accidentally
   made `ADMIN01` eligible. Fixed: the engine now only considers `role == 'personnel'`.
5. **"Admin/Personnel not connected" confusion** — they always shared the same DB, but:
   default login `pb001` had no invite (now guaranteed one), Auto-Allot gave no feedback
   (now toasts the count), and pages didn't refresh (now **poll every 5s** + admin
   **↻ Refresh** button).

---

## 5. Project Structure (end of Week 1)

```
training-portal/
├── WEEK1.md                       # this file
├── README_FULLSTACK.md            # setup + architecture notes
├── personnel_dataset.csv          # expanded (95) — *_original.csv is the backup
├── training_workshops.csv         # expanded (16)
├── historical_allotments.csv      # expanded (84)
├── main.py                        # OLD CSV backend (kept for reference)
│
├── backend/
│   ├── requirements.txt
│   └── app/
│       ├── database.py            # engine/session (SQLite → Postgres)
│       ├── models.py              # SQLAlchemy ORM models
│       ├── schemas.py             # Pydantic contracts (hides performance_score)
│       ├── security.py            # bcrypt password hashing
│       ├── ml.py                  # Random Forest + XAI + ranking + retrain
│       ├── seed.py                # loads CSVs + pre-seeds live allotments
│       └── main.py                # FastAPI app (all endpoints)
│
└── frontend/
    └── src/
        ├── api/client.js          # single API client
        ├── components/
        │   ├── shared/ui.jsx      # Card, Button, Table, StatusBadge
        │   ├── admin/             # MetricCards, ZoneChart, RetrainButton,
        │   │                      #   WorkshopForm, WorkshopList,
        │   │                      #   SmartAllotmentTable, PersonnelDirectory
        │   └── personnel/         # MyProfile, MyAllotments, TrainingHistory
        ├── pages/                 # Login, AdminDashboard, PersonnelDashboard
        └── App.jsx                # role-based routing
```

---

## 6. API Endpoints (end of Week 1)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/login` | Role-based login |
| GET | `/api/workshops` | List workshops |
| POST | `/api/workshops` | Admin: create workshop |
| GET | `/api/allot/{program_id}` | Preview AI ranking (no DB write) + XAI |
| POST | `/api/allot/{program_id}/commit` | Admin: persist allotments as Pending |
| GET | `/api/admin/allotments/{program_id}` | Admin roster (scores, status, XAI) |
| POST | `/api/admin/allotments/{id}/accept` | Admin: confirm allotment |
| POST | `/api/admin/allotments/{id}/reject` | Admin: reject → returns replacement |
| GET | `/api/personnel` | Admin: personnel directory (with scores) |
| GET | `/api/me/{personnel_id}` | Personnel profile (NO score) |
| GET | `/api/me/{personnel_id}/allotments` | Personnel's allotments |
| PATCH | `/api/allotments/{id}` | Personnel: accept/decline (triggers replacement) |
| POST | `/api/ai/retrain` | Retrain model on latest feedback |
| GET | `/api/admin/metrics` | Dashboard KPIs + zone distribution |

---

## 7. How to Run

**Backend** (first time creates + seeds the DB):
```powershell
cd c:\Users\itsha\training-portal\backend
C:\python310\python.exe -m pip install -r requirements.txt
C:\python310\python.exe -m app.seed
C:\python310\python.exe -m uvicorn app.main:app --reload
```
→ API at http://localhost:8000/docs

**Frontend** (separate terminal):
```powershell
cd c:\Users\itsha\training-portal\frontend
npm install
npm run dev
```
→ App at http://localhost:5173

**Demo logins:**

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin` |
| Personnel | `pb001` | `password` (any `pbNNN` works) |

**Demo flow:** Admin → Auto-Allot a workshop → note a Personnel ID from the table →
log in as that ID (lowercase) → see the invitation → Accept/Decline → watch the admin
side update (poll or ↻ Refresh), with the AI sliding in a replacement on reject.

---

## 8. Verified Working
- DB seeded: 95 personnel, 16 workshops, 84 historical rows, ~25 live allotments.
- XAI reason strings generated correctly.
- Auto-replacement promotes the next-best candidate with a reason.
- Retrain reported ~96% confidence on the expanded data.
- Cross-dashboard sync proven: admin allot → personnel sees invite; personnel accept →
  admin sees Accepted.
- Personnel decline response leaks **no** AI metadata (verified response keys).
- Frontend builds clean.

---

## 9. Known Gaps / Planned for Next Week
- **Authentication is a demo token, not a signed JWT**, and endpoints don't yet enforce
  the caller's role — an admin API route can currently be hit by anyone who knows the URL.
  **Adding JWT + a role-guard dependency is the top priority before deployment.**
- Move the deterministic data generator into the repo (currently a scratch script).
- Consider PostgreSQL migration + Alembic migrations for schema versioning.
- Frontend bundle is large (Recharts) — could code-split if needed.

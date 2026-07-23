# Smart Training Allotment System — Full-Stack

## Folder Structure

```
training-portal/
├── personnel_dataset.csv          # existing source data (used to seed the DB)
├── training_workshops.csv
├── historical_allotments.csv
├── main.py                        # OLD CSV backend (kept for reference)
│
├── backend/
│   ├── requirements.txt
│   └── app/
│       ├── database.py            # engine/session (SQLite dev → Postgres prod)
│       ├── models.py             # SQLAlchemy ORM models
│       ├── schemas.py            # Pydantic contracts (hides Performance_Score)
│       ├── ml.py                 # Random Forest + allotment engine (from main.py)
│       ├── seed.py               # loads CSVs into the DB
│       └── main.py               # FastAPI app (DB-backed endpoints)
│
└── frontend/                      # Vite + React + Tailwind
    └── src/
        ├── api/client.js          # single API client
        ├── components/
        │   ├── shared/ui.jsx      # Card, Button, Table, StatusBadge
        │   ├── admin/             # WorkshopForm, WorkshopList, AllotmentPanel, PersonnelDirectory
        │   └── personnel/         # MyProfile, MyAllotments, TrainingHistory
        ├── pages/                 # Login, AdminDashboard, PersonnelDashboard
        └── App.jsx                # role-based routing
```

## Backend — run

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -r requirements.txt
python -m app.seed                                    # create + populate the DB
uvicorn app.main:app --reload                         # http://localhost:8000/docs
```

Switch to PostgreSQL for production with **no code changes** — just set:
```bash
set DATABASE_URL=postgresql+psycopg://user:pass@host:5432/training
```

## Frontend — scaffold + run

The React source files are provided; scaffold the Vite shell around them:

```bash
cd frontend
npm create vite@latest . -- --template react     # keep src files when prompted, or overwrite index.html/main.jsx only
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

In `tailwind.config.js` set:
```js
content: ["./index.html", "./src/**/*.{js,jsx}"],
```
In `src/index.css` add the three Tailwind directives (`@tailwind base; @tailwind components; @tailwind utilities;`) and import it in `main.jsx`. Then:

```bash
npm run dev                                       # http://localhost:5173
```

## Demo logins (created by seed.py)
| Role      | Username | Password   |
|-----------|----------|------------|
| Admin     | `admin`  | `admin`    |
| Personnel | `pb001`  | `password` |

## Key design decisions
- **Two allotment tables.** `historical_allotments` (your CSV) is training data for the ML model; `allotments` is the live table created by Auto-Allot and updated when personnel accept/reject.
- **Performance_Score hidden server-side.** Personnel endpoints return the `PersonnelPublic` schema, which omits the score entirely — it never leaves the server, so it can't be inspected in the browser network tab. Admin endpoints use `PersonnelAdmin`.
- **Preview vs. commit.** `GET /api/allot/{id}` previews the ranking without writing; `POST /api/allot/{id}/commit` persists it. This keeps the AI logic idempotent and lets you show a dry run before assigning.
- **Auth is a demo token.** Swap `login()` for signed JWTs + a dependency that checks the role before production.
```

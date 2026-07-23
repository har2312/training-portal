# Deployment Guide — Free Stack (Neon + Render + Vercel)

This deploys the whole app for free:

| Layer | Platform | Why |
|-------|----------|-----|
| Database | **Neon** (PostgreSQL) | Free, **persistent** (Render's free DB expires; Neon doesn't) |
| Backend API | **Render** (Web Service) | Free FastAPI hosting |
| Frontend | **Vercel** | Free Vite/React static hosting |

**Order matters** (there's a chicken-and-egg with URLs):
**1) GitHub → 2) Neon DB → 3) Render backend → 4) Vercel frontend → 5) point them at each other.**

Total time: ~25–30 minutes. You need three free accounts (sign up with GitHub for all three to make it easy).

---

## Step 1 — Put the code on GitHub

The repo is already initialized and committed locally. You just need to push it.

1. Go to **https://github.com/new**.
2. **Repository name:** `training-portal` · keep it **Public** (or Private — both work) · **do NOT** tick "Add a README". Click **Create repository**.
3. GitHub shows a "push an existing repository" box. Copy the URL (e.g. `https://github.com/<you>/training-portal.git`).
4. In your terminal, from `c:\Users\itsha\training-portal`, run:

```powershell
git branch -M main
git remote add origin https://github.com/<you>/training-portal.git
git push -u origin main
```

If it asks you to sign in, a browser window opens — authorize it. When it finishes, refresh the GitHub page; you should see the `backend/` and `frontend/` folders.

---

## Step 2 — Create the database (Neon)

1. Go to **https://neon.tech** → **Sign up** (choose *Continue with GitHub*).
2. On first login it offers to **Create a project**. Set:
   - **Project name:** `training-portal`
   - **Postgres version:** leave default
   - **Region:** pick the one nearest you (e.g. *AWS ap-south-1 / Singapore*).
   - Click **Create project**.
3. You land on the project dashboard with a **Connection string** box. Make sure the **"Connection pooling"** toggle is **ON**, then click **Copy** (the "psql" / URI value). It looks like:
   ```
   postgresql://neondb_owner:XXXX@ep-xxxx-pooler.ap-south-1.aws.neon.tech/neondb?sslmode=require
   ```
4. **Paste this somewhere safe** — you'll give it to Render in the next step. (Our backend auto-converts the `postgresql://` scheme to the right driver, so use it exactly as copied.)

You don't create any tables — the backend does that automatically on first boot.

---

## Step 3 — Deploy the backend (Render)

1. Go to **https://render.com** → **Get Started** → *Sign in with GitHub*.
2. Top-right **New +** → **Web Service**.
3. **Connect your repository:** find `training-portal` in the list → **Connect**. (If you don't see it, click *Configure account* / grant Render access to the repo.)
4. Fill in the settings:
   - **Name:** `training-portal-api`
   - **Region:** nearest you
   - **Branch:** `main`
   - **Root Directory:** `backend`   ← **important**
   - **Runtime / Language:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** **Free**
5. Scroll to **Environment Variables** → **Add Environment Variable** and add:
   | Key | Value |
   |-----|-------|
   | `DATABASE_URL` | *(paste the Neon connection string from Step 2)* |
   | `FRONTEND_ORIGIN` | `http://localhost:5173` *(temporary — we fix this in Step 5)* |
6. Click **Create Web Service**. Render builds and boots it (first build ~3–5 min). Watch the **Logs** tab; you're looking for:
   ```
   Database was empty — seeded initial data.
   Application startup complete.
   ```
   That means it created all tables and seeded the demo data into Neon automatically.
7. At the top you'll see your API URL, e.g. **`https://training-portal-api.onrender.com`**. Open `https://training-portal-api.onrender.com/health` in a browser — it should show `{"status":"ok"}`. **Copy this API URL.**

> ⏱️ **Free-tier note:** the service sleeps after ~15 min of inactivity. The first request after it sleeps takes ~50 seconds to wake up, then it's fast again. Normal for free hosting.

---

## Step 4 — Deploy the frontend (Vercel)

1. Go to **https://vercel.com** → **Sign Up** → *Continue with GitHub*.
2. **Add New… → Project** → find `training-portal` → **Import**.
3. Configure:
   - **Framework Preset:** Vercel auto-detects **Vite** — leave it.
   - **Root Directory:** click **Edit** → select **`frontend`** → **Continue**.   ← **important**
   - **Build Command / Output:** leave defaults (`npm run build`, `dist`).
4. Expand **Environment Variables** and add:
   | Key | Value |
   |-----|-------|
   | `VITE_API_URL` | *(paste your Render API URL from Step 3, no trailing slash)* |
5. Click **Deploy**. After ~1–2 min you get a live URL like **`https://training-portal.vercel.app`**. **Copy it.**

---

## Step 5 — Connect them (fix CORS) & finish

The backend currently only trusts `localhost`. Point it at your real frontend:

1. Back in **Render** → your service → **Environment** (left sidebar).
2. Edit **`FRONTEND_ORIGIN`** → set it to your Vercel URL, e.g. `https://training-portal.vercel.app` (no trailing slash). **Save Changes** — Render redeploys automatically (~1 min).
3. Open your Vercel URL and **log in**:
   - Admin: `admin` / `admin`
   - Personnel: `pb001` / `password`

If login works and the dashboards load with data, **you're live.** 🎉

> If the browser console shows a **CORS error**, double-check `FRONTEND_ORIGIN` exactly matches the Vercel URL (scheme + host, no trailing slash). You can list several comma-separated origins if you add a custom domain later.

---

## Everyday workflow (after it's set up)

Any push to `main` auto-deploys both services:

```powershell
git add -A
git commit -m "your change"
git push
```

Render rebuilds the API; Vercel rebuilds the frontend. No manual steps.

**To reset/reseed the database:** the backend only auto-seeds when the DB is *empty*. To force a fresh seed, drop the tables in the Neon dashboard (**SQL Editor** → `DROP SCHEMA public CASCADE; CREATE SCHEMA public;`) and restart the Render service (**Manual Deploy → Clear build cache & deploy**, or just **Restart**).

---

## What got added for production

- **`backend/app/database.py`** — auto-normalizes managed-Postgres URLs to the psycopg v3 driver + connection pooling with `pool_pre_ping` (survives free-tier idling).
- **Self-contained seeding** — CSVs live in `backend/data/`; `seed_if_empty()` populates a fresh DB on first boot without wiping an existing one.
- **Env-driven CORS** via `FRONTEND_ORIGIN`; **`/health`** probe.
- **New tables for the future:** `notifications`, `allotment_events` (full audit trail of every accept/reject), `workshop_feedback`, and `topics` / `designations` reference tables.
- **`render.yaml`** (optional Blueprint), **`backend/.python-version`**, root **`.gitignore`**, **`frontend/.env.example`**.

---

## Full database schema (10 tables)

| Table | Purpose |
|-------|---------|
| `personnel` | People + auth (username/role) + specialization |
| `workshops` | Training programs (topic, min_designation, dates, capacity) |
| `allotments` | Live assignments (Pending/Accepted/Rejected) |
| `historical_allotments` | Past outcomes — ML training seed |
| `training_history` | Topic-wise completed trainings (per person) |
| `allotment_events` | **Audit trail** — every status change (who/when) |
| `notifications` | In-app alerts (invitations, updates) |
| `workshop_feedback` | Post-training ratings/comments |
| `topics` | Reference list of training topics |
| `designations` | Reference designation hierarchy (with rank) |

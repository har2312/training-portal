# Week 2 — Progress Report

**Project:** Smart Training Allotment & Management System
**Organization:** Prasar Bharati / NABM (government broadcasting)
**Stack:** FastAPI · SQLAlchemy · scikit-learn (backend) · React + Vite + Tailwind CSS (frontend) · SQLite (dev) → PostgreSQL (prod)

> Week 1 delivered the full-stack migration (DB, API, both dashboards, XAI, auto-replacement, continuous learning). Week 2 is a deep AI + business-rules upgrade plus an automated chatbot. See [WEEK1.md](WEEK1.md) for the starting point.

---

## 1. Goals for Week 2

1. Enforce strict government business rules: a designation hierarchy, per-workshop **Topic** + **minimum-designation** threshold, and a new Auto-Allot priority order.
2. Make the ML **topic-aware** (evaluate training history per topic, not a gross count).
3. Add advanced AI: **"The Oracle"** (unsupervised skill-gap analysis) and a **manual admin override**.
4. Reorganize both dashboards around **Topic** and **Upcoming / Ongoing / Completed**.
5. Give personnel a **visual analytics** section and a **zero-hallucination chatbot**.

---

## 2. Backend & AI Upgrades

### 2.1 Schema Restructure (the foundation)
- [backend/app/constants.py](backend/app/constants.py) — single source of truth:
  - **Designation hierarchy** (strict, senior→junior): `ADG, DDG, Director, DD, AD, AE, SEA, EA, Senior Tech, Tech, Helper` with `designation_rank()` and `meets_threshold()` ("AE & above" = rank ≤ AE).
  - **Topics**: `AI, Signal, Content, Administration, Awareness`.
  - `schedule_status()` — derives **Upcoming / Ongoing / Completed** from a workshop's dates vs today.
- [backend/app/models.py](backend/app/models.py):
  - `Personnel.specialization` (educational topic) for the Educational-Relevance rule.
  - `Workshop.topic` + `Workshop.min_designation`.
  - **New `TrainingHistory` table** (per-topic completed trainings) — this is what makes the ML topic-aware and powers personnel analytics + The Oracle.

### 2.2 Strict Hierarchy & Topic-Aware Auto-Allot
[backend/app/ml.py](backend/app/ml.py):
- **Hard filters:** retirement (`service_time_left > 2`) + **designation threshold** (`min_designation` & above).
- **Strict priority order** (as required):
  1. **Zone preference** (in-zone before out-of-zone)
  2. **Educational relevance** (`specialization == workshop.topic`)
  3. **Designation constraint** (threshold filter + seniority tiebreak)

  The topic-aware Random Forest probability ranks candidates *within* these tiers.
- **Crucial ML fix — topic-wise history:** the history feature is now *"trainings in **this workshop's** topic"*, read from `TrainingHistory`, **not** a gross count. Someone with 5 AI trainings and 0 Signal trainings is correctly treated as untrained for a Signal course.
- **XAI reasons** updated to reflect the new logic, e.g.
  *"Local zone (saves travel) | Educated in Signal | No prior Signal training (priority) | AD (meets SEA+) | High performance"*.

### 2.3 "The Oracle" — Predictive Skill-Gap Analyzer (Unsupervised ML)
- `GET /api/ai/oracle` → `run_oracle()` in [ml.py](backend/app/ml.py).
- **K-Means clustering** (scikit-learn) over each person's age, zone, designation rank, topic-wise training counts, and years-since-last-training (standardized features).
- For each cluster it finds the **weakest topic** and the recency gap and emits a human-readable recommendation, e.g.
  *"18 Directors in the East zone have minimal technical training in 'Signal' (avg 9.3 yrs since last training). Recommend a 'Digital Broadcasting' workshop in Kolkata."*

### 2.4 Manual Admin Override
- `GET /api/personnel/search?q=` — fast name/ID search.
- `POST /api/admin/allotments/manual` — instantly append a specific person to a workshop's allotment list after Auto-Allot has run.

### 2.5 Zero-Hallucination Chatbot (NLP)
- [backend/app/chatbot.py](backend/app/chatbot.py) — a **rule-based intent engine** (no LLM in the answer path, so it structurally cannot invent facts).
- `POST /api/chat` (`personnel_id`, `message`) → `{intent, reply, suggestions}`.
- Every factual answer is a live SQLite query; policy answers are curated fixed text; unknowns (e.g. instructor) return an honest "not available".
- **18 intents** across three classes:
  - **DB-backed personal:** `my_upcoming`, `next_workshop`, `my_ongoing`, `pending_actions`, `workshop_venue`, `total_trainings`, `topic_history` (per-topic), `my_profile`, `travel_allowance` (personalized — compares venue vs the user's station).
  - **DB-backed catalog:** `workshop_by_topic` ("when is the AI workshop?" → exact dates + venues).
  - **Curated policy / conversational:** `reporting_time`, `certificate`, `attendance`, `accept_decline`, `instructor`, `greeting`, `thanks`, `help`, `fallback` (with suggestion chips).

### 2.6 Supporting Endpoints
- `GET /api/meta` — topics + designation hierarchy (drives the frontend dropdowns).
- `GET /api/workshops?topic=` — topic filter; every workshop response now carries `schedule_status`.
- `GET /api/me/{id}/analytics` — total trainings + topic-wise breakdown + history.
- `GET /api/me/{id}/allotments` now includes `topic` + `schedule_status`.

---

## 3. Frontend Upgrades

### 3.1 Global Categorization
- New shared UI ([components/shared/ui.jsx](frontend/src/components/shared/ui.jsx)): `TopicBadge`, `ScheduleBadge`, `PillTabs`.
- Workshops are **filterable by Topic** and split into **Upcoming / Ongoing / Completed** on both dashboards.

### 3.2 Admin Dashboard
- **The Oracle widget** ([OracleWidget.jsx](frontend/src/components/admin/OracleWidget.jsx)) at the top of the Command Center — real-time skill-gap recommendations.
- **Workshop form** ([WorkshopForm.jsx](frontend/src/components/admin/WorkshopForm.jsx)) now has **Topic** and **Minimum Designation** dropdowns (populated from `/api/meta`).
- **Search & Add** ([SearchAddPersonnel.jsx](frontend/src/components/admin/SearchAddPersonnel.jsx)) inside the allotment table — live search a person by name/ID and append them.
- **Workshop list** ([WorkshopList.jsx](frontend/src/components/admin/WorkshopList.jsx)) — topic pills + schedule tabs + colored badges.

### 3.3 Personnel Dashboard
- Tabs: **Action Required · My Trainings · Analytics · Profile**.
- **My Trainings** ([MyTrainings.jsx](frontend/src/components/personnel/MyTrainings.jsx)) — assigned workshops categorized Upcoming/Ongoing/Completed, topic-filterable.
- **Training Analytics** ([TrainingAnalytics.jsx](frontend/src/components/personnel/TrainingAnalytics.jsx)) — total trainings + topic-wise **pie chart** (Recharts).
- **Profile** — info + past training history; performance score and AI metadata stay strictly hidden.
- **Chatbot widget** ([ChatbotWidget.jsx](frontend/src/components/personnel/ChatbotWidget.jsx)) — floating bottom-right launcher, User/Bot bubbles, typing indicator, suggestion chips, slate/blue palette.

---

## 4. Data Regeneration

New topic/hierarchy-aware seed data (deterministic generator):

| Data | Week 1 | Week 2 |
|------|--------|--------|
| Personnel | 95 | **95** (+ `specialization`, new designation hierarchy) |
| Workshops | 16 | **16** — now with `topic`, `min_designation`, and dates spanning **9 Upcoming / 2 Ongoing / 5 Completed** |
| Training history | — | **303 rows** (topic-wise completed trainings) — NEW |
| Historical allotments | 84 | **86** (topic-aware labels) |
| Live allotments (pre-seeded) | ~25 | **~81** across 46 personnel, realistic Accepted/Pending/Rejected mix |

---

## 5. Bugs Found & Fixed This Week

1. **Admin "All Officers" pool bug (carryover)** — resolved by the new `min_designation` model; the engine only considers `role == 'personnel'`.
2. **`personnel_id` merge ambiguity** in `train_model` (index + column collision) — fixed by not indexing the personnel frame.
3. **Personnel dashboard data mismatch** — Analytics showed "6 completed" (from `TrainingHistory`) but the "Completed" tab was empty (it read from live allotments). Fixed by sourcing each tab correctly: **Completed → TrainingHistory**, **Upcoming/Ongoing → allotments**; and the seed now guarantees every tab is populated (PB001: 6 completed, 2 upcoming, 1 ongoing, 1 pending).
4. **Chatbot intent hijack** — a bare topic mention ("when is the AI workshop") wrongly hit `topic_history` because the entity boost applied with zero keyword matches. Fixed: boost only when the intent's own keywords also match.

---

## 6. New / Changed API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/meta` | Topics + designation hierarchy |
| GET | `/api/workshops?topic=` | Topic filter; responses include `schedule_status` |
| GET | `/api/ai/oracle` | K-Means skill-gap recommendations |
| GET | `/api/personnel/search?q=` | Manual-override name/ID search |
| POST | `/api/admin/allotments/manual` | Manually add a person to a workshop |
| GET | `/api/me/{id}/analytics` | Topic-wise training analytics |
| POST | `/api/chat` | Personnel chatbot (rule-based, DB-backed) |

Plus updated Auto-Allot (`/api/allot/*`) and admin allotment views carrying the topic-aware XAI reason.

---

## 7. Verified Working
- Topic-aware XAI shows *"No prior Signal training (priority)"* even for people with trainings in other topics — the crucial ML fix confirmed.
- Priority order confirmed: an education-matched candidate outranks higher-ML-score candidates (Zone → Education → Designation).
- The Oracle produces 5 skill-gap insights via K-Means.
- Manual search + add works; topic filter + schedule tabs populate on both dashboards.
- Personnel dashboard consistent: PB001 shows 6 Completed / 2 Upcoming / 1 Ongoing / 1 Action Required.
- Chatbot verified across 16 questions — exact dates/venues from the DB, correct per-topic counts, personalized TA/DA answer, honest fallback.
- Frontend builds clean.

---

## 8. How to Run (unchanged)

```powershell
# Backend  (use python310 — see WEEK1.md for why)
cd c:\Users\itsha\training-portal\backend
C:\python310\python.exe -m app.seed
C:\python310\python.exe -m uvicorn app.main:app --reload

# Frontend
cd c:\Users\itsha\training-portal\frontend
npm run dev
```

**Demo logins:** admin `admin`/`admin` · personnel `pb001`/`password`.
**Demo flow:** log in as `pb001` → see populated Upcoming/Ongoing/Completed + Analytics → click the 💬 assistant and ask "where is my next workshop?" / "am I eligible for travel allowance?". As admin → Command Center shows The Oracle; create a workshop with a Topic + Min-Designation; Auto-Allot; use Search & Add to append someone manually.

---

## 9. Known Gaps / Planned for Next Week
- **Auth is still a demo token, not signed JWT**, and endpoints don't enforce the caller's role — top priority before deployment.
- Only 46/95 personnel have live allotments; could extend the seed to cover all 95 for a fuller demo.
- Move the deterministic data generator into the repo (still a scratch script).
- PostgreSQL + Alembic migrations for schema versioning.
- Chatbot could gain optional fuzzy matching / synonyms and a "did you mean" flow.

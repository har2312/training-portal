"""
FastAPI application — DB-backed version of your original main.py.

Endpoints:
  POST /api/login                       -> role-based login
  GET  /api/workshops                   -> list workshops
  POST /api/workshops                   -> admin: create workshop
  GET  /api/allot/{program_id}          -> preview ranked candidates (no DB write)
  POST /api/allot/{program_id}/commit   -> admin: persist allotments as Pending
  GET  /api/admin/allotments/{program_id} -> admin: allotted list w/ scores + status
  GET  /api/personnel                   -> admin: personnel directory (w/ scores)
  GET  /api/me/{personnel_id}           -> personnel profile (NO score)
  GET  /api/me/{personnel_id}/allotments-> personnel's allotments
  PATCH /api/allotments/{id}            -> personnel: accept/reject
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_

import os

from .database import get_db, engine, Base
from . import models, schemas, ml, chatbot, services
from .security import verify_password
from .constants import TOPICS, DESIGNATION_HIERARCHY, schedule_status
from .seed import seed_if_empty

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Smart Training Allotment System")

# Allowed frontend origins come from FRONTEND_ORIGIN (comma-separated) in prod,
# plus the local Vite dev server. By default we also allow any *.vercel.app
# origin via regex, so preview/production Vercel URLs work without reconfiguring.
#   FRONTEND_ORIGIN=https://my-app.vercel.app          (exact origins)
#   FRONTEND_ORIGIN_REGEX=https://.*\.vercel\.app      (override the default)
_origins = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
_origin_list = [o.strip().rstrip("/") for o in _origins.split(",") if o.strip()]
_origin_regex = os.getenv("FRONTEND_ORIGIN_REGEX", r"https://.*\.vercel\.app")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origin_list,
    allow_origin_regex=_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    """On boot: create tables, seed the DB if empty (prod first run), train the model."""
    db = next(get_db())
    try:
        if seed_if_empty(db):
            print("Database was empty — seeded initial data.")
        ml.train_model(db)
    finally:
        db.close()


@app.get("/health")
def health():
    """Lightweight liveness probe for the hosting platform."""
    return {"status": "ok"}


# ---------- Auth ----------
@app.post("/api/login", response_model=schemas.LoginResponse)
def login(body: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.Personnel).filter(
        models.Personnel.username == body.username
    ).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # Demo token. In production, issue a signed JWT here.
    return schemas.LoginResponse(
        personnel_id=user.personnel_id, name=user.name, role=user.role,
        token=f"demo-{user.personnel_id}",
    )


# ---------- Workshops ----------
def _workshop_out(ws: models.Workshop) -> schemas.WorkshopOut:
    """Serialize a workshop and attach the derived schedule status."""
    return schemas.WorkshopOut(
        program_id=ws.program_id, title=ws.title, domain=ws.domain,
        topic=ws.topic, min_designation=ws.min_designation,
        level_of_participants=ws.level_of_participants,
        from_date=ws.from_date, to_date=ws.to_date, duration_days=ws.duration_days,
        venue=ws.venue, capacity=ws.capacity, target_zone=ws.target_zone,
        schedule_status=schedule_status(ws.from_date, ws.to_date),
    )


@app.get("/api/workshops", response_model=list[schemas.WorkshopOut])
def get_workshops(topic: str | None = None, db: Session = Depends(get_db)):
    q = db.query(models.Workshop)
    if topic:
        q = q.filter(models.Workshop.topic == topic)
    return [_workshop_out(w) for w in q.all()]


@app.get("/api/meta")
def get_meta():
    """Enumerations the frontend needs: topics + designation hierarchy."""
    return {"topics": TOPICS, "designations": DESIGNATION_HIERARCHY}


@app.post("/api/workshops", response_model=schemas.WorkshopOut)
def create_workshop(body: schemas.WorkshopCreate, db: Session = Depends(get_db)):
    if db.get(models.Workshop, body.program_id):
        raise HTTPException(status_code=409, detail="Program_ID already exists")
    ws = models.Workshop(**body.model_dump())
    db.add(ws)
    db.commit()
    db.refresh(ws)
    return _workshop_out(ws)


# ---------- Allotment ----------
@app.get("/api/allot/{program_id}")
def preview_allotment(program_id: str, db: Session = Depends(get_db)):
    """Runs the AI logic and returns ranked candidates WITHOUT writing to the DB."""
    ws = db.get(models.Workshop, program_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workshop not found")

    ranked = ml.rank_candidates(db, ws, limit=ws.capacity)  # ai_reason already attached
    people = []
    for _, row in ranked.iterrows():
        people.append({
            "personnel_id": row["personnel_id"],
            "name": row["name"],
            "designation": row["designation"],
            "zone": row["zone"],
            "specialization": row["specialization"],
            "trainings_completed": int(row["trainings_completed"]),
            "ml_match_probability": float(row["ml_match_probability"]),
            "ai_reason": row["ai_reason"],  # XAI (admin-only), topic-aware
        })
    return {
        "program_id": program_id,
        "workshop_title": ws.title,
        "topic": ws.topic,
        "capacity": ws.capacity,
        "allotted_personnel": people,
    }


@app.post("/api/allot/{program_id}/commit")
def commit_allotment(program_id: str, db: Session = Depends(get_db)):
    """Persists the ranked candidates as Pending allotments (admin action)."""
    ws = db.get(models.Workshop, program_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workshop not found")

    ranked = ml.rank_candidates(db, ws, limit=ws.capacity)
    created = 0
    for _, row in ranked.iterrows():
        exists = db.query(models.Allotment).filter_by(
            program_id=program_id, personnel_id=row["personnel_id"]
        ).first()
        if exists:
            continue
        a = models.Allotment(
            program_id=program_id,
            personnel_id=row["personnel_id"],
            status="Pending",
            ml_match_probability=float(row["ml_match_probability"]),
        )
        db.add(a)
        db.flush()  # assign allotment_id for the audit event
        services.notify_invitation(db, a, ws)
        created += 1
    db.commit()
    return {"program_id": program_id, "allotments_created": created}


def _admin_row(a: models.Allotment, p: models.Personnel, ws: models.Workshop, tmat=None) -> schemas.AllotmentAdminRow:
    """Build an admin allotment row incl. the topic-aware XAI reason."""
    reason = ml.build_reason(
        {
            "personnel_id": p.personnel_id,
            "zone": p.zone,
            "specialization": p.specialization,
            "designation": p.designation,
            "performance_score": p.performance_score,
        },
        ws,
        tmat,
    )
    return schemas.AllotmentAdminRow(
        allotment_id=a.allotment_id, program_id=a.program_id,
        personnel_id=a.personnel_id, status=a.status,
        ml_match_probability=a.ml_match_probability,
        name=p.name, designation=p.designation, zone=p.zone,
        trainings_completed=p.trainings_completed,
        performance_score=p.performance_score,
        ai_reason=reason,
    )


@app.get("/api/admin/allotments/{program_id}", response_model=list[schemas.AllotmentAdminRow])
def admin_allotments(program_id: str, db: Session = Depends(get_db)):
    """Admin view: allotted personnel with details, performance_score, status, XAI reason."""
    ws = db.get(models.Workshop, program_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workshop not found")
    tmat = ml._topic_matrix(db)
    rows = (
        db.query(models.Allotment, models.Personnel)
        .join(models.Personnel, models.Allotment.personnel_id == models.Personnel.personnel_id)
        .filter(models.Allotment.program_id == program_id)
        .all()
    )
    return [_admin_row(a, p, ws, tmat) for a, p in rows]


def _assign_replacement(db: Session, ws: models.Workshop) -> schemas.AllotmentAdminRow | None:
    """
    Find the next-best eligible candidate for a workshop, excluding everyone who
    already has an allotment row for it (any status), create a Pending allotment,
    and return the admin row (with XAI). None if the eligible pool is exhausted.
    """
    existing = {
        a.personnel_id
        for a in db.query(models.Allotment).filter_by(program_id=ws.program_id).all()
    }
    ranked = ml.rank_candidates(db, ws, exclude_ids=existing, limit=1)
    if ranked.empty:
        return None
    row = ranked.iloc[0]
    new = models.Allotment(
        program_id=ws.program_id,
        personnel_id=row["personnel_id"],
        status="Pending",
        ml_match_probability=float(row["ml_match_probability"]),
    )
    db.add(new)
    db.flush()
    services.notify_invitation(db, new, ws)
    db.commit()
    db.refresh(new)
    p = db.get(models.Personnel, row["personnel_id"])
    return _admin_row(new, p, ws, ml._topic_matrix(db))


@app.post("/api/admin/allotments/{allotment_id}/accept", response_model=schemas.AllotmentAdminRow)
def admin_accept(allotment_id: int, db: Session = Depends(get_db)):
    """Admin confirms an allotment."""
    a = db.get(models.Allotment, allotment_id)
    if not a:
        raise HTTPException(status_code=404, detail="Allotment not found")
    prev, a.status = a.status, "Accepted"
    services.record_event(db, a, prev, "Accepted", "admin")
    db.commit()
    p = db.get(models.Personnel, a.personnel_id)
    ws = db.get(models.Workshop, a.program_id)
    return _admin_row(a, p, ws)


@app.post("/api/admin/allotments/{allotment_id}/reject", response_model=schemas.ReplacementResult)
def admin_reject(allotment_id: int, db: Session = Depends(get_db)):
    """
    Admin rejects an allotment -> Smart Waitlist: the seat is freed and the AI
    instantly nominates the next-best candidate to replace them.
    """
    a = db.get(models.Allotment, allotment_id)
    if not a:
        raise HTTPException(status_code=404, detail="Allotment not found")
    prev, a.status = a.status, "Rejected"
    services.record_event(db, a, prev, "Rejected", "admin")
    db.commit()
    ws = db.get(models.Workshop, a.program_id)
    replacement = _assign_replacement(db, ws)
    return schemas.ReplacementResult(rejected_allotment_id=allotment_id, replacement=replacement)


# ---------- Personnel directory (admin) ----------
@app.get("/api/personnel", response_model=list[schemas.PersonnelAdmin])
def personnel_directory(db: Session = Depends(get_db)):
    return db.query(models.Personnel).filter(models.Personnel.role == "personnel").all()


# ---------- Personnel self-service ----------
@app.get("/api/me/{personnel_id}", response_model=schemas.PersonnelPublic)
def my_profile(personnel_id: str, db: Session = Depends(get_db)):
    """Profile WITHOUT performance_score (schema enforces the omission)."""
    p = db.get(models.Personnel, personnel_id)
    if not p:
        raise HTTPException(status_code=404, detail="Personnel not found")
    return p


@app.get("/api/me/{personnel_id}/allotments")
def my_allotments(personnel_id: str, db: Session = Depends(get_db)):
    """Allotments for this person, joined with workshop details."""
    rows = (
        db.query(models.Allotment, models.Workshop)
        .join(models.Workshop, models.Allotment.program_id == models.Workshop.program_id)
        .filter(models.Allotment.personnel_id == personnel_id)
        .all()
    )
    return [
        {
            "allotment_id": a.allotment_id,
            "status": a.status,
            "program_id": w.program_id,
            "title": w.title,
            "topic": w.topic,
            "venue": w.venue,
            "from_date": w.from_date,
            "to_date": w.to_date,
            "duration_days": w.duration_days,
            "schedule_status": schedule_status(w.from_date, w.to_date),
        }
        for a, w in rows
    ]


@app.patch("/api/allotments/{allotment_id}")
def update_allotment_status(
    allotment_id: int, body: schemas.AllotmentStatusUpdate, db: Session = Depends(get_db)
):
    """
    Personnel accepts or declines an allotment. On decline, the Smart Waitlist
    silently assigns a replacement server-side. The response is personnel-safe:
    it carries NO AI metadata (no reason, no replacement identity, no scores).
    """
    if body.status not in ("Accepted", "Rejected"):
        raise HTTPException(status_code=400, detail="status must be Accepted or Rejected")
    a = db.get(models.Allotment, allotment_id)
    if not a:
        raise HTTPException(status_code=404, detail="Allotment not found")
    prev, a.status = a.status, body.status
    services.record_event(db, a, prev, body.status, "personnel")
    db.commit()

    replaced = False
    if body.status == "Rejected":
        ws = db.get(models.Workshop, a.program_id)
        replaced = _assign_replacement(db, ws) is not None

    return {
        "allotment_id": allotment_id,
        "status": a.status,
        "replacement_assigned": replaced,  # boolean only — no identity leaked
    }


# ---------- Advanced AI: continuous learning + dashboard metrics ----------
@app.post("/api/ai/retrain", response_model=schemas.RetrainResult)
def retrain_model(db: Session = Depends(get_db)):
    """Retrain the Random Forest on historical + live accept/reject feedback."""
    result = ml.train_model(db)
    return schemas.RetrainResult(**result)


@app.get("/api/admin/metrics", response_model=schemas.DashboardMetrics)
def dashboard_metrics(db: Session = Depends(get_db)):
    """Top-card metrics + zone distribution for the admin command center."""
    total_workshops = db.query(models.Workshop).count()

    accepted = (
        db.query(models.Allotment, models.Personnel)
        .join(models.Personnel, models.Allotment.personnel_id == models.Personnel.personnel_id)
        .filter(models.Allotment.status == "Accepted")
        .all()
    )
    trained_ids = {p.personnel_id for _, p in accepted}

    zone_counts: dict[str, int] = {}
    for _, p in accepted:
        zone_counts[p.zone or "Unknown"] = zone_counts.get(p.zone or "Unknown", 0) + 1

    return schemas.DashboardMetrics(
        total_workshops=total_workshops,
        personnel_trained=len(trained_ids),
        ai_confidence=round(ml.model_confidence(), 3),
        zone_distribution=[schemas.ZoneCount(zone=z, count=c) for z, c in sorted(zone_counts.items())],
    )


# ---------- Notifications ----------
@app.get("/api/me/{personnel_id}/notifications", response_model=list[schemas.NotificationOut])
def my_notifications(personnel_id: str, unread_only: bool = False, db: Session = Depends(get_db)):
    q = db.query(models.Notification).filter(models.Notification.personnel_id == personnel_id)
    if unread_only:
        q = q.filter(models.Notification.is_read == False)  # noqa: E712
    return q.order_by(models.Notification.created_at.desc()).limit(50).all()


@app.post("/api/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int, db: Session = Depends(get_db)):
    n = db.get(models.Notification, notification_id)
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.is_read = True
    db.commit()
    return {"id": notification_id, "is_read": True}


# ---------- Personnel chatbot ----------
@app.post("/api/chat", response_model=schemas.ChatResponse)
def chat(body: schemas.ChatRequest, db: Session = Depends(get_db)):
    """Rule-based, DB-backed assistant for the personnel dashboard (no hallucination)."""
    if not db.get(models.Personnel, body.personnel_id):
        raise HTTPException(status_code=404, detail="Personnel not found")
    return schemas.ChatResponse(**chatbot.answer(db, body.personnel_id, body.message))


# ---------- The Oracle: K-Means skill-gap analyzer ----------
@app.get("/api/ai/oracle", response_model=list[schemas.OracleInsight])
def oracle(db: Session = Depends(get_db)):
    """Unsupervised skill-gap recommendations across the personnel base."""
    return [schemas.OracleInsight(**i) for i in ml.run_oracle(db)]


# ---------- Manual admin override ----------
@app.get("/api/personnel/search", response_model=list[schemas.PersonnelSearchResult])
def search_personnel(q: str, db: Session = Depends(get_db)):
    """Fast name/ID search for the admin's manual 'Search & Add' box."""
    like = f"%{q}%"
    return (
        db.query(models.Personnel)
        .filter(models.Personnel.role == "personnel")
        .filter(or_(models.Personnel.name.ilike(like), models.Personnel.personnel_id.ilike(like)))
        .limit(10)
        .all()
    )


@app.post("/api/admin/allotments/manual", response_model=schemas.AllotmentAdminRow)
def manual_allot(body: schemas.ManualAllotRequest, db: Session = Depends(get_db)):
    """Admin manually appends a specific person to a workshop's allotment list."""
    ws = db.get(models.Workshop, body.program_id)
    p = db.get(models.Personnel, body.personnel_id)
    if not ws or not p:
        raise HTTPException(status_code=404, detail="Workshop or personnel not found")
    existing = db.query(models.Allotment).filter_by(
        program_id=body.program_id, personnel_id=body.personnel_id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Already allotted to this workshop")
    a = models.Allotment(
        program_id=body.program_id, personnel_id=body.personnel_id,
        status="Pending", ml_match_probability=None,
    )
    db.add(a)
    db.flush()
    services.record_event(db, a, None, "Pending", "admin", "Manually added")
    services.notify_invitation(db, a, ws)
    db.commit()
    db.refresh(a)
    return _admin_row(a, p, ws, ml._topic_matrix(db))


# ---------- Personnel topic-wise analytics ----------
@app.get("/api/me/{personnel_id}/analytics", response_model=schemas.PersonnelAnalytics)
def my_analytics(personnel_id: str, db: Session = Depends(get_db)):
    """Total trainings + topic-wise breakdown + history for the personnel dashboard."""
    hist = (
        db.query(models.TrainingHistory)
        .filter(models.TrainingHistory.personnel_id == personnel_id)
        .all()
    )
    counts: dict[str, int] = {}
    for h in hist:
        counts[h.topic] = counts.get(h.topic, 0) + 1
    return schemas.PersonnelAnalytics(
        total_trainings=len(hist),
        topic_breakdown=[schemas.TopicCount(topic=t, count=c) for t, c in sorted(counts.items())],
        history=[
            schemas.TrainingHistoryItem(topic=h.topic, title=h.title, completed_date=h.completed_date)
            for h in sorted(hist, key=lambda x: x.completed_date or "", reverse=True)
        ],
    )

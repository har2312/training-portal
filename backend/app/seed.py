"""
Database seeder. Loads the bundled CSVs (backend/data/) into the database.

    python -m app.seed            # DROP everything and reseed (local dev)
    seed_if_empty(db)             # insert only if empty (safe for prod startup)

Personnel get demo credentials: username = personnel_id lower-cased
(e.g. pb001), password 'password'. Plus one admin: 'admin' / 'admin'.
"""
import os
import pandas as pd

from .database import Base, engine, SessionLocal
from . import models
from .security import hash_password
from .constants import TOPICS, TECHNICAL_TOPICS, DESIGNATION_HIERARCHY

# CSVs are bundled inside the backend so deployment is self-contained.
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))


def _csv(name: str) -> pd.DataFrame:
    return pd.read_csv(os.path.join(DATA_DIR, name))


def _load(db):
    """Insert all rows. Assumes empty tables."""
    # Reference tables
    for t in TOPICS:
        db.add(models.TopicRef(name=t, is_technical=t in TECHNICAL_TOPICS))
    for i, d in enumerate(DESIGNATION_HIERARCHY):
        db.add(models.DesignationRef(name=d, rank=i))

    # Personnel
    for _, r in _csv("personnel_dataset.csv").iterrows():
        db.add(models.Personnel(
            personnel_id=r["Personnel_ID"],
            name=r["Name"],
            designation=r["Designation"],
            stream=r["Stream"],
            qualification=r.get("Qualification"),
            zone=r["Zone"],
            station=r["Station"],
            age=int(r["Age"]),
            service_time_left=float(r["Service_Time_Left"]),
            trainings_completed=int(r["Trainings_Completed"]),
            specialization=r.get("Specialization"),
            performance_score=int(r["Performance_Score"]),
            username=str(r["Personnel_ID"]).lower(),
            password_hash=hash_password("password"),
            role="personnel",
        ))

    # Admin account
    db.add(models.Personnel(
        personnel_id="ADMIN01", name="System Administrator",
        designation="Admin", stream="Admin", zone="All", station="HQ",
        age=40, service_time_left=99, trainings_completed=0,
        specialization=None, performance_score=None,
        username="admin", password_hash=hash_password("admin"), role="admin",
    ))

    # Workshops
    for _, r in _csv("training_workshops.csv").iterrows():
        db.add(models.Workshop(
            program_id=r["Program_ID"], title=r["Title"], domain=r["Domain"],
            topic=r.get("Topic"), min_designation=r.get("Min_Designation"),
            level_of_participants=r["Level_Of_Participants"],
            from_date=str(r["From_Date"]), to_date=str(r["To_Date"]),
            duration_days=int(r["Duration_Days"]), venue=r["Venue"],
            capacity=int(r["Capacity"]), target_zone=r["Target_Zone"],
        ))

    # Commit parents first so FK children below satisfy constraints on Postgres.
    db.commit()

    # Historical (ML training data)
    for _, r in _csv("historical_allotments.csv").iterrows():
        db.add(models.HistoricalAllotment(
            allotment_id=r["Allotment_ID"], program_id=r["Program_ID"],
            personnel_id=r["Personnel_ID"], user_action=r["User_Action"],
            feedback_score=int(r["Feedback_Score"]),
            is_optimal_match=int(r["Is_Optimal_Match"]),
        ))

    # Topic-wise training history
    for _, r in _csv("training_history.csv").iterrows():
        db.add(models.TrainingHistory(
            personnel_id=r["Personnel_ID"], topic=r["Topic"],
            title=r["Title"], completed_date=str(r["Completed_Date"]),
        ))

    db.commit()
    _seed_live_allotments(db)


def seed():
    """Full reset + reseed. Destructive — for local development."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        _load(db)
        print("Seed complete.")
    finally:
        db.close()


def seed_if_empty(db):
    """Non-destructive: seed only when the DB has no personnel (prod first boot)."""
    Base.metadata.create_all(bind=engine)
    if db.query(models.Personnel).first() is None:
        _load(db)
        return True
    return False


def _ensure(db, personnel_id, program_id, status, prob):
    """Idempotently give a person a specific allotment (for a guaranteed demo spread)."""
    if db.query(models.Allotment).filter_by(personnel_id=personnel_id, program_id=program_id).first():
        return
    db.add(models.Allotment(
        personnel_id=personnel_id, program_id=program_id,
        status=status, ml_match_probability=prob,
    ))


def _seed_live_allotments(db):
    """
    Pre-populate a few live allotments so the admin dashboard (metrics, zone
    chart) and personnel 'Action Required' are non-empty on first load.
    Runs the real allotment engine, then marks a realistic status mix.
    """
    from . import ml
    ml.train_model(db)

    from .constants import schedule_status

    # Auto-allot EVERY upcoming/ongoing workshop so many personnel get real
    # assignments across both tabs. Completed workshops are represented by
    # TrainingHistory instead, so we skip them here (avoids a double source).
    for ws in db.query(models.Workshop).all():
        if schedule_status(ws.from_date, ws.to_date) == "Completed":
            continue
        ranked = ml.rank_candidates(db, ws, limit=min(ws.capacity, 8))
        for i, (_, row) in enumerate(ranked.iterrows()):
            # A realistic mix: some Accepted (populate metrics/zone chart),
            # one Rejected, the rest Pending invitations.
            status = "Accepted" if i < 3 else ("Rejected" if i == 3 else "Pending")
            db.add(models.Allotment(
                program_id=ws.program_id,
                personnel_id=row["personnel_id"],
                status=status,
                ml_match_probability=float(row["ml_match_probability"]),
            ))
    db.commit()

    # Guarantee the default demo login (pb001) a full, non-empty spread:
    #   Completed -> its 6 TrainingHistory rows (already seeded)
    #   Ongoing   -> Accepted assignment
    #   Upcoming  -> one Accepted + one Pending (Action Required)
    _ensure(db, "PB001", "D26AI09", "Accepted", 0.82)   # ongoing
    _ensure(db, "PB001", "D26AI01", "Accepted", 0.78)   # upcoming
    _ensure(db, "PB001", "D26AD06", "Pending", 0.71)    # upcoming (action required)
    db.commit()

    # Seed an invitation notification for every pending allotment so the
    # notifications feature has data on first load.
    shops = {w.program_id: w for w in db.query(models.Workshop).all()}
    for a in db.query(models.Allotment).filter_by(status="Pending").all():
        w = shops.get(a.program_id)
        if w:
            db.add(models.Notification(
                personnel_id=a.personnel_id, category="invitation",
                message=f"You've been invited to '{w.title}' ({w.topic}) starting {w.from_date}.",
            ))
    db.commit()

    # Retrain so the model also learns from the pre-seeded human decisions.
    ml.train_model(db)


if __name__ == "__main__":
    seed()

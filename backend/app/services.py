"""
Side-effect helpers for allotment writes: audit trail + notifications.
Keeping these in one place means every status change is recorded consistently.
"""
from . import models


def record_event(db, allotment: models.Allotment, from_status, to_status, actor, note=""):
    """Append an immutable audit row for an allotment status transition."""
    db.add(models.AllotmentEvent(
        allotment_id=allotment.allotment_id,
        program_id=allotment.program_id,
        personnel_id=allotment.personnel_id,
        from_status=from_status,
        to_status=to_status,
        actor=actor,
        note=note,
    ))


def notify(db, personnel_id, category, message):
    """Queue an in-app notification for a person."""
    db.add(models.Notification(
        personnel_id=personnel_id, category=category, message=message,
    ))


def notify_invitation(db, allotment: models.Allotment, workshop: models.Workshop):
    """Convenience: audit + notification for a freshly created Pending allotment."""
    record_event(db, allotment, None, "Pending", "system", "Allotment created")
    notify(
        db, allotment.personnel_id, "invitation",
        f"You've been invited to '{workshop.title}' ({workshop.topic}) starting {workshop.from_date}. "
        f"Please Accept or Decline in Action Required.",
    )

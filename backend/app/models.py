"""
SQLAlchemy ORM models.

Design notes:
- Personnel.performance_score is admin-only. It lives in the DB but is never
  serialized to personnel-facing responses (enforced in schemas.py).
- HistoricalAllotment is the *training* data for the ML model (mirrors your
  historical_allotments.csv). Allotment is the *live* record created when the
  admin runs Auto-Allot; personnel accept/reject these.
"""
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, ForeignKey, DateTime, func
)
from sqlalchemy.orm import relationship
from .database import Base


class Personnel(Base):
    __tablename__ = "personnel"

    personnel_id = Column(String, primary_key=True, index=True)   # e.g. PB001
    name = Column(String, nullable=False)
    designation = Column(String, nullable=False)                  # DDG, DD, AD, EA...
    stream = Column(String, nullable=False, index=True)           # Engineering, Programme...
    qualification = Column(String)
    zone = Column(String, index=True)                             # North/South/East/West
    station = Column(String)
    age = Column(Integer)
    service_time_left = Column(Float)                             # years
    trainings_completed = Column(Integer, default=0)             # gross count (display only)
    specialization = Column(String, index=True)                  # educational topic: AI/Signal/...
    performance_score = Column(Integer)                           # 1-10, ADMIN-ONLY

    # Auth (not in the original CSV — added for the two-role login).
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String, default="personnel")                   # 'admin' | 'personnel'

    allotments = relationship("Allotment", back_populates="personnel")
    training_history = relationship("TrainingHistory", back_populates="personnel")


class Workshop(Base):
    __tablename__ = "workshops"

    program_id = Column(String, primary_key=True, index=True)     # e.g. D23EG01
    title = Column(String, nullable=False)
    domain = Column(String, nullable=False, index=True)           # legacy stream tag (display)
    topic = Column(String, index=True)                            # AI/Signal/Content/Administration/Awareness
    min_designation = Column(String)                              # threshold: "AE" => AE & above
    level_of_participants = Column(String)                        # legacy label (display)
    from_date = Column(String)                                    # ISO date strings, kept as-is
    to_date = Column(String)
    duration_days = Column(Integer)
    venue = Column(String)
    capacity = Column(Integer, nullable=False)
    target_zone = Column(String)                                  # zone name or "All"

    allotments = relationship("Allotment", back_populates="workshop")


class Allotment(Base):
    """Live allotment produced by Auto-Allot; personnel accept/reject."""
    __tablename__ = "allotments"

    allotment_id = Column(Integer, primary_key=True, autoincrement=True)
    program_id = Column(String, ForeignKey("workshops.program_id"), index=True)
    personnel_id = Column(String, ForeignKey("personnel.personnel_id"), index=True)
    status = Column(String, default="Pending")                   # Pending | Accepted | Rejected
    ml_match_probability = Column(Float)                         # snapshot of the score at allotment
    created_at = Column(DateTime, server_default=func.now())

    workshop = relationship("Workshop", back_populates="allotments")
    personnel = relationship("Personnel", back_populates="allotments")


class HistoricalAllotment(Base):
    """Past outcomes used only to train the Random Forest (your CSV)."""
    __tablename__ = "historical_allotments"

    allotment_id = Column(String, primary_key=True)              # AL001...
    program_id = Column(String, ForeignKey("workshops.program_id"))
    personnel_id = Column(String, ForeignKey("personnel.personnel_id"))
    user_action = Column(String)                                 # Accepted | Rejected
    feedback_score = Column(Integer)
    is_optimal_match = Column(Integer)                           # label: 0/1


class TrainingHistory(Base):
    """
    Completed past trainings, per topic. This is what makes the ML topic-aware:
    'trainings in the workshop's topic' is derived from these rows, not a gross
    count. Also powers the personnel topic-wise analytics and The Oracle.
    """
    __tablename__ = "training_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    personnel_id = Column(String, ForeignKey("personnel.personnel_id"), index=True)
    topic = Column(String, index=True)                           # one of TOPICS
    title = Column(String)
    completed_date = Column(String)                              # ISO date

    personnel = relationship("Personnel", back_populates="training_history")


# ===========================================================================
# Future-proof / auxiliary tables (added for production)
# ===========================================================================
class AllotmentEvent(Base):
    """Immutable audit trail: every status change on an allotment, who & when."""
    __tablename__ = "allotment_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    allotment_id = Column(Integer, ForeignKey("allotments.allotment_id"), index=True)
    program_id = Column(String, index=True)
    personnel_id = Column(String, index=True)
    from_status = Column(String)
    to_status = Column(String)
    actor = Column(String)                                       # 'admin' | 'personnel' | 'system'
    note = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class Notification(Base):
    """In-app notifications for personnel (invitations, replacements, reminders)."""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    personnel_id = Column(String, ForeignKey("personnel.personnel_id"), index=True)
    category = Column(String)                                    # invitation | update | reminder
    message = Column(Text)
    is_read = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, server_default=func.now())


class WorkshopFeedback(Base):
    """Post-training feedback (drives a future feedback-loop / quality metrics)."""
    __tablename__ = "workshop_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    program_id = Column(String, ForeignKey("workshops.program_id"), index=True)
    personnel_id = Column(String, ForeignKey("personnel.personnel_id"), index=True)
    rating = Column(Integer)                                     # 1-5
    comments = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class TopicRef(Base):
    """Reference/lookup table for training topics (extensible without code change)."""
    __tablename__ = "topics"

    name = Column(String, primary_key=True)
    is_technical = Column(Boolean, default=False)
    description = Column(String)


class DesignationRef(Base):
    """Reference table for the designation hierarchy (rank 0 = most senior)."""
    __tablename__ = "designations"

    name = Column(String, primary_key=True)
    rank = Column(Integer, index=True)

"""
Pydantic schemas = the API contract.

The critical rule: PersonnelPublic OMITS performance_score. Personnel-facing
endpoints return PersonnelPublic; admin endpoints return PersonnelAdmin.
This is the enforcement point that keeps the score hidden.
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


# ---------- Personnel ----------
class PersonnelBase(BaseModel):
    personnel_id: str
    name: str
    designation: str
    stream: str
    qualification: Optional[str] = None
    zone: Optional[str] = None
    station: Optional[str] = None
    age: Optional[int] = None
    service_time_left: Optional[float] = None
    trainings_completed: Optional[int] = None
    specialization: Optional[str] = None

    class Config:
        from_attributes = True


class PersonnelPublic(PersonnelBase):
    """What personnel see about themselves — NO performance_score."""
    pass


class PersonnelAdmin(PersonnelBase):
    """What admins see — includes the hidden score."""
    performance_score: Optional[int] = None
    role: Optional[str] = None


# ---------- Workshop ----------
class WorkshopBase(BaseModel):
    title: str
    domain: str
    topic: Optional[str] = None
    min_designation: Optional[str] = None
    allowed_designations: Optional[List[str]] = None  # specific eligible grades
    level_of_participants: Optional[str] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    duration_days: Optional[int] = None
    venue: Optional[str] = None
    capacity: int
    target_zone: Optional[str] = "All"


class WorkshopCreate(WorkshopBase):
    program_id: str


class WorkshopOut(WorkshopBase):
    program_id: str
    schedule_status: Optional[str] = None  # Upcoming | Ongoing | Completed (derived)

    class Config:
        from_attributes = True


# ---------- Allotment ----------
class AllotmentOut(BaseModel):
    allotment_id: int
    program_id: str
    personnel_id: str
    status: str
    ml_match_probability: Optional[float] = None

    class Config:
        from_attributes = True


class AllotmentAdminRow(AllotmentOut):
    """Admin allotment view — joins personnel details incl. performance_score."""
    name: str
    designation: str
    zone: Optional[str] = None
    trainings_completed: Optional[int] = None
    performance_score: Optional[int] = None
    ai_reason: Optional[str] = None  # XAI explanation (admin-only)


class ReplacementResult(BaseModel):
    """Returned after an admin reject: the vacated seat's new best candidate."""
    rejected_allotment_id: int
    replacement: Optional[AllotmentAdminRow] = None  # None if pool exhausted


class AllotmentStatusUpdate(BaseModel):
    status: str  # "Accepted" | "Rejected"


class RetrainResult(BaseModel):
    trained: bool
    samples: int
    confidence: float


class ZoneCount(BaseModel):
    zone: str
    count: int


class DashboardMetrics(BaseModel):
    total_workshops: int
    personnel_trained: int
    ai_confidence: float
    zone_distribution: List[ZoneCount]


# ---------- The Oracle ----------
class OracleInsight(BaseModel):
    cluster: int
    count: int
    designation: str
    zone: str
    weak_topic: str
    avg_years_since_training: float
    recommendation: str


# ---------- Manual override / search ----------
class PersonnelSearchResult(BaseModel):
    personnel_id: str
    name: str
    designation: str
    zone: Optional[str] = None
    specialization: Optional[str] = None

    class Config:
        from_attributes = True


class ManualAllotRequest(BaseModel):
    program_id: str
    personnel_id: str


# ---------- Personnel analytics ----------
class TopicCount(BaseModel):
    topic: str
    count: int


class TrainingHistoryItem(BaseModel):
    topic: str
    title: Optional[str] = None
    completed_date: Optional[str] = None

    class Config:
        from_attributes = True


class PersonnelAnalytics(BaseModel):
    total_trainings: int
    topic_breakdown: List[TopicCount]
    history: List[TrainingHistoryItem]


# ---------- Notifications ----------
class NotificationOut(BaseModel):
    id: int
    category: Optional[str] = None
    message: str
    is_read: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------- Chatbot ----------
class ChatRequest(BaseModel):
    personnel_id: str
    message: str


class ChatResponse(BaseModel):
    intent: str
    reply: str
    suggestions: List[str] = []


# ---------- Auth ----------
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    personnel_id: str
    name: str
    role: str
    token: str  # simple token for the demo; swap for JWT in production

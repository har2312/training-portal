"""
Personnel chatbot — rule-based intent engine.

Design principle: ZERO hallucination. Every factual answer is read directly
from SQLite (workshops, allotments, training history). Policy answers are
fixed, curated text — not generated. There is no LLM in the answer path, so
the bot can never invent a date, venue, or number.
"""
import re
from datetime import date

from sqlalchemy.orm import Session

from . import models
from .constants import TOPICS, schedule_status


# --------------------------------------------------------------------------
# Curated policy text (configured facts, not generated)
# --------------------------------------------------------------------------
POLICY = {
    "travel_allowance": (
        "As per government norms, personnel deputed to a training station outside their "
        "home station are entitled to Travel Allowance (TA) and Daily Allowance (DA) at "
        "their pay level. In-station trainings are not eligible for TA. Claims are submitted "
        "through your DDO after completion."
    ),
    "certificate": (
        "A certificate of participation is issued by the training institute (NABM) on "
        "successful completion with a minimum of 90% attendance. It is added to your service record."
    ),
    "attendance": "A minimum of 90% attendance is mandatory to complete a workshop and receive certification.",
    "accept_decline": (
        "Open the 'Action Required' tab on your dashboard. Each pending invitation has "
        "'Accept' and 'Decline' buttons. Declining automatically frees your seat for the "
        "next eligible candidate."
    ),
    "reporting_time": (
        "Standard reporting is by 9:30 AM on the first day. Sessions usually run 10:00 AM "
        "to 5:00 PM. Exact timings are confirmed by the training institute before the workshop."
    ),
    "instructor": (
        "Faculty/instructor details are shared by the training institute closer to the "
        "workshop date and are not maintained in the portal yet."
    ),
}

SUGGESTIONS = [
    "Where is my next workshop?",
    "Do I have any pending invitations?",
    "How many trainings have I completed?",
    "Am I eligible for travel allowance?",
    "When is the AI workshop?",
]


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def _fmt(iso: str | None) -> str:
    if not iso:
        return "TBD"
    try:
        return date.fromisoformat(str(iso)[:10]).strftime("%d %b %Y")
    except ValueError:
        return str(iso)


def _person(db: Session, pid: str) -> models.Personnel | None:
    return db.get(models.Personnel, pid)


def _my_workshops(db: Session, pid: str):
    """This person's non-declined allotments joined with workshop + schedule status."""
    rows = (
        db.query(models.Allotment, models.Workshop)
        .join(models.Workshop, models.Allotment.program_id == models.Workshop.program_id)
        .filter(models.Allotment.personnel_id == pid)
        .all()
    )
    out = []
    for a, w in rows:
        out.append({
            "status": a.status, "title": w.title, "topic": w.topic,
            "venue": w.venue, "from_date": w.from_date, "to_date": w.to_date,
            "duration_days": w.duration_days, "target_zone": w.target_zone,
            "schedule": schedule_status(w.from_date, w.to_date),
        })
    return out


def _detect_topic(msg: str) -> str | None:
    for t in TOPICS:
        if re.search(rf"\b{re.escape(t.lower())}\b", msg):
            return t
    if any(k in msg for k in ("artificial intelligence", "machine learning", " ml ")):
        return "AI"
    if any(k in msg for k in ("transmitter", "satellite", "rf ", "broadcast", "uplink")):
        return "Signal"
    if any(k in msg for k in ("procurement", "vigilance", "finance", "admin")):
        return "Administration"
    return None


# --------------------------------------------------------------------------
# Intent handlers  (db, pid, msg, topic) -> reply string
# --------------------------------------------------------------------------
def _h_greeting(db, pid, msg, topic):
    p = _person(db, pid)
    name = p.name.split()[0] if p else "there"
    return f"Hello {name}! I can help with your workshops, schedules, and training policies. Ask me anything."


def _h_help(db, pid, msg, topic):
    return ("I can tell you about: your upcoming/ongoing trainings, your next workshop's date & venue, "
            "pending invitations, how many trainings you've completed (overall or by topic), travel "
            "allowance eligibility, certificates, attendance rules, and when a specific topic's workshop is scheduled.")


def _h_my_upcoming(db, pid, msg, topic):
    ws = [w for w in _my_workshops(db, pid) if w["schedule"] == "Upcoming" and w["status"] != "Rejected"]
    if topic:
        ws = [w for w in ws if w["topic"] == topic]
    if not ws:
        return f"You have no upcoming {topic + ' ' if topic else ''}workshops scheduled right now."
    ws.sort(key=lambda w: w["from_date"] or "")
    lines = [f"• {w['title']} ({w['topic']}) — {_fmt(w['from_date'])} at {w['venue']} [{w['status']}]" for w in ws]
    return f"You have {len(ws)} upcoming workshop(s):\n" + "\n".join(lines)


def _h_next(db, pid, msg, topic):
    ws = [w for w in _my_workshops(db, pid) if w["schedule"] == "Upcoming" and w["status"] != "Rejected"]
    if not ws:
        return "You have no upcoming workshops scheduled."
    nxt = min(ws, key=lambda w: w["from_date"] or "9999")
    return (f"Your next workshop is '{nxt['title']}' ({nxt['topic']}), starting {_fmt(nxt['from_date'])} "
            f"and running to {_fmt(nxt['to_date'])} at {nxt['venue']}. Status: {nxt['status']}.")


def _h_ongoing(db, pid, msg, topic):
    ws = [w for w in _my_workshops(db, pid) if w["schedule"] == "Ongoing" and w["status"] != "Rejected"]
    if not ws:
        return "You have no trainings in progress at the moment."
    lines = [f"• {w['title']} ({w['topic']}) at {w['venue']}, until {_fmt(w['to_date'])}" for w in ws]
    return "Currently ongoing for you:\n" + "\n".join(lines)


def _h_pending(db, pid, msg, topic):
    ws = [w for w in _my_workshops(db, pid) if w["status"] == "Pending"]
    if not ws:
        return "You have no pending invitations. You're all caught up."
    lines = [f"• {w['title']} ({w['topic']}) — {_fmt(w['from_date'])} at {w['venue']}" for w in ws]
    return (f"You have {len(ws)} invitation(s) awaiting your response:\n" + "\n".join(lines)
            + "\nYou can Accept or Decline them in the 'Action Required' tab.")


def _h_venue(db, pid, msg, topic):
    ws = [w for w in _my_workshops(db, pid) if w["schedule"] in ("Upcoming", "Ongoing") and w["status"] != "Rejected"]
    if topic:
        ws = [w for w in ws if w["topic"] == topic]
    if not ws:
        return "I couldn't find an active workshop for you to give a venue for."
    nxt = min(ws, key=lambda w: w["from_date"] or "9999")
    return f"'{nxt['title']}' is being held at {nxt['venue']} (starts {_fmt(nxt['from_date'])})."


def _h_total(db, pid, msg, topic):
    n = db.query(models.TrainingHistory).filter_by(personnel_id=pid).count()
    return f"You have completed {n} training(s) so far. You can see the topic-wise breakdown on the Analytics tab."


def _h_topic_history(db, pid, msg, topic):
    if not topic:
        return _h_total(db, pid, msg, topic)
    n = db.query(models.TrainingHistory).filter_by(personnel_id=pid, topic=topic).count()
    return f"You have completed {n} training(s) in {topic}."


def _h_profile(db, pid, msg, topic):
    p = _person(db, pid)
    if not p:
        return "I couldn't find your profile."
    return (f"You are {p.name}, {p.designation} ({p.stream}), specialization {p.specialization}, "
            f"posted at {p.station} in the {p.zone} zone. Service time left: {p.service_time_left} years.")


def _h_travel(db, pid, msg, topic):
    p = _person(db, pid)
    base = POLICY["travel_allowance"]
    if not p:
        return base
    ws = [w for w in _my_workshops(db, pid) if w["schedule"] in ("Upcoming", "Ongoing") and w["status"] != "Rejected"]
    if ws:
        nxt = min(ws, key=lambda w: w["from_date"] or "9999")
        if nxt["venue"] and p.station and nxt["venue"].lower() != p.station.lower():
            return (f"{base}\n\nFor you specifically: '{nxt['title']}' is at {nxt['venue']} while your station "
                    f"is {p.station} — this is an out-station training, so you are eligible for TA/DA.")
        return (f"{base}\n\nFor you specifically: '{nxt['title']}' is at your home station ({p.station}), "
                f"so TA is not applicable for it.")
    return base


def _h_workshop_by_topic(db, pid, msg, topic):
    q = db.query(models.Workshop)
    if topic:
        q = q.filter(models.Workshop.topic == topic)
    shops = q.all()
    upcoming = [w for w in shops if schedule_status(w.from_date, w.to_date) == "Upcoming"]
    upcoming.sort(key=lambda w: w.from_date or "")
    if not upcoming:
        return f"There are no upcoming {topic + ' ' if topic else ''}workshops in the catalogue right now."
    lines = [f"• {w.title} — {_fmt(w.from_date)} to {_fmt(w.to_date)} at {w.venue} (min. {w.min_designation})"
             for w in upcoming[:6]]
    head = f"Upcoming {topic} workshop(s):" if topic else "Upcoming workshops:"
    return head + "\n" + "\n".join(lines)


def _policy(key):
    return lambda db, pid, msg, topic: POLICY[key]


# --------------------------------------------------------------------------
# Intent registry: (name, keyword list, handler, requires_topic)
# Ordered by priority — earlier wins ties.
# --------------------------------------------------------------------------
INTENTS = [
    ("greeting", ["hello", "hi ", "hey", "namaste", "good morning", "good evening"], _h_greeting, False),
    ("thanks", ["thank", "thanks", "great", "awesome"], lambda *_: "You're welcome! Anything else?", False),
    ("help", ["help", "what can you do", "options", "capabilit"], _h_help, False),
    ("travel_allowance", ["travel allowance", "ta/da", "ta da", "tada", "allowance", "reimburse", "da ", "travel cost"], _h_travel, False),
    ("instructor", ["instructor", "faculty", "trainer", "who is teaching", "who will teach"], _policy("instructor"), False),
    ("reporting_time", ["what time", "start time", "timing", "reporting", "when should i reach", "when do i report"], _policy("reporting_time"), False),
    ("certificate", ["certificate", "certification", "certified"], _policy("certificate"), False),
    ("attendance", ["attendance", "how many days do i need", "minimum attendance"], _policy("attendance"), False),
    ("accept_decline", ["how do i accept", "how to accept", "how do i decline", "how to decline", "reject invitation", "accept invitation"], _policy("accept_decline"), False),
    ("topic_history", ["how many", "completed", "done", "attended", "finished"], _h_topic_history, True),
    ("total_trainings", ["how many trainings", "total training", "trainings completed", "trainings have i", "completed", "done so far"], _h_total, False),
    ("pending_actions", ["pending", "invitation", "action required", "accept or", "awaiting", "respond"], _h_pending, False),
    ("my_ongoing", ["ongoing", "in progress", "current training", "right now", "happening now"], _h_ongoing, False),
    ("next_workshop", ["next workshop", "next training", "soonest", "upcoming next"], _h_next, False),
    ("workshop_venue", ["where is", "venue", "location", "which city", "held"], _h_venue, False),
    ("my_upcoming", ["my upcoming", "my workshop", "my training", "my schedule", "assigned to me", "upcoming"], _h_my_upcoming, False),
    ("workshop_by_topic", ["when is", "is there", "any workshop", "schedule", "workshop on", "catalogue", "available workshop"], _h_workshop_by_topic, False),
    ("my_profile", ["my designation", "my zone", "my profile", "my specialization", "my station", "service left", "who am i"], _h_profile, False),
]


def _score(msg: str, keywords: list[str]) -> int:
    return sum(1 for kw in keywords if kw in msg)


def answer(db: Session, personnel_id: str, message: str) -> dict:
    """Route a message to the best intent and return a factual, DB-backed reply."""
    msg = f" {message.lower().strip()} "
    topic = _detect_topic(msg)

    best = None  # (score, name, handler)
    for name, keywords, handler, requires_topic in INTENTS:
        if requires_topic and not topic:
            continue
        score = _score(msg, keywords)
        # Entity boost only when the intent's own keywords also matched, so a bare
        # topic mention ("when is the AI workshop") can't hijack topic_history.
        if requires_topic and topic and score > 0:
            score += 2
        if score > 0 and (best is None or score > best[0]):
            best = (score, name, handler)

    if best is None:
        return {
            "intent": "fallback",
            "reply": ("I'm not sure about that one. I can help with your workshops, schedules, "
                      "pending invitations, trainings completed, and training policies."),
            "suggestions": SUGGESTIONS,
        }

    _, name, handler = best
    return {"intent": name, "reply": handler(db, personnel_id, msg, topic), "suggestions": []}

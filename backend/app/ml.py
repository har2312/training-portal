"""
ML engine (Week 2).

Supervised ranking (Random Forest) — now TOPIC-AWARE: the history feature is the
count of past trainings *in the workshop's topic*, not a gross count. A person
with 5 AI trainings and 0 Signal trainings is treated as untrained for a Signal
course.

Auto-Allot priority order (strict):
    1. Zone preference        (in-zone before out-of-zone)
    2. Educational relevance  (specialization matches workshop topic)
    3. Designation constraint (hard filter: min_designation & above) + seniority
ML probability (topic-aware) ranks candidates within those tiers.

Unsupervised (K-Means) — "The Oracle" skill-gap analyzer.
"""
import numpy as np
import pandas as pd
from datetime import date
from sklearn.ensemble import RandomForestClassifier
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session

from . import models
from .constants import (
    TOPICS, TECHNICAL_TOPICS, designation_rank, meets_threshold,
)

_rf_model: RandomForestClassifier | None = None
_model_confidence: float = 0.0
_training_samples: int = 0


# ---------------------------------------------------------------------------
# Topic-wise history helpers
# ---------------------------------------------------------------------------
def _topic_matrix(db: Session) -> pd.DataFrame:
    """personnel_id -> per-topic completed-training counts + last training date."""
    hist = pd.read_sql(db.query(models.TrainingHistory).statement, db.bind)
    people = pd.read_sql(db.query(models.Personnel).statement, db.bind)[["personnel_id"]]

    if hist.empty:
        mat = people.copy()
        for t in TOPICS:
            mat[f"topic_{t}"] = 0
        mat["last_training"] = None
        return mat.set_index("personnel_id")

    counts = (
        hist.groupby(["personnel_id", "topic"]).size().unstack(fill_value=0)
        .reindex(columns=TOPICS, fill_value=0)
    )
    counts.columns = [f"topic_{c}" for c in counts.columns]
    last = hist.groupby("personnel_id")["completed_date"].max().rename("last_training")

    mat = people.set_index("personnel_id").join(counts).join(last)
    for t in TOPICS:
        col = f"topic_{t}"
        if col not in mat:
            mat[col] = 0
        mat[col] = mat[col].fillna(0).astype(int)
    return mat


def _extract_features(rows: pd.DataFrame, topic: str, target_zone: str, tmat: pd.DataFrame) -> pd.DataFrame:
    """Feature matrix for the supervised model, topic-aware."""
    f = pd.DataFrame(index=rows.index)
    topic_col = f"topic_{topic}" if f"topic_{topic}" in tmat.columns else None

    def topic_count(pid):
        if topic_col is None or pid not in tmat.index:
            return 0
        return int(tmat.at[pid, topic_col])

    f["Topic_Trainings"] = rows["personnel_id"].map(topic_count)
    f["Specialization_Match"] = (rows["specialization"] == topic).astype(int)
    f["Zone_Match"] = rows["zone"].apply(lambda z: 1 if target_zone == "All" or target_zone == z else 0)
    f["Designation_Rank"] = rows["designation"].map(designation_rank)
    f["Service_Time_Left"] = rows["service_time_left"]
    f["Performance_Score"] = rows["performance_score"]
    return f


# ---------------------------------------------------------------------------
# Training (continuous learning)
# ---------------------------------------------------------------------------
def train_model(db: Session) -> dict:
    global _rf_model, _model_confidence, _training_samples

    people = pd.read_sql(db.query(models.Personnel).statement, db.bind)
    shops = pd.read_sql(db.query(models.Workshop).statement, db.bind).set_index("program_id")
    tmat = _topic_matrix(db)

    frames_X, labels = [], []

    hist = pd.read_sql(db.query(models.HistoricalAllotment).statement, db.bind)
    if not hist.empty:
        for pid_w, grp in hist.groupby("program_id"):
            if pid_w not in shops.index:
                continue
            ws = shops.loc[pid_w]
            joined = grp.merge(people, on="personnel_id", how="inner")
            if joined.empty:
                continue
            frames_X.append(_extract_features(joined, ws["topic"], ws["target_zone"], tmat))
            labels.append(joined["is_optimal_match"].astype(int).reset_index(drop=True))

    decided = pd.read_sql(
        db.query(models.Allotment).filter(models.Allotment.status.in_(["Accepted", "Rejected"])).statement,
        db.bind,
    )
    if not decided.empty:
        for pid_w, grp in decided.groupby("program_id"):
            if pid_w not in shops.index:
                continue
            ws = shops.loc[pid_w]
            joined = grp.merge(people, on="personnel_id", how="inner")
            if joined.empty:
                continue
            frames_X.append(_extract_features(joined, ws["topic"], ws["target_zone"], tmat))
            labels.append((joined["status"] == "Accepted").astype(int).reset_index(drop=True))

    if not frames_X:
        _rf_model, _model_confidence, _training_samples = None, 0.0, 0
        return {"trained": False, "samples": 0, "confidence": 0.0}

    X = pd.concat([f.reset_index(drop=True) for f in frames_X], ignore_index=True)
    y = pd.concat([pd.Series(l).reset_index(drop=True) for l in labels], ignore_index=True)

    model = RandomForestClassifier(n_estimators=120, random_state=42)
    model.fit(X, y)
    _rf_model = model
    _training_samples = len(X)
    _model_confidence = float(model.score(X, y)) if y.nunique() > 1 else 0.5
    return {"trained": True, "samples": _training_samples, "confidence": _model_confidence}


def model_confidence() -> float:
    return _model_confidence


# ---------------------------------------------------------------------------
# Explainable AI
# ---------------------------------------------------------------------------
def build_reason(row, workshop: models.Workshop, tmat: pd.DataFrame | None = None) -> str:
    """Human-readable, admin-only. Reflects the new topic-aware logic."""
    parts = []
    tz = workshop.target_zone
    if tz == "All":
        parts.append("Open zone")
    elif row["zone"] == tz:
        parts.append("Local zone (saves travel)")
    else:
        parts.append("Out-of-zone (fills vacancy)")

    if row.get("specialization") == workshop.topic:
        parts.append(f"Educated in {workshop.topic}")

    # Topic-wise history (the crucial fix)
    tcount = 0
    if tmat is not None and row["personnel_id"] in tmat.index:
        col = f"topic_{workshop.topic}"
        if col in tmat.columns:
            tcount = int(tmat.at[row["personnel_id"], col])
    if tcount == 0:
        parts.append(f"No prior {workshop.topic} training (priority)")
    else:
        parts.append(f"{tcount} prior {workshop.topic} training(s)")

    parts.append(f"{row['designation']} (meets {workshop.min_designation}+)")
    ps = row.get("performance_score")
    if ps is not None and pd.notna(ps):
        parts.append("High performance" if int(ps) >= 8 else "Solid performance" if int(ps) >= 5 else "Developing")
    return " | ".join(parts)


# ---------------------------------------------------------------------------
# Ranking / allotment  (strict priority: Zone -> Education -> Designation)
# ---------------------------------------------------------------------------
def rank_candidates(db: Session, workshop: models.Workshop, exclude_ids=None, limit=None) -> pd.DataFrame:
    exclude_ids = exclude_ids or set()
    people = pd.read_sql(
        db.query(models.Personnel).filter(models.Personnel.role == "personnel").statement, db.bind
    )
    tmat = _topic_matrix(db)

    # Hard filters: retirement, designation threshold, exclusions.
    elig = people[people["service_time_left"] > 2.0].copy()
    elig = elig[~elig["personnel_id"].isin(exclude_ids)]
    elig = elig[elig["designation"].apply(lambda d: meets_threshold(d, workshop.min_designation))]
    if elig.empty:
        elig["ml_match_probability"] = []
        elig["ai_reason"] = []
        return elig

    # Topic-aware ML probability
    X = _extract_features(elig, workshop.topic, workshop.target_zone, tmat)
    elig["ml_match_probability"] = _rf_model.predict_proba(X)[:, 1] if _rf_model is not None else 0.0

    # Priority sort keys
    tz = workshop.target_zone
    elig["_zone_pref"] = elig["zone"].apply(lambda z: 1 if tz == "All" or tz == z else 0)
    elig["_edu"] = (elig["specialization"] == workshop.topic).astype(int)
    elig["_seniority"] = elig["designation"].map(designation_rank)

    ranked = elig.sort_values(
        by=["_zone_pref", "_edu", "ml_match_probability", "_seniority"],
        ascending=[False, False, False, True],
    )

    ranked["ai_reason"] = ranked.apply(lambda r: build_reason(r, workshop, tmat), axis=1)
    return ranked.head(limit) if limit else ranked


# ---------------------------------------------------------------------------
# The Oracle — K-Means skill-gap analyzer
# ---------------------------------------------------------------------------
def _years_since(iso: str | None, today: date) -> float:
    if not iso or (isinstance(iso, float) and pd.isna(iso)):
        return 10.0  # never trained -> large gap
    try:
        return round((today - date.fromisoformat(str(iso)[:10])).days / 365.0, 1)
    except ValueError:
        return 10.0


def run_oracle(db: Session, k: int = 5) -> list[dict]:
    """
    Cluster personnel by age, zone, designation rank, and topic-wise training
    counts; surface the weakest topic per cluster as a skill-gap recommendation.
    """
    people = pd.read_sql(
        db.query(models.Personnel).filter(models.Personnel.role == "personnel").statement, db.bind
    )
    if len(people) < k:
        return []
    tmat = _topic_matrix(db)
    today = date.today()

    df = people.merge(tmat.reset_index(drop=True).assign(personnel_id=tmat.index),
                      on="personnel_id", how="left")
    for t in TOPICS:
        df[f"topic_{t}"] = df.get(f"topic_{t}", 0)
        df[f"topic_{t}"] = df[f"topic_{t}"].fillna(0)
    df["years_since"] = df["last_training"].apply(lambda x: _years_since(x, today))
    df["desig_rank"] = df["designation"].map(designation_rank)
    df["zone_code"] = df["zone"].astype("category").cat.codes

    feature_cols = ["age", "zone_code", "desig_rank", "years_since"] + [f"topic_{t}" for t in TOPICS]
    X = StandardScaler().fit_transform(df[feature_cols].fillna(0))

    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    df["cluster"] = km.fit_predict(X)

    VENUE = {"North": "Delhi", "South": "Bengaluru", "East": "Kolkata",
             "West": "Mumbai", "North-East": "Shillong", "Central": "Bhopal"}
    insights = []
    for c, grp in df.groupby("cluster"):
        if len(grp) < 3:
            continue
        zone = grp["zone"].mode().iat[0]
        desig = grp["designation"].mode().iat[0]
        # weakest topic = lowest average count across the cluster
        avg = {t: grp[f"topic_{t}"].mean() for t in TOPICS}
        weak_topic = min(avg, key=avg.get)
        avg_gap = round(grp["years_since"].mean(), 1)
        # Only report a genuine gap
        if avg[weak_topic] >= 1.5 and avg_gap < 3:
            continue
        kind = "technical" if weak_topic in TECHNICAL_TOPICS else "domain"
        rec_title = {
            "AI": "AI & Automation", "Signal": "Digital Broadcasting",
            "Content": "Modern Content Production", "Administration": "Governance & Procurement",
            "Awareness": "Public Service Orientation",
        }[weak_topic]
        insights.append({
            "cluster": int(c),
            "count": int(len(grp)),
            "designation": desig,
            "zone": zone,
            "weak_topic": weak_topic,
            "avg_years_since_training": avg_gap,
            "recommendation": (
                f"{len(grp)} {desig}s in the {zone} zone have minimal {kind} training in "
                f"'{weak_topic}' (avg {avg_gap} yrs since last training). "
                f"Recommend a '{rec_title}' workshop in {VENUE.get(zone, zone)}."
            ),
        })
    insights.sort(key=lambda i: (-i["avg_years_since_training"], -i["count"]))
    return insights

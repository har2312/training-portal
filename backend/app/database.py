"""
Database engine + session setup.

Development uses SQLite by default; production uses PostgreSQL via the
DATABASE_URL environment variable. Providers (Neon/Render/Supabase) hand out
URLs like `postgres://...` or `postgresql://...`; we normalize them to the
psycopg v3 driver that this project installs, so no manual editing is needed.

    Local:  (unset)                  -> sqlite:///./training_portal.db
    Prod:   DATABASE_URL=postgres://user:pass@host/db?sslmode=require
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


def _normalize(url: str) -> str:
    # Managed Postgres providers often use the legacy 'postgres://' scheme and
    # default to psycopg2. Force the psycopg (v3) driver that we ship.
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


DATABASE_URL = _normalize(os.getenv("DATABASE_URL", "sqlite:///./training_portal.db"))
IS_SQLITE = DATABASE_URL.startswith("sqlite")

connect_args = {"check_same_thread": False} if IS_SQLITE else {}
# pool_pre_ping avoids stale-connection errors on free tiers that idle the DB.
engine_kwargs = {} if IS_SQLITE else {"pool_pre_ping": True, "pool_recycle": 300}

engine = create_engine(DATABASE_URL, connect_args=connect_args, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

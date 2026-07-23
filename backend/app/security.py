"""
Password hashing via the bcrypt library directly.

We use bcrypt straight (not passlib) because passlib 1.7.4 is incompatible
with bcrypt >= 4.1 — it reads bcrypt.__about__, which newer bcrypt removed.
"""
import bcrypt


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

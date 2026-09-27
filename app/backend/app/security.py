"""PBKDF2 口令散列（stdlib 实现，无 bcrypt 依赖坑）+ JWT 签发校验。"""
import datetime as dt
import hashlib
import secrets

import jwt

from .config import settings

_ITERATIONS = 200_000


def hash_password(plain: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", plain.encode(), salt.encode(), _ITERATIONS
    ).hex()
    return f"pbkdf2:{_ITERATIONS}:{salt}:{digest}"


def verify_password(plain: str, stored: str) -> bool:
    try:
        _, iterations, salt, digest = stored.split(":")
        candidate = hashlib.pbkdf2_hmac(
            "sha256", plain.encode(), salt.encode(), int(iterations)
        ).hex()
        return secrets.compare_digest(candidate, digest)
    except (ValueError, AttributeError):
        return False


def create_token(patient_id: int) -> str:
    payload = {
        "sub": str(patient_id),
        "exp": dt.datetime.utcnow() + dt.timedelta(hours=settings.JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None

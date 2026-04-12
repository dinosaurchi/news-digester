"""Session and password-authentication service."""

import base64
import hashlib
import hmac
import secrets
import uuid

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db
from app.models.user import User

_PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
_PASSWORD_HASH_ITERATIONS = 600_000

# Process-local server-side sessions. The trusted identity lives in users;
# this map only connects an opaque cookie value to a user id.
_sessions: dict[str, str] = {}


def hash_password(password: str) -> str:
    """Return a salted password hash."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _PASSWORD_HASH_ITERATIONS,
    )
    return "$".join(
        [
            _PASSWORD_HASH_ALGORITHM,
            str(_PASSWORD_HASH_ITERATIONS),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(digest).decode("ascii"),
        ]
    )


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a stored hash."""
    try:
        algorithm, raw_iterations, raw_salt, raw_digest = password_hash.split("$", 3)
        if algorithm != _PASSWORD_HASH_ALGORITHM:
            return False
        iterations = int(raw_iterations)
        salt = base64.urlsafe_b64decode(raw_salt.encode("ascii"))
        expected_digest = base64.urlsafe_b64decode(raw_digest.encode("ascii"))
    except (ValueError, TypeError):
        return False

    actual_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(actual_digest, expected_digest)


def bootstrap_admin_user(db: Session) -> User:
    """Ensure the configured dev/admin user exists.

    This path is intentionally narrow: it creates one configured admin when no
    users exist. It does not manage additional users or rotate existing hashes.
    """
    existing = db.query(User).order_by(User.created_at).first()
    if existing is not None:
        return existing

    username = settings.ADMIN_USERNAME.strip()
    password = settings.ADMIN_PASSWORD
    display_name = settings.ADMIN_DISPLAY_NAME.strip() or username
    role = settings.ADMIN_ROLE.strip() or "admin"

    if not username or not password:
        raise ValueError("ADMIN_USERNAME and ADMIN_PASSWORD must not be empty")

    user = User(
        username=username,
        password_hash=hash_password(password),
        display_name=display_name,
        role=role,
        status="active",
    )
    db.add(user)
    db.flush()
    return user


def authenticate_user(db: Session, *, username: str, password: str) -> User | None:
    """Return the active user for valid credentials, otherwise None."""
    user = db.query(User).filter(User.username == username).first()
    if user is None or user.status != "active":
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_session(db: Session, *, user: User) -> dict:
    """Create a server-side session for an authenticated user."""
    session_id = uuid.uuid4().hex
    _sessions[session_id] = user.id
    payload = user_to_session_dict(user)
    payload["session_id"] = session_id
    return payload


def get_session_user(db: Session, *, session_id: str) -> dict | None:
    """Return the current session user DTO payload, or None."""
    user_id = _sessions.get(session_id)
    if not user_id:
        return None

    user = db.get(User, user_id)
    if user is None or user.status != "active":
        _sessions.pop(session_id, None)
        return None

    return user_to_session_dict(user)


def delete_session(db: Session, *, session_id: str) -> None:
    """Remove a server-side session."""
    _sessions.pop(session_id, None)


def user_to_session_dict(user: User) -> dict:
    """Convert a User ORM object to the stable frontend user shape."""
    return {
        "id": user.id,
        "username": user.username,
        "displayName": user.display_name,
        "role": user.role,
    }


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """FastAPI dependency that returns the authenticated user dict or raises 401."""
    from fastapi import HTTPException

    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = get_session_user(db, session_id=session_id)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired")

    return user

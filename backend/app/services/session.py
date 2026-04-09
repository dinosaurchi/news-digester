"""Stub session service — dict-backed, no real auth."""

import uuid

# In-memory session store: session_id -> user dict
_sessions: dict[str, dict] = {}


def create_session(db, *, username: str) -> dict:
    """Create a new stub session for the given username."""
    session_id = uuid.uuid4().hex
    user = {
        "id": "user-1",
        "username": username,
        "displayName": username[0].upper() + username[1:] if username else "User",
        "role": "admin",
        "session_id": session_id,
    }
    _sessions[session_id] = user
    return user


def get_session_user(db, *, session_id: str) -> dict | None:
    """Return the user dict for a session, or None."""
    return _sessions.get(session_id)


def delete_session(db, *, session_id: str) -> None:
    """Remove a session."""
    _sessions.pop(session_id, None)

"""Redis-backed session store.

Provides a thin abstraction over Redis for server-side session storage.
All sessions are stored as JSON-serialized dicts with a configurable TTL.
"""

import json
import logging

import redis

from app.config import settings

logger = logging.getLogger(__name__)

SESSION_TTL_SECONDS: int = 86_400  # 24 hours

# Key prefix for all session keys in Redis
_SESSION_KEY_PREFIX = "sme:session:"

_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis | None:
    """Return a shared Redis client, creating it on first call.

    Returns ``None`` if Redis is unreachable so callers can fall back
    gracefully (e.g. during tests or in degraded mode).
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    try:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        # Verify connectivity with a lightweight ping
        _redis_client.ping()
        return _redis_client
    except redis.ConnectionError:
        logger.warning(
            "Redis is unavailable at %s — sessions will not persist across restarts",
            settings.REDIS_URL,
        )
        return None


def _session_key(session_id: str) -> str:
    """Return the Redis key for a session."""
    return f"{_SESSION_KEY_PREFIX}{session_id}"


def set_session(session_id: str, data: dict, ttl: int | None = None) -> bool:
    """Store session data in Redis as JSON with a TTL.

    Args:
        session_id: Unique session identifier.
        data: Arbitrary dict to store (will be JSON-serialized).
        ttl: Time-to-live in seconds. Defaults to ``SESSION_TTL_SECONDS``.

    Returns:
        ``True`` if the value was stored, ``False`` on failure.
    """
    client = get_redis_client()
    if client is None:
        return False

    try:
        key = _session_key(session_id)
        value = json.dumps(data)
        effective_ttl = ttl if ttl is not None else SESSION_TTL_SECONDS
        client.setex(key, effective_ttl, value)
        return True
    except redis.RedisError:
        logger.warning("Failed to store session %s in Redis", session_id)
        return False


def get_session(session_id: str) -> dict | None:
    """Retrieve session data from Redis.

    Returns:
        The stored dict, or ``None`` if the session does not exist or
        Redis is unavailable.
    """
    client = get_redis_client()
    if client is None:
        return None

    try:
        key = _session_key(session_id)
        value = client.get(key)
        if value is None:
            return None
        return json.loads(value)
    except (redis.RedisError, json.JSONDecodeError):
        logger.warning("Failed to retrieve session %s from Redis", session_id)
        return None


def delete_session(session_id: str) -> bool:
    """Remove a session from Redis.

    Returns:
        ``True`` if the key was deleted (or did not exist), ``False`` on
        Redis failure.
    """
    client = get_redis_client()
    if client is None:
        return False

    try:
        key = _session_key(session_id)
        client.delete(key)
        return True
    except redis.RedisError:
        logger.warning("Failed to delete session %s from Redis", session_id)
        return False


def clear_sessions() -> None:
    """Remove all session keys from Redis using SCAN.

    This is safe for large keyspaces because it iterates incrementally
    rather than loading all keys into memory at once.
    """
    client = get_redis_client()
    if client is None:
        return

    try:
        cursor = 0
        while True:
            cursor, keys = client.scan(
                cursor, match=f"{_SESSION_KEY_PREFIX}*", count=100
            )
            if keys:
                client.delete(*keys)
            if cursor == 0:
                break
    except redis.RedisError:
        logger.warning("Failed to clear sessions from Redis")

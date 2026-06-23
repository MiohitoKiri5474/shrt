"""Server-side JWT revocation backed by Redis.

JWTs are stateless: once issued they remain valid until they expire. Logout
that only clears the client cookie does nothing for a token already copied
elsewhere — it stays valid for the remainder of its ``exp`` window. This module
maintains a blocklist of revoked ``jti`` (JWT ID) claims in Redis so that a
logged-out token is rejected server-side for the rest of its lifetime.

Each blocklist entry is written with ``SETEX`` using the token's *remaining*
TTL, so revoked entries expire from Redis exactly when the token itself would
have expired — the blocklist never grows without bound.

Fail-open policy: if Redis is unavailable, both ``revoke`` and ``is_revoked``
fail open (log a warning, do not raise). Failing closed on ``is_revoked`` would
reject *every* authenticated request during a Redis outage — a self-inflicted
denial of service. The bounded cost of failing open is that an already-revoked
token regains validity, but only for its remaining (<= ACCESS_TOKEN_EXPIRE)
window and only while Redis is down. The blocklist is defense-in-depth layered
on top of the short token lifetime, not the primary access control.
"""

import logging
import os
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)

_REVOKED_PREFIX = "revoked_jti:"


@runtime_checkable
class TokenBlocklist(Protocol):
    """Interface for token revocation stores (Redis in prod, fakes in tests)."""

    async def revoke(self, jti: str, ttl_seconds: int) -> None: ...

    async def is_revoked(self, jti: str) -> bool: ...


class NullTokenBlocklist:
    """No-op blocklist used when ``REDIS_URL`` is not configured.

    Revocation is unavailable: logout still clears the cookie and auth still
    works, but a stolen token cannot be invalidated server-side. A warning is
    logged once when this implementation is selected.
    """

    async def revoke(self, jti: str, ttl_seconds: int) -> None:
        return None

    async def is_revoked(self, jti: str) -> bool:
        return False


class RedisTokenBlocklist:
    """Redis-backed blocklist. Holds one pooled async client for the app's
    lifetime — never create or close a client per request."""

    def __init__(self, client) -> None:
        self._client = client

    async def revoke(self, jti: str, ttl_seconds: int) -> None:
        # A non-positive TTL means the token is already expired (or expiring this
        # instant) and needs no blocklist entry — it is rejected on its own.
        if ttl_seconds <= 0:
            return
        try:
            await self._client.setex(f"{_REVOKED_PREFIX}{jti}", ttl_seconds, "1")
        except Exception:
            # Fail open: never let a Redis outage block logout (would be a DoS).
            logger.warning(
                "Token blocklist: failed to revoke jti %s (Redis unavailable)",
                jti,
                exc_info=True,
            )

    async def is_revoked(self, jti: str) -> bool:
        try:
            return bool(await self._client.exists(f"{_REVOKED_PREFIX}{jti}"))
        except Exception:
            # Fail open: a Redis outage must not reject every authenticated
            # request. See module docstring for the security tradeoff.
            logger.warning(
                "Token blocklist: revocation check failed for jti %s (Redis "
                "unavailable) — failing open",
                jti,
                exc_info=True,
            )
            return False


_blocklist: TokenBlocklist | None = None


def _build_blocklist() -> TokenBlocklist:
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        logger.warning(
            "REDIS_URL not set — JWT revocation disabled. Logout will not "
            "invalidate tokens server-side; they remain valid until expiry."
        )
        return NullTokenBlocklist()
    import redis.asyncio as redis  # pragma: no cover — exercised only with a live Redis

    client = redis.from_url(redis_url, decode_responses=True)  # pragma: no cover
    return RedisTokenBlocklist(client)  # pragma: no cover


def get_token_blocklist() -> TokenBlocklist:
    """FastAPI dependency returning the process-wide blocklist singleton.

    Tests override this via ``app.dependency_overrides`` with an in-memory fake,
    mirroring how ``get_db`` is overridden in ``conftest.py``.
    """
    global _blocklist
    if _blocklist is None:
        _blocklist = _build_blocklist()
    return _blocklist

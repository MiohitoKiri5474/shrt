"""Server-side JWT revocation backed by Redis.

JWTs are stateless: once issued they remain valid until they expire. Logout
that only clears the client cookie does nothing for a token already copied
elsewhere — it stays valid for the remainder of its ``exp`` window. This module
maintains a blocklist of revoked ``jti`` (JWT ID) claims in Redis so that a
logged-out token is rejected server-side for the rest of its lifetime.

Each blocklist entry is written with ``SETEX`` using the token's *remaining*
TTL, so revoked entries expire from Redis exactly when the token itself would
have expired — the blocklist never grows without bound.

Fail-closed policy: if Redis is unavailable during ``is_revoked``, the token
is treated as revoked (returns True). This is a deliberate security-over-
availability tradeoff: failing open would allow a logged-out token to remain
valid during a Redis outage, which is a worse outcome than briefly rejecting
valid requests. ``revoke`` still fails open (log + no raise) because blocking
logout would be a denial-of-service.

Local bridge cache: each process also remembers the ``jti`` values it revokes
in an in-process cache. This still matters even with fail-closed ``is_revoked``:
``revoke()`` can fail to write to Redis during an outage (fails open — logout
must not block) and Redis can then *recover* before the token's TTL elapses.
In that window ``is_revoked``'s Redis call succeeds (no exception, so
fail-closed never triggers) but returns ``False`` since the key was never
written — the local cache is what still rejects that jti on the process that
revoked it, for the rest of its lifetime.
"""

import logging
import os
import time
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
        # Local bridge cache: jti -> monotonic deadline. Lets a token revoked on
        # THIS process stay rejected through a brief Redis outage instead of
        # failing open for its full remaining lifetime. See module docstring.
        self._local_revoked: dict[str, float] = {}

    def _remember_local(self, jti: str, ttl_seconds: int) -> None:
        self._local_revoked[jti] = time.monotonic() + ttl_seconds

    def _local_has(self, jti: str) -> bool:
        deadline = self._local_revoked.get(jti)
        if deadline is None:
            return False
        if deadline <= time.monotonic():
            # Entry aged out exactly when the token itself expires — drop it so
            # the cache stays bounded.
            del self._local_revoked[jti]
            return False
        return True

    async def revoke(self, jti: str, ttl_seconds: int) -> None:
        # A non-positive TTL means the token is already expired (or expiring this
        # instant) and needs no blocklist entry — it is rejected on its own.
        if ttl_seconds <= 0:
            return
        # Record locally first so a Redis outage during revoke cannot lose the
        # revocation on the process that performed it.
        self._remember_local(jti, ttl_seconds)
        try:
            await self._client.setex(f"{_REVOKED_PREFIX}{jti}", ttl_seconds, "1")
        except Exception:
            # Fail open: never let a Redis outage block logout (would be a DoS).
            # The local cache above still rejects this jti on this process.
            logger.warning(
                "Token blocklist: failed to revoke jti %s (Redis unavailable)",
                jti,
                exc_info=True,
            )

    async def is_revoked(self, jti: str) -> bool:
        # Local cache is positive-authoritative: if this process revoked the
        # token, it stays revoked regardless of Redis availability.
        if self._local_has(jti):
            return True
        try:
            return bool(await self._client.exists(f"{_REVOKED_PREFIX}{jti}"))
        except Exception:
            # Fail closed: a Redis outage means we cannot confirm the token
            # is not revoked, so we treat it as revoked. See module docstring.
            logger.warning(
                "Token blocklist: revocation check failed for jti %s (Redis "
                "unavailable) — failing closed",
                jti,
                exc_info=True,
            )
            return True


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

"""Server-side, single-use CSRF state for the Steam OpenID link flow (Redis).

Unlike the OAuth login flow, the Steam callback is a browser redirect back from
Steam with NO auth header — so the state is what binds the callback to the user
who started the link. ``/start`` (authenticated) mints a state and stashes the
initiating user's ``public_id`` under it; ``/callback`` consumes the state
(``GETDEL`` — single use) and resolves that user. Entries expire after
``oauth_state_ttl_seconds`` so a leaked/replayed state cannot be reused.
"""

from __future__ import annotations

from uuid import UUID

from slate.config import settings
from slate.infrastructure.cache.redis_client import get_redis_client

_KEY_PREFIX = "steam:link:state:"


async def store_steam_state(state: str, user_public_id: UUID) -> None:
    """Persist the initiating *user_public_id* under *state* (single-use TTL)."""
    client = get_redis_client()
    await client.set(
        f"{_KEY_PREFIX}{state}",
        str(user_public_id),
        ex=settings.oauth_state_ttl_seconds,
    )


async def consume_steam_state(state: str) -> UUID | None:
    """Atomically fetch-and-delete the user bound to *state* (single use)."""
    client = get_redis_client()
    raw = await client.getdel(f"{_KEY_PREFIX}{state}")
    if raw is None:
        return None
    try:
        return UUID(raw)
    except (ValueError, TypeError):
        return None

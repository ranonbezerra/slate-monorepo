"""Deterministic Steam client for tests and offline development.

Returns a small canned owned-games list whose titles line up with the dummy
catalog matcher, so the import path can be exercised end-to-end without a live
Steam Web API key.
"""

from __future__ import annotations

from .base import AbstractSteamClient, OwnedGame

# Titles chosen to match ``DummyCatalogMatcher``'s canned catalog (Hollow Knight,
# Celeste, Hades) plus one that won't match (drives the "unmatched" counter).
_CANNED_OWNED = [
    OwnedGame(appid=367520, name="Hollow Knight", playtime_minutes=1200),
    OwnedGame(appid=504230, name="Celeste", playtime_minutes=300),
    OwnedGame(appid=1145360, name="Hades", playtime_minutes=0),
    OwnedGame(appid=999999, name="Totally Unknown Indie Game", playtime_minutes=42),
]


class DummySteamClient(AbstractSteamClient):
    """A canned Steam client that never touches the network."""

    def __init__(self, owned: list[OwnedGame] | None = None) -> None:
        self._owned = owned if owned is not None else list(_CANNED_OWNED)

    async def get_owned_games(self, steam_id: str) -> list[OwnedGame]:
        """Return the canned owned-games list, ignoring *steam_id*."""
        return list(self._owned)

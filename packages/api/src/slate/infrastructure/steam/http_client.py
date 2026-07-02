"""httpx-backed Steam Web API client (ROADMAP Epic 30).

Calls the official ``IPlayerService/GetOwnedGames`` endpoint. The host is a
hard-coded constant — never user input — so a malicious ``steam_id`` can only
influence a query parameter, never the request target (SSRF-safe). A private
profile (no ``games`` array in the response) resolves to ``[]``.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from .base import AbstractSteamClient, OwnedGame, SteamApiError

logger = structlog.get_logger()

# SSRF guard: the endpoint host is fixed. The only attacker-influenced value is
# the ``steamid`` query param, which cannot change where the request is sent.
_OWNED_GAMES_URL = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
_TIMEOUT_SECONDS = 15.0


class SteamHttpClient(AbstractSteamClient):
    """Fetch owned games from the live Steam Web API."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def get_owned_games(self, steam_id: str) -> list[OwnedGame]:
        """Fetch and parse ``GetOwnedGames`` for *steam_id* (SteamID64)."""
        params: dict[str, str | int] = {
            "key": self._api_key,
            "steamid": steam_id,
            "include_appinfo": 1,
            "include_played_free_games": 1,
            "format": "json",
        }
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            try:
                resp = await client.get(_OWNED_GAMES_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
                return _parse_owned_games(data)
            except httpx.HTTPError as exc:
                # The httpx exception message embeds the request URL — whose query
                # string carries the API key. Log ONLY the status; never the error.
                status = (
                    exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
                )
                logger.warning("steam_owned_games_request_failed", status=status)
        # Raised OUTSIDE the except so no `__context__`/`__cause__` links back to
        # the URL-bearing httpx error — it can't reach a traceback log or Sentry.
        raise SteamApiError("Steam API request failed")


def _parse_owned_games(data: Any) -> list[OwnedGame]:
    """Parse a ``GetOwnedGames`` payload into ``OwnedGame`` rows.

    A private profile returns ``{"response": {}}`` with no ``games`` key ⇒ ``[]``.
    Malformed rows (missing appid/name) are skipped rather than aborting the sync.
    """
    response = data.get("response") if isinstance(data, dict) else None
    if not isinstance(response, dict):
        return []
    raw_games = response.get("games")
    if not isinstance(raw_games, list):
        return []

    owned: list[OwnedGame] = []
    for item in raw_games:
        if not isinstance(item, dict):
            continue
        appid = item.get("appid")
        name = item.get("name")
        if not isinstance(appid, int) or not isinstance(name, str) or not name.strip():
            continue
        playtime = item.get("playtime_forever")
        minutes = playtime if isinstance(playtime, int) and playtime >= 0 else 0
        owned.append(OwnedGame(appid=appid, name=name.strip(), playtime_minutes=minutes))
    return owned

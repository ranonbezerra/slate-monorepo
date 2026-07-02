"""Steam Web API port (ROADMAP Epic 30).

The account-sync upgrade over the OCR screenshot import: instead of reading a
library screenshot, we pull the user's entire owned library + playtime straight
from Steam. This module is the hexagonal *port* — a narrow contract the rest of
the app depends on, with an httpx-backed adapter and a canned dummy behind it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class SteamApiError(Exception):
    """A Steam Web API call failed. Deliberately carries NO request detail.

    The raw httpx error embeds the request URL, whose query string contains the
    Steam API key — so the adapter raises this sanitized error instead, dropping
    the original exception chain, to keep the key out of logs/Sentry.
    """


@dataclass(frozen=True)
class OwnedGame:
    """One game the Steam account owns, with total playtime.

    ``playtime_minutes`` is Steam's ``playtime_forever`` (all-time minutes across
    every device); a never-launched game reports ``0``.
    """

    appid: int
    name: str
    playtime_minutes: int


class AbstractSteamClient(ABC):
    """Contract for reading a Steam account's owned games."""

    @abstractmethod
    async def get_owned_games(self, steam_id: str) -> list[OwnedGame]:
        """Return the games owned by *steam_id* (a SteamID64).

        A private profile (Steam returns no ``games`` list) yields ``[]`` rather
        than an error — an empty result is a legitimate outcome the caller
        surfaces as a "private or empty" hint, not a failure.
        """
        ...

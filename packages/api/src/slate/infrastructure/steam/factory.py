"""Factory for the Steam Web API client.

Uses the dummy under tests or when no ``STEAM_API_KEY`` is configured (the
feature is disabled); otherwise the httpx-backed client. Returning the dummy
when unconfigured keeps a caller's code path working, but the router-level guard
(``is_steam_enabled``) is what actually 503s the feature off in production.
"""

from __future__ import annotations

from slate.config import Settings

from .base import AbstractSteamClient


def get_steam_client(settings: Settings) -> AbstractSteamClient:
    """Return the Steam client for the current environment."""
    if settings.app_env == "testing" or not settings.steam_api_key:
        from .dummy import DummySteamClient

        return DummySteamClient()

    from .http_client import SteamHttpClient

    return SteamHttpClient(settings.steam_api_key)


def is_steam_enabled(settings: Settings) -> bool:
    """True when the Steam account-sync feature is available.

    Enabled with a configured key, or always in testing (the dummy stands in).
    Empty key outside testing ⇒ the endpoints degrade to a clear 503.
    """
    return settings.app_env == "testing" or bool(settings.steam_api_key)

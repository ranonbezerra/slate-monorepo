"""Pydantic schemas for the Steam account-sync import (Epic 30)."""

from __future__ import annotations

from pydantic import BaseModel


class SteamStartResponse(BaseModel):
    """The Steam OpenID URL for the SPA to navigate the browser to.

    Returned as JSON (not a 302) because ``/start`` is authenticated with the
    in-memory Bearer token: the SPA fetches this, then sets ``window.location``.
    """

    redirect_url: str


class SteamImportSummary(BaseModel):
    """Outcome of one Steam owned-library import.

    ``imported`` = games newly added to the library (on PC (Steam));
    ``already_owned`` = matched games the user already had on that platform
    (idempotent skip); ``unmatched`` = owned Steam games we couldn't map to a
    catalog game; ``private_or_empty`` = Steam returned no games (a private
    profile or a genuinely empty library) — a hint for the UI, not an error.
    """

    imported: int
    already_owned: int
    unmatched: int
    private_or_empty: bool

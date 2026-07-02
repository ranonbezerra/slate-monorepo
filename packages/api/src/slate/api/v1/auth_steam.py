"""Steam account-link endpoints (OpenID 2.0) — ROADMAP Epic 30.

``/start`` (authenticated) mints a CSRF ``state`` bound server-side to the
initiating user and redirects the browser to Steam. ``/callback`` (a browser
redirect back from Steam, so NOT authenticated — the ``state`` is what binds it
to the user) verifies the assertion with Steam and persists the SteamID64, then
redirects the browser back to the web app. This is LINK only; the actual library
import is a separate authenticated endpoint (``/v1/library/steam/import``).
"""

from __future__ import annotations

import secrets
from urllib.parse import urlsplit, urlunsplit

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from slate.api.v1._rate_limit import rate_limit
from slate.config import settings
from slate.core.library.steam_schemas import SteamStartResponse
from slate.deps import CurrentUserDep
from slate.deps.auth import UserRepoDep
from slate.infrastructure.steam.factory import is_steam_enabled
from slate.infrastructure.steam.openid import (
    build_login_redirect_url,
    extract_openid_params,
    verify_assertion,
)
from slate.infrastructure.steam.state_store import (
    consume_steam_state,
    store_steam_state,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/v1/auth/steam", tags=["auth"])

_check_steam_connect_rate = rate_limit(
    "auth_steam_connect", settings.rate_limit_steam_connect_per_minute, 60, by="ip"
)
_check_steam_callback_rate = rate_limit(
    "auth_steam_callback", settings.rate_limit_steam_connect_per_minute, 60, by="ip"
)


def _require_enabled() -> None:
    """503 when the Steam feature is disabled (no API key configured)."""
    if not is_steam_enabled(settings):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Steam import is not configured.",
        )


def _callback_url(state: str) -> str:
    """The return_to URL Steam redirects the browser back to (carries *state*)."""
    return f"{settings.oauth_redirect_base_url}/v1/auth/steam/callback?state={state}"


def _web_origin() -> str:
    """The web app origin (scheme://host[:port]) derived from the success URL."""
    parts = urlsplit(settings.oauth_web_success_url)
    return urlunsplit((parts.scheme, parts.netloc, "", "", ""))


def _account_redirect(outcome: str) -> RedirectResponse:
    """Redirect the browser to the web app's account page with a Steam *outcome*."""
    return RedirectResponse(
        f"{_web_origin()}/account?steam={outcome}",
        status_code=status.HTTP_302_FOUND,
    )


@router.get("/start", dependencies=[Depends(_check_steam_connect_rate)])
async def steam_start(current_user: CurrentUserDep) -> SteamStartResponse:
    """Begin linking Steam: mint a state, return the Steam OpenID URL as JSON.

    Authenticated (Bearer), so the SPA fetches this and navigates the browser to
    ``redirect_url`` itself — a 302 here couldn't carry the in-memory token.
    """
    _require_enabled()

    state = secrets.token_urlsafe(32)
    await store_steam_state(state, current_user.public_id)

    realm = f"{settings.oauth_redirect_base_url}/"
    url = build_login_redirect_url(return_to=_callback_url(state), realm=realm)
    return SteamStartResponse(redirect_url=url)


@router.get("/callback", dependencies=[Depends(_check_steam_callback_rate)])
async def steam_callback(
    state: str,
    request: Request,
    user_repo: UserRepoDep,
) -> RedirectResponse:
    """Complete linking: validate state, verify the assertion, persist SteamID64."""
    _require_enabled()

    user_public_id = await consume_steam_state(state)
    if user_public_id is None:
        return _account_redirect("error")

    user = await user_repo.get_by_public_id(user_public_id)
    if user is None:
        return _account_redirect("error")

    openid_params = extract_openid_params(request.query_params)
    steam_id = await verify_assertion(openid_params)
    if steam_id is None:
        logger.warning("steam_callback_verification_failed", user_id=user.id)
        return _account_redirect("error")

    # steam_id is unique. If this Steam account is already linked to a *different*
    # Slate user, fail cleanly (no takeover, no 500) — the check reveals nothing
    # about the other account. Re-linking your own is idempotent.
    existing = await user_repo.get_by_steam_id(steam_id)
    if existing is not None and existing.id != user.id:
        logger.warning("steam_link_conflict", user_id=user.id)
        return _account_redirect("error")

    await user_repo.set_steam_id(user, steam_id)
    logger.info("steam_account_linked", user_id=user.id)
    return _account_redirect("connected")

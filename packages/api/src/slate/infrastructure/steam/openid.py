"""Steam OpenID 2.0 helpers (ROADMAP Epic 30).

Steam authenticates via OpenID 2.0 ``identifier_select``: we redirect the
browser to Steam, and Steam redirects back with a signed assertion. We verify
that assertion by echoing the ``openid.*`` params back with
``mode=check_authentication`` and requiring ``is_valid:true`` — never trusting
the returned SteamID without this round-trip — then extract the SteamID64 from
the ``claimed_id``. The endpoint host is a hard-coded constant (SSRF-safe).
"""

from __future__ import annotations

import re
from collections.abc import Mapping

import httpx

_OPENID_LOGIN_URL = "https://steamcommunity.com/openid/login"
_OPENID_NS = "http://specs.openid.net/auth/2.0"
_IDENTIFIER_SELECT = "http://specs.openid.net/auth/2.0/identifier_select"
_VERIFY_TIMEOUT_SECONDS = 15.0

# A Steam claimed_id is exactly ``.../openid/id/<17-digit SteamID64>``.
_CLAIMED_ID_RE = re.compile(r"^https://steamcommunity\.com/openid/id/(\d{17})$")


def build_login_redirect_url(*, return_to: str, realm: str) -> str:
    """Build the Steam OpenID ``checkid_setup`` redirect URL.

    ``return_to`` is where Steam sends the browser back (our callback, carrying
    the CSRF ``state``); ``realm`` is the trust root shown to the user.
    """
    params = {
        "openid.ns": _OPENID_NS,
        "openid.mode": "checkid_setup",
        "openid.return_to": return_to,
        "openid.realm": realm,
        "openid.identity": _IDENTIFIER_SELECT,
        "openid.claimed_id": _IDENTIFIER_SELECT,
    }
    query = httpx.QueryParams(params)
    return f"{_OPENID_LOGIN_URL}?{query}"


def extract_openid_params(query: Mapping[str, str]) -> dict[str, str]:
    """Return only the ``openid.*`` params from a callback query mapping."""
    return {key: value for key, value in query.items() if key.startswith("openid.")}


async def verify_assertion(openid_params: Mapping[str, str]) -> str | None:
    """Verify a returned OpenID assertion with Steam; return the SteamID64.

    Echoes the ``openid.*`` params back with ``mode=check_authentication`` and
    requires the response body to contain ``is_valid:true``. Returns the SteamID64
    parsed from ``openid.claimed_id`` on success, or ``None`` on any failure
    (invalid signature, missing/mismatched claimed_id, network error).
    """
    claimed_id = openid_params.get("openid.claimed_id", "")
    match = _CLAIMED_ID_RE.match(claimed_id)
    if match is None:
        return None
    steam_id = match.group(1)

    payload = dict(openid_params)
    payload["openid.mode"] = "check_authentication"
    try:
        async with httpx.AsyncClient(timeout=_VERIFY_TIMEOUT_SECONDS) as client:
            resp = await client.post(_OPENID_LOGIN_URL, data=payload)
            resp.raise_for_status()
            body = resp.text
    except httpx.HTTPError:
        return None

    if not _is_valid_response(body):
        return None
    return steam_id


def _is_valid_response(body: str) -> bool:
    """True when the check_authentication body asserts ``is_valid:true``.

    The response is a key-value document (one ``key:value`` per line); we require
    an exact ``is_valid:true`` line so a substring like ``is_valid:false`` can't
    slip through.
    """
    return any(line.strip() == "is_valid:true" for line in body.splitlines())

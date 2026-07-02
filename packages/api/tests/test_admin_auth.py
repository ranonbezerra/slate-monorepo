"""Backoffice admin login: a valid non-admin must be indistinguishable from a
wrong password. Both go through ``POST /internal/v1/auth/login`` and must return
the exact same 401 body — no oracle telling an attacker their credentials work.
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from slate.infrastructure.db.models import User
from slate.infrastructure.db.repositories.admin import AdminRepository
from tests.conftest import _TestSessionFactory

_PW = "SecurePass1"  # pragma: allowlist secret


async def _register(client: AsyncClient, email: str) -> dict[str, Any]:
    resp = await client.post(
        "/v1/auth/register",
        json={"email": email, "password": _PW, "display_name": "BO User"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _grant_admin(email: str) -> None:
    async with _TestSessionFactory() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one()
        await AdminRepository(session).grant(user.id)
        await session.commit()


async def _login(client: AsyncClient, email: str, password: str) -> Any:
    return await client.post(
        "/internal/v1/auth/login", json={"email": email, "password": password}
    )


class TestAdminLogin:
    async def test_admin_logs_in(self, async_client: AsyncClient) -> None:
        await _register(async_client, "boss@example.com")
        await _grant_admin("boss@example.com")

        resp = await _login(async_client, "boss@example.com", _PW)
        assert resp.status_code == 200
        assert resp.json()["access_token"]

    async def test_admin_cookie_mode_sets_refresh_cookie(self, async_client: AsyncClient) -> None:
        # How the backoffice actually logs in: cookie mode keeps the refresh token
        # in an httpOnly cookie and omits it from the body.
        await _register(async_client, "cookieboss@example.com")
        await _grant_admin("cookieboss@example.com")

        resp = await async_client.post(
            "/internal/v1/auth/login",
            json={"email": "cookieboss@example.com", "password": _PW},
            headers={"X-Auth-Mode": "cookie"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["access_token"]
        assert body["refresh_token"] == ""
        assert "slate_refresh_token" in resp.cookies

    async def test_valid_non_admin_is_generic_401(self, async_client: AsyncClient) -> None:
        # Correct credentials, but no admin grant → must look like a bad password.
        await _register(async_client, "plain@example.com")

        resp = await _login(async_client, "plain@example.com", _PW)
        assert resp.status_code == 401
        assert resp.json() == {"detail": "Invalid credentials"}

    async def test_wrong_password_matches_non_admin_response(
        self, async_client: AsyncClient
    ) -> None:
        # The whole point: a valid-but-not-admin response and a wrong-password
        # response are byte-for-byte identical (no credential oracle).
        await _register(async_client, "plain2@example.com")
        await _grant_admin("plain2@example.com")  # is an admin, but wrong password below

        wrong = await _login(async_client, "plain2@example.com", "WrongPass9")
        await _register(async_client, "nonadmin@example.com")
        non_admin = await _login(async_client, "nonadmin@example.com", _PW)

        assert wrong.status_code == non_admin.status_code == 401
        assert wrong.json() == non_admin.json() == {"detail": "Invalid credentials"}

    async def test_unknown_email_is_generic_401(self, async_client: AsyncClient) -> None:
        resp = await _login(async_client, "ghost@example.com", _PW)
        assert resp.status_code == 401
        assert resp.json() == {"detail": "Invalid credentials"}

    async def test_admin_with_mfa_gets_challenge_not_tokens(
        self, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # An MFA-enabled admin gets the challenge (mirrors the player login); a
        # non-admin never reaches this branch (covered above).
        await _register(async_client, "mfaboss@example.com")
        await _grant_admin("mfaboss@example.com")

        from slate.core.auth.mfa import MfaService

        async def _enabled(_self: MfaService, _user_id: int) -> bool:
            return True

        monkeypatch.setattr(MfaService, "is_enabled", _enabled)

        resp = await _login(async_client, "mfaboss@example.com", _PW)
        assert resp.status_code == 200
        body = resp.json()
        assert body["mfa_required"] is True
        assert body["mfa_token"]
        assert body["access_token"] == ""

    async def test_single_user_mode_is_generic_401(
        self, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The JWT-bypass single-user account must not be a backoffice door.
        await _register(async_client, "solo@example.com")
        await _grant_admin("solo@example.com")

        from slate.api.v1 import admin_auth

        monkeypatch.setattr(admin_auth.settings, "single_user_mode", True)
        resp = await _login(async_client, "solo@example.com", _PW)
        assert resp.status_code == 401
        assert resp.json() == {"detail": "Invalid credentials"}

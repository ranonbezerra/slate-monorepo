"""Account-lifecycle endpoints: data export + self-service erasure (GDPR/LGPD)."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select

from slate.core.auth.security import create_access_token
from slate.infrastructure.db.models import User
from tests.conftest import _TestSessionFactory

_EMAIL = "test@example.com"
_PASSWORD = "StrongPass123"  # pragma: allowlist secret


class TestDataExport:
    async def test_export_returns_the_users_data(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await async_client.get("/v1/auth/me/export", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        # The portable document has the profile + every personal-data collection.
        assert body["profile"]["email"] == _EMAIL
        assert set(body) >= {
            "exported_at",
            "profile",
            "library",
            "play_sessions",
            "captures",
            "picks",
        }
        assert isinstance(body["library"], list)

    async def test_export_requires_auth(self, async_client: AsyncClient) -> None:
        resp = await async_client.get("/v1/auth/me/export")
        assert resp.status_code == 401


class TestAccountDeletion:
    async def test_wrong_password_is_rejected(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await async_client.post(
            "/v1/auth/delete-account",
            headers=auth_headers,
            json={"password": "WrongPass123"},  # pragma: allowlist secret
        )
        assert resp.status_code == 403

    async def test_delete_erases_the_account(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await async_client.post(
            "/v1/auth/delete-account",
            headers=auth_headers,
            json={"password": _PASSWORD},
        )
        assert resp.status_code == 200

        # The row is gone: the old token no longer resolves, and login fails.
        me = await async_client.get("/v1/auth/me", headers=auth_headers)
        assert me.status_code == 401
        login = await async_client.post(
            "/v1/auth/login", json={"email": _EMAIL, "password": _PASSWORD}
        )
        assert login.status_code == 401
        async with _TestSessionFactory() as session:
            found = (
                await session.execute(select(User).where(User.email == _EMAIL))
            ).scalar_one_or_none()
        assert found is None

    async def test_oauth_only_account_deletes_without_password(
        self, async_client: AsyncClient
    ) -> None:
        # An OAuth-only user has no password to confirm; the authenticated session
        # is the gate. Seed one directly and mint its access token.
        async with _TestSessionFactory() as session:
            user = User(email="oauthonly@example.com", password_hash=None, display_name="OA")
            session.add(user)
            await session.commit()
            token = create_access_token(str(user.public_id), user.token_version)

        resp = await async_client.post(
            "/v1/auth/delete-account",
            headers={"Authorization": f"Bearer {token}"},
            json={"password": ""},
        )
        assert resp.status_code == 200

    async def test_delete_requires_auth(self, async_client: AsyncClient) -> None:
        resp = await async_client.post("/v1/auth/delete-account", json={"password": _PASSWORD})
        assert resp.status_code == 401

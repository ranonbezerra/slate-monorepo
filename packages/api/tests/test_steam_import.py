"""Tests for the Steam import service + connect/import routes (Epic 30)."""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

from slate.api.v1 import auth_steam
from slate.core.library.service import LibraryService
from slate.core.library.steam_import import SteamImportService
from slate.infrastructure.catalog.dummy import DummyCatalogMatcher
from slate.infrastructure.db.models import Platform, User
from slate.infrastructure.db.repositories.game import GameRepository
from slate.infrastructure.db.repositories.library import LibraryRepository
from slate.infrastructure.db.repositories.platform import PlatformRepository
from slate.infrastructure.db.repositories.user import UserRepository
from slate.infrastructure.steam.base import OwnedGame
from slate.infrastructure.steam.dummy import DummySteamClient
from tests.conftest import _TestSessionFactory

_STEAM_ID = "76561197960287930"


async def _make_user(*, steam_id: str | None = _STEAM_ID) -> int:
    """Create a user (optionally Steam-linked) and return its internal id."""
    async with _TestSessionFactory() as session:
        user = User(
            email="steam@example.com",
            password_hash="x",  # pragma: allowlist secret
            display_name="Steam Player",
            steam_id=steam_id,
        )
        session.add(user)
        await session.flush()
        user_id = user.id
        await session.commit()
    return user_id


async def _seed_steam_platform() -> int:
    """Insert the seeded pc-steam platform and return its id."""
    async with _TestSessionFactory() as session:
        platform = Platform(slug="pc-steam", label="PC (Steam)", family="pc")
        session.add(platform)
        await session.flush()
        pid = platform.id
        await session.commit()
    return pid


def _build_service(session: Any, steam_client: DummySteamClient) -> SteamImportService:
    game_repo = GameRepository(session)
    library_repo = LibraryRepository(session)
    platform_repo = PlatformRepository(session)
    library_service = LibraryService(game_repo, library_repo, platform_repo)
    return SteamImportService(
        steam_client,
        DummyCatalogMatcher(),
        library_service,
        game_repo,
        library_repo,
        platform_repo,
    )


class TestImportService:
    async def test_imports_matched_games_with_playtime(self) -> None:
        user_id = await _make_user()
        await _seed_steam_platform()

        async with _TestSessionFactory() as session:
            user = await UserRepository(session).get_by_id(user_id)
            assert user is not None
            service = _build_service(session, DummySteamClient())
            summary = await service.import_owned_games(user)
            await session.commit()

        # 3 canned games match (Hollow Knight, Celeste, Hades); 1 is unmatched.
        assert summary.imported == 3
        assert summary.already_owned == 0
        assert summary.unmatched == 1
        assert summary.private_or_empty is False

        # Playtime was recorded on the imported entries.
        async with _TestSessionFactory() as session:
            entries = await LibraryRepository(session).list_for_user(user_id)
            by_title = {e.game.title: e.steam_playtime_minutes for e in entries}
            assert by_title["Hollow Knight"] == 1200
            assert by_title["Celeste"] == 300
            assert by_title["Hades"] == 0

    async def test_reimport_is_idempotent(self) -> None:
        user_id = await _make_user()
        await _seed_steam_platform()

        async with _TestSessionFactory() as session:
            user = await UserRepository(session).get_by_id(user_id)
            assert user is not None
            await _build_service(session, DummySteamClient()).import_owned_games(user)
            await session.commit()

        async with _TestSessionFactory() as session:
            user = await UserRepository(session).get_by_id(user_id)
            assert user is not None
            summary = await _build_service(session, DummySteamClient()).import_owned_games(user)
            await session.commit()

        assert summary.imported == 0
        assert summary.already_owned == 3
        assert summary.unmatched == 1

    async def test_no_steam_id_raises(self) -> None:
        user_id = await _make_user(steam_id=None)
        await _seed_steam_platform()
        async with _TestSessionFactory() as session:
            user = await UserRepository(session).get_by_id(user_id)
            assert user is not None
            service = _build_service(session, DummySteamClient())
            with pytest.raises(ValueError, match="Steam not connected"):
                await service.import_owned_games(user)

    async def test_empty_library_is_private_or_empty(self) -> None:
        user_id = await _make_user()
        await _seed_steam_platform()
        async with _TestSessionFactory() as session:
            user = await UserRepository(session).get_by_id(user_id)
            assert user is not None
            service = _build_service(session, DummySteamClient(owned=[]))
            summary = await service.import_owned_games(user)

        assert summary.private_or_empty is True
        assert summary.imported == 0
        assert summary.already_owned == 0
        assert summary.unmatched == 0

    async def test_truncates_over_cap(self) -> None:
        user_id = await _make_user()
        await _seed_steam_platform()
        # 3 owned, cap 1 => only the first is processed.
        owned = [
            OwnedGame(appid=1, name="Hollow Knight", playtime_minutes=5),
            OwnedGame(appid=2, name="Celeste", playtime_minutes=5),
            OwnedGame(appid=3, name="Hades", playtime_minutes=5),
        ]
        async with _TestSessionFactory() as session:
            user = await UserRepository(session).get_by_id(user_id)
            assert user is not None
            game_repo = GameRepository(session)
            library_repo = LibraryRepository(session)
            platform_repo = PlatformRepository(session)
            service = SteamImportService(
                DummySteamClient(owned=owned),
                DummyCatalogMatcher(),
                LibraryService(game_repo, library_repo, platform_repo),
                game_repo,
                library_repo,
                platform_repo,
                max_games=1,
            )
            summary = await service.import_owned_games(user)
            await session.commit()

        assert summary.imported == 1
        assert summary.unmatched == 0


class TestConnectRoutes:
    async def test_start_requires_auth(self, async_client: AsyncClient) -> None:
        resp = await async_client.get("/v1/auth/steam/start")
        assert resp.status_code == 401

    async def test_start_returns_steam_url(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from uuid import UUID

        async def _fake_store(state: str, user_public_id: UUID) -> None:
            return None

        monkeypatch.setattr(auth_steam, "store_steam_state", _fake_store)
        resp = await async_client.get("/v1/auth/steam/start", headers=auth_headers)
        assert resp.status_code == 200
        url = resp.json()["redirect_url"]
        assert url.startswith("https://steamcommunity.com/openid/login")
        assert "openid.mode=checkid_setup" in url
        assert "openid.return_to=" in url

    async def test_callback_valid_links_steam_id(
        self,
        async_client: AsyncClient,
        register_user: dict[str, Any],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from uuid import UUID

        # Resolve the registered user's public_id to bind the state to it.
        async with _TestSessionFactory() as session:
            user = await UserRepository(session).get_by_email("test@example.com")
            assert user is not None
            public_id = user.public_id

        async def _fake_consume(state: str) -> UUID | None:
            return public_id

        async def _fake_verify(params: dict[str, str]) -> str | None:
            return _STEAM_ID

        monkeypatch.setattr(auth_steam, "consume_steam_state", _fake_consume)
        monkeypatch.setattr(auth_steam, "verify_assertion", _fake_verify)

        resp = await async_client.get("/v1/auth/steam/callback?state=s&openid.claimed_id=x")
        assert resp.status_code == 302
        assert "steam=connected" in resp.headers["location"]

        async with _TestSessionFactory() as session:
            user = await UserRepository(session).get_by_email("test@example.com")
            assert user is not None
            assert user.steam_id == _STEAM_ID

    async def test_callback_invalid_assertion_no_link(
        self,
        async_client: AsyncClient,
        register_user: dict[str, Any],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from uuid import UUID

        async with _TestSessionFactory() as session:
            user = await UserRepository(session).get_by_email("test@example.com")
            assert user is not None
            public_id = user.public_id

        async def _fake_consume(state: str) -> UUID | None:
            return public_id

        async def _fake_verify(params: dict[str, str]) -> str | None:
            return None

        monkeypatch.setattr(auth_steam, "consume_steam_state", _fake_consume)
        monkeypatch.setattr(auth_steam, "verify_assertion", _fake_verify)

        resp = await async_client.get("/v1/auth/steam/callback?state=s")
        assert resp.status_code == 302
        assert "steam=error" in resp.headers["location"]

        async with _TestSessionFactory() as session:
            user = await UserRepository(session).get_by_email("test@example.com")
            assert user is not None
            assert user.steam_id is None

    async def test_callback_bad_state_rejected(
        self, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from uuid import UUID

        async def _fake_consume(state: str) -> UUID | None:
            return None

        monkeypatch.setattr(auth_steam, "consume_steam_state", _fake_consume)
        resp = await async_client.get("/v1/auth/steam/callback?state=expired")
        assert resp.status_code == 302
        assert "steam=error" in resp.headers["location"]


class TestImportEndpoint:
    async def test_requires_auth(self, async_client: AsyncClient) -> None:
        resp = await async_client.post("/v1/library/steam/import")
        assert resp.status_code == 401

    async def test_not_connected_returns_409(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        # The default registered user has no steam_id linked.
        resp = await async_client.post("/v1/library/steam/import", headers=auth_headers)
        assert resp.status_code == 409
        assert "Steam not connected" in resp.json()["detail"]

    async def test_returns_summary_shape(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        # Link the default user's Steam id + seed the platform, then import.
        await _seed_steam_platform()
        async with _TestSessionFactory() as session:
            user = await UserRepository(session).get_by_email("test@example.com")
            assert user is not None
            user.steam_id = _STEAM_ID
            await session.commit()

        resp = await async_client.post("/v1/library/steam/import", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert set(data) == {"imported", "already_owned", "unmatched", "private_or_empty"}
        assert data["imported"] == 3
        assert data["unmatched"] == 1
        assert data["private_or_empty"] is False

    async def test_disabled_returns_503(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from slate.config import settings

        monkeypatch.setattr(settings, "app_env", "production")
        monkeypatch.setattr(settings, "steam_api_key", "")
        resp = await async_client.post("/v1/library/steam/import", headers=auth_headers)
        assert resp.status_code == 503


class TestConnectDisabled:
    async def test_start_disabled_returns_503(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from slate.config import settings

        monkeypatch.setattr(settings, "app_env", "production")
        monkeypatch.setattr(settings, "steam_api_key", "")
        resp = await async_client.get("/v1/auth/steam/start", headers=auth_headers)
        assert resp.status_code == 503

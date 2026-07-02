"""Unit tests for the Steam Web API client + OpenID verifier (Epic 30)."""

from __future__ import annotations

import httpx
import pytest

from slate.config import settings
from slate.infrastructure.steam.base import SteamApiError
from slate.infrastructure.steam.dummy import DummySteamClient
from slate.infrastructure.steam.factory import get_steam_client, is_steam_enabled
from slate.infrastructure.steam.http_client import SteamHttpClient, _parse_owned_games
from slate.infrastructure.steam.openid import (
    build_login_redirect_url,
    extract_openid_params,
    verify_assertion,
)


class TestDummyClient:
    async def test_returns_canned_games(self) -> None:
        client = DummySteamClient()
        games = await client.get_owned_games("76561197960287930")
        assert len(games) == 4
        assert any(g.name == "Hollow Knight" for g in games)
        assert all(g.playtime_minutes >= 0 for g in games)

    async def test_accepts_custom_owned_list(self) -> None:
        from slate.infrastructure.steam.base import OwnedGame

        client = DummySteamClient(owned=[OwnedGame(appid=1, name="X", playtime_minutes=10)])
        games = await client.get_owned_games("id")
        assert games == [OwnedGame(appid=1, name="X", playtime_minutes=10)]


class TestParseOwnedGames:
    def test_parses_games(self) -> None:
        data = {
            "response": {
                "game_count": 2,
                "games": [
                    {"appid": 367520, "name": "Hollow Knight", "playtime_forever": 1200},
                    {"appid": 504230, "name": "Celeste", "playtime_forever": 0},
                ],
            }
        }
        games = _parse_owned_games(data)
        assert len(games) == 2
        assert games[0].appid == 367520
        assert games[0].playtime_minutes == 1200
        assert games[1].playtime_minutes == 0

    def test_private_profile_returns_empty(self) -> None:
        # A private profile: response present but no "games" key.
        assert _parse_owned_games({"response": {}}) == []

    def test_missing_response_returns_empty(self) -> None:
        assert _parse_owned_games({}) == []
        assert _parse_owned_games("nonsense") == []

    def test_skips_malformed_rows(self) -> None:
        data = {
            "response": {
                "games": [
                    {"appid": 1, "name": "Good"},
                    {"appid": "bad", "name": "NoAppId"},
                    {"appid": 2, "name": ""},
                    {"name": "MissingAppId"},
                    "not-a-dict",
                    {"appid": 3, "name": "AlsoGood", "playtime_forever": -5},
                ]
            }
        }
        games = _parse_owned_games(data)
        names = [g.name for g in games]
        assert names == ["Good", "AlsoGood"]
        # Negative playtime is clamped to 0.
        assert games[1].playtime_minutes == 0
        # A row with no playtime key defaults to 0.
        assert games[0].playtime_minutes == 0


class TestHttpClient:
    async def test_get_owned_games_parses_response(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, object] = {}

        def _handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            return httpx.Response(
                200,
                json={
                    "response": {
                        "games": [
                            {"appid": 10, "name": "Half-Life", "playtime_forever": 99},
                        ]
                    }
                },
            )

        transport = httpx.MockTransport(_handler)
        real_async_client = httpx.AsyncClient

        def _patched(*args: object, **kwargs: object) -> httpx.AsyncClient:
            kwargs["transport"] = transport
            return real_async_client(**kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(httpx, "AsyncClient", _patched)

        client = SteamHttpClient("secret-key")  # pragma: allowlist secret
        games = await client.get_owned_games("76561197960287930")
        assert len(games) == 1
        assert games[0].name == "Half-Life"
        assert games[0].playtime_minutes == 99
        # SSRF-safe: request goes to the hard-coded Steam host.
        assert str(captured["url"]).startswith(
            "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
        )
        assert "steamid=76561197960287930" in str(captured["url"])

    async def test_api_error_never_leaks_the_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # A Steam API error must raise a sanitized SteamApiError — the request URL
        # (which carries ?key=<secret>) must appear NOWHERE reachable from it, so
        # it can't reach a traceback log or Sentry.
        def _handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(403, text="Forbidden")

        transport = httpx.MockTransport(_handler)
        real_async_client = httpx.AsyncClient

        def _patched(*args: object, **kwargs: object) -> httpx.AsyncClient:
            kwargs["transport"] = transport
            return real_async_client(**kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(httpx, "AsyncClient", _patched)

        client = SteamHttpClient("super-secret-key")  # pragma: allowlist secret
        with pytest.raises(SteamApiError) as excinfo:
            await client.get_owned_games("76561197960287930")

        exc = excinfo.value
        assert "super-secret-key" not in str(exc)
        # No exception chain back to the URL-bearing httpx error.
        assert exc.__cause__ is None
        assert exc.__context__ is None


class TestFactory:
    def test_testing_uses_dummy(self) -> None:
        assert isinstance(get_steam_client(settings), DummySteamClient)

    def test_is_enabled_in_testing(self) -> None:
        assert is_steam_enabled(settings) is True

    def test_disabled_without_key_outside_testing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "app_env", "production")
        monkeypatch.setattr(settings, "steam_api_key", "")
        assert is_steam_enabled(settings) is False
        # Unconfigured => the factory still returns the dummy (never a live client).
        assert isinstance(get_steam_client(settings), DummySteamClient)

    def test_configured_key_uses_http_client(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "app_env", "production")
        monkeypatch.setattr(settings, "steam_api_key", "live-key")  # pragma: allowlist secret
        assert is_steam_enabled(settings) is True
        assert isinstance(get_steam_client(settings), SteamHttpClient)


class _FakeRedis:
    """Minimal in-memory async Redis supporting set/getdel (single-use state)."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.store[key] = value

    async def getdel(self, key: str) -> str | None:
        return self.store.pop(key, None)


class TestStateStore:
    async def test_store_then_consume_roundtrip(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from uuid import uuid4

        from slate.infrastructure.steam import state_store

        fake = _FakeRedis()
        monkeypatch.setattr(state_store, "get_redis_client", lambda: fake)

        user_id = uuid4()
        await state_store.store_steam_state("st8", user_id)
        # First consume returns the bound user; it is single-use.
        assert await state_store.consume_steam_state("st8") == user_id
        assert await state_store.consume_steam_state("st8") is None

    async def test_consume_unknown_state_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from slate.infrastructure.steam import state_store

        monkeypatch.setattr(state_store, "get_redis_client", lambda: _FakeRedis())
        assert await state_store.consume_steam_state("missing") is None

    async def test_consume_malformed_value_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from slate.infrastructure.steam import state_store

        fake = _FakeRedis()
        fake.store["steam:link:state:bad"] = "not-a-uuid"
        monkeypatch.setattr(state_store, "get_redis_client", lambda: fake)
        assert await state_store.consume_steam_state("bad") is None


class TestOpenIdRedirect:
    def test_build_redirect_has_openid_params(self) -> None:
        url = build_login_redirect_url(
            return_to="http://api/v1/auth/steam/callback?state=s",
            realm="http://api/",
        )
        assert url.startswith("https://steamcommunity.com/openid/login?")
        assert "openid.mode=checkid_setup" in url
        assert "openid.ns=http" in url
        assert "identifier_select" in url

    def test_extract_openid_params_filters(self) -> None:
        params = extract_openid_params({"openid.mode": "id_res", "state": "s", "openid.sig": "x"})
        assert params == {"openid.mode": "id_res", "openid.sig": "x"}


class TestVerifyAssertion:
    def _valid_params(self) -> dict[str, str]:
        return {
            "openid.ns": "http://specs.openid.net/auth/2.0",
            "openid.mode": "id_res",
            "openid.claimed_id": "https://steamcommunity.com/openid/id/76561197960287930",
            "openid.sig": "abc",
        }

    def _mock_httpx(self, monkeypatch: pytest.MonkeyPatch, body: str) -> dict[str, object]:
        captured: dict[str, object] = {}

        def _handler(request: httpx.Request) -> httpx.Response:
            captured["mode"] = httpx.QueryParams(request.content.decode()).get("openid.mode")
            return httpx.Response(200, text=body)

        transport = httpx.MockTransport(_handler)
        real = httpx.AsyncClient

        def _patched(*args: object, **kwargs: object) -> httpx.AsyncClient:
            kwargs["transport"] = transport
            return real(**kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(httpx, "AsyncClient", _patched)
        return captured

    async def test_valid_assertion_returns_steam_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured = self._mock_httpx(monkeypatch, "ns:...\nis_valid:true\n")
        steam_id = await verify_assertion(self._valid_params())
        assert steam_id == "76561197960287930"
        # The verification POST flips mode to check_authentication.
        assert captured["mode"] == "check_authentication"

    async def test_invalid_assertion_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._mock_httpx(monkeypatch, "ns:...\nis_valid:false\n")
        assert await verify_assertion(self._valid_params()) is None

    async def test_bad_claimed_id_returns_none_without_network(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _boom(*_a: object, **_k: object) -> None:
            raise AssertionError("should not hit the network")

        monkeypatch.setattr(httpx, "AsyncClient", _boom)
        params = self._valid_params()
        params["openid.claimed_id"] = "https://evil.example/openid/id/76561197960287930"
        assert await verify_assertion(params) is None

    async def test_network_error_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("boom")

        transport = httpx.MockTransport(_handler)
        real = httpx.AsyncClient

        def _patched(*args: object, **kwargs: object) -> httpx.AsyncClient:
            kwargs["transport"] = transport
            return real(**kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(httpx, "AsyncClient", _patched)
        assert await verify_assertion(self._valid_params()) is None

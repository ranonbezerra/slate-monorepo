"""Tests for the Backlog Concierge SSE chat endpoint."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import select

from tests.conftest import _TestSessionFactory


async def _seed_entry_for(email: str) -> None:
    from dailyloadout.infrastructure.db.models import Game, LibraryEntry, Platform, User

    async with _TestSessionFactory() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one()
        game = Game(slug=f"g-{uuid4().hex[:6]}", title="Hollow Knight", metadata_source="user")
        session.add(game)
        await session.flush()
        platform = Platform(slug=f"p-{uuid4().hex[:6]}", label="PC", family="pc")
        session.add(platform)
        await session.flush()
        session.add(
            LibraryEntry(
                user_id=user.id, game_id=game.id, platform_id=platform.id, status="playing"
            )
        )
        await session.commit()


def _parse_sse(body: str) -> list[dict[str, Any]]:
    return [json.loads(line[5:].strip()) for line in body.splitlines() if line.startswith("data:")]


async def test_chat_requires_auth(async_client: AsyncClient) -> None:
    resp = await async_client.post("/v1/concierge/chat", json={"message": "hi"})
    assert resp.status_code == 401


async def test_chat_streams_guarded_reply(
    async_client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await _seed_entry_for("test@example.com")

    resp = await async_client.post(
        "/v1/concierge/chat",
        json={"message": "What should I play tonight?"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]

    events = _parse_sse(resp.text)
    deltas = "".join(e["delta"] for e in events if "delta" in e)
    done = [e for e in events if e.get("done")]

    assert "give this a go" in deltas
    assert "RECOMMEND" not in deltas
    assert len(done) == 1
    assert done[0]["thread_id"]  # server-issued thread id for the next turn


async def test_chat_reuses_thread_id(
    async_client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await _seed_entry_for("test@example.com")

    resp = await async_client.post(
        "/v1/concierge/chat",
        json={"message": "Anything good?", "thread_id": "my-thread-123"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    done = [e for e in _parse_sse(resp.text) if e.get("done")]
    assert done[0]["thread_id"] == "my-thread-123"


async def test_chat_rejects_empty_message(
    async_client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await async_client.post(
        "/v1/concierge/chat", json={"message": ""}, headers=auth_headers
    )
    assert resp.status_code == 422

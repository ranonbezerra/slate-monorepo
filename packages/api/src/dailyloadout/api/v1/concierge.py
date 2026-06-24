"""Backlog Concierge chat endpoint (Server-Sent Events).

v1 streams the *guarded* answer: the service runs the agent to completion and
validates any recommendation, then this endpoint chunks the final text over SSE.
Token-level streaming with an in-stream guard is a later epic (ROADMAP Epic 15).
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from dailyloadout.core.concierge.schemas import ChatRequest
from dailyloadout.deps import CurrentUserDep
from dailyloadout.deps.concierge import ConciergeServiceDep

router = APIRouter(prefix="/v1/concierge", tags=["concierge"])


def _sse(payload: dict[str, object]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _word_chunks(text: str) -> list[str]:
    """Split into word-sized chunks (spaces preserved) for a typing effect."""
    if not text:
        return []
    words = text.split(" ")
    return [w if i == len(words) - 1 else w + " " for i, w in enumerate(words)]


@router.post("/chat")
async def chat(
    body: ChatRequest,
    current_user: CurrentUserDep,
    concierge_service: ConciergeServiceDep,
) -> StreamingResponse:
    """Stream a guarded concierge reply as Server-Sent Events."""
    thread_id = body.thread_id or uuid4().hex

    async def event_stream() -> AsyncIterator[str]:
        text = await concierge_service.reply(
            user_id=current_user.id,
            user_created_at=current_user.created_at,
            thread_id=thread_id,
            message=body.message,
        )
        for chunk in _word_chunks(text):
            yield _sse({"delta": chunk})
        yield _sse({"done": True, "thread_id": thread_id})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable proxy buffering so chunks flush
        },
    )

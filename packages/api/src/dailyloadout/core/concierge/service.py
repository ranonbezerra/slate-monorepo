"""Backlog Concierge service: runs the agent, then enforces the UUID guard.

v1 streaming model is deliberately simple — the agent runs its tool loop to
completion, we validate any recommended game (reroll once, else degrade), and
the *guarded* answer is what the endpoint streams. True token streaming with an
in-stream guard is a later epic (ROADMAP Epic 15).
"""

from __future__ import annotations

import re
from datetime import datetime

from dailyloadout.core.stats.service import StatsService
from dailyloadout.infrastructure.agent.concierge.base import (
    AbstractConciergeAgent,
    ConciergeRequest,
)
from dailyloadout.infrastructure.agent.concierge.tools import (
    build_concierge_tools,
    validate_recommendation,
)
from dailyloadout.infrastructure.db.repositories.library import LibraryRepository
from dailyloadout.infrastructure.db.repositories.mission import MissionRepository

SYSTEM_PROMPT = (
    "You are the Backlog Concierge for DailyLoadout — a friendly, concise gaming "
    "companion that helps the player decide what to play from THEIR OWN library.\n"
    "\n"
    "Rules:\n"
    "- Always ground answers in the user's real data. Use the tools — never invent "
    "games, stats, or progress.\n"
    "- Call search_library first to see what they actually own before recommending "
    "anything. Use get_mission_history to recall where they left off, get_play_stats "
    "for habits, and estimate_session_fit when they mention how much time they have.\n"
    "- Keep replies short and conversational — a sentence or two, not an essay.\n"
    "- When you recommend ONE specific game, end your reply with a line in exactly this "
    "form, using the id from search_library:\n"
    "  RECOMMEND: <library_entry id>\n"
    "  Only emit that line for a game that appeared in search_library results.\n"
    "- If nothing fits, say so plainly and ask a clarifying question instead of guessing."
)

# Sent on a reroll when the agent recommended a game that isn't in the library.
_CORRECTION_MESSAGE = (
    "That recommendation wasn't a game in my library. Call search_library again and "
    "only recommend a game that actually appears in the results."
)

_DEGRADE_NOTE = (
    "I'm not certain that one's in your library — want me to take another look "
    "or narrow it down by platform or mood?"
)

_RECOMMEND_RE = re.compile(r"^\s*RECOMMEND:\s*(\S+)\s*$", re.IGNORECASE | re.MULTILINE)


def _split_recommendation(text: str) -> tuple[str, str | None]:
    """Return (prose without the RECOMMEND marker, recommended id or None)."""
    match = _RECOMMEND_RE.search(text)
    rec_id = match.group(1) if match else None
    prose = _RECOMMEND_RE.sub("", text).strip()
    return prose, rec_id


class ConciergeService:
    def __init__(
        self,
        *,
        library_repo: LibraryRepository,
        mission_repo: MissionRepository,
        stats_service: StatsService,
        agent: AbstractConciergeAgent,
    ) -> None:
        self._library_repo = library_repo
        self._mission_repo = mission_repo
        self._stats_service = stats_service
        self._agent = agent

    async def reply(
        self,
        *,
        user_id: int,
        user_created_at: datetime,
        thread_id: str,
        message: str,
    ) -> str:
        """Run one guarded chat turn and return the user-facing answer text."""
        tools = build_concierge_tools(
            user_id=user_id,
            user_created_at=user_created_at,
            library_repo=self._library_repo,
            mission_repo=self._mission_repo,
            stats_service=self._stats_service,
        )

        reply = await self._agent.respond(
            ConciergeRequest(
                thread_id=thread_id,
                message=message,
                system=SYSTEM_PROMPT,
                tools=tools,
            )
        )
        prose, rec_id = _split_recommendation(reply.text)

        if rec_id is not None and not await self._is_valid(user_id, rec_id):
            # Reroll once with a correction (Epic 7 guard pattern, MAX_REROLLS=1).
            reply = await self._agent.respond(
                ConciergeRequest(
                    thread_id=thread_id,
                    message=_CORRECTION_MESSAGE,
                    system=SYSTEM_PROMPT,
                    tools=tools,
                )
            )
            prose, rec_id = _split_recommendation(reply.text)
            if rec_id is not None and not await self._is_valid(user_id, rec_id):
                # Degrade rather than surface a game that isn't in the library.
                return f"{prose}\n\n{_DEGRADE_NOTE}".strip() if prose else _DEGRADE_NOTE

        return prose

    async def _is_valid(self, user_id: int, public_id: str) -> bool:
        return await validate_recommendation(self._library_repo, user_id, public_id)

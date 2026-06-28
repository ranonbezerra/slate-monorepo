"""Write tool functions for the Backlog Concierge (ROADMAP Epic 12).

These turn the Concierge from a recommender into the *conversational operator*
of the play_session pipeline: it can start a play_session, brief it, log an offline
session, and update a game's status — all funnelling through the same shared
orchestrator and guard rails the REST endpoints use.

Like the read tools (``tools.py``) these are framework-free and return
LLM-friendly text, never raising — service-layer ``HTTPException``s are caught
and rendered as a sentence the model can relay. Every function is scoped to a
``user_id`` so the Concierge can only mutate the caller's own data, and the
invariants (one active play_session per user; UUID-existence on every pick) hold here
exactly as they do on the REST surface.
"""

from __future__ import annotations

import structlog
from fastapi import HTTPException

from dailyloadout.config import Settings
from dailyloadout.core.cache.invalidation import invalidate_user_stats
from dailyloadout.core.play_session.briefing import BriefingMode, generate_briefing_for_mode
from dailyloadout.core.play_session.start import create_play_session_for_entry
from dailyloadout.infrastructure.agent.base import AbstractBriefingAgent
from dailyloadout.infrastructure.agent.concierge.base import ConciergeTool
from dailyloadout.infrastructure.agent.concierge.tools import _resolve_entry
from dailyloadout.infrastructure.agent.concierge.write_schemas import (
    GenerateBriefingArgs,
    RetroactiveDebriefArgs,
    SetStatusArgs,
    StartPlaySessionArgs,
)
from dailyloadout.infrastructure.db.repositories.library import LibraryRepository
from dailyloadout.infrastructure.db.repositories.play_session import PlaySessionRepository
from dailyloadout.infrastructure.llm.base import AbstractLLMClient

logger = structlog.get_logger()

# The statuses a player can move a game between (mirrors the library schema).
_VALID_STATUSES = {"backlog", "playing", "paused", "completed", "dropped"}
# Conversational briefing tops out at quick — deep research is slow and belongs
# to the deliberate briefing flow, not a one-tap chat turn.
_BRIEFING_CHOICES = {"none", "quick"}


async def start_play_session(
    library_repo: LibraryRepository,
    play_session_repo: PlaySessionRepository,
    llm_client: AbstractLLMClient,
    agent: AbstractBriefingAgent | None,
    settings: Settings,
    user_id: int,
    *,
    library_entry_public_id: str,
    briefing: str = "none",
) -> str:
    """Start a play_session for one game, optionally with a quick briefing."""
    entry = await _resolve_entry(library_repo, user_id, library_entry_public_id)
    if entry is None:
        return "That game is not in the library, so I can't start it."

    if await play_session_repo.get_active_for_user(user_id) is not None:
        return "There's already an active play_session. Finish or end it before starting another."

    choice = briefing.strip().lower() if briefing else "none"
    if choice not in _BRIEFING_CHOICES:
        choice = "none"

    briefing_text: str | None = None
    if choice != "none":
        briefing_text = (
            await generate_briefing_for_mode(
                play_session_repo,
                library_repo,
                llm_client,
                agent,
                settings,
                entry,
                "quick",
            )
            or None
        )

    try:
        await create_play_session_for_entry(
            play_session_repo=play_session_repo,
            library_repo=library_repo,
            user_id=user_id,
            entry=entry,
            briefing_text=briefing_text,
        )
    except HTTPException:
        return "There's already an active play_session. Finish or end it before starting another."

    started = f"Started a play_session for {entry.game.title}."
    if briefing_text:
        return f"{started}\n\nBriefing:\n{briefing_text}"
    return started


async def generate_briefing(
    library_repo: LibraryRepository,
    play_session_repo: PlaySessionRepository,
    llm_client: AbstractLLMClient,
    agent: AbstractBriefingAgent | None,
    settings: Settings,
    user_id: int,
    *,
    mode: str = "quick",
) -> str:
    """Generate a briefing for the user's active play_session and persist it.

    ``mode`` is accepted for tool-schema compatibility but always clamped to
    ``quick``: the deep-research graph is too expensive to trigger from a single
    chat turn (it would bypass the briefing limiter + cost guard).
    """
    _ = mode  # accepted but intentionally ignored — always clamped to quick.
    play_session = await play_session_repo.get_active_for_user(user_id)
    if play_session is None:
        return "There's no active play_session to brief. Start one first."

    # Clamp to 'quick' (mirror start_play_session's _BRIEFING_CHOICES): one 6/min chat
    # turn must not be able to trigger the full deep-research graph and bypass the
    # briefing limiter + cost guard.
    selected: BriefingMode = "quick"
    briefing_text = await generate_briefing_for_mode(
        play_session_repo,
        library_repo,
        llm_client,
        agent,
        settings,
        play_session.library_entry,
        selected,
    )
    if not briefing_text:
        return "I couldn't put together a briefing right now. Try again in a moment."

    await play_session_repo.set_briefing(play_session.id, briefing_text)
    return f"Briefing for {play_session.library_entry.game.title}:\n{briefing_text}"


async def submit_retroactive_debrief(
    library_repo: LibraryRepository,
    play_session_repo: PlaySessionRepository,
    llm_client: AbstractLLMClient,
    user_id: int,
    *,
    library_entry_public_id: str,
    debrief_text: str,
) -> str:
    """Log a past, untracked play session as a pre-ended retroactive play_session."""
    entry = await _resolve_entry(library_repo, user_id, library_entry_public_id)
    if entry is None:
        return "That game is not in the library, so I can't log a session for it."

    extracted_state = None
    try:
        extracted = await llm_client.extract_debrief_state(
            game_title=entry.game.title,
            debrief_text=debrief_text,
        )
        extracted_state = {
            "location": extracted.location,
            "next_action": extracted.next_action,
            "level": extracted.level,
            "current_quest": extracted.current_quest,
        }
        if extracted.next_action:
            await library_repo.update(entry, play_session_next_action=extracted.next_action)
    except Exception:
        logger.warning("concierge_retroactive_extraction_failed", exc_info=True)

    await play_session_repo.create_retroactive(
        user_id=user_id,
        library_entry_id=entry.id,
        debrief_text=debrief_text,
        extracted_state=extracted_state,
    )
    await invalidate_user_stats(user_id)
    next_action = (extracted_state or {}).get("next_action")
    logged = f"Logged your past session for {entry.game.title}."
    if next_action:
        return f"{logged} Saved next step: {next_action}"
    return logged


async def set_status(
    library_repo: LibraryRepository,
    user_id: int,
    *,
    library_entry_public_id: str,
    status: str,
) -> str:
    """Change a library entry's status (backlog/playing/paused/completed/dropped)."""
    normalised = status.strip().lower()
    if normalised not in _VALID_STATUSES:
        options = ", ".join(sorted(_VALID_STATUSES))
        return f"'{status}' isn't a valid status. Use one of: {options}."

    entry = await _resolve_entry(library_repo, user_id, library_entry_public_id)
    if entry is None:
        return "That game is not in the library."

    await library_repo.update(entry, status=normalised)
    await invalidate_user_stats(user_id)
    return f"Marked {entry.game.title} as {normalised}."


def build_concierge_write_tools(
    *,
    user_id: int,
    library_repo: LibraryRepository,
    play_session_repo: PlaySessionRepository,
    llm_client: AbstractLLMClient,
    agent: AbstractBriefingAgent | None,
    settings: Settings,
) -> list[ConciergeTool]:
    """Build the per-request write tool set, each bound to *user_id* and the repos."""

    async def _start(library_entry_public_id: str, briefing: str = "none") -> str:
        return await start_play_session(
            library_repo,
            play_session_repo,
            llm_client,
            agent,
            settings,
            user_id,
            library_entry_public_id=library_entry_public_id,
            briefing=briefing,
        )

    async def _brief(mode: str = "quick") -> str:
        return await generate_briefing(
            library_repo, play_session_repo, llm_client, agent, settings, user_id, mode=mode
        )

    async def _retro(library_entry_public_id: str, debrief_text: str) -> str:
        return await submit_retroactive_debrief(
            library_repo,
            play_session_repo,
            llm_client,
            user_id,
            library_entry_public_id=library_entry_public_id,
            debrief_text=debrief_text,
        )

    async def _status(library_entry_public_id: str, status: str) -> str:
        return await set_status(
            library_repo, user_id, library_entry_public_id=library_entry_public_id, status=status
        )

    return [
        ConciergeTool(
            name="start_play_session",
            description="Start a play session (play_session) for one game from the library. Pass "
            "briefing='quick' to include a short catch-up briefing. Only one play_session can be "
            "active at a time.",
            args_schema=StartPlaySessionArgs,
            coroutine=_start,
        ),
        ConciergeTool(
            name="generate_briefing",
            description="Write a catch-up briefing for the currently active play_session "
            "and save it. Use after start_play_session, or when the player asks for a "
            "refresher on where they left off.",
            args_schema=GenerateBriefingArgs,
            coroutine=_brief,
        ),
        ConciergeTool(
            name="submit_retroactive_debrief",
            description="Log a past play session the player did NOT track live (e.g. 'I played "
            "two hours offline'). Records what happened and saves their next step.",
            args_schema=RetroactiveDebriefArgs,
            coroutine=_retro,
        ),
        ConciergeTool(
            name="set_status",
            description="Change a game's status in the library: backlog, playing, paused, "
            "completed, or dropped.",
            args_schema=SetStatusArgs,
            coroutine=_status,
        ),
    ]

"""Briefing helpers: preview, extraction fallback, and generation."""

from __future__ import annotations

import asyncio
from typing import Literal

import structlog

from dailyloadout.config import Settings
from dailyloadout.config import settings as _settings
from dailyloadout.core.play_session.anti_hallucination import validate_briefing
from dailyloadout.infrastructure.agent.base import AbstractBriefingAgent, DeepBriefRequest
from dailyloadout.infrastructure.agent.graph.state import PlaySessionContext
from dailyloadout.infrastructure.db.models import LibraryEntry, PlaySession
from dailyloadout.infrastructure.db.repositories.library import LibraryRepository
from dailyloadout.infrastructure.db.repositories.play_session import PlaySessionRepository
from dailyloadout.infrastructure.llm.base import AbstractLLMClient
from dailyloadout.infrastructure.research.base import ResearchUnavailableError

logger = structlog.get_logger()

BriefingMode = Literal["quick", "deep"]


def _collect_previous_debriefs(recent_play_sessions: list[PlaySession]) -> list[dict[str, object]]:
    """Flatten recent ended play_sessions into the debrief context the LLM expects."""
    previous_debriefs: list[dict[str, object]] = []
    for m in recent_play_sessions:
        debrief_data: dict[str, object] = {}
        if m.extracted_state:
            debrief_data.update(m.extracted_state)
        if m.debrief_text:
            debrief_data["raw_text"] = m.debrief_text
        if debrief_data:
            previous_debriefs.append(debrief_data)
    return previous_debriefs


async def build_play_session_context(
    play_session_repo: PlaySessionRepository,
    library_repo: LibraryRepository,
    llm_client: AbstractLLMClient,
    entry: LibraryEntry,
) -> PlaySessionContext:
    """Assemble the grounding context for a deep briefing run.

    Mirrors the context ``generate_briefing`` uses: the last 3 debriefs plus
    the most recent extracted location/quest/level and the entry's next action.
    """
    await ensure_extractions_complete(play_session_repo, library_repo, llm_client, entry.id)
    recent_play_sessions = await play_session_repo.get_recent_for_entry(entry.id, limit=3)
    previous_debriefs = _collect_previous_debriefs(recent_play_sessions)

    latest_state: dict[str, object] = {}
    if recent_play_sessions and recent_play_sessions[0].extracted_state:
        latest_state = recent_play_sessions[0].extracted_state

    return PlaySessionContext(
        game_title=entry.game.title,
        location=latest_state.get("location"),  # type: ignore[typeddict-item]
        current_quest=latest_state.get("current_quest"),  # type: ignore[typeddict-item]
        next_action=entry.play_session_next_action,
        level=latest_state.get("level"),  # type: ignore[typeddict-item]
        previous_debriefs=previous_debriefs,
    )


async def build_preview(
    play_session_repo: PlaySessionRepository,
    library_repo: LibraryRepository,
    llm_client: AbstractLLMClient,
    entry: LibraryEntry,
    position_override: str | None = None,
    *,
    agent: AbstractBriefingAgent | None = None,
    settings: Settings | None = None,
    mode: BriefingMode = "quick",
) -> dict[str, object]:
    """Build a briefing preview dict for a library entry.

    Shared by ``preview_briefing`` and ``submit_retroactive_debrief``. Does NOT
    check for active play_sessions. When *mode* is ``deep`` and an *agent* is given,
    the deep web-researched path runs (falling back to quick on failure);
    otherwise the quick single-shot briefing is used.
    """
    await ensure_extractions_complete(play_session_repo, library_repo, llm_client, entry.id)

    recent_play_sessions = await play_session_repo.get_recent_for_entry(entry.id, limit=1)
    last_context = None
    if recent_play_sessions and recent_play_sessions[0].extracted_state:
        last_context = recent_play_sessions[0].extracted_state

    if mode == "deep" and agent is not None:
        briefing_text = await generate_briefing_for_mode(
            play_session_repo,
            library_repo,
            llm_client,
            agent,
            settings or _settings,
            entry,
            "deep",
        )
    else:
        briefing_text = await generate_briefing(
            play_session_repo,
            library_repo,
            llm_client,
            entry.id,
            entry.game.title,
            entry.play_session_next_action,
            position_override=position_override,
        )

    return {
        "library_entry": entry,
        "briefing_text": briefing_text or None,
        "last_session_context": last_context,
    }


async def ensure_extractions_complete(
    play_session_repo: PlaySessionRepository,
    library_repo: LibraryRepository,
    llm_client: AbstractLLMClient,
    library_entry_id: int,
) -> None:
    """Sync fallback: extract state for play_sessions with debrief but no extraction.

    This handles the case where the Taskiq worker failed or hasn't processed
    the debrief yet. Called before briefing generation to ensure context is
    available.
    """
    pending = await play_session_repo.get_pending_extractions(library_entry_id)
    for play_session in pending:
        logger.info(
            "debrief_extraction_sync_fallback",
            play_session_id=play_session.id,
        )
        try:
            extracted = await llm_client.extract_debrief_state(
                game_title=play_session.library_entry.game.title,
                debrief_text=play_session.debrief_text,  # type: ignore[arg-type]
            )
            state_dict = {
                "location": extracted.location,
                "next_action": extracted.next_action,
                "level": extracted.level,
                "current_quest": extracted.current_quest,
            }
            await play_session_repo.set_extracted_state(play_session.id, state_dict)
            if extracted.next_action:
                await library_repo.update(
                    play_session.library_entry, play_session_next_action=extracted.next_action
                )
        except Exception:
            logger.warning(
                "debrief_extraction_sync_fallback_failed",
                play_session_id=play_session.id,
                exc_info=True,
            )


async def generate_briefing_for_mode(
    play_session_repo: PlaySessionRepository,
    library_repo: LibraryRepository,
    llm_client: AbstractLLMClient,
    agent: AbstractBriefingAgent | None,
    settings: Settings,
    entry: LibraryEntry,
    mode: BriefingMode,
) -> str:
    """Produce a briefing for *mode*, degrading deep -> quick on any failure.

    The deep path runs the research agent under a hard wall-clock ceiling; any
    timeout, research outage, or unexpected error falls back to the quick
    single-shot briefing, as does an empty deep result.
    """

    async def _quick() -> str:
        return await generate_briefing(
            play_session_repo,
            library_repo,
            llm_client,
            entry.id,
            entry.game.title,
            entry.play_session_next_action,
        )

    if mode != "deep" or agent is None:
        return await _quick()

    context = await build_play_session_context(play_session_repo, library_repo, llm_client, entry)
    try:
        result = await asyncio.wait_for(
            agent.deep_brief(DeepBriefRequest(context=context, thread_id=str(entry.public_id))),
            timeout=settings.deep_briefing_deadline_seconds + 5,
        )
    except (TimeoutError, ResearchUnavailableError):
        logger.warning("deep_briefing_fell_back_to_quick", library_entry_id=entry.id)
        return await _quick()
    except Exception:
        logger.warning("deep_briefing_failed", library_entry_id=entry.id, exc_info=True)
        return await _quick()

    return result.text or await _quick()


async def generate_briefing(
    play_session_repo: PlaySessionRepository,
    library_repo: LibraryRepository,
    llm_client: AbstractLLMClient,
    library_entry_id: int,
    game_title: str,
    current_next_action: str | None,
    position_override: str | None = None,
) -> str:
    """Generate a briefing from the last 3 debriefs.

    If *position_override* is provided, it's passed to the LLM as the
    player's corrected current position.

    Runs anti-hallucination validation on the output. If suspicious,
    appends a disclaimer.
    """
    await ensure_extractions_complete(
        play_session_repo, library_repo, llm_client, library_entry_id
    )
    recent_play_sessions = await play_session_repo.get_recent_for_entry(library_entry_id, limit=3)

    previous_debriefs = _collect_previous_debriefs(recent_play_sessions)

    try:
        briefing = await llm_client.generate_briefing(
            game_title=game_title,
            previous_debriefs=previous_debriefs,
            current_next_action=current_next_action,
            position_override=position_override,
        )
    except Exception:
        logger.warning("briefing_generation_failed", exc_info=True)
        return ""

    if not briefing:
        return ""

    # Anti-hallucination check.
    if previous_debriefs:
        context_parts = [game_title]
        for d in previous_debriefs:
            context_parts.extend(str(v) for v in d.values() if v is not None)
        if current_next_action:
            context_parts.append(current_next_action)
        if position_override:
            context_parts.append(position_override)
        context_text = " ".join(context_parts)

        result = validate_briefing(briefing, context_text)
        if result.is_suspicious:
            briefing += (
                "\n\n\u26a0\ufe0f Note: This briefing may contain inaccuracies. "
                "Some details could not be verified against your session notes."
            )

    return briefing

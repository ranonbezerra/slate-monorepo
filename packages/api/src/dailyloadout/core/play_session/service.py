"""PlaySession service: lifecycle management, briefing, and debrief orchestration."""

from __future__ import annotations

from uuid import UUID

import structlog
from fastapi import HTTPException, status

from dailyloadout.config import Settings
from dailyloadout.config import settings as default_settings
from dailyloadout.core.cache.invalidation import invalidate_user_stats
from dailyloadout.core.play_session.briefing import (
    BriefingMode,
    build_preview,
    generate_briefing,
    generate_briefing_for_mode,
)
from dailyloadout.core.play_session.start import create_play_session_for_entry
from dailyloadout.infrastructure.agent.base import AbstractBriefingAgent
from dailyloadout.infrastructure.db.models import LibraryEntry, PlaySession
from dailyloadout.infrastructure.db.repositories.library import LibraryRepository
from dailyloadout.infrastructure.db.repositories.play_session import PlaySessionRepository
from dailyloadout.infrastructure.llm.base import AbstractLLMClient

logger = structlog.get_logger()


class PlaySessionService:
    """Orchestrates play_session lifecycle: start, briefing, debrief, and end."""

    def __init__(
        self,
        play_session_repo: PlaySessionRepository,
        library_repo: LibraryRepository,
        llm_client: AbstractLLMClient,
        agent: AbstractBriefingAgent | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._play_session_repo = play_session_repo
        self._library_repo = library_repo
        self._llm_client = llm_client
        self._agent = agent
        self._settings = settings or default_settings

    # -- Start play_session ---------------------------------------------------

    async def _load_startable_entry(
        self, user_id: int, library_entry_public_id: UUID
    ) -> LibraryEntry:
        """Load an entry for start/preview; raise 404 if missing, 409 if busy."""
        entry = await self._library_repo.get_by_public_id(library_entry_public_id, user_id)
        if entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Library entry not found"
            )
        if await self._play_session_repo.get_active_for_user(user_id) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have an active play_session. End it first.",
            )
        return entry

    async def start_play_session(
        self,
        user_id: int,
        library_entry_public_id: UUID,
        briefing_text: str | None = None,
        mode: BriefingMode = "quick",
        skip_briefing: bool = False,
    ) -> PlaySession:
        """Start a new play_session for a library entry.

        If *briefing_text* is provided, it's used as-is. If *skip_briefing* is
        set, the play_session starts with no briefing at all (the "just play" path).
        Otherwise a briefing is generated in *mode* (quick or deep).
        """
        entry = await self._load_startable_entry(user_id, library_entry_public_id)

        if briefing_text is None and not skip_briefing:
            briefing_text = await generate_briefing_for_mode(
                self._play_session_repo,
                self._library_repo,
                self._llm_client,
                self._agent,
                self._settings,
                entry,
                mode,
            )

        return await create_play_session_for_entry(
            play_session_repo=self._play_session_repo,
            library_repo=self._library_repo,
            user_id=user_id,
            entry=entry,
            briefing_text=briefing_text,
        )

    # -- Preview briefing ------------------------------------------------

    async def preview_briefing(
        self,
        user_id: int,
        library_entry_public_id: UUID,
        position_override: str | None = None,
        mode: BriefingMode = "quick",
    ) -> dict[str, object]:
        """Preview a briefing (quick or deep) without creating a play_session."""
        entry = await self._load_startable_entry(user_id, library_entry_public_id)
        return await build_preview(
            self._play_session_repo,
            self._library_repo,
            self._llm_client,
            entry,
            position_override=position_override,
            agent=self._agent,
            settings=self._settings,
            mode=mode,
        )

    # -- Retroactive debrief ---------------------------------------------

    async def submit_retroactive_debrief(
        self,
        user_id: int,
        library_entry_public_id: UUID,
        debrief_text: str,
    ) -> dict[str, object]:
        """Record a debrief for a play session that wasn't tracked.

        Creates a pre-ended play_session with ``play_session_type="retroactive"``,
        runs LLM extraction synchronously, and returns a fresh briefing
        preview.
        """
        entry = await self._library_repo.get_by_public_id(library_entry_public_id, user_id)
        if entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Library entry not found"
            )

        extracted_state = None
        try:
            extracted = await self._llm_client.extract_debrief_state(
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
                await self._library_repo.update(
                    entry, play_session_next_action=extracted.next_action
                )
        except Exception:
            logger.warning("retroactive_extraction_failed", exc_info=True)

        await self._play_session_repo.create_retroactive(
            user_id=user_id,
            library_entry_id=entry.id,
            debrief_text=debrief_text,
            extracted_state=extracted_state,
        )
        await invalidate_user_stats(user_id)

        return await build_preview(
            self._play_session_repo,
            self._library_repo,
            self._llm_client,
            entry,
        )

    # -- Query -----------------------------------------------------------

    async def get_play_session(self, user_id: int, play_session_public_id: UUID) -> PlaySession:
        """Return a play_session scoped to *user_id*, or raise 404."""
        play_session = await self._play_session_repo.get_by_public_id(
            play_session_public_id, user_id=user_id
        )
        if play_session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="PlaySession not found"
            )
        return play_session

    async def get_active_play_session(self, user_id: int) -> PlaySession | None:
        """Return the user's active play_session, or None."""
        return await self._play_session_repo.get_active_for_user(user_id)

    async def list_play_sessions(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[PlaySession], int]:
        """Return the user's play_sessions along with the total count."""
        play_sessions = await self._play_session_repo.list_for_user(
            user_id, limit=limit, offset=offset
        )
        total = await self._play_session_repo.count_for_user(user_id)
        return play_sessions, total

    # -- Debrief ---------------------------------------------------------

    async def submit_debrief(
        self,
        user_id: int,
        play_session_public_id: UUID,
        debrief_text: str,
    ) -> PlaySession:
        """Submit a debrief for a play_session and end it.

        Saves the debrief text, ends the play_session immediately, and dispatches
        the LLM extraction to a background Taskiq worker.
        """
        play_session = await self.get_play_session(user_id, play_session_public_id)
        if play_session.ended_at is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="PlaySession is already ended"
            )

        await self._play_session_repo.set_debrief(play_session.id, debrief_text)
        await self._play_session_repo.end_play_session(
            play_session.id, ended_via="debrief_completed"
        )
        await invalidate_user_stats(user_id)

        game_title = play_session.library_entry.game.title
        try:
            from dailyloadout.infrastructure.tasks.debrief_extraction import (
                extract_debrief_state_task,
            )

            await extract_debrief_state_task.kiq(play_session.id, game_title, debrief_text)
            logger.info("debrief_extraction_dispatched", play_session_id=play_session.id)
        except Exception:
            logger.warning(
                "debrief_extraction_dispatch_failed",
                play_session_id=play_session.id,
                exc_info=True,
            )

        return await self.get_play_session(user_id, play_session_public_id)

    # -- End play_session (no debrief) ----------------------------------------

    async def end_play_session(
        self,
        user_id: int,
        play_session_public_id: UUID,
        ended_via: str = "paused_app",
    ) -> PlaySession:
        """End a play_session without a debrief."""
        play_session = await self.get_play_session(user_id, play_session_public_id)
        if play_session.ended_at is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="PlaySession is already ended"
            )

        await self._play_session_repo.end_play_session(play_session.id, ended_via=ended_via)
        await invalidate_user_stats(user_id)
        return await self.get_play_session(user_id, play_session_public_id)

    # -- Regenerate briefing ---------------------------------------------

    async def regenerate_briefing(
        self,
        user_id: int,
        play_session_public_id: UUID,
        position_override: str | None = None,
    ) -> PlaySession:
        """Regenerate the briefing for an active play_session.

        If *position_override* is provided, it replaces the stored session
        context for suggestion generation.
        """
        play_session = await self.get_play_session(user_id, play_session_public_id)
        if play_session.ended_at is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot regenerate briefing for an ended play_session",
            )

        entry = play_session.library_entry
        briefing_text = await generate_briefing(
            self._play_session_repo,
            self._library_repo,
            self._llm_client,
            entry.id,
            entry.game.title,
            entry.play_session_next_action,
            position_override=position_override,
        )
        if briefing_text:
            await self._play_session_repo.set_briefing(play_session.id, briefing_text)

        return await self.get_play_session(user_id, play_session_public_id)

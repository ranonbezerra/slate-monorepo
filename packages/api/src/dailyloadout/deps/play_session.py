"""PlaySession dependencies: repository and service."""

from typing import Annotated

from fastapi import Depends

from dailyloadout.config import settings
from dailyloadout.core.play_session.service import PlaySessionService
from dailyloadout.infrastructure.agent.base import AbstractBriefingAgent
from dailyloadout.infrastructure.agent.factory import get_briefing_agent
from dailyloadout.infrastructure.db.repositories.play_session import PlaySessionRepository

from .capture import LLMClientDep
from .db import DbSession
from .library import LibraryRepoDep

# ── Repository ────────────────────────────────────────────────────────


def get_play_session_repo(db: DbSession) -> PlaySessionRepository:
    """Provide a ``PlaySessionRepository`` bound to the current session."""
    return PlaySessionRepository(db)


PlaySessionRepoDep = Annotated[PlaySessionRepository, Depends(get_play_session_repo)]


# ── Briefing agent ────────────────────────────────────────────────────


def get_briefing_agent_dep(llm_client: LLMClientDep) -> AbstractBriefingAgent | None:
    """Provide the deep-research briefing agent, or ``None`` if disabled."""
    return get_briefing_agent(settings, llm_client)


BriefingAgentDep = Annotated[AbstractBriefingAgent | None, Depends(get_briefing_agent_dep)]


# ── Service ───────────────────────────────────────────────────────────


def get_play_session_service(
    play_session_repo: PlaySessionRepoDep,
    library_repo: LibraryRepoDep,
    llm_client: LLMClientDep,
    agent: BriefingAgentDep,
) -> PlaySessionService:
    """Provide a ``PlaySessionService`` wired to the current dependencies."""
    return PlaySessionService(
        play_session_repo,
        library_repo,
        llm_client,
        agent=agent,
        settings=settings,
    )


PlaySessionServiceDep = Annotated[PlaySessionService, Depends(get_play_session_service)]

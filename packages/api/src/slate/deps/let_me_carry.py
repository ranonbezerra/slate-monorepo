"""let_me_carry dependencies: agent + service."""

from typing import Annotated

from fastapi import Depends

from slate.config import settings
from slate.core.let_me_carry.service import LetMeCarryService
from slate.infrastructure.agent.let_me_carry.factory import get_let_me_carry_agent

from .capture import LLMClientDep
from .library import LibraryRepoDep
from .play_session import PlaySessionRepoDep, RecapAgentDep
from .stats import StatsServiceDep


def get_let_me_carry_service(
    library_repo: LibraryRepoDep,
    play_session_repo: PlaySessionRepoDep,
    stats_service: StatsServiceDep,
    llm_client: LLMClientDep,
    recap_agent: RecapAgentDep,
) -> LetMeCarryService:
    """Provide a ``LetMeCarryService`` wired to the configured agent provider."""
    return LetMeCarryService(
        library_repo=library_repo,
        play_session_repo=play_session_repo,
        stats_service=stats_service,
        agent=get_let_me_carry_agent(settings),
        llm_client=llm_client,
        recap_agent=recap_agent,
        settings=settings,
    )


LetMeCarryServiceDep = Annotated[LetMeCarryService, Depends(get_let_me_carry_service)]

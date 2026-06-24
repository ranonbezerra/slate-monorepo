"""Port for the Backlog Concierge chat agent."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from pydantic import BaseModel


@dataclass
class ConciergeTool:
    """A read-only tool the agent may call.

    ``coroutine`` already has the user/repos bound; it accepts only the
    LLM-facing arguments described by ``args_schema`` and returns text.
    """

    name: str
    description: str
    args_schema: type[BaseModel]
    coroutine: Callable[..., Awaitable[str]]


@dataclass
class ConciergeRequest:
    """One chat turn. ``tools`` are built per-request, scoped to the user."""

    thread_id: str
    message: str
    system: str
    tools: list[ConciergeTool]


@dataclass
class ConciergeReply:
    """The agent's raw answer for a turn (before the UUID guard runs)."""

    text: str


class AbstractConciergeAgent(ABC):
    """Contract for the conversational, tool-using backlog agent."""

    @abstractmethod
    async def respond(self, req: ConciergeRequest) -> ConciergeReply:
        """Run the tool-using loop for one turn and return the answer text."""
        ...

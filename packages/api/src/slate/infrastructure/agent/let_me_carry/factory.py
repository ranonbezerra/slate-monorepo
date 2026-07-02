"""Factory for the let_me_carry agent."""

from __future__ import annotations

from slate.config import Settings

from .base import AbstractLetMeCarryAgent


def get_let_me_carry_agent(settings: Settings) -> AbstractLetMeCarryAgent:
    """Return the LetMeCarry agent for the configured provider.

    Defaults to the deterministic dummy (also used in tests/CI) so the
    tool-calling model is never required unless explicitly enabled.
    """
    if settings.app_env == "testing" or settings.let_me_carry_provider == "dummy":
        from .dummy import DummyLetMeCarryAgent

        return DummyLetMeCarryAgent()

    if settings.let_me_carry_provider == "langgraph":
        from .langgraph_agent import LangGraphLetMeCarryAgent

        return LangGraphLetMeCarryAgent(settings=settings)

    msg = f"Unknown let_me_carry provider: {settings.let_me_carry_provider}"
    raise ValueError(msg)

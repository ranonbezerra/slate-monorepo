"""Deterministic recap agent for tests and offline development."""

from __future__ import annotations

from .base import AbstractRecapAgent, BriefResult, DeepBriefRequest


class DummyRecapAgent(AbstractRecapAgent):
    """Return a canned deep-research recap without running the graph."""

    async def deep_brief(self, req: DeepBriefRequest) -> BriefResult:
        """Return a deterministic, spoiler-safe recap for tests."""
        title = req.context.get("game_title", "your game")
        return BriefResult(
            text=(
                f"Previously on {title}: you were making progress. "
                "Head toward the next area and continue your current objective."
            ),
            source="deep_research",
            suspicious=False,
        )

"""Corrective / Adaptive RAG: relevance-gated recap routing (Epic 29).

CRAG (Yan et al., 2401.15884) adds a *retrieval evaluator* + *action trigger* to plain
RAG. Slate's deep-recap graph already has the corrective machinery (grade → refine →
web-search → anti-hallucinate); what was missing is the trigger — an automatic choice
between the cheap local-RAG recap and the expensive web-research recap, instead of a
manual ``mode`` flag.

This module is the pure decision layer (no DB, no I/O):

- ``evaluate_local_relevance`` grades whether the player's retrieved history carries
  enough concrete content to ground a faithful recap — reusing the anti-hallucination
  token notion (Epic 6), so it's deterministic and cheap (no extra LLM call).
- ``route_recap`` maps the verdict to a path, **entitlement-gated**: a free-tier user is
  never silently escalated to the paid deep path.

The DB retrieval and the actual generation stay in ``recap.py``; this keeps the guard
files untouched and the routing logic unit-testable in isolation.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, Protocol

from slate.config import Settings
from slate.core.play_session.anti_hallucination import extract_interesting_tokens

RelevanceVerdict = Literal["correct", "incorrect", "ambiguous"]
RecapPath = Literal["quick", "deep"]


class _SessionLike(Protocol):
    """The only fields the evaluator reads — keeps it decoupled from the ORM row."""

    wrap_up_text: str | None
    extracted_state: dict[str, object] | None


def _session_text(session: _SessionLike) -> str:
    """Flatten a retrieved session into its content string (note + structured state)."""
    parts: list[str] = []
    if session.wrap_up_text:
        parts.append(session.wrap_up_text)
    if session.extracted_state:
        parts.extend(str(v) for v in session.extracted_state.values() if v is not None)
    return " ".join(parts)


def evaluate_local_relevance(
    sessions: Sequence[_SessionLike], settings: Settings
) -> RelevanceVerdict:
    """Grade whether the retrieved local history is enough to ground a recap.

    Deterministic and model-free: counts the content-bearing sessions and the distinct
    "interesting" tokens (proper nouns / numbers) across them.

    - ``incorrect`` — no local history, or too thin to ground on → escalate to web.
    - ``correct`` — enough sessions *and* enough concrete content → the cheap local path.
    - ``ambiguous`` — borderline → escalate and let the deep path blend local + web.
    """
    content = [s for s in sessions if (s.wrap_up_text or s.extracted_state)]
    if not content:
        return "incorrect"

    tokens: set[str] = set()
    for session in content:
        tokens |= extract_interesting_tokens(_session_text(session))
    richness = len(tokens)

    if len(content) >= settings.adaptive_min_correct_sessions and (
        richness >= settings.adaptive_rich_token_min
    ):
        return "correct"
    if richness < settings.adaptive_sparse_token_max:
        return "incorrect"
    return "ambiguous"


def route_recap(verdict: RelevanceVerdict, *, entitled_to_deep: bool) -> RecapPath:
    """Map a relevance verdict to a recap path, gated by deep-path entitlement.

    ``correct`` always stays quick. ``incorrect``/``ambiguous`` want the deep path — but
    a user not entitled to deep is **never** auto-escalated: they stay quick (the caller
    may surface an upgrade nudge instead). Deep inherently blends the local context in,
    so ``ambiguous`` maps to deep rather than a distinct "combine" path.
    """
    if verdict == "correct":
        return "quick"
    return "deep" if entitled_to_deep else "quick"


def deep_recap_entitled(settings: Settings) -> bool:
    """Whether the current user may be auto-routed to the paid deep path.

    Placeholder for the future per-user tier gate (a separate monetization epic); today
    it reads a single default. The router only needs the boolean, so swapping this for a
    real ``user.tier`` check later is a one-line change.
    """
    return settings.adaptive_deep_entitled_default

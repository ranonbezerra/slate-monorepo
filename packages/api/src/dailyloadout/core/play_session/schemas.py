"""Pydantic request / response schemas for the play_session layer."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from dailyloadout.core.library.schemas import LibraryEntryResponse


class ExtractedState(BaseModel):
    """Structured state extracted from a play_session debrief by the LLM.

    Mirrors the shape persisted by ``extract_debrief_state_task`` /
    ``ConciergeService`` (see ``infrastructure.llm.base.ExtractedState``). All
    fields are optional so older rows and partial extractions still validate;
    unknown keys are ignored for forward/backward compatibility with the JSONB
    column.
    """

    model_config = ConfigDict(extra="ignore")

    location: str | None = None
    next_action: str | None = None
    level: str | None = None
    current_quest: str | None = None


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class PlaySessionStartRequest(BaseModel):
    """Body for ``POST /v1/play-sessions``."""

    library_entry_public_id: UUID
    briefing_text: str | None = Field(
        default=None,
        max_length=10000,
        description="Pre-generated briefing from a preview call. Skips LLM generation.",
    )
    mode: Literal["quick", "deep"] = Field(
        default="quick",
        description="Briefing mode: 'quick' (single-shot) or 'deep' (web-researched).",
    )
    skip_briefing: bool = Field(
        default=False,
        description="Start with no briefing at all (don't generate one). The "
        "briefing is an optional stage — this is the 'just play' path.",
    )


class BriefingPreviewRequest(BaseModel):
    """Body for ``POST /v1/play-sessions/preview-briefing``."""

    library_entry_public_id: UUID
    position_override: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional player-provided correction of their current in-game position.",
    )
    mode: Literal["quick", "deep"] = Field(
        default="quick",
        description="Briefing mode: 'quick' (single-shot) or 'deep' (web-researched).",
    )


class RetroactiveDebriefRequest(BaseModel):
    """Body for ``POST /v1/play-sessions/retroactive-debrief``."""

    library_entry_public_id: UUID
    debrief_text: str = Field(min_length=3, max_length=5000)


class PlaySessionDebriefRequest(BaseModel):
    """Body for ``PATCH /v1/play-sessions/{public_id}/debrief``."""

    debrief_text: str = Field(min_length=3, max_length=5000)


class PlaySessionEndRequest(BaseModel):
    """Body for ``POST /v1/play-sessions/{public_id}/end``."""

    ended_via: Literal["paused_app"] = "paused_app"


class RegenerateBriefingRequest(BaseModel):
    """Body for ``POST /v1/play-sessions/{public_id}/briefing/regenerate``."""

    current_position: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional player-provided correction of their current in-game position.",
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class PlaySessionResponse(BaseModel):
    """Full play_session with related library entry."""

    public_id: UUID
    library_entry: LibraryEntryResponse
    play_session_type: str = "regular"
    briefing_text: str | None = None
    debrief_text: str | None = None
    extracted_state: ExtractedState | None = None
    ended_via: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    last_session_context: ExtractedState | None = None

    model_config = {"from_attributes": True}


class PlaySessionListItem(BaseModel):
    """PlaySession summary for list views."""

    public_id: UUID
    library_entry: LibraryEntryResponse
    play_session_type: str = "regular"
    ended_via: str | None = None
    started_at: datetime
    ended_at: datetime | None = None

    model_config = {"from_attributes": True}


class PlaySessionListResponse(BaseModel):
    """Paginated list of play_sessions."""

    items: list[PlaySessionListItem]
    total: int


class BriefingPreviewResponse(BaseModel):
    """Briefing preview without creating a play_session."""

    library_entry: LibraryEntryResponse
    briefing_text: str | None = None
    last_session_context: ExtractedState | None = None

    model_config = {"from_attributes": True}


# Valid ended_via values (for documentation / validation).
EndedVia = Literal["debrief_completed", "paused_app", "auto_clamp", "retroactive"]

PlaySessionType = Literal["regular", "retroactive"]

PlaySessionStatus = Literal["active", "ended"]


__all__ = [
    "BriefingPreviewRequest",
    "BriefingPreviewResponse",
    "EndedVia",
    "ExtractedState",
    "PlaySessionDebriefRequest",
    "PlaySessionEndRequest",
    "PlaySessionListItem",
    "PlaySessionListResponse",
    "PlaySessionResponse",
    "PlaySessionStartRequest",
    "PlaySessionStatus",
    "PlaySessionType",
    "RegenerateBriefingRequest",
    "RetroactiveDebriefRequest",
]

"""Response schema for the account data export (GDPR/LGPD portability).

Clamps ``GET /v1/auth/me/export``: only the fields declared here are serialized,
so a future edit to the export builder can't silently leak an internal column
(``id``, ``password_hash``, ``token_version``, ...) that isn't in the contract.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class ExportProfile(BaseModel):
    public_id: str
    email: str
    display_name: str
    email_verified: bool
    locale: str
    timezone: str
    created_at: datetime


class ExportLibraryEntry(BaseModel):
    public_id: str
    status: str
    acquired_at: date | None
    next_action: str | None
    last_played_at: datetime | None
    created_at: datetime


class ExportPlaySession(BaseModel):
    public_id: str
    recap_text: str | None
    wrap_up_text: str | None
    extracted_state: dict[str, object] | None
    started_at: datetime
    ended_at: datetime | None


class ExportCapture(BaseModel):
    public_id: str
    input_type: str
    raw_text: str | None
    status: str
    created_at: datetime


class ExportPick(BaseModel):
    public_id: str
    mood: str
    available_minutes: int
    mental_energy: str
    action: str | None
    reasoning: str | None
    created_at: datetime


class ExportResponse(BaseModel):
    """The portable account dump. A missing/extra field on the source dict is a
    contract error surfaced at serialization, not a silent leak."""

    exported_at: datetime
    profile: ExportProfile
    library: list[ExportLibraryEntry]
    play_sessions: list[ExportPlaySession]
    captures: list[ExportCapture]
    picks: list[ExportPick]

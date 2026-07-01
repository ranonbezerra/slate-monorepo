"""Account lifecycle: self-service data export + erasure (GDPR/LGPD rights).

Two user-facing rights, both re-authentication-gated at the router:
- **Export** (portability — GDPR art. 20 / LGPD art. 18): a machine-readable dump
  of the account's personal data.
- **Erasure** (right to be forgotten — GDPR art. 17 / LGPD art. 18): a true
  hard-delete; FK cascades remove owned rows, audit refs are ``SET NULL``.
"""

from __future__ import annotations

from datetime import UTC, datetime

from slate.core.auth.security import verify_password
from slate.infrastructure.db.models import Capture, LibraryEntry, Pick, PlaySession, User
from slate.infrastructure.db.repositories.capture import CaptureRepository
from slate.infrastructure.db.repositories.library import LibraryRepository
from slate.infrastructure.db.repositories.pick import PickRepository
from slate.infrastructure.db.repositories.play_session import PlaySessionRepository
from slate.infrastructure.db.repositories.user import UserRepository

# Personal-scale export bound: enough for any real account, caps a pathological one.
_EXPORT_LIMIT = 10_000


class ReauthError(Exception):
    """Raised when re-authentication for a destructive account action fails."""


class AccountService:
    """Self-service account export + erasure."""

    def __init__(
        self,
        users: UserRepository,
        library: LibraryRepository,
        play_sessions: PlaySessionRepository,
        captures: CaptureRepository,
        picks: PickRepository,
    ) -> None:
        self._users = users
        self._library = library
        self._play_sessions = play_sessions
        self._captures = captures
        self._picks = picks

    async def delete_account(self, user: User, password: str | None) -> None:
        """Permanently erase *user* after re-authentication.

        A password-holding account must confirm with its password; an OAuth-only
        account (no password set) is gated by the authenticated session alone.
        """
        if user.password_hash is not None:  # noqa: SIM102 — nested `if` narrows the type for mypy
            if not password or not verify_password(password, user.password_hash):
                raise ReauthError("Password is incorrect")
        await self._users.hard_delete(user.id)

    async def export_data(self, user: User) -> dict[str, object]:
        """Assemble the user's personal data as a portable structure."""
        library = await self._library.list_for_user(user.id, limit=_EXPORT_LIMIT)
        sessions = await self._play_sessions.list_for_user(user.id, limit=_EXPORT_LIMIT)
        captures = await self._captures.list_for_user(user.id, limit=_EXPORT_LIMIT)
        picks = await self._picks.list_for_user(user.id, limit=_EXPORT_LIMIT)
        return {
            "exported_at": datetime.now(UTC),
            "profile": {
                "public_id": str(user.public_id),
                "email": user.email,
                "display_name": user.display_name,
                "email_verified": user.email_verified,
                "locale": user.locale,
                "timezone": user.timezone,
                "created_at": user.created_at,
            },
            "library": [_entry(e) for e in library],
            "play_sessions": [_session(s) for s in sessions],
            "captures": [_capture(c) for c in captures],
            "picks": [_pick(p) for p in picks],
        }


def _entry(e: LibraryEntry) -> dict[str, object]:
    return {
        "public_id": str(e.public_id),
        "status": e.status,
        "acquired_at": e.acquired_at,
        "next_action": e.play_session_next_action,
        "last_played_at": e.last_played_at,
        "created_at": e.created_at,
    }


def _session(s: PlaySession) -> dict[str, object]:
    return {
        "public_id": str(s.public_id),
        "recap_text": s.recap_text,
        "wrap_up_text": s.wrap_up_text,
        "extracted_state": s.extracted_state,
        "started_at": s.started_at,
        "ended_at": s.ended_at,
    }


def _capture(c: Capture) -> dict[str, object]:
    return {
        "public_id": str(c.public_id),
        "input_type": c.input_type,
        "raw_text": c.raw_text,
        "status": c.status,
        "created_at": c.created_at,
    }


def _pick(p: Pick) -> dict[str, object]:
    return {
        "public_id": str(p.public_id),
        "mood": p.mood,
        "available_minutes": p.available_minutes,
        "mental_energy": p.mental_energy,
        "action": p.action,
        "reasoning": p.reasoning,
        "created_at": p.created_at,
    }

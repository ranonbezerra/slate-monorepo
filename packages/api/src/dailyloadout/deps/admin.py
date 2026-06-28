"""Backoffice service dependency providers.

The home for admin *service* DI. The admin auth gate (``AdminUserDep``) and the
older service providers still live in ``deps/auth.py``; new backoffice domains
wire their services here to keep ``auth.py`` within the file-size budget.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from dailyloadout.core.admin.loadouts_service import AdminLoadoutService
from dailyloadout.core.admin.play_sessions_service import AdminPlaySessionService
from dailyloadout.infrastructure.db.repositories.admin import AdminAuditRepository
from dailyloadout.infrastructure.db.repositories.loadout import LoadoutRepository
from dailyloadout.infrastructure.db.repositories.play_session import PlaySessionRepository
from dailyloadout.infrastructure.db.repositories.user import UserRepository

from .db import DbSession


def get_admin_loadout_service(db: DbSession) -> AdminLoadoutService:
    """Provide an ``AdminLoadoutService`` wired to the loadout + user repos."""
    return AdminLoadoutService(LoadoutRepository(db), UserRepository(db))


AdminLoadoutServiceDep = Annotated[AdminLoadoutService, Depends(get_admin_loadout_service)]


def get_admin_play_session_service(db: DbSession) -> AdminPlaySessionService:
    """Provide an ``AdminPlaySessionService`` wired to the play-session + user repos."""
    return AdminPlaySessionService(
        PlaySessionRepository(db), UserRepository(db), AdminAuditRepository(db)
    )


AdminPlaySessionServiceDep = Annotated[
    AdminPlaySessionService, Depends(get_admin_play_session_service)
]

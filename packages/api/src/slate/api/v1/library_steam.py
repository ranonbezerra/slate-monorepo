"""Steam library-import endpoint (ROADMAP Epic 30).

Kept separate from the OCR bulk-import router (``library_import.py``): this is
the account-sync path — no upload, it pulls the owned library straight from
Steam. Requires the user to have linked their Steam account first
(``/v1/auth/steam/start``).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from slate.api.v1._rate_limit import rate_limit
from slate.config import settings
from slate.core.library.steam_schemas import SteamImportSummary
from slate.deps import CurrentUserDep
from slate.deps.steam import SteamImportServiceDep
from slate.infrastructure.steam.factory import is_steam_enabled

router = APIRouter(prefix="/v1/library/steam", tags=["library"])


@router.post(
    "/import",
    response_model=SteamImportSummary,
    dependencies=[
        Depends(
            rate_limit(
                "steam_import",
                settings.rate_limit_steam_import_per_minute,
                60,
                by="user",
                fail_closed=True,
            )
        ),
    ],
)
async def import_steam_library(
    current_user: CurrentUserDep,
    steam_import_service: SteamImportServiceDep,
) -> SteamImportSummary:
    """Sync the caller's owned Steam library into their Slate library.

    409 if the user has not connected a Steam account; 503 if the feature is not
    configured. A private/empty Steam profile returns a summary with
    ``private_or_empty=True`` (not an error).
    """
    if not is_steam_enabled(settings):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Steam import is not configured.",
        )
    try:
        return await steam_import_service.import_owned_games(current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

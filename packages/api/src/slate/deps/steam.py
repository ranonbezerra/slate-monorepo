"""Steam account-sync dependencies (Epic 30): client + import service."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from slate.config import settings
from slate.core.library.steam_import import SteamImportService
from slate.infrastructure.catalog.factory import get_catalog_matcher
from slate.infrastructure.steam.base import AbstractSteamClient
from slate.infrastructure.steam.factory import get_steam_client

from .capture import IGDBClientDep
from .library import (
    GameRepoDep,
    LibraryRepoDep,
    LibraryServiceDep,
    PlatformRepoDep,
)


def get_steam_client_dep() -> AbstractSteamClient:
    """Provide the Steam client for the current environment (dummy in testing)."""
    return get_steam_client(settings)


SteamClientDep = Annotated[AbstractSteamClient, Depends(get_steam_client_dep)]


async def get_steam_import_service(
    steam_client: SteamClientDep,
    library_service: LibraryServiceDep,
    game_repo: GameRepoDep,
    library_repo: LibraryRepoDep,
    platform_repo: PlatformRepoDep,
    igdb_client: IGDBClientDep,
) -> SteamImportService:
    """Provide a ``SteamImportService`` wired to the current collaborators."""
    return SteamImportService(
        steam_client,
        get_catalog_matcher(settings, igdb_client),
        library_service,
        game_repo,
        library_repo,
        platform_repo,
        max_games=settings.steam_import_max_games,
    )


SteamImportServiceDep = Annotated[SteamImportService, Depends(get_steam_import_service)]

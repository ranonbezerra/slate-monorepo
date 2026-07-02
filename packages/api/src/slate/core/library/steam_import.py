"""Steam owned-library import service (ROADMAP Epic 30).

The account-sync upgrade over the OCR screenshot import: pull the user's entire
owned Steam library + playtime and funnel each title through the same catalog
matcher the screenshot import uses. Matched games are added to the library on
"PC (Steam)" (idempotent — already-owned platforms are skipped) with their
all-time playtime recorded; unmatched titles are counted for the UI.
"""

from __future__ import annotations

import structlog

from slate.core.capture.games import slugify
from slate.core.library.service import LibraryService
from slate.core.library.steam_schemas import SteamImportSummary
from slate.infrastructure.catalog.base import AbstractCatalogMatcher, CatalogMatch
from slate.infrastructure.db.models import Game, User
from slate.infrastructure.db.repositories.game import GameRepository
from slate.infrastructure.db.repositories.library import LibraryRepository
from slate.infrastructure.db.repositories.platform import PlatformRepository
from slate.infrastructure.steam.base import AbstractSteamClient, OwnedGame

logger = structlog.get_logger()

# The seeded platform the Steam library maps onto (see the platforms migration).
_STEAM_PLATFORM_SLUG = "pc-steam"


class SteamImportService:
    """Import a user's owned Steam library into their Slate library."""

    def __init__(
        self,
        steam_client: AbstractSteamClient,
        catalog_matcher: AbstractCatalogMatcher,
        library_service: LibraryService,
        game_repo: GameRepository,
        library_repo: LibraryRepository,
        platform_repo: PlatformRepository,
        *,
        max_games: int = 500,
    ) -> None:
        self._steam = steam_client
        self._matcher = catalog_matcher
        self._library_service = library_service
        self._game_repo = game_repo
        self._library_repo = library_repo
        self._platform_repo = platform_repo
        self._max_games = max_games

    async def import_owned_games(self, user: User) -> SteamImportSummary:
        """Sync *user*'s owned Steam library into Slate.

        Raises:
            ValueError: If the user has not connected a Steam account, or the
                "PC (Steam)" platform is missing from the catalog.
        """
        if not user.steam_id:
            raise ValueError("Steam not connected")

        platform = await self._platform_repo.get_by_slug(_STEAM_PLATFORM_SLUG)
        if platform is None:  # pragma: no cover - seeded by migration in every env
            raise ValueError("Steam platform not configured")

        owned = await self._steam.get_owned_games(user.steam_id)
        if not owned:
            # A private profile or a genuinely empty library — not an error.
            return SteamImportSummary(
                imported=0, already_owned=0, unmatched=0, private_or_empty=True
            )

        capped = self._cap(owned)
        matches = await self._matcher.match_many([g.name for g in capped])

        imported = 0
        already_owned = 0
        unmatched = 0
        for owned_game, match in zip(capped, matches, strict=True):
            if not match.matched:
                unmatched += 1
                continue
            added = await self._add_matched_game(
                user.id, match, owned_game.playtime_minutes, platform.id
            )
            if added:
                imported += 1
            else:
                already_owned += 1

        logger.info(
            "steam_import_completed",
            user_id=user.id,
            imported=imported,
            already_owned=already_owned,
            unmatched=unmatched,
        )
        return SteamImportSummary(
            imported=imported,
            already_owned=already_owned,
            unmatched=unmatched,
            private_or_empty=False,
        )

    def _cap(self, owned: list[OwnedGame]) -> list[OwnedGame]:
        """Cap the owned list at ``max_games``, logging when truncated."""
        if len(owned) <= self._max_games:
            return owned
        logger.warning("steam_import_truncated", total=len(owned), cap=self._max_games)
        return owned[: self._max_games]

    async def _add_matched_game(
        self, user_id: int, match: CatalogMatch, playtime_minutes: int, platform_id: int
    ) -> bool:
        """Resolve *match* to a game, add it on Steam, and record playtime.

        Returns True if a new Steam entry was created for this game, False if the
        user already owned it on Steam (idempotent re-import). Playtime is always
        (re)written so a re-sync refreshes the recorded hours.
        """
        game = await self._resolve_game(match)
        already = await self._library_repo.exists(user_id, game.id, platform_id)
        await self._library_service.add_to_library(
            user_id,
            game.public_id,
            platform_ids=[platform_id],
            status="backlog",
        )
        await self._library_repo.set_steam_playtime(
            user_id, game.id, platform_id, playtime_minutes
        )
        return not already

    async def _resolve_game(self, match: CatalogMatch) -> Game:
        """Resolve a catalog *match* to a canonical ``Game`` row, creating it once.

        Mirrors the capture commit path (``get_or_create_game``): prefer the IGDB
        id, then the slug, else create a shared IGDB-attributed row.
        """
        if match.igdb_id is not None:
            existing = await self._game_repo.get_by_igdb_id(match.igdb_id)
            if existing is not None:
                return existing

        slug = slugify(match.title)
        existing = await self._game_repo.get_by_slug(slug)
        if existing is not None:
            return existing

        return await self._game_repo.create(
            slug=slug,
            title=match.title,
            metadata_source="igdb",
            igdb_id=match.igdb_id,
            summary=match.summary,
            cover_url=match.cover_url,
            first_release_date=match.first_release_date,
            genres=match.genres,
            is_shared=True,
        )

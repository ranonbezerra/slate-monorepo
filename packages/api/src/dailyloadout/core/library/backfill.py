"""Backfill IGDB metadata onto games that predate IGDB credentials.

Games created from captures/manual entry before ``IGDB_CLIENT_ID`` was set have
``igdb_id IS NULL`` and no genres/cover/summary — which is why, e.g., the
"Time by Genre" analytics chart renders empty. This module re-matches each such
game against the live IGDB catalogue (reusing the same fuzzy scorer the bulk
library-import uses) and fills in the canonical metadata.

It is deliberately conservative:

* The game's ``title``/``slug`` are left untouched (we only fill metadata), so
  no slug collisions and the user's known title is preserved.
* If the matched ``igdb_id`` already belongs to a *different* catalogue row, the
  unenriched row is a duplicate of an already-canonical game; we **skip** it and
  report it rather than risk a merge (repointing library entries is a separate,
  riskier operation).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from dailyloadout.infrastructure.catalog.matcher import best_match
from dailyloadout.infrastructure.db.repositories.game import GameRepository
from dailyloadout.infrastructure.igdb.base import IGDBSearchClient


@dataclass
class BackfillItem:
    """One game's outcome: the local title, the matched IGDB title, the score."""

    title: str
    igdb_title: str
    score: float


@dataclass
class BackfillReport:
    """Aggregate outcome of a backfill run."""

    enriched: list[BackfillItem] = field(default_factory=list)
    matched_dry_run: list[BackfillItem] = field(default_factory=list)
    unmatched: list[str] = field(default_factory=list)
    skipped_collision: list[BackfillItem] = field(default_factory=list)

    @property
    def scanned(self) -> int:
        return (
            len(self.enriched)
            + len(self.matched_dry_run)
            + len(self.unmatched)
            + len(self.skipped_collision)
        )


async def backfill_games(
    *,
    game_repo: GameRepository,
    igdb_client: IGDBSearchClient,
    min_score: float,
    dry_run: bool = False,
    limit: int | None = None,
    search_limit: int = 5,
) -> BackfillReport:
    """Enrich games with ``igdb_id IS NULL`` against IGDB.

    Returns a :class:`BackfillReport`. When ``dry_run`` is true, matches are
    reported under ``matched_dry_run`` and nothing is written.
    """
    games = await game_repo.list_unenriched(limit=limit)
    report = BackfillReport()

    for game in games:
        candidates = await igdb_client.search_games(game.title, limit=search_limit)
        result = best_match(game.title, candidates, min_score)
        if result is None:
            report.unmatched.append(game.title)
            continue

        igdb_game, score = result
        item = BackfillItem(title=game.title, igdb_title=igdb_game.title, score=score)

        existing = await game_repo.get_by_igdb_id(igdb_game.igdb_id)
        if existing is not None and existing.id != game.id:
            report.skipped_collision.append(item)
            continue

        if dry_run:
            report.matched_dry_run.append(item)
            continue

        await game_repo.update(
            game,
            igdb_id=igdb_game.igdb_id,
            summary=igdb_game.summary,
            cover_url=igdb_game.cover_url,
            genres=igdb_game.genres,
            first_release_date=igdb_game.first_release_date,
            metadata_source="igdb",
        )
        report.enriched.append(item)

    return report

"""CaptureCandidateRepository.create_bulk mass-assignment guard.

``create_bulk`` unpacks a caller-supplied dict into the ORM model. Identity /
ownership keys must be rejected so a widened field map can't override
``capture_id`` or set ``id``/``public_id`` via the unpack.
"""

from __future__ import annotations

import pytest

from slate.infrastructure.db.repositories.capture_candidate import CaptureCandidateRepository
from tests.conftest import _TestSessionFactory


class TestCreateBulkGuard:
    async def test_rejects_protected_keys(self) -> None:
        async with _TestSessionFactory() as session:
            repo = CaptureCandidateRepository(session)
            for bad in ({"id": 5}, {"public_id": "x"}, {"capture_id": 999}, {"created_at": "now"}):
                with pytest.raises(ValueError, match="cannot be set"):
                    # The guard raises before any DB write, so the (fake) capture_id
                    # never has to exist.
                    await repo.create_bulk(1, [{"title": "Halo", **bad}])

"""Account-lifecycle endpoints: data export + self-service erasure (GDPR/LGPD).

Served under ``/v1/auth`` (a separate module from ``auth.py`` to keep each router
within the file-size budget). Both are authenticated; erasure re-authenticates
with the account password and is rate-limited so a stolen access token can't
brute-force the password through it.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from slate.api.v1._rate_limit import rate_limit
from slate.config import settings
from slate.core.auth.account import ReauthError
from slate.core.auth.schemas import DeleteAccountRequest, MessageResponse
from slate.deps.account import AccountServiceDep
from slate.deps.auth import CurrentUserDep

router = APIRouter(prefix="/v1/auth", tags=["auth"])

# Modest per-user cap: erasure re-auths with the password, so bound the attempts a
# hijacked session could use to guess it. Export is a heavier read — cap it too.
_delete_rate = Depends(rate_limit("auth_delete_account", 10, 60, by="user"))
_export_rate = Depends(
    rate_limit("auth_export", settings.rate_limit_read_per_minute, 60, by="user")
)


@router.post(
    "/delete-account",
    response_model=MessageResponse,
    dependencies=[_delete_rate],
)
async def delete_account(
    current_user: CurrentUserDep,
    service: AccountServiceDep,
    body: DeleteAccountRequest,
) -> MessageResponse:
    """Permanently erase the caller's account after password re-authentication."""
    if settings.single_user_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account deletion is disabled in single-user mode",
        )
    try:
        await service.delete_account(current_user, body.password)
    except ReauthError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return MessageResponse(message="Account permanently deleted")


@router.get("/me/export", dependencies=[_export_rate])
async def export_account(
    current_user: CurrentUserDep,
    service: AccountServiceDep,
) -> dict[str, object]:
    """Return the caller's personal data as a portable JSON document."""
    return await service.export_data(current_user)

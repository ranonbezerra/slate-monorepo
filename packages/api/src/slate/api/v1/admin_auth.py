"""Backoffice admin login — password + admin-grant behind one indistinguishable door.

Reusing the player ``/v1/auth/login`` for the backoffice leaks: it returns 200
for any valid account, so a non-admin learns their credentials are correct and
only the admin grant is missing. This endpoint verifies the password AND the
admin grant, and collapses *either* failure into the same generic
``401 Invalid credentials`` — a valid non-admin is indistinguishable from a bad
password. It otherwise mirrors the player login (Turnstile step-up, MFA
challenge, cookie/body token modes) and shares its rate-limit buckets so an
attacker can't double their attempts by splitting across the two endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from slate.api.v1.auth import _check_login_account_rate, _check_login_rate
from slate.api.v1.auth_cookies import is_cookie_mode, set_refresh_cookie
from slate.config import settings
from slate.core.auth import login_stepup
from slate.core.auth.schemas import LoginRequest, LoginResponse
from slate.core.auth.security import create_mfa_challenge_token
from slate.deps import AuthServiceDep, DbSession, MfaServiceDep
from slate.deps.captcha import verify_turnstile
from slate.infrastructure.db.repositories.admin import AdminRepository

router = APIRouter(prefix="/internal/v1", tags=["internal"])

# One non-committal message for both a wrong password and a valid non-admin.
_INVALID = "Invalid credentials"


@router.post(
    "/auth/login",
    response_model=LoginResponse,
    dependencies=[Depends(_check_login_rate), Depends(_check_login_account_rate)],
)
async def admin_login(
    body: LoginRequest,
    auth_service: AuthServiceDep,
    mfa_service: MfaServiceDep,
    db: DbSession,
    request: Request,
    response: Response,
) -> LoginResponse:
    """Authenticate a backoffice admin; non-admins get the same 401 as bad creds.

    The admin gate is folded into the credential check so a valid non-admin (and
    the single-user JWT-bypass account) fails exactly like a wrong password —
    same status, same detail — and never reaches the MFA/token branches.
    """
    if await login_stepup.login_stepup_required(body.email):
        await verify_turnstile(request)
    try:
        user = await auth_service.verify_credentials(body.email, body.password)
        if settings.single_user_mode or not await AdminRepository(db).is_admin(user.id):
            raise ValueError(_INVALID)
    except ValueError as exc:
        await login_stepup.record_login_failure(body.email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID) from exc
    await login_stepup.reset_login_failures(body.email)

    if await mfa_service.is_enabled(user.id):
        challenge = create_mfa_challenge_token(str(user.public_id), user.token_version)
        return LoginResponse(mfa_required=True, mfa_token=challenge)

    access_token, refresh_token = await auth_service.issue_tokens(user)
    if is_cookie_mode(request):
        set_refresh_cookie(response, refresh_token)
        return LoginResponse(access_token=access_token)
    return LoginResponse(access_token=access_token, refresh_token=refresh_token)

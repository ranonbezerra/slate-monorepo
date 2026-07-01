# auth — authentication, authorization, tokens, sessions

Audit `packages/api` for identity & access flaws.

- **AuthN/JWT**: is the algorithm pinned (no `alg:none`/confusion)? are `exp`/`iat`
  verified, `aud`/`iss` set+checked? is `token_version` checked on EVERY request
  (so logout-all/ban truly invalidates access tokens)? `sub` = public_id (not
  internal id)?
- **Tokens**: password-reset / email-verify / MFA-challenge tokens — entropy,
  single-use (atomic consume?), expiry, purpose-scoping, session-revoke on use.
- **MFA**: TOTP replay guard + recovery codes — single-use under concurrency
  (conditional UPDATE, not check-then-write)? hashed at rest?
- **Refresh tokens**: rotation atomic (conditional revoke)? reuse-detection?
- **OAuth**: PKCE, single-use `state`, provider allowlist, redirect_uri from
  config only, browser-binding (login-CSRF), verified-email account-linking.
- **Authorization / IDOR**: every user-facing resource scoped to the owner
  (`user_id`) in the query, not just by public_id? enumerate list/get/update/
  delete routes.
- **Admin / `/internal/v1`**: is the admin gate DB-backed and on EVERY internal
  route (no authenticated-only escalation)? single-user-mode bypass blocked?
  mutations audited?
- **Cookies/CSRF**: refresh cookie attributes (HttpOnly/Secure/SameSite/Path);
  is CSRF handled for cookie-authenticated state changes?

Read `core/auth/*`, `deps/auth.py`, `api/v1/auth*.py`, `api/v1/admin*.py`, the
oauth infra, and the refresh/mfa repositories.

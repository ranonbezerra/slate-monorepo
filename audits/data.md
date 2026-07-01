# data — data exposure, logging/PII, serialization, mass-assignment

Audit `packages/api` for sensitive-data leakage and API-contract flaws.

- **Secrets/PII in logs**: are JWTs, refresh/reset tokens, passwords, TOTP
  secrets/codes, or the SECRET_KEY ever passed to `logger.*` / a structlog event?
  emails/IPs/user free-text logged in full? LLM prompt/completion capture —
  redacted before storage? access-log query-string redaction covers OAuth
  `code`/`state`?
- **Error responses**: do any 4xx/5xx return stack traces, SQL, file paths, or
  raw exception strings to the client? generic 500 handler in prod? SQLAlchemy
  `echo` off? docs/OpenAPI disabled in prod?
- **Response leakage**: does any `response_model` serialize internal/sensitive
  fields (`password_hash`, `mfa_secret`, token hashes, `token_version`,
  `is_admin`, internal auto-increment `id`)? any route returning an ORM object
  without a response_model? admin schemas leaking into user routes?
- **Mass-assignment / over-posting**: can a request body set fields it shouldn't
  (`id`, `public_id`, `user_id`, `is_admin`, `status`, `is_shared`,
  `email_verified`)? any `Model(**payload)` / blind `setattr(**fields)` without a
  column allow/deny list? status/role fields validated via `Literal`/enum?
- **public_id discipline**: internal `id` never exposed where public_id should be
  (enumeration).

Read `core/*/schemas.py` (request + response), the routers' `response_model`
usage, the services that build ORM objects from payloads, the logging/observability
layer, and the middleware error handling.

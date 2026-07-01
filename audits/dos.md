# dos — rate limiting, cost, resource bounds, concurrency

Audit `packages/api` for denial-of-service, unbounded spend, and race conditions.

- **Rate limiting**: are auth/expensive routes rate-limited? per-IP AND
  per-account (a botnet rotating IPs shouldn't get unbounded attempts against one
  account)? fail-closed on the account-minting/secret-verifying routes? can the
  client IP be spoofed (X-Forwarded-For trust / `forwarded-allow-ips`) to rotate
  the identity?
- **Cost / LLM spend**: is every LLM/vision/STT route behind the cost-guard
  kill-switch? does the WORKER path (Taskiq) have equivalent metering, or is it an
  unmetered LLM-spend backdoor? are per-user budgets (IGDB, import) atomic
  (INCR-then-check, no TOCTOU)?
- **Resource bounds**: upload size caps enforced BEFORE buffering? image
  decompression-bomb guard (`Image.MAX_IMAGE_PIXELS`)? audio duration bounded
  BEFORE transcription (not just byte size)? pagination `limit`/`offset` bounded?
- **Concurrency / TOCTOU**: single-use / one-per-user invariants enforced by a
  conditional UPDATE + rowcount (or DB constraint), not check-then-write? Look at
  pick/capture/play_session state transitions, refresh rotation, MFA consume,
  quota counters, one-active-session, registration double-create.
- **Retry side effects**: are background-task retries idempotent (no double
  spend / duplicate rows / re-sent email)?

Read `api/v1/_rate_limit.py`, `api/v1/_cost_guard.py`, the capture/upload routes,
`infrastructure/cache/usage_counter.py`, and the state-transition repositories.

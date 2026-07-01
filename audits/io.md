# io — media pipeline, cache/Redis, worker, email

Audit `packages/api` I/O boundaries not covered elsewhere.

- **Media / uploads**: image decompression bombs (Pillow `MAX_IMAGE_PIXELS` +
  bomb-warning-as-error)? MIME validated by magic bytes, not trusted
  content-type? upload size capped before buffering? stored paths derived safely
  (UUID/tempfile, no user filename → no traversal)? audio duration bounded before
  Whisper? temp files cleaned up? HEIF/`pillow-heif` kept patched?
- **Redis / cache**: how are keys built — can attacker-controlled input (email,
  query, game title, thread_id) collide with or overwrite another user's counter/
  state/cache entry (delimiter injection)? are identities in the key typed/hashed
  and separated? anything sensitive stored at rest (raw tokens, TOTP secrets,
  PII)? security keys always set a TTL? deserialization JSON (not pickle/eval)?
  socket timeouts set so a hung Redis triggers the fail-mode branch?
- **Taskiq worker**: JSON serializer (not pickle → no broker-injection RCE)? do
  tasks re-scope IDs to their owner or trust a raw id (cross-user write via a
  forged message)? idempotent side effects on retry? errors leak data / leave
  half-mutated state?
- **Email / SMTP**: header injection via display_name/email into To/From/Subject
  (`\r\n`)? links built from server config (not the Host header → poisoning)?
  plaintext vs HTML (content injection)? reset/forgot an email-existence oracle?
  per-email rate limit (not just per-IP) so a victim can't be inbox-bombed?
  recipient always the DB email (no open-relay)? token logged?

Read `core/capture/ingestion.py` + the capture/STT/image infra,
`infrastructure/cache/*`, `infrastructure/tasks/*` + `workers/*`, and
`infrastructure/email/*`.

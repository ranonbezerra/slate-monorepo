# injection — SQL/ORM, SSRF, and input validation

Audit `packages/api` for injection and request-forgery.

- **SQL/ORM**: grep every place user/LLM input reaches a query. Any raw `text()`
  / `execute()` with interpolated input (f-string/format/%/+)? Every `.ilike()`/
  `.like()` — is `escape=` actually passed (else the wildcard escaping is a no-op
  → wildcard injection / query-DoS)? `ORDER BY`/sort from user input allowlisted?
  `LIMIT`/`OFFSET` bounded? pgvector params bound (not string-built)?
- **SSRF**: any server-side fetch of a user/LLM-influenced URL (deep-research
  scrape, IGDB, avatar, webhook)? is the resolved IP validated (reject
  private/loopback/link-local) AND pinned against DNS-rebinding? redirects
  disabled? SNI/Host preserved?
- **Command/template injection**: `subprocess`, `os.system`, `eval`, `exec`,
  Jinja `from_string` on user input?
- **Path traversal**: user-controlled filenames/paths in file reads/writes.
- **Input validation**: Pydantic bounds (max_length, ge/le) on free-text and
  numeric inputs; unbounded request bodies.

Read `infrastructure/db/repositories/*`, `infrastructure/research/*` (searxng),
`infrastructure/catalog/*` (igdb), and the admin search services.

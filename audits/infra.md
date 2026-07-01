# infra — CI/CD, Docker, compose, supply chain, dependencies

Audit deployment/pipeline security and the dependency surface (not app logic).

- **GitHub Actions** (`.github/workflows/*`): any `pull_request_target` running
  untrusted PR code with secrets? any `${{ github.event.* }}` interpolated
  directly into a `run:` block (script injection)? secrets echoed/logged?
  over-broad `permissions:`? deploy jobs reachable from forks? actions pinned to
  SHA vs floating tag (esp. anything with write scope)?
- **Docker**: container runs as non-root (`USER`)? secrets baked in (`COPY .env`,
  ARG secrets)? base image pinned, no `latest`? `FORWARDED_ALLOW_IPS` not `*`?
- **compose**: backing services (Postgres/Redis) not published to `0.0.0.0`?
  no weak/default passwords (`${VAR:?}` fail-closed)? pinned image digests?
  prod hardening (cap_drop, no-new-privileges, read-only rootfs)?
- **Secrets hygiene**: `.gitignore` covers `.env`; detect-secrets baseline; no
  committed secret with a dangerous default; SSH known-hosts pinned (no TOFU) for
  prod deploy.
- **Supply chain**: lockfiles committed (poetry.lock, bun.lock, pubspec.lock)?
  `--frozen-lockfile` in CI? any `curl | bash`?
- **Dependencies**: read `packages/api/pyproject.toml` + `poetry.lock` and
  `packages/web/*/package.json`; flag any version with a well-known CVE
  (python-multipart, pillow, cryptography, jinja2, requests/urllib3/aiohttp,
  starlette, python-jose). Run `bun audit` / `pip-audit` if available.

Read the workflows, Dockerfile(s), docker-compose*.yml, infra/, Makefile,
.gitignore, .secrets.baseline, and the manifests/lockfiles.

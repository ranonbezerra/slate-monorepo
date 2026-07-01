# web — frontend (player app + backoffice)

Audit `packages/web` (app = player, backoffice = admin, shared = @slate/shared)
for client/browser-side flaws. API-side is covered by other modules.

- **XSS**: any `dangerouslySetInnerHTML`, `innerHTML`, `document.write`, `eval`,
  `new Function`, or LLM/user content rendered as HTML (recaps, concierge output
  must be text nodes)?
- **Auth token storage**: access token in memory (good) vs localStorage
  (XSS-stealable)? refresh token an httpOnly cookie the JS never sees?
- **CSRF**: cookie-mode auth — is a custom header / SameSite the defense? any
  state-changing GET?
- **CSP / headers**: is a Content-Security-Policy set (build-time meta or server
  header)? clickjacking (`frame-ancestors`/X-Frame-Options) on backoffice?
- **Open redirect / postMessage / window.open** with user-controlled URLs (OAuth
  callback handling)?
- **Secrets in bundle**: any non-public secret baked into `VITE_*` / the client
  bundle? `.env` gitignored?
- **Deps**: obviously outdated/vulnerable frontend deps.

Read the `@slate/shared` api client + auth hooks, the recap/concierge rendering
components, the OAuth callback page, `index.html`, and the vite configs.

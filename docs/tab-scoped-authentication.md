# Tab-scoped SPA authentication

> This describes the intended/current Node session behavior. Django's
> server-rendered portal has been removed; routes not yet implemented in Node
> are unavailable. See
> [`../backend/docs/API_MIGRATION_STATUS.md`](../backend/docs/API_MIGRATION_STATUS.md).

The React application uses an independent API session for each browser tab. A
successful login issues a random bearer token, stores only its SHA-256 digest in
the PostgreSQL database, and returns the plaintext token once to the browser.
The SPA keeps that token in `sessionStorage` and sends it as an
`Authorization: Bearer` header.
The token expires after 14 days; signing out revokes only the token for the
current tab.

The API does not use a shared browser session cookie for authentication.

The login endpoint continues to require CSRF validation. The frontend obtains a
CSRF token before login; the bearer token is used only after authentication.
The Node API uses existing account/session tables. A complete schema migration
for a fresh PostgreSQL database is not included.

# Tab-scoped SPA authentication

The React application uses an independent API session for each browser tab. A
successful login issues a random bearer token, stores only its SHA-256 digest in
PostgreSQL, and returns the plaintext token once to the browser. The SPA keeps
that token in `sessionStorage` and sends it as an `Authorization: Bearer` header.
The token expires after 14 days; signing out revokes only the token for the
current tab.

The REST API does not use Django's shared browser session cookie for
authentication. A Django session cookie from a server-rendered portal therefore
does not authenticate React API requests. Server-rendered Django portal pages
still use Django's normal cookie session, which remains shared across tabs.

The login endpoint continues to require CSRF validation. The frontend obtains a
CSRF token before login; the bearer token is used only after authentication.
Apply the `accounts` migration before deploying this change.

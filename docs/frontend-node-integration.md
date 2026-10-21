# Frontend and Node API integration

All frontend API clients now target the Node API. In local development, Vite
proxies `/api` and `/media` to `http://127.0.0.1:3000`; set
`VITE_NODE_PROXY_TARGET` to override the Node origin. In production, the
default `/api/v1` and `/media` paths require a same-origin reverse proxy. For a
separate API origin, set `VITE_API_BASE_URL` when building the frontend.

Node currently implements health, registration/login/session foundations,
preferences and activity, public property browsing, property-type and amenity
options, property-image management, and storage reporting. The React app still
contains screens that call routes the Node API has not implemented. Since the
Django fallback has been removed, those calls receive 404 until the Node
replacements are developed and tested.

The route-by-route inventory and behavior gaps are in
[`../backend/docs/API_MIGRATION_STATUS.md`](../backend/docs/API_MIGRATION_STATUS.md).
Do not interpret an implemented route as production-certified: several
handlers have unit tests with mocked PostgreSQL, and actual hosting, database
compatibility, and end-to-end workflows remain unverified.

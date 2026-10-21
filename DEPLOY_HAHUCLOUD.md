# HahuCloud deployment (Node.js and PostgreSQL)

The deployable application is the Express API in `backend/` and the React/Vite
frontend in `frontend/`. The Django/Python application has been removed.
HahuCloud must provide a supported Node.js application runtime, PostgreSQL
connectivity, and persistent writable storage before this project can run
there. These provider capabilities have not been verified from this workspace.

## Check with HahuCloud first

Confirm that the account supports:

- Node.js 20 or newer and a process manager that runs `backend/src/server.js`
  with its assigned `PORT`.
- PostgreSQL connections from the Node application, including the provider's
  host, port, database, user, TLS requirements, and connection limits.
- Persistent writable directories for separate public and private media.
- HTTPS, the frontend/API origin arrangement, and outbound connections needed
  by the application.

If any of these are unavailable, do not upload or configure the app as though
it were deployable on that account. The former Python/Passenger configuration
is no longer part of this project.

## API deployment

Configure the Node application root as `backend/`, use Node 20+, install with
`npm ci`, and start with `npm start`. The server listens on `0.0.0.0:$PORT`.
Configure these variables in HahuCloud's private application environment;
never publish credentials in the frontend document root:

| Variable | Purpose |
| --- | --- |
| `NODE_ENV` | Set to `production`. |
| `DATABASE_URL` | PostgreSQL connection URL. Alternatively configure `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, and `PGPASSWORD`. |
| `PGSSL` | Set to `true` only when the PostgreSQL provider requires TLS. |
| `FRONTEND_ORIGINS` | Comma-separated, exact HTTPS origins allowed to call the API. |
| `CSRF_TRUSTED_ORIGINS` | Exact frontend origins allowed for CSRF-protected requests. |
| `MEDIA_ROOT` | Absolute persistent path for public property images. |
| `PRIVATE_MEDIA_ROOT` | Separate absolute persistent path for private originals. |
| `MEDIA_CAPACITY_BYTES` | Optional, provider-confirmed media allocation used for warnings. |

Production startup requires `MEDIA_ROOT` and `PRIVATE_MEDIA_ROOT`; the paths
must be separate, writable, outside the application release directory, and
persistent across restarts and deployments. Never expose the private media
directory through a static web server.

The health endpoint is `GET /api/v1/health/`. It returns an error if PostgreSQL
cannot be reached. Test it after the host starts the process.

## PostgreSQL readiness is a deployment blocker

The Node API currently queries the existing PostgreSQL table layout described
in [`backend/docs/POSTGRESQL_CATALOG_SNAPSHOT.md`](backend/docs/POSTGRESQL_CATALOG_SNAPSHOT.md).
This repository does not yet include a complete schema-creation migration for
a new empty PostgreSQL database. Its checked-in SQL migration only adds media
metadata, and that migration has not been applied. Do not point the API at an
empty database and assume it will initialize itself. Confirm the approved
database, schema, required grants, and migration plan; take and verify backups
before any schema or data change. Never use a superuser account for the app.

The PostgreSQL snapshot and earlier local inspection are not proof that any
particular HahuCloud database is authoritative or compatible. No database,
media, DNS, or production deployment changes are authorized by this guide.

## Frontend deployment

Build the frontend with Node.js and npm:

```powershell
Set-Location 'frontend'
npm ci
npm run build
```

Publish the contents of `frontend/dist` to the frontend document root. By
default, the browser calls `/api/v1` and `/media` on the same origin, so
configure a same-origin reverse proxy to the Node service. If the API is
hosted on a separate origin, set `VITE_API_BASE_URL` to its full
`https://api.example.com/api/v1` URL at build time, and set both API origin
allow-lists to the exact frontend origin. Prefer an API hostname under the
frontend's site; unrelated domains may block the `SameSite=Lax` CSRF cookie
needed by login.

Configure the frontend host's SPA fallback so application routes serve
`index.html`. Do not publish `.env` files, database credentials, private media,
or backend source files to the public document root.

## Feature coverage

Removing Django also removes routes that Node has not implemented yet. The
frontend still contains features that call those routes; they will return 404
until equivalent Node handlers and PostgreSQL tests are added. Check
[`backend/docs/API_MIGRATION_STATUS.md`](backend/docs/API_MIGRATION_STATUS.md)
before enabling the site for users. Do not treat a successful health check or
frontend build as full application readiness.

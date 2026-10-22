# HahuCloud deployment (Node.js and PostgreSQL)

The deployable application is the Express API in `backend/` and the React/Vite
frontend in `frontend/`. The Django/Python application has been removed.
HahuCloud must provide a supported Node.js application runtime, PostgreSQL
connectivity, and persistent writable storage before this project can run
there. These provider capabilities have not been verified from this workspace.
The intended existing HahuCloud database was reported as PostgreSQL 13.12.
PostgreSQL 13 reached upstream end-of-life on November 13, 2025. The deployment
preflight will block that version; arrange a provider-supported PostgreSQL
upgrade (15 or newer) before production. A major-version upgrade must follow
HahuCloud's documented procedure and a verified backup/restore plan.
See the upstream [PostgreSQL versioning policy](https://www.postgresql.org/support/versioning/).

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
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_SECURE` | SMTP host, port (587 by default), and direct-TLS setting. |
| `SMTP_USER`, `SMTP_PASS` | Private SMTP credentials. |
| `EMAIL_FROM` | Verified sender address. |
| `FRONTEND_URL` | Exact HTTPS frontend origin used to create email links. |

Production startup requires `MEDIA_ROOT` and `PRIVATE_MEDIA_ROOT`; the paths
must be separate, writable, outside the application release directory, and
persistent across restarts and deployments. `npm run check:deployment`
validates the local path properties but cannot confirm provider persistence.
Never expose the private media directory through a static web server.

The health endpoint is `GET /api/v1/health/`. It returns an error if PostgreSQL
cannot be reached. Test it after the host starts the process.

## Existing PostgreSQL database readiness

The deployment target is an existing database, not a new empty database. The
Node API expects the prior application's PostgreSQL schema and does not
initialize it. The catalog snapshot in
[`backend/docs/POSTGRESQL_CATALOG_SNAPSHOT.md`](backend/docs/POSTGRESQL_CATALOG_SNAPSHOT.md)
is from a different, local PostgreSQL 18.6 candidate; it is not evidence about
the HahuCloud database. Compare the actual target schema and grants before
deployment.

Run the read-only database and media preflight from the backend after setting
the private production environment:

```powershell
Set-Location backend
npm ci
$env:NODE_ENV = 'production'
npm run check:deployment
```

The check verifies PostgreSQL reachability/version, a non-superuser application
role with the required core table privileges, required existing tables,
complete SMTP configuration, and that the separate public/private media
directories exist, are writable, and are outside the release directory. It
does not change the database, send mail, or prove that provider volumes survive
a restart; confirm persistence with HahuCloud and a staging restart test.

The additive `001_media_file_metadata.sql` migration depends on the existing
`user_propertyimage` table and creates `backend_media_file_metadata`. It is not
applied automatically. Before applying it, compare the target catalog, back up
the database, restore-test that backup on the same PostgreSQL major version,
and run the migration against the isolated restore first. Review the migration
plan and use a dedicated non-superuser schema-migration role. From `backend/`,
`npm run migrate` performs a no-DDL preflight; only `npm run migrate -- --apply`
applies the versioned, checksummed migration. Configure the dedicated role with
`MIGRATION_DATABASE_URL` only for this controlled step; it needs `CREATE` on
`public` and `REFERENCES` on `public.user_propertyimage`. Set
`APPLICATION_DATABASE_ROLE` if the migration should grant that non-superuser
app role access to the new metadata table. The web process never runs
migrations automatically. Never use a superuser account for the app or
migration.

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

Node handlers now cover the documented legacy API paths and methods. Backend
tests exercise the workflows with mocked PostgreSQL; they do not certify
compatibility with the HahuCloud schema or production data. Review
[`backend/docs/API_MIGRATION_STATUS.md`](backend/docs/API_MIGRATION_STATUS.md)
and complete the PostgreSQL upgrade/schema preflight, SMTP verification, and
persistent-media restart test before enabling the site for users. A successful
health check or frontend build alone is not full application readiness.

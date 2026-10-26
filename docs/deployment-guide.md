# Deployment guide

This is a preparation guide, not authorization to deploy. The frontend and
backend have separate artifacts, configuration, and release checks. HahuCloud
runtime capabilities, cPanel document root, PostgreSQL target/schema, TLS
termination, persistent media mounts, and email delivery must be confirmed
with the provider and owner before a release.

The current deployment notes describe PostgreSQL 13.23 as a temporary hosting
compatibility exception; PostgreSQL 13 is upstream end-of-life. An older
HahuCloud note records a different minor version, so confirm the actual
provider version rather than treating either note as authoritative. No
isolated PostgreSQL 13 integration test has been completed.

## Release prerequisites

1. Review the current Git changes and approve exactly which files are part of
   the release. Preserve unrelated local changes.
2. Confirm the Node.js 20+ runtime, API process manager, PostgreSQL endpoint
   and supported version, database grants/schema, TLS, proxy routing, outbound
   SMTP, and persistent writable storage with HahuCloud.
3. Use an existing, verified application database. There is no complete
   migration for an empty database.
4. Back up PostgreSQL and both public and private media roots together, and
   test restoration into an isolated database and separate media location.
5. Complete the handover test matrix on staging. Never use the live database
   for local builds or tests.

## Frontend release

From `frontend/`:

```powershell
npm ci
npm run build
```

The build runs TypeScript, Vite, and public/private route prerendering. Upload
the **contents** of `frontend/dist/` to the owner-confirmed cPanel document
root. The build output includes `index.html`, static assets, `.htaccess`,
`robots.txt`, and `sitemap.xml`. Do not upload the source `.env` files,
backend source, database files, private media, or unreviewed archives to the
public document root.

The frontend defaults to `/api/v1`. When using a different API origin, set
`VITE_API_BASE_URL` at build time to the API base URL and confirm backend
`FRONTEND_ORIGINS` and `CSRF_TRUSTED_ORIGINS` match the exact frontend origin.
The configured API hostname is on a different registrable domain from the
website; credentialed cookies may be affected by browser third-party-cookie
policies. This requires staging verification.

The frontend `.htaccess` contains SPA fallback and HTTP/www canonical redirect
rules. cPanel must support `mod_rewrite` and honor HTTPS state correctly. A
TLS-terminating proxy that reports the backend connection as HTTP can cause a
redirect loop if the rule is not adapted to the provider's supported
configuration. Do not add a second competing redirect rule without reviewing
the effective chain.

The repository's `render.yaml` is a separate Render free-service example and
does not provision persistent media storage. It is not the HahuCloud/cPanel
deployment configuration.

## Backend release

Configure the backend as a Node application rooted at `backend/`, install with
`npm ci`, and start with `npm start`. The server listens on the assigned
`PORT` and exposes `GET /api/v1/health/`. Keep all backend variables in the
private application environment, never in the document root or frontend
bundle.

Required settings depend on topology. The backend supports `DATABASE_URL` or
the `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD` settings.
Configure `NODE_ENV`, `FRONTEND_ORIGINS`, `CSRF_TRUSTED_ORIGINS`,
`MEDIA_ROOT`, and `PRIVATE_MEDIA_ROOT`; production requires separate absolute
persistent media roots outside the release directory. SMTP-dependent flows
also require `SMTP_HOST`, `SMTP_PORT`, `SMTP_SECURE`, `SMTP_USER`, `SMTP_PASS`,
`EMAIL_FROM`, and `FRONTEND_URL`. Optional/runtime settings are listed in
[`../backend/.env.example`](../backend/.env.example) and the root
[README](../README.md).

Do not run SQL changes during process startup. `npm run check:deployment` is a
readiness preflight but requires a database connection and configured media;
only run it against a confirmed staging/target environment. The
`001_media_file_metadata.sql` migration is additive but not applied. It must
be tested on an isolated restore and explicitly approved before
`npm run migrate -- --apply`.

## Redirect and SEO verification

After an approved staging or production release, test a bounded redirect chain
for `http://infinityhouseproperties.com/`,
`http://www.infinityhouseproperties.com/`,
`https://www.infinityhouseproperties.com/`, and
`https://infinityhouseproperties.com/`. Each should end at the HTTPS
non-www canonical origin without a repeated URL or excessive redirects. For
example, use `curl -sSIL --max-redirs 5 <URL>` and inspect each `Location`
header. Do not use automatic follow mode with an unbounded limit.

Then verify the four public pages, their title/description/canonical/robots
metadata, the four-URL sitemap, private-route noindex metadata, static assets,
login/API calls, and a direct nested-route reload. Verify the API health route
and representative authorized/unauthorized actions in staging. Confirm public
media survives restart and private originals are not publicly reachable.

No production redirects, APIs, cPanel files, database, or media were changed
or tested during handover preparation.

## Rollback

Roll back application code by restoring the previously verified frontend
build and backend release. Do not restore a database backup over live data as
a routine code rollback, and do not delete media created by the release.
Investigate and reconcile writes separately. See the
[backend rollback plan](../backend/docs/ROLLBACK.md).

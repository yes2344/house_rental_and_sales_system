# System verification and current readiness

## Result

**The deployable source is Node.js/PostgreSQL only, but feature migration and
production readiness remain incomplete.** Django source and runtime
configuration have been removed. The React frontend now sends requests to
Node; routes without a Node handler return 404. The historical 73-route
coverage inventory is in
[`API_MIGRATION_STATUS.md`](./API_MIGRATION_STATUS.md); route-by-route UI
notes are in [`../../docs/frontend-node-integration.md`](../../docs/frontend-node-integration.md).

## Executed checks

| Area | Evidence | Result |
|---|---|---|
| Node automated tests | Run `npm test` in `backend/` before release. Tests cover validators, mocked account/session flows, role serialization limits, public property query behavior, transaction helper commit/rollback, and isolated local-media tests. | **Unit tests only.** They do not exercise all routes or a live database. |
| React type check and production build | Run `npm run build` in `frontend/` after frontend changes. | **Build does not establish API feature parity.** |
| Browser property browsing | Prior local browser smoke check loaded the homepage and one property detail from the Node API. Detail gallery had 7 images; 8 page images loaded and 0 were broken. | **Partial pass.** This was not a full browser suite or cross-role test. |
| Previous browser/API gap evidence | Earlier Vite logs showed requests to `homepage-notes`, `brokerage/contact`, `auth/me`, and `locations` refused at `127.0.0.1:8000`. | **Historical.** Missing handlers must now be implemented in Node; Django is no longer available. |
| Previous Python/Django system check | The prior check failed because the configured MySQL endpoint refused the connection. | **Not applicable to the current source tree.** There is no Python app or MySQL client requirement. |
| PostgreSQL backup archive | The documented custom-format backup exists, is 166,644 bytes, has SHA-256 `e4dc4ff9bc0569037c5ac2c6279a72b617ccdaf4357f9d42f7dac681ab58d69d`; PostgreSQL 18 `pg_restore --list` succeeded and indexed 321 archive objects. Prior preparation documented a restore to a separate verification database with 34 tables and 955 aggregate rows matching the source. | **Archive verified; prior restore evidence available.** No restore was repeated during this verification. |
| PostgreSQL compatibility | The inspected candidate is PostgreSQL 18.6. | **PostgreSQL 13 unverified.** |
| Current DB/data reconciliation | The PostgreSQL candidate is not confirmed as the authoritative production database. No migration writes were run. | **Not verified.** Existing-user/property/viewing-request counts and relationships were not compared before and after a migration. |
| Media | Prior local media audit recorded 152 referenced files decoding successfully. Automated upload tests use isolated temporary storage and mocked PostgreSQL. | **Partial.** Persistence across a real server restart and coordinated media/database restore were not tested in this run. |
| API roles and security | Unit tests cover session/CSRF rejection, permission serialization, image object access, invalid images, and validation cases. | **Partial.** No complete admin/agent/owner/customer allowed-and-denied API matrix was run against a live database. |
| Full-stack restart and write flows | PostgreSQL credentials are not configured in `backend/.env`; the Node and Vite services are stopped. The candidate credentials are intentionally not reused for write-capable integration tests. | **Not run.** Create/update/delete, duplicate submissions, concurrent updates, persistence after restart, and endpoint-level rollback remain unverified. |

The root has no `package.json`; run Node and frontend commands from their
respective package directories.

## Node endpoint and module inventory

The mounted route definitions are in [`../src/routes/index.js`](../src/routes/index.js).
Current route groups include:

- `GET /api/v1/health/`
- `GET /api/v1/amenities/`
- `GET /api/v1/property-types/`
- `GET /api/v1/properties/` and `GET /api/v1/properties/:slug/`
- `GET /api/v1/auth/csrf/`, `POST /api/v1/auth/register/`,
  `POST /api/v1/auth/login/`, `POST /api/v1/auth/logout/`,
  `GET/PATCH /api/v1/auth/me/`, `GET/PATCH /api/v1/auth/preferences/`,
  `POST /api/v1/auth/preferences/reset/`, and
  `GET /api/v1/auth/activity/`
- Property/submission image routes under
  `/api/v1/management/properties/:propertyId/images/`,
  `/api/v1/management/properties/:propertyId/images/:imageId/`,
  `/api/v1/submissions/:submissionId/images/`, and
  `/api/v1/management/images/:imageId/original/`

The backend is organized under `backend/src/` into routes, controllers,
services, validators, middleware, configuration, and PostgreSQL access. This
route list is not feature parity: numerous routes from the previous API have
no Node replacement, and several mounted operations lack live database
integration tests.

## Page, role, and test coverage

See the detailed route table in
[`API_MIGRATION_STATUS.md`](./API_MIGRATION_STATUS.md).
Only the public home/property browse and one property detail have browser smoke
evidence. Login, registration, logout, account settings, submission flows,
viewings, favorites, all management pages, and protected actions have not had
full browser tests. Administrator, agent, owner, and public-user direct API
authorization has not been exhaustively verified. A route guard in React is
not proof of backend authorization.

## Data safety, backup, and rollback

- Backup: `C:\Users\computer\AppData\Local\InfinityHouse\migration-backups\infinity-house-debre_markos_real_estate-2026-10-20T15-05-31-556Z-1512.dump`
- Backup SHA-256: `e4dc4ff9bc0569037c5ac2c6279a72b617ccdaf4357f9d42f7dac681ab58d69d`
- The previous preparation restored this backup to a separate verification
  database, not over the candidate. It did not validate PostgreSQL 13, media
  files, or authority of the candidate as production.
- No destructive schema changes or source-database writes were made for this
  verification.
- Follow [`ROLLBACK.md`](./ROLLBACK.md) for application-release recovery.
  Django is no longer included. Keep verified database/media backups and do
  not confuse a code rollback with a data restore.

## Local commands

Use an approved disposable PostgreSQL database restored from the verified
backup. Do not point the write-capable backend at production or at the
unconfirmed candidate. Copy the secret-free template and set its values
locally; do not commit `backend/.env`.

```powershell
Set-Location 'D:\reacttrain\house sales and rental management system\backend'
Copy-Item .env.example .env
# Edit backend\.env with approved disposable DB credentials and media paths.
npm ci
npm test
npm start
```

In a second terminal:

```powershell
Set-Location 'D:\reacttrain\house sales and rental management system\frontend'
npm ci
npm run dev
```

The backend template is [`../.env.example`](../.env.example). It contains
variable names and local-development defaults only; provide PostgreSQL 13
connection details, allowed frontend/CSRF origins, and persistent
`MEDIA_ROOT`/`PRIVATE_MEDIA_ROOT` paths through local or server environment
settings. The React production validation command is `npm run build`.

## Cutover blockers

1. Implement and test every frontend-used API operation that is still pending
   in Node. The 73-route inventory enumerates the outstanding areas; there is
   no Django fallback.
2. Confirm the authoritative source database, establish a least-privilege Node
   role, and run reconciliation against a disposable restored copy.
3. Validate schema/migration behavior and restore compatibility on PostgreSQL
   13; test constraints, relationships, sequence values, and transaction
   behavior on that target.
4. Test API success, validation, unauthenticated access, insufficient
   permissions, missing objects, database outages, duplicates, concurrency,
   and rollback for each relevant endpoint.
5. Run page-by-page desktop/mobile browser and direct-API role tests for
   administrator, agent, owner, and public-user roles.
6. Verify full-stack create/update/delete and persistence after backend
   restart using disposable data, including physical media and database
   references.
7. Resolve the explicitly sample-labelled property records with the data
   owner; do not silently delete or rewrite them.
8. Provision persistent media storage and backup/restore on the actual
   deployment target. The configured deployment must not lose uploads on
   restart.

Until these blockers are cleared and the results documented, production
deployment is unsafe.

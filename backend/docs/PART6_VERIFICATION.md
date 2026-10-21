# Part 6 system verification

## Result

**Migration verification is incomplete; Django must not be removed.** This
branch is still a split application. The React frontend uses Node only for
public property-type options, property search/listing, property details, and
public property images. Many authentication, location, account, viewing,
submission, dashboard, management, and branding operations still use Django.
The complete 73-route replacement inventory is in
[`API_MIGRATION_STATUS.md`](./API_MIGRATION_STATUS.md); route-by-route UI
evidence is in [`../../docs/frontend-node-integration.md`](../../docs/frontend-node-integration.md).

## Executed checks

| Area | Evidence | Result |
|---|---|---|
| Node automated tests | `npm test` in `backend/`; 36 tests passed, 0 failed. Tests include validators, mocked account/session flows, role serialization limits, public property query behavior, transaction helper commit/rollback, and isolated local-media tests. | **Pass for these unit tests.** They do not exercise all routes or a live database. |
| React type check and production build | `npm run build` in `frontend/`; TypeScript and Vite completed successfully. | **Pass.** |
| Browser property browsing | Prior local browser smoke check loaded the homepage and one property detail from the Node API. Detail gallery had 7 images; 8 page images loaded and 0 were broken. | **Partial pass.** This was not a full browser suite or cross-role test. |
| Browser requests still assigned to Django | Vite logs showed requests to `homepage-notes`, `brokerage/contact`, `auth/me`, and `locations` refused at `127.0.0.1:8000`. | **Fail in the observed setup.** The Django service was not running; other routes were not tested. |
| Django system check | `python manage.py check` with the repository virtual environment failed because Django's configured MySQL endpoint at `127.0.0.1` refused the connection (`MySQLdb.OperationalError`, error 2002). | **Blocked.** No Django test suite was run because it could create a test database against an unverified MySQL target. |
| PostgreSQL backup archive | The documented custom-format backup exists, is 166,644 bytes, has SHA-256 `e4dc4ff9bc0569037c5ac2c6279a72b617ccdaf4357f9d42f7dac681ab58d69d`; PostgreSQL 18 `pg_restore --list` succeeded and indexed 321 archive objects. Prior preparation documented a restore to a separate verification database with 34 tables and 955 aggregate rows matching the source. | **Archive verified; prior restore evidence available.** No restore was repeated during this verification. |
| PostgreSQL compatibility | The inspected candidate is PostgreSQL 18.6. | **PostgreSQL 13 unverified.** |
| Current DB/data reconciliation | The PostgreSQL candidate is not confirmed as the authoritative production database. No migration writes were run. | **Not verified.** Existing-user/property/viewing-request counts and relationships were not compared before and after a migration. |
| Media | Prior local media audit recorded 152 referenced files decoding successfully. Automated upload tests use isolated temporary storage and mocked PostgreSQL. | **Partial.** Persistence across a real server restart and coordinated media/database restore were not tested in this run. |
| API roles and security | Unit tests cover session/CSRF rejection, permission serialization, image object access, invalid images, and validation cases. | **Partial.** No complete admin/agent/owner/customer allowed-and-denied API matrix was run against a live database. |
| Full-stack restart and write flows | PostgreSQL credentials are not configured in `backend/.env`; the Node and Vite services are stopped. The candidate credentials are intentionally not reused for write-capable integration tests. | **Not run.** Create/update/delete, duplicate submissions, concurrent updates, persistence after restart, and endpoint-level rollback remain unverified. |

The initial `npm` invocation from the repository root failed because the root
has no `package.json`; rerunning the commands from `backend/` and `frontend/`
produced the passing results above.

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
route list is not feature parity: numerous Django routes have no Node
replacement, and several mounted operations lack live database integration
tests.

## Page, role, and test coverage

See the detailed route table in
[`../../docs/frontend-node-integration.md`](../../docs/frontend-node-integration.md).
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
- Follow [`ROLLBACK.md`](./ROLLBACK.md) for recovery. Keep Django, its
  migrations, the original deployment configuration, and backups until
  parity, reconciliation, and an approved cutover have passed.

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

1. Implement and test every frontend-used Django operation in Node. The browser
   integration map and 73-route inventory enumerate the outstanding areas.
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

Until these blockers are cleared and the results documented, Django removal
and production cutover are unsafe and are not performed.

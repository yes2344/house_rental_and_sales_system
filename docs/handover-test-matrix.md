# Handover test matrix

Verification performed locally on 2026-10-24. Backend unit/workflow tests
completed with a deliberately invalid local database URL so tests could not
connect to a configured database. No production endpoint, database, SMTP
service, or hosted media volume was tested.

| Area | Automated/local evidence | Handover acceptance still required |
|---|---|---|
| Public pages | Production frontend build passed. Generated Home, About, Contact, and Property Management HTML matched configured title, description, canonical, and `index, follow`. | Verify pages and assets load through cPanel and inspect rendered content. |
| Private/account pages | Explicit private routes and the shared dynamic-route fallback generate `noindex, follow` without canonicals. Apache rewrite rules route `/submissions/*` and `/management/listings/*` to that fallback before generic SPA handling. | Verify cPanel honors the rewrite rules and live pages remain protected by authentication; robots metadata alone is not access control. |
| Sitemap and robots | Build output contains `robots.txt` and `sitemap.xml`; sitemap has exactly four configured public canonical URLs. | Fetch both from the deployed site and confirm search-engine access/host configuration. |
| Login, registration, password reset | Backend auth/email unit and workflow tests passed in the 128-test suite. | Browser tests against staging, SMTP delivery, cross-origin cookies, and real DB schema. |
| Property search/details | Backend property/API tests are present; production build passed. Some tests use mocked SQL, with prior local read-only DB coverage documented. | Search/filter behavior against staging schema and actual listings. |
| Property creation/publication | Managed-property and admin workflow tests are present; full backend suite passed. | Create/review/publish using staging accounts and confirm role scope and persistence. |
| Image upload/replacement | Six focused property-image tests passed as part of the suite, using temporary filesystem and mocked PostgreSQL. | Upload limits through host/proxy, persistent volume across restart, visible watermark, and public/private access controls on staging. |
| Owner submissions | Submission workflow tests passed with mocked database behavior. | Browser flow, review/assignment, and attachment persistence on staging. |
| Viewing requests | Workflow tests exist and passed in the full suite; current API status lists Node handlers. | End-to-end customer/agent transitions, notifications, timezone, and DB constraints on staging. |
| Administrator permissions | Tests cover administrator-only routes and selected allow/deny cases. | Verify least-privilege matrix using real staging roles and ensure no cross-account data leakage. |
| Agent permissions | Tests cover agent scope and selected denial/approval flows. | Verify city/assignment scope and role transitions in staging. |
| API connectivity | Unit tests exercise the health handler and CORS/CSRF behavior. A deployment-readiness command using workspace configuration timed out; target identity is unverified. | Verify actual API DNS/TLS, database reachability, CORS/CSRF, health, and frontend integration in confirmed staging. |
| Database operations | Transaction, migration, inspection, and readiness logic have unit tests; all 128 backend tests passed. | Verify actual schema/grants/version, isolated restore, migration, backup, restore, and representative workflows on staging. |
| Redirects | Local `.htaccess` rules were inspected; no live HTTP requests or cPanel configuration changes were made. | Check HTTP/www variants, TLS proxy behavior, and bounded redirect chains in staging/production. |
| Frontend tests | No separate frontend test script is defined; `npm run build` passed. | Add/execute browser acceptance checks for critical workflows before sign-off. |

## Run locally

```powershell
Set-Location frontend
npm ci
npm run build

Set-Location ..\backend
npm ci
npm test
```

For backend tests, ensure the process cannot inherit production credentials.
The recorded run used a non-routable test database URL. Do not run migration,
bootstrap, inspection, readiness, or cleanup commands until the database
target is confirmed; some of those commands connect to the configured database.

## Known evidence gaps

- No PostgreSQL integration test against HahuCloud's actual schema/version was
  performed.
- No production deployment, browser/API end-to-end run, email send, or media
  persistence/restore was performed.
- Dynamic private routes under `/submissions/` and `/management/listings/`
  are served a generated `private-route-fallback.html` with `noindex, follow`
  before React loads. The `.htaccess` rules were checked in the local build,
  but their behavior still needs cPanel/Apache staging verification.
- The deployment-readiness check was inadvertently invoked with `--help`
  (which is not a supported help mode) and timed out while using the workspace
  backend environment. No database write was requested or made; the configured
  endpoint's identity was not inspected and remains unknown.
- Existing documentation is inconsistent in places: the image migration
  guide describes dynamic branding and says upload metadata needs no schema,
  while current source uses a fixed watermark and writes to
  `backend_media_file_metadata`; the checked-in migration README says that
  table's migration is pending. Older viewing/admin guides also describe
  workflows as unavailable or historical while the current API status lists
  Node handlers. Reconcile these docs with the owner before relying on those
  older descriptions.

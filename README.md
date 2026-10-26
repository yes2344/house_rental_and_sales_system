# Infinity House Properties

Infinity House Properties is a real-estate website with a React/Vite frontend,
a Node.js/Express API, and PostgreSQL storage. The current deployment target is
HahuCloud/cPanel, but the provider's Node runtime, database connectivity, TLS
behavior, and persistent media storage have not been verified from this
workspace.

## Project map

- `frontend/` — React application, Vite configuration, page metadata, public
  static assets, route prerendering, and `.htaccess` rules.
- `backend/` — Express API, authentication and authorization, property and
  image workflows, SQL migration utilities, and automated tests.
- `backend/db/migrations/` — reviewed SQL migrations for an existing schema;
  this is not a complete schema bootstrap for a new database.
- `docs/` — product, development, and deployment documentation.
- `backend/docs/` — database, API coverage, migration, media, and rollback
  evidence.
- `google-indexing-package/` — robots and sitemap source files consumed by the
  frontend prerender build.

The repository also contains ignored local artifacts and legacy directories.
They are not a substitute for the current React/Node application and must not
be copied into a handover or deployment package without a separate review.

## Runtime and dependencies

- Node.js 20 or newer and npm are required for both applications.
- PostgreSQL must have the established application schema. No supported
  empty-database bootstrap is included.
- Frontend dependencies and exact lockfile are in `frontend/package.json` and
  `frontend/package-lock.json`.
- Backend dependencies and exact lockfile are in `backend/package.json` and
  `backend/package-lock.json`.
- Python is not required to build or run the current frontend/backend.

Install and check locally:

```powershell
Set-Location frontend
npm ci
npm run build

Set-Location ..\backend
npm ci
npm test
```

The backend tests are Node's built-in test runner. Frontend `package.json`
defines a production build but no separate frontend test command. Never point
local development or test commands at production data.

## Configuration names

Set values in private runtime environments only. Do not publish or commit
values:

- Backend database: `DATABASE_URL`, or `PGHOST`, `PGPORT`, `PGDATABASE`,
  `PGUSER`, `PGPASSWORD`; optional `PGSCHEMA`, `PGSSL`, and
  `PGSSL_REJECT_UNAUTHORIZED`.
- Backend runtime and browser security: `NODE_ENV`, `PORT`,
  `FRONTEND_ORIGINS`, `CSRF_TRUSTED_ORIGINS`.
- Backend email: `SMTP_HOST`, `SMTP_PORT`, `SMTP_SECURE`, `SMTP_USER`,
  `SMTP_PASS`, `EMAIL_FROM`, `FRONTEND_URL`.
- Persistent media: `MEDIA_ROOT`, `PRIVATE_MEDIA_ROOT`,
  `MEDIA_CAPACITY_BYTES`, `MEDIA_WARNING_PERCENT`.
- Explicit schema migration: `MIGRATION_DATABASE_URL`,
  `APPLICATION_DATABASE_ROLE`.
- One-time platform-owner bootstrap: `PLATFORM_OWNER_USERNAME`,
  `PLATFORM_OWNER_EMAIL`, `PLATFORM_OWNER_PASSWORD`,
  `PLATFORM_OWNER_BOOTSTRAP_CONFIRM`.
- Frontend build: `VITE_API_BASE_URL`; local Vite proxy:
  `VITE_NODE_PROXY_TARGET`.

See [`backend/.env.example`](./backend/.env.example) and
[`frontend/.env.example`](./frontend/.env.example) for variable descriptions.
Never include real `.env` files in a source package or frontend document root.

## Guides and evidence

- [Administrator guide](./docs/administrator-guide.md)
- [Agent guide](./docs/agent-guide.md)
- [Customer guide](./docs/customer-guide.md)
- [Deployment guide](./docs/deployment-guide.md)
- [Handover test matrix](./docs/handover-test-matrix.md)
- [HahuCloud deployment notes](./DEPLOY_HAHUCLOUD.md)
- [API migration/coverage status](./backend/docs/API_MIGRATION_STATUS.md)
- [Database migration policy](./backend/db/migrations/README.md)
- [Backup and media recovery](./backend/docs/LOCAL_MEDIA_MIGRATION.md)
- [Rollback plan](./backend/docs/ROLLBACK.md)

These documents describe repository evidence, not a production certification.
Some older workflow documents still describe historical behavior; check the
API coverage status and handover test matrix before relying on a workflow.
The frontend and backend have not been end-to-end tested against the HahuCloud
database, runtime, email provider, or media volumes.

## Handover package exclusions

Include reviewed source, lockfiles, tests, migrations, guides, and required
public assets. Exclude `.env` files except the blank `.env.example` templates,
database dumps, SQLite databases, public/private media, private originals,
`node_modules`, `.venv`, caches, `frontend/dist` from the source package, and
unreviewed ZIP archives. Treat a frontend production build as a separate
deployment artifact, not as a source archive. No handover archive has been
created.

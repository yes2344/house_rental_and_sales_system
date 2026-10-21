# Local development

## Requirements

- Node.js 20 or newer
- PostgreSQL with the application schema described in
  [`backend/docs/POSTGRESQL_CATALOG_SNAPSHOT.md`](../backend/docs/POSTGRESQL_CATALOG_SNAPSHOT.md)

The repository does not create a complete schema for a new empty PostgreSQL
database yet. Use only a database that has been separately prepared and
approved for development. Never point local development at a production
database.

## Start the API

Copy `backend/.env.example` to `backend/.env` and configure either
`DATABASE_URL` or the `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, and
`PGPASSWORD` values. Keep credentials in the ignored `.env` file.

```powershell
Set-Location 'D:\reacttrain\house sales and rental management system\backend'
npm ci
npm test
npm start
```

The API listens on `http://127.0.0.1:3000` by default and checks PostgreSQL at
`http://127.0.0.1:3000/api/v1/health/`. Production mode additionally requires
separate absolute `MEDIA_ROOT` and `PRIVATE_MEDIA_ROOT` directories. Local
defaults use the workspace `media` and `private-media` folders.

## Start the frontend

In a second terminal:

```powershell
Set-Location 'D:\reacttrain\house sales and rental management system\frontend'
npm ci
npm run dev
```

Vite proxies `/api` and `/media` to Node at `http://127.0.0.1:3000`. Set
`VITE_NODE_PROXY_TARGET` in the frontend environment to change that target.
For a frontend hosted separately from the API, set `VITE_API_BASE_URL` to the
API's full `/api/v1` URL and configure the backend's `FRONTEND_ORIGINS` and
`CSRF_TRUSTED_ORIGINS` to the frontend's exact origin.

## Current API coverage

The frontend now sends API requests to Node; Django is no longer a fallback.
Some frontend features still call routes that have not been implemented in
Node, so those features will return 404. See
[`backend/docs/API_MIGRATION_STATUS.md`](../backend/docs/API_MIGRATION_STATUS.md)
before relying on account verification, password reset, favorites, viewing
requests, management, or other pending features. Node tests exercise current
handlers with isolated storage or mocked PostgreSQL; they do not certify a
production database or full feature parity.

For the existing media audit, storage behavior, and backup guidance, see
[`backend/docs/LOCAL_MEDIA_MIGRATION.md`](../backend/docs/LOCAL_MEDIA_MIGRATION.md).

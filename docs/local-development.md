# Local development

## Backend

The local `.env` in this development setup is configured for an isolated
MySQL 8.4.9 server on `127.0.0.1:3307`. It uses a new data directory under
`%LOCALAPPDATA%\InfinityHouse\mysql84`; it does not replace or modify the
separate XAMPP MariaDB instance on port 3306. Keep the MySQL server terminal
open while using Django. Start it in PowerShell with:

```powershell
$mysqlHome = Join-Path $env:LOCALAPPDATA 'InfinityHouse\mysql84\mysql-8.4.9-winx64'
$mysqlData = Join-Path $env:LOCALAPPDATA 'InfinityHouse\mysql84\data'
& "$mysqlHome\bin\mysqld.exe" --no-defaults `
  "--basedir=$mysqlHome" "--datadir=$mysqlData" `
  --port=3307 --bind-address=127.0.0.1 --mysqlx=0 `
  --character-set-server=utf8mb4 --collation-server=utf8mb4_0900_ai_ci `
  --sql-mode=STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION `
  --console
```

For a different computer, install MySQL 8.4 or newer, create a database and a
least-privilege application user, then set `MYSQL_DATABASE`, `MYSQL_USER`,
`MYSQL_PASSWORD`, `MYSQL_HOST`, and `MYSQL_PORT` in the ignored project-root
`.env`. Copy `.env.example` only if `.env` does not already exist; never commit
`.env`.

Activate the virtual environment and start Django:

```powershell
.\.venv\Scripts\Activate.ps1
python manage.py check
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

The local database for this setup has already been migrated and is empty.
Create a local administrator if you want to test Django admin:

```powershell
python manage.py createsuperuser
```

Development and production both require explicit MySQL settings; there is no
SQLite or PostgreSQL fallback. Keep local `.env` pointed at the local database
so development commands cannot modify a hosted database.

## Frontend

In a second PowerShell terminal:

```powershell
Set-Location 'D:\house sales and rental management system\frontend'
npm run dev
```

The frontend's existing API proxy targets Django at
`http://127.0.0.1:8000` by default. Public property listings, detail pages,
and property-type options use the Node API at `http://127.0.0.1:3000` through
the `/node-api` Vite proxy. Configure Node's database connection before
starting Vite if those pages are to show PostgreSQL-backed listings.

## Node.js and PostgreSQL migration

The Node API is being introduced alongside Django so each feature can be
verified before traffic is moved. Django remains the active frontend API.
Node currently implements its health endpoint, account/session foundations,
public property browsing, and property-image storage endpoints. The frontend
uses Node for public property browsing and still uses Django for authentication
and other routes that do not yet have Node replacements; see
[`backend/docs/API_MIGRATION_STATUS.md`](../backend/docs/API_MIGRATION_STATUS.md)
for the complete 73-route status inventory.

Install Node.js 20 or newer and PostgreSQL. Use a disposable local database
restored from a verified backup; do not point the write-capable Node service at
the candidate or production database without explicit approval and a
least-privilege application role. Configure `backend/.env` from
`backend/.env.example` and start the Node service:

```powershell
Set-Location 'D:\house sales and rental management system\backend'
$env:DATABASE_URL = 'postgresql://house_user:your_password@127.0.0.1:5432/house_db'
npm ci
npm start
```

Property images are written under `MEDIA_ROOT\property_images` and
`PRIVATE_MEDIA_ROOT\private_property_images`. Local defaults point to the
workspace `media` and `private-media` folders, which are separate from
`backend/src`; production must configure persistent absolute paths outside the
web application's executable code. The private path must not be served by a
static server. Uploads are limited to 10 MiB and decoded JPEG, PNG, or WebP.
See [`backend/docs/LOCAL_MEDIA_MIGRATION.md`](../backend/docs/LOCAL_MEDIA_MIGRATION.md)
for the existing-media audit and coordinated database/file backup procedure.

Verify the service using `http://127.0.0.1:3000/api/v1/health/`. It returns a
503 response if PostgreSQL is unavailable. To exercise an implemented route
through Vite, set `VITE_API_BASE_URL=/node-api/api/v1` in the frontend
environment; the Vite dev server rewrites `/node-api/*` to Node on port 3000.
The remaining `/api/*` calls and `/media/*` assets continue to use Django by
default. The public property pages read from PostgreSQL while customer actions,
favorites, viewing requests, location lists, homepage content, and account
features remain Django-backed. Do not switch those operations until their Node
endpoints, shared identity, and role permissions have been implemented and
tested.

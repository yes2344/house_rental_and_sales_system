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

The frontend's local API proxy targets Django at `http://127.0.0.1:8000` by
default. Open the local Vite URL printed in the terminal.

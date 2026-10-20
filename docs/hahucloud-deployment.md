# HahuCloud shared-hosting deployment

For the current Infinity House domains and full staging/production safety checklist, follow the root [DEPLOY_HAHUCLOUD.md](../DEPLOY_HAHUCLOUD.md). This guide now reflects MySQL-only configuration.

Before proceeding, confirm with HahuCloud that the account provides MySQL 8.4 or newer with InnoDB, a Python 3.13 application environment, Passenger, and persistent filesystem paths for public and private media. Django 6.1.1 does not support older MySQL server versions. The application is configured for `django.db.backends.mysql`; it does not fall back to SQLite or PostgreSQL.

In cPanel, create a MySQL database and user, grant the user privileges on that database, and configure `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_HOST`, and `MYSQL_PORT` using the actual cPanel values. Set credentials only in the application’s private environment settings. Install dependencies using `python -m pip install -r requirements.txt`.

Do not run migrations or create accounts automatically at web-process startup. First inspect `python manage.py migrate --plan` against a new staging database, take and verify backups before any migration containing existing data, then apply only the explicitly approved plan. Create the Django superuser interactively with `python manage.py createsuperuser`.

The React/Vite frontend remains static: build it with the configured `VITE_API_BASE_URL` and upload the contents of `frontend/dist` to the frontend domain’s document root. Confirm Apache honors `frontend/public/.htaccess`, HTTPS, credentialed CORS, and CSRF behavior. Never expose database credentials, private media, or Django source in the frontend document root.

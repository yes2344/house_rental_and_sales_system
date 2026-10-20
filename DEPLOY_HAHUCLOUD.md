# Infinity House deployment to HahuCloud

This guide prepares a fresh HahuCloud deployment for:

- Frontend: `https://infinityhouseproperties.com`
- Django API: `https://infinityhouseproperty.com`
- Python application root: `/home/infinit1/house_rental_api`
- cPanel virtual environment: `/home/infinit1/virtualenv/house_rental_api/3.13/`
- cPanel startup file: `passenger_wsgi.py`
- cPanel WSGI entry point: `application`
- Django settings: `house.settings`
- MySQL: database created in HahuCloud cPanel

The project keeps Django and React in separate directories. Upload the Django
application to the Python application root; upload only the contents of
`frontend/dist` to the frontend domain's document root. Do not combine these
roots unless HahuCloud explicitly requires a different layout.

## Status and important cautions

- The existing `passenger_wsgi.py` inserts the project root into Python's
  import path, selects `house.settings`, and exports `application`. The
  configured cPanel startup file and entry point match this candidate. Verify
  the application starts and imports that file in the cPanel manager before
  treating WSGI compatibility as established.
- **Authentication domain blocker:** the requested frontend host
  `infinityhouseproperties.com` and API host `infinityhouseproperty.com` are
  different sites, not sibling subdomains. Django's CSRF cookie currently uses
  its default `SameSite=Lax`; the project does not configure cross-site cookie
  behavior. The React client uses credentialed requests, and login is
  CSRF-protected. CORS configuration alone does not override browser
  SameSite/third-party-cookie rules, so login is likely to fail on the
  requested host pair, and any other endpoint using Django CSRF protection may
  fail as well. Prefer an API hostname under the frontend's
  site, such as `api.infinityhouseproperties.com`, if available. If the
  separate `infinityhouseproperty.com` domain is mandatory, resolve and test a
  robust cross-site authentication/CSRF strategy before production; do not
  assume that setting `SameSite=None` alone works in browsers that block
  third-party cookies.
- Django 6.1.1 requires MySQL 8.4 or newer. Confirm HahuCloud provides MySQL 8.4
  or newer with InnoDB, and obtain the actual database host, name, username,
  port, TLS requirements, and connection limits from cPanel/support. Do not
  guess these settings or assume the reported SQLite deployment is the
  authoritative source of current data.
- Django 6.1.1 requires Python 3.12 or newer, so Python 3.13.16 meets Django's
  minimum. Compatibility of the complete pinned `requirements.txt` set with
  the HahuCloud image has not been verified. Test it in a separate staging
  application/database first. `django-cloudinary-storage==0.3.0` has old
  compatibility metadata and deserves particular testing if Cloudinary is
  used.
- This guide does not authorize copying data, migrating a production database,
  creating an administrator, changing DNS, or deploying. Do not assume any
  existing database or uploaded media has been deleted.
- The Render startup command no longer runs migrations or creates an
  administrator. This HahuCloud guide remains the deployment procedure; do not
  configure automatic migrations on any web-process startup.
- `docs/hahucloud-deployment.md` now summarizes and links to this current
  MySQL-only guide. Follow this file for the full target-specific procedure.
- `house.settings` has no project-specific `LOGGING` configuration. Confirm
  cPanel captures Python application stdout/stderr and tracebacks. If not, a
  separately reviewed logging change may be needed; never log passwords,
  authorization headers, or environment-variable values.

## 1. Confirm HahuCloud-specific requirements

Before uploading or running commands, confirm:

1. The Python application manager supports the configured Python 3.13
   virtualenv, imports `/home/infinit1/house_rental_api/passenger_wsgi.py`,
   accepts the `application` callable, and uses the application root as the
   working directory (or otherwise adds it to `sys.path`).
2. The cPanel MySQL server version (at least 8.4), InnoDB availability,
   host, port, database name, username, TLS requirements, application
   connectivity method, and connection limits.
3. The Python app can reach the cPanel MySQL service and whether TLS is
   required. Verify the host, port, and any CA certificate settings with
   HahuCloud rather than guessing.
4. Which forwarded HTTPS header the platform supplies, if any, and how the
   application manager restarts the Python process and exposes its logs.
5. Whether the frontend document root supports the supplied `.htaccess` SPA
   fallback, or requires another rewrite configuration.
6. Whether application storage persists through restarts/releases and is
   backed up, including paths for public and private image files.
7. Whether the main domain and API domain have HTTPS certificates, and whether
   outbound HTTPS to the selected email and image providers is allowed.
8. Whether the host's Python package environment supports all pinned
   requirements and any required wheels/system libraries.
9. Whether `api.infinityhouseproperties.com` can be configured under the
   frontend's domain. If not, plan a supported same-origin proxy or validate a
   cross-site cookie/authentication design in staging.
10. Whether the API can be served from a same-origin path such as `/api/` on
    the frontend domain, or whether the separate-domain arrangement is fixed.

Do not claim production readiness until the Python application, MySQL,
storage, HTTPS, and package requirements are confirmed and staging tests pass.

## 2. Prepare and upload backend files

The backend application root must contain `manage.py`, `requirements.txt`,
`passenger_wsgi.py`, the `house/` project package, all Django apps, migration
directories, templates, and required support modules/assets. Preserve every
app's migrations.

Upload the backend source into:

```text
/home/infinit1/house_rental_api
```

Do not upload or place these in the frontend's public document root:

- `.env`, `.env.backup`, or any credential-bearing environment file
- `.git/` or `.venv/`
- `db.sqlite3`
- Local `media/`, `private-media/`, or `staticfiles/` directories
- `frontend/node_modules/`, frontend source, or repository files not needed
  for the Django application

Do not delete local files or remote data to prepare an upload. If there are
existing deployment files or media on the account, inventory and back them up
before replacing anything.

## 3. Activate the cPanel virtual environment and validate dependencies

Use cPanel's Python application interface to activate the environment, or
confirm the generated activation path with HahuCloud. The expected path is:

```text
/home/infinit1/virtualenv/house_rental_api/3.13/
```

From the backend application root, install the unchanged dependency pins into
that virtual environment:

```sh
cd /home/infinit1/house_rental_api
python -m pip install -r requirements.txt
python -m pip check
```

Perform this first in an isolated staging application. Do not upgrade,
downgrade, or edit package versions as part of installation. If installation
or runtime checks fail, record the package/version and error, then review any
proposed requirements change before applying it.

## 4. Create and configure MySQL

In cPanel, create a MySQL database and a dedicated application user. Grant that
user privileges on that database sufficient to create/alter tables and indexes
for Django migrations. Use MySQL 8.4 or newer with InnoDB; older versions do
not meet the Django 6.1.1 backend's supported-version requirement. cPanel often prefixes the
database and user names; copy the exact values shown there.

Set the following private Python-application environment variables using the
actual cPanel values. Settings require these explicit MySQL variables and
provide no alternate database fallback.

```text
MYSQL_DATABASE=<cPanel MySQL database name>
MYSQL_USER=<cPanel MySQL username>
MYSQL_PASSWORD=<set privately in cPanel>
MYSQL_HOST=<host supplied by cPanel>
MYSQL_PORT=<port supplied by cPanel>
# MYSQL_SSL_CA=<CA certificate path if required by HahuCloud>
```

The configured connection uses `utf8mb4` for English and Amharic data,
`READ COMMITTED` transaction isolation, connection health checks, and a
60-second persistent connection lifetime. If HahuCloud requires verified TLS,
set `MYSQL_SSL_CA` to the provider-supplied CA certificate path. Do not guess
connection options or embed credentials in a URL.

The repository contains a local `db.sqlite3`, and a prior report described a
SQLite deployment, but neither establishes which database currently holds
authoritative production data. Do not copy, overwrite, or migrate any existing
database until its identity is confirmed, a full backup is verified, and a
separate data-transfer plan is approved. Start initial compatibility work with
a new empty staging MySQL database.

## 5. Provision the cPanel environment and install dependencies

Create the Python application and activate its virtual environment as above.
Install the requirements, including the MySQL `mysqlclient` driver:

```sh
cd /home/infinit1/house_rental_api
python -m pip install -r requirements.txt
python -m pip check
```

Verify the host's Python environment can install `mysqlclient` before a
production cutover. Do not upload local virtual environments or database files.

## 6. Set production environment variables in cPanel

Use the Python application's private environment-variable editor. Set values
from HahuCloud and your chosen providers; never commit them, paste them into
the frontend, or include them in this guide.

Required production settings include:

```text
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<new-long-random-secret>
DJANGO_ALLOWED_HOSTS=infinityhouseproperty.com
PUBLIC_FRONTEND_URL=https://infinityhouseproperties.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://infinityhouseproperties.com
DJANGO_CORS_ALLOWED_ORIGINS=https://infinityhouseproperties.com
DJANGO_SECURE_SSL_REDIRECT=True
MYSQL_DATABASE=<cPanel MySQL database name>
MYSQL_USER=<cPanel MySQL username>
MYSQL_PASSWORD=<set privately in cPanel>
MYSQL_HOST=<host supplied by cPanel>
MYSQL_PORT=<port supplied by cPanel>
```

Only add `www.infinityhouseproperties.com` to CORS/CSRF origins if the
frontend is actually served from that origin. `PUBLIC_FRONTEND_URL` must be an
HTTPS origin without a path, query, or fragment.

HTTPS is enforced by default with `DEBUG=False`. Set the following only after HahuCloud confirms its proxy behavior:

```text
DJANGO_TRUST_PROXY_SSL_HEADER=True
```

That setting makes Django trust `HTTP_X_FORWARDED_PROTO=https`. Do not enable
it unless HahuCloud confirms it sets that header reliably. HSTS defaults to
one year in production; subdomain inclusion and preload default off. Do not
enable subdomain HSTS until all affected domains are HTTPS-only.

For production email, select a working provider and configure the relevant
variables, for example:

```text
EMAIL_BACKEND=<configured Django email backend>
DEFAULT_FROM_EMAIL=<verified sender>
EMAIL_HOST=<SMTP host, if applicable>
EMAIL_PORT=<SMTP port, if applicable>
EMAIL_USE_TLS=<provider-required setting, if applicable>
EMAIL_USE_SSL=<provider-required setting, if applicable>
EMAIL_HOST_USER=<SMTP username, if applicable>
EMAIL_HOST_PASSWORD=<SMTP password, if applicable>
BREVO_API_KEY=<private Brevo key, only if using the Brevo backend>
```

Do not leave production email on the console backend. For the Brevo backend,
the settings require `BREVO_API_KEY` and a configured `DEFAULT_FROM_EMAIL`.
Confirm outbound provider connectivity and verify sender configuration.

Cache defaults to database cache in production. Choose one supported backend
deliberately:

```text
DJANGO_CACHE_BACKEND=django.core.cache.backends.db.DatabaseCache
DJANGO_CACHE_LOCATION=<cache table name>
```

If using database cache, create its table once in the confirmed database as a
separately approved step. Alternatively, select the supported local-memory
cache, understanding that data is process-local and resets on restart. Do not
use `locmem` for correctness-sensitive shared state across multiple workers.

## 7. Configure public and private image storage

Choose and test one media strategy before production:

### Cloudinary

Set `CLOUDINARY_URL` privately in cPanel. With it set, Django uses Cloudinary
for public media and the project's custom private-image storage for private
originals. Test normal property-image URLs and authorization-protected
original-image retrieval. Verify outbound HTTPS and credentials without
printing them.

### Persistent HahuCloud filesystem

If not using Cloudinary, configure persistent, backed-up directories outside
any deploy-overwritten application release:

```text
DJANGO_SERVE_MEDIA=True
DJANGO_MEDIA_ROOT=<persistent public media directory>
DJANGO_PRIVATE_MEDIA_ROOT=<persistent private originals directory>
```

Use actual persistent paths outside deploy-overwritten code releases. New public
images are stored under `DJANGO_MEDIA_ROOT`; private originals are stored under
`DJANGO_PRIVATE_MEDIA_ROOT`. Do not leave production paths at the settings
defaults under the application code root unless HahuCloud confirms those paths
persist across releases. Confirm write permissions and perform a restart/backup
restore test with a staging upload.

The `media/` directory is served at `/media/` by Django when local media
serving is enabled. Keep private originals outside public web roots; access to
them is handled by the application's protected image endpoint. Confirm both
directories persist across app restart/release and are included in backups.
Do not copy local media into a new deployment without a separately planned,
verified transfer.

## 8. Confirm and start the WSGI application

The existing `passenger_wsgi.py` already inserts the application root into
`sys.path`, sets `DJANGO_SETTINGS_MODULE` to `house.settings`, and exports
`application`. These match the configured cPanel filename and entry point:

```text
Startup file: passenger_wsgi.py
Entry point:  application
```

After upload, verify in the cPanel Python application UI that it imports that
file from `/home/infinit1/house_rental_api` with the
`/home/infinit1/virtualenv/house_rental_api/3.13/` environment. Restart using
the cPanel control only after configuration is complete. If startup fails,
inspect the application log and confirm working directory, Python version,
virtualenv path, dependencies, environment variables, and file permissions.

Do not use the Render `startCommand`. In particular, do not put
`manage.py migrate` or any administrator-creation command in automatic web
startup.

## 9. Run safe staging checks, static collection, and migrations

In the staging app with staging environment variables configured, first run:

```sh
cd /home/infinit1/house_rental_api
python manage.py check
python manage.py check --deploy
python manage.py makemigrations --check --dry-run
```

Review and resolve deployment warnings in context. Then, after confirming the
staging database identity and its backup/restore path, run:

```sh
python manage.py migrate --plan
python manage.py collectstatic --noinput
```

`migrate --plan` is for review; inspect every operation before applying it.
The existing `viewings.0004_viewingrequestevent_message_and_more` migration
closes duplicate active viewing requests (without deleting them) and adds
history records. Review those status changes before applying migrations to any
database containing existing records. Before applying
`properties.0015_mysql_generated_unique_keys`, inspect for duplicate root
location slugs and multiple primary images per property; those conflict with
the replacement MySQL unique keys and are not automatically rewritten.
MySQL's default collation may compare unique text keys case-insensitively, so
review case-only duplicate slugs/usernames in existing data before import.
MySQL schema changes are not generally
transactional; test the entire migration sequence on a disposable staging
database first. Only after staging validation and a verified backup, and after
explicit approval for the selected database, run:

```sh
python manage.py migrate --noinput
```

Never apply migrations automatically at application startup or run them against
an unidentified existing database.

Create the first Django built-in administrator interactively from the private
application shell after migrations are approved and complete:

```sh
python manage.py createsuperuser
```

Do not put the administrator password in a committed file, deployment
manifest, or frontend environment variable.

For MySQL backups, use cPanel's database backup facility or a trusted
`mysqldump` client. Keep the backup outside the application release and test
restoration to a separate non-production database before any migration:

```sh
mysqldump --host="$MYSQL_HOST" --port="$MYSQL_PORT" --user="$MYSQL_USER" --password --single-transaction --default-character-set=utf8mb4 "$MYSQL_DATABASE" > house-before-migration.sql
mysql --host="$MYSQL_HOST" --port="$MYSQL_PORT" --user="$MYSQL_USER" --password "$MYSQL_DATABASE" < house-before-migration.sql
```

The `--password` option prompts for the password; do not put credentials in
shell history. For restore tests, create and select a separate disposable
database before importing. Verify the backup is non-empty, record its location
and timestamp, and confirm application/media backup coverage.

If data in the existing SQLite or a legacy database must be preserved, first
identify the live source and database configuration with the operator, stop
writes for a consistent snapshot, make and verify an independent backup, and
restore that snapshot to an isolated copy. Then apply an explicitly reviewed
cross-engine export/import mapping to a separately initialized MySQL database;
compare record counts, IDs, relations, decimal/date values, account roles,
viewing-request history, and image paths, and run the full feature tests before
cutover. SQLite/PostgreSQL physical backups cannot be restored directly as a
MySQL database. Keep the original read-only and available for rollback until
the owner approves final cutover. Do not run this data transfer as part of this
code change.

WhiteNoise is already configured for Django static files. `collectstatic`
populates `STATIC_ROOT` (`staticfiles/`); this output is separate from the
React build. Do not upload local generated `staticfiles/` as a substitute for
running collection in the target environment.

## 10. Build and upload the React frontend

Build on a development machine from `frontend`, using the final API origin.
For PowerShell:

```powershell
Set-Location 'D:\house sales and rental management system\frontend'
$env:VITE_API_BASE_URL = 'https://infinityhouseproperty.com/api/v1/'
npm run build
```

The build command is `tsc -b && vite build`; output is `frontend/dist`.
`VITE_API_BASE_URL` is compiled into public JavaScript and is not a secret.
Do not put API keys, passwords, database credentials, or Django secret keys in
any `VITE_*` variable.

Upload **only the contents** of `frontend/dist` to the document root assigned
to `infinityhouseproperties.com`, including `.htaccess` if the host uses
Apache. Do not assume that document root is the Python application root.
Never upload Django source, `.env` files, private media, or the whole
repository to the public document root.

The existing `frontend/public/.htaccess` rewrites unknown paths to
`index.html`. Confirm the hosting web server supports the needed rewrite.
Otherwise configure its equivalent SPA fallback so a direct visit or refresh
on routes such as `/login`, `/dashboard`, and `/properties/...` returns
`index.html`. Existing API calls use `/api/v1/` with trailing slashes; keep
that prefix in `VITE_API_BASE_URL`.

**Authentication domain blocker:** the currently requested API domain
`infinityhouseproperty.com` is a different registrable domain from the
frontend `infinityhouseproperties.com`. This is cross-site, and the current
settings do not provide an environment variable for `CSRF_COOKIE_SAMESITE`.
The default `SameSite=Lax` CSRF cookie may not be sent on cross-site API
requests. Do not treat `DJANGO_CSRF_TRUSTED_ORIGINS` or CORS as a substitute
for cookie behavior. Prefer an API hostname under `infinityhouseproperties.com`
(for example `api.infinityhouseproperties.com`) or a confirmed same-origin
proxy. If the separate API domain is mandatory, agree on a supported
cross-site cookie/authentication design and test login and every unsafe API
request in real browsers with third-party cookies restricted. Do not assume
that `SameSite=None` alone works where browsers block third-party cookies.

## 11. Configure DNS and HTTPS only after staging succeeds

Do not change DNS during preparation. Once the staging deployment, backup
restore test, and feature checks pass, configure the domain and API subdomain
using HahuCloud's instructions. Ensure both hosts have valid HTTPS before
enabling production redirects and secure cookies. Confirm that frontend
requests to the API pass credentialed CORS and CSRF checks with the exact
frontend origin. Avoid enabling HSTS subdomain coverage until all relevant
subdomains are HTTPS-only.

## 12. Test the deployed staging application

Before production cutover, test:

1. `https://infinityhouseproperty.com/api/v1/properties/` returns expected
   public listing JSON, and
   `https://infinityhouseproperty.com/api/v1/auth/csrf/` works over HTTPS.
2. Frontend API requests, browser CORS, cookies, CSRF-protected writes, and
   direct navigation/refresh on nested React routes.
3. Public registration, verification email, login/logout, and password reset.
4. Property search, property details, favorites, and property image delivery.
5. Owner property submission and editing, and viewing-request creation and
   management.
6. Administrator account/property functions and agent onboarding, assigned
   work, and permission restrictions.
7. Private original-image access is authorized and inaccessible publicly.
8. Uploaded media survives an app restart if local storage is selected; test
   Cloudinary operations if Cloudinary is selected.
9. Error logs are visible in cPanel and do not disclose secrets.
10. A database and media backup can actually be restored to a non-production
    target.

## Troubleshooting

- **Application import/startup error:** verify the cPanel startup file, callable,
  Python version, virtualenv, project root, environment variables, dependency
  installation, and application logs. Do not replace working WSGI code without
  an error showing it is required.
- **Database connection failure:** check cPanel-provided MySQL host, port,
  database/user names, grants, InnoDB availability, TLS requirements,
  outbound/local connectivity, and the installed `mysqlclient` driver. The app
  reads only the `MYSQL_*` variables listed above.
- **Django rejects the host or origin:** verify `DJANGO_ALLOWED_HOSTS`,
  `PUBLIC_FRONTEND_URL`, `DJANGO_CSRF_TRUSTED_ORIGINS`, and
  `DJANGO_CORS_ALLOWED_ORIGINS` exactly match the HTTPS hostnames in use.
- **HTTPS redirect loop:** verify TLS termination and forwarded-protocol
  behavior with HahuCloud before setting `DJANGO_TRUST_PROXY_SSL_HEADER`.
- **Static assets missing:** confirm `collectstatic` succeeded in the intended
  app environment, WhiteNoise is in use, and the frontend build contents went
  to the correct document root.
- **React refresh returns 404:** confirm `.htaccess` is honored or configure
  HahuCloud's equivalent SPA rewrite.
- **Images disappear after deploy/restart:** confirm media paths are persistent
  and not inside a replaced code release, or validate Cloudinary configuration.
- **Email fails:** verify the backend selection, sender verification, provider
  credentials in cPanel, and outbound provider connectivity. Do not print
  environment values when diagnosing.
- **A package is incompatible:** reproduce in the isolated Python 3.13.16
  staging virtualenv, preserve the error output with secrets redacted, and
  review any dependency change before approval.

## Configuration variable names (values are private)

Core Django: `DJANGO_DEBUG`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`,
`PUBLIC_FRONTEND_URL`, `DJANGO_CSRF_TRUSTED_ORIGINS`,
`DJANGO_CORS_ALLOWED_ORIGINS`, `DJANGO_SECURE_SSL_REDIRECT`,
`DJANGO_TRUST_PROXY_SSL_HEADER`.

MySQL: `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_HOST`,
`MYSQL_PORT`, optionally `MYSQL_SSL_CA` and `MYSQL_TEST_DATABASE`.

Media and cache: `CLOUDINARY_URL`, `DJANGO_SERVE_MEDIA`,
`DJANGO_MEDIA_ROOT`, `DJANGO_PRIVATE_MEDIA_ROOT`, `DJANGO_CACHE_BACKEND`,
`DJANGO_CACHE_LOCATION`.

Email: `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`,
`EMAIL_USE_SSL`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`,
`EMAIL_TIMEOUT_SECONDS`, `BREVO_API_KEY`, `DEFAULT_FROM_EMAIL`.

## Final go-live gate

Proceed only after HahuCloud confirms the WSGI manager and MySQL
connection contract, pinned dependencies pass in staging, HTTPS/CORS/CSRF and
SPA routing work, persistent/Cloudinary media is verified, and backups have
been restored successfully. Keep any existing services, databases, and media
untouched until a separate data-transfer and rollback plan is approved.

# HahuCloud shared-hosting deployment

This guide targets the HahuCloud shared-hosting account described by the site owner: Python application support, PostgreSQL, and a main domain with subdomains. It keeps the React/Vite frontend static on the main domain and runs Django with the hosting control panel's Python application/Passenger integration on an API subdomain.

The site owner confirmed Python applications and PostgreSQL are available on their account. HahuCloud's [shared-hosting page](https://www.hahucloud.com/shared-hosting) and [VPS page](https://www.hahucloud.com/vps) list these as separate products; verify the exact Python version, PostgreSQL version/connection host, Passenger setup, and resource limits shown for your own plan before installing. Do not use `render.yaml` or the Render/Netlify proxy configuration for this setup.

## 1. Prepare domains and control-panel resources

1. Point your domain's DNS to the HahuCloud account and enable its SSL certificate for both the main site (including `www` if used) and an API subdomain such as `api.example.com`.
2. In the control panel, create the PostgreSQL database and database user, and grant that user access to the database. Record the database name, username, password, host, and port privately.
3. Create a Python application for the API subdomain. Choose a Python version supported by both HahuCloud and `requirements.txt`; set the application root to a directory outside `public_html`, for example `hpc-api`, and set the application URL to the API subdomain.
4. Note the virtual-environment path shown by the control panel. Do not put database credentials or API keys in Git.

## 2. Deploy the Django API

Upload/clone the repository into the Python application's root, including `passenger_wsgi.py`. Activate the virtual environment shown by the control panel and install the pinned packages:

```sh
pip install -r requirements.txt
```

Set these environment variables in the Python application's control-panel settings (or in an ignored `.env` file in the application root):

```dotenv
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<long-random-secret>
DJANGO_ALLOWED_HOSTS=api.example.com
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SERVE_MEDIA=True
DJANGO_MEDIA_ROOT=/home/CPANEL_USER/hpc-api/media
DJANGO_PRIVATE_MEDIA_ROOT=/home/CPANEL_USER/hpc-private-media
PUBLIC_FRONTEND_URL=https://example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://example.com,https://www.example.com
DJANGO_CORS_ALLOWED_ORIGINS=https://example.com,https://www.example.com
POSTGRES_DB=<database-name>
POSTGRES_USER=<database-user>
POSTGRES_PASSWORD=<database-password>
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
EMAIL_BACKEND=accounts.email_backend.BrevoEmailBackend
BREVO_API_KEY=<brevo-api-key>
DEFAULT_FROM_EMAIL=<verified-sender@example.com>
DJANGO_SUPERUSER_USERNAME=<initial-admin-username>
DJANGO_SUPERUSER_EMAIL=<initial-admin-email>
DJANGO_SUPERUSER_PASSWORD=<strong-initial-admin-password>
```

Replace `example.com`, `CPANEL_USER`, and all placeholders with values from your account. Use the actual PostgreSQL hostname and port from HahuCloud if they differ from `localhost:5432`. Both `DJANGO_MEDIA_ROOT` and `DJANGO_PRIVATE_MEDIA_ROOT` must be persistent directories outside the deploy-overwritten code release, but inside the account's storage quota. The Django media endpoint serves only `MEDIA_ROOT`; private originals remain in `DJANGO_PRIVATE_MEDIA_ROOT` and are served only through the authorization-checked image endpoint.

If the control panel offers a built-in Python application environment-variable editor, prefer it for secrets. If using `.env`, restrict file permissions and keep it outside the public web root. The repository `.gitignore` already excludes local environment files.

Run these commands from the application root using the selected Python virtual environment. `check --deploy` must not report CSRF or HTTPS redirect issues before going live. Enable HSTS subdomain coverage only if all subdomains under the API hostname are HTTPS-only; HSTS preload is optional.

```sh
python manage.py check --deploy
python manage.py migrate --noinput
python manage.py ensure_demo_admin
python manage.py collectstatic --noinput
```

The administrator command requires `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, and `DJANGO_SUPERUSER_PASSWORD` for first-time setup. Set those only for the command in the control panel's private environment, then remove the password variable if the panel allows one-off environment values. Restart the Python application through the control panel after installing packages, changing environment variables, or deploying code. The shared account's persistent filesystem is used for uploaded public media; make sure the hosting backup policy includes the configured media directory and the PostgreSQL database.

Check `https://api.example.com/api/v1/properties/` and `https://api.example.com/api/v1/auth/csrf/` before publishing the frontend. The first should return JSON; the second should return a CSRF token and set its cookie.

## 3. Build and upload the React frontend

On a development machine, from the `frontend` directory, build with the public API URL:

```sh
npm ci
$env:VITE_API_BASE_URL = "https://api.example.com/api/v1"
npm run build
```

Upload the **contents** of `frontend/dist` to the main domain's document root (`public_html`), including the generated `.htaccess`. The rewrite file serves existing assets directly and sends client-side routes to `index.html`. Do not upload the source tree, `.env`, or `node_modules`.

## 4. Configure durable media and email

- `DJANGO_SERVE_MEDIA=True` uses the HahuCloud account's persistent `DJANGO_MEDIA_ROOT` and serves public listing media from the API origin. Keep both public and private media directories outside deploy cleanup and included in backups.
- To store media with Cloudinary instead, set `CLOUDINARY_URL` and omit `DJANGO_SERVE_MEDIA` (or set it to `False`); Cloudinary storage takes precedence.
- Production email uses Brevo over HTTPS. Set the API key and a sender that has been verified with Brevo. If you use a different email provider, configure its Django email backend and settings explicitly rather than leaving a console backend in production.

## 5. Verify the live site

1. Confirm HTTPS works on both the main domain and API subdomain without a redirect loop.
2. Open the main domain and test listing search, property details, images, registration/login, an owner submission, and a viewing request.
3. In browser developer tools, verify API requests from the frontend origin pass CORS and that login's CSRF request sets a cookie.
4. Upload a property image, confirm it remains available after restarting the Python application, and confirm the hosting backup includes the media directory.
5. Test a backup restore for both PostgreSQL and media before announcing the site.

HSTS preload is intentionally not enabled automatically; only opt in if the root domain and every subdomain that could receive HSTS are permanently HTTPS-only. Never run a database migration against live data without a verified, restorable backup.

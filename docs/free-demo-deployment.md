# Free demo deployment

This repository is prepared for a demo deployment with Netlify (React), Render (Django), Neon (PostgreSQL), and Cloudinary (uploaded media). Provider free plans have limits and may change; this setup is not intended for production workloads or guaranteed availability.

## 1. Create the hosted database

1. Create a PostgreSQL project in Neon.
2. Copy its pooled connection string, including `sslmode=require`. Treat it as a password.

## 2. Deploy the API to Render

1. In Render, create a Blueprint from this repository and confirm the `render.yaml` configuration.
2. Enter the Neon connection string for `DATABASE_URL` and Cloudinary URL for `CLOUDINARY_URL`. For the not-yet-created Netlify site, enter a temporary HTTPS origin for `DJANGO_CSRF_TRUSTED_ORIGINS`; replace it after creating the site.
3. Enter the initial administrator username, email, and a strong password for `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, and `DJANGO_SUPERUSER_PASSWORD`. These are server-side secrets/configuration; never use `VITE_*` for them.
4. Deploy the `kefaleshabeshahome-api` service. The startup command runs migrations and creates that administrator only if it does not already exist. It does not reset the password on later restarts.
5. Copy the backend origin shown in the Render dashboard. If Render assigned a different hostname than `kefaleshabeshahome-api.onrender.com`, update `DJANGO_ALLOWED_HOSTS` to match.

## 3. Deploy the frontend to Netlify

1. Import this repository into Netlify. The root `netlify.toml` sets the base directory and build output.
2. Set `VITE_API_PROXY_TARGET` to the backend origin from the Render dashboard (HTTPS, no trailing slash or path).
3. Set the frontend's public API base URL to `/api/v1` if it is not already set.
4. Deploy. The build creates Netlify proxy rules for `/api/*` and `/media/*`, followed by the single-page-app fallback. Netlify builds fail if the backend origin is missing.
5. Copy the assigned Netlify site origin, such as `https://your-site.netlify.app`, and replace the temporary value in Render's `DJANGO_CSRF_TRUSTED_ORIGINS`. Include any additional frontend origins as a comma-separated list, then redeploy the API.

## 4. Verify

- Open the Netlify URL and test browsing, sign-in, listing images, and a viewing request.
- Verify `/api/v1/auth/csrf/` through the Netlify URL.
- Test an image upload and confirm its URL is served from Cloudinary.
- Check the Render and Netlify deploy logs for build or runtime errors.

## Notes

- Keep provider credentials in provider environment settings, never in Git or frontend `VITE_*` variables.
- Django admin static files are collected during the Render build and served through WhiteNoise.
- Local development continues to use local media storage. Cloudinary storage is enabled only when `CLOUDINARY_URL` is present.
- The demo Blueprint uses in-memory caching and one Gunicorn worker to avoid a separate cache-table setup on the free service. Cache state (including throttle counters) is process-local and resets when the service restarts.
- Existing local users, listings, and uploaded images are not copied into Neon or Cloudinary automatically. Recreate the demo content through the application, or arrange a separate data/media migration before deployment.
- Render free services can sleep while idle, causing a delay on the first request. Free-tier storage, database, bandwidth, and usage limits apply.
- The Render Blueprint starts one Gunicorn worker because the free service is resource-constrained.

# Free demo deployment

This guide describes a provider-neutral static frontend deployment with Render (Django), Neon (PostgreSQL), and Cloudinary (uploaded media). For the planned HahuCloud shared-hosting deployment, follow [hahucloud-deployment.md](./hahucloud-deployment.md) instead. Provider free plans have limits and may change; this setup is not intended for production workloads or guaranteed availability.

## 1. Create the hosted database

1. Create a PostgreSQL project in Neon.
2. Copy its pooled connection string, including `sslmode=require`. Treat it as a password.

## 2. Deploy the API to Render

1. In Render, create a Blueprint from this repository and confirm the `render.yaml` configuration.
2. Enter the Neon connection string for `DATABASE_URL` and Cloudinary URL for `CLOUDINARY_URL`. Production startup requires Cloudinary so uploads are not silently written to Render's ephemeral filesystem.
3. Enter the deployed frontend's HTTPS origin for `PUBLIC_FRONTEND_URL`. The backend uses it for verification and password-reset links, and adds it to the default CORS and CSRF trusted-origin settings.
4. Enter the initial administrator username, email, and a strong password for `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, and `DJANGO_SUPERUSER_PASSWORD`. These are server-side secrets/configuration; never use `VITE_*` for them.
5. Add a Brevo API key and a verified sender address for `BREVO_API_KEY` and `DEFAULT_FROM_EMAIL`. Production startup requires both when using the configured Brevo backend.
6. Deploy the `kefaleshabeshahome-api` service. The startup command runs migrations and creates that administrator only if it does not already exist. It does not reset the password on later restarts.
7. Copy the backend origin shown in the Render dashboard. If Render assigned a different hostname than `kefaleshabeshahome-api.onrender.com`, update `DJANGO_ALLOWED_HOSTS` to match.

## 3. Build and deploy the frontend

1. Configure the static frontend host to build from `frontend` with `npm run build` and publish the `dist` directory.
2. Set `VITE_API_BASE_URL` to the backend API origin followed by `/api/v1`, for example `https://your-api.example.com/api/v1`.
3. Configure the host to serve `index.html` for unknown frontend routes, including `/verify-email`, `/forgot-password`, and `/reset-password`. This is required for direct navigation from account emails.
4. Configure `/media/*` to reach the backend if the deployment serves media from its local media directory. Production uploads should use the configured Cloudinary storage.
5. Set `PUBLIC_FRONTEND_URL` on the backend to the deployed frontend's exact HTTPS origin (no path, query, or fragment), then redeploy the backend.

## 4. Verify

- Open the frontend URL and test browsing, sign-in, listing images, and a viewing request.
- Verify the API's `/api/v1/auth/csrf/` endpoint from the deployed frontend.
- Register with a controlled mailbox, open the verification email, and confirm its link uses the deployed frontend hostname and loads the verification page.
- Test an image upload and confirm its URL is served from Cloudinary.
- Check the backend and frontend host logs for build or runtime errors.

## Notes

- Keep provider credentials in provider environment settings, never in Git or frontend `VITE_*` variables.
- Django admin static files are collected during the Render build and served through WhiteNoise.
- Local development continues to use local media storage. Cloudinary storage is enabled only when `CLOUDINARY_URL` is present.
- The demo Blueprint uses in-memory caching and one Gunicorn worker to avoid a separate cache-table setup on the free service. Cache state (including throttle counters) is process-local and resets when the service restarts.
- Existing local users, listings, and uploaded images are not copied into Neon or Cloudinary automatically. Recreate the demo content through the application, or arrange a separate data/media migration before deployment.
- Render free services can sleep while idle, causing a delay on the first request. Free-tier storage, database, bandwidth, and usage limits apply.
- The Render Blueprint starts one Gunicorn worker because the free service is resource-constrained.

# Account verification and password recovery email

New public registrations remain inactive until the email verification link is used. Verification links expire after 24 hours by default. Password reset links use Django's one-time token generator and expire after 24 hours by default.

## Local development

With `DJANGO_DEBUG=True`, Django uses its console email backend by default. Registering an account or requesting a reset prints the complete message and link in the Django runserver terminal; this does not deliver mail to an inbox. The public frontend origin defaults to `http://127.0.0.1:5173`.

## Production

Set these environment variables on the backend deployment. Use the SMTP credentials supplied by the mail provider; do not commit them or put them in `.env.example`.

```dotenv
PUBLIC_FRONTEND_URL=https://your-frontend.example
DEFAULT_FROM_EMAIL=Habasha Property Center <no-reply@your-domain.example>
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.your-provider.example
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_TIMEOUT_SECONDS=10
EMAIL_VERIFICATION_TIMEOUT_SECONDS=86400
PASSWORD_RESET_TIMEOUT_SECONDS=86400
```

Use the frontend's HTTPS origin with no path, query, or fragment. Email links are rejected unless the configured public origin is HTTPS outside debug mode. Configure sender-domain DNS and provider authorization separately, then send a real verification and reset message to a controlled mailbox before announcing the service. SMTP provider delivery is not proven by local tests.

Email verification, resend, and password-reset request endpoints are rate-limited. Reset-request responses intentionally do not disclose whether an account exists. The frontend links are `/verify-email`, `/forgot-password`, and `/reset-password`.

## Database deployment

The verification-token table is added by a forward-only Django migration. Back up the database and run the migration during the normal deployment process; do not reset or recreate the database.

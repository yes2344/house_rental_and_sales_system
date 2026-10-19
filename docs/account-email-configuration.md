# Account verification and password recovery email

New public registrations remain inactive until the email verification link is used. Verification links expire after 24 hours by default. Password reset links use Django's one-time token generator and expire after 24 hours by default.

## Local development

With `DJANGO_DEBUG=True`, Django uses its console email backend by default. Registering an account or requesting a reset prints the complete message and link in the Django runserver terminal; this does not deliver mail to an inbox. The public frontend origin defaults to `http://127.0.0.1:5173`.

## Production

Render's free web services block outbound traffic on SMTP ports 25, 465, and 587. Use Brevo's HTTPS transactional email API instead of Gmail SMTP. Create a Brevo account, generate an API key, and add a sender address in Brevo's sender settings; the sender must be verified before Brevo will accept messages.

```dotenv
PUBLIC_FRONTEND_URL=https://your-frontend.example
DEFAULT_FROM_EMAIL=Infinity House <verified-sender@example.com>
EMAIL_BACKEND=accounts.email_backend.BrevoEmailBackend
BREVO_API_KEY=
EMAIL_TIMEOUT_SECONDS=10
EMAIL_VERIFICATION_TIMEOUT_SECONDS=86400
PASSWORD_RESET_TIMEOUT_SECONDS=86400
```

In the backend host's environment settings, set `PUBLIC_FRONTEND_URL` to the deployed frontend origin, with no path, query, or fragment. Production refuses to start without this setting so verification and recovery links cannot silently point to a stale site. Set `BREVO_API_KEY` to the secret API key from Brevo and `DEFAULT_FROM_EMAIL` to the sender address verified in Brevo, optionally with a display name. Do not commit the API key or paste it into chat. The Render Blueprint prompts for the frontend origin and uses the Brevo backend.

When `DEBUG=False` and the Brevo backend is selected, Django refuses to start unless both the API key and an explicit sender address are configured. This prevents deployments from appearing healthy while verification and password-recovery email delivery is unusable.

Email links are rejected unless the configured public origin is HTTPS outside debug mode. The backend adds that origin to its default CORS and CSRF trusted-origin settings. The backend sends transactional messages to Brevo over HTTPS (port 443), avoiding Render's SMTP egress restriction. After setting the frontend origin, key, and verified sender, redeploy and send real verification and reset messages to controlled mailboxes. Local tests mock the provider API; they do not prove external delivery.

For deployments that are not subject to Render's SMTP egress restriction, Django's standard SMTP backend can still be selected with the appropriate provider-specific settings.

Email verification, resend, and password-reset request endpoints are rate-limited. Reset-request responses intentionally do not disclose whether an account exists. The frontend links are `/verify-email`, `/forgot-password`, and `/reset-password`.

## Database deployment

The verification-token table is added by a forward-only Django migration. Back up the database and run the migration during the normal deployment process; do not reset or recreate the database.

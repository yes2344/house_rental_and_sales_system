# Account email features

The Node API supports email verification, verification resend, and password
reset through SMTP. Configure these values only in the private backend
environment:

| Variable | Purpose |
| --- | --- |
| `SMTP_HOST` | Provider SMTP hostname. |
| `SMTP_PORT` | SMTP port; defaults to 587. |
| `SMTP_SECURE` | `true` for direct TLS (commonly port 465); otherwise STARTTLS is used where supported. |
| `SMTP_USER`, `SMTP_PASS` | Provider credentials. |
| `EMAIL_FROM` | Verified sender address. |
| `FRONTEND_URL` | Exact HTTPS frontend origin for verification/reset links. |

Provider failures return an error rather than a success-shaped response, and
the issued one-time token is removed if delivery fails. Email addresses that
do not match an eligible account receive the same API response as matching
addresses. Tokens are stored as digests in PostgreSQL.

`npm run check:deployment` validates that SMTP configuration is present and
well-formed but does not send a message. Verify SMTP TLS, sender/domain
authorization, delivery, and spam handling in staging before enabling these
flows. Never put SMTP credentials in the frontend build or source control.

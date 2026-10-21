# Account email features

> **Email delivery is not implemented in the current Node API.** Password
> recovery, email verification, and resend endpoints are listed as pending in
> [`../backend/docs/API_MIGRATION_STATUS.md`](../backend/docs/API_MIGRATION_STATUS.md).
> The previous Django email configuration and environment variables have been
> removed; do not configure the old provider settings expecting them to work.

When implementing email in Node, use a provider-supported HTTPS API or a
verified SMTP service, keep credentials in the private server environment, and
test provider errors, token expiration, rate limits, and account-enumeration
behavior. Do not return a success response when delivery fails.

The frontend still contains password recovery and verification screens, but
they cannot complete their API requests until the corresponding Node routes
and email service are implemented and tested.

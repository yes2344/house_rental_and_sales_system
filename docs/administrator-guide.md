# Administrator guide

This guide is for the authorized Platform Owner and administrator accounts.
Use individual accounts and strong, unique passwords. Do not share credentials
or invitation tokens in tickets, source files, or public messages.

## Access and boundaries

- Sign in through the website and use only the management screens shown for
  your account.
- The backend enforces permissions; hiding a menu item is not an authorization
  control.
- Administrator operations and role coverage are described in the
  [API migration status](../backend/docs/API_MIGRATION_STATUS.md). The
  automated suite has mocked workflow coverage, but production database access
  and the full browser experience have not been verified.
- Agent accounts are a separate role. Do not use an agent account for
  administrator-only account, property, public-page, or audit operations.

## Account and agent management

The current Node API has administrator routes for users, public accounts,
delegated accounts, agent assignment, and audit events. Create or update an
account only after confirming the intended person's identity, role, scope, and
approval. Review the permission effect before saving. Agent invitations use a
one-time token flow; communicate such tokens privately and promptly.

The one-time Platform Owner bootstrap script is an operational setup tool, not
a routine user-management action. It has a read-only mode by default and
requires an explicit confirmation variable for account creation. Use it only
for an approved initial setup against a verified staging or target database.
Never use it to promote an existing account, reset credentials, or transfer
ownership.

## Listings, submissions, and public content

- Review agent-created listings and owner submissions before publication.
- Check listing accuracy, permissions, image visibility, and customer contact
  details before approving publication.
- Manage public About, Contact, and Property Management copy only through
  authorized management screens and approved business content.
- Updating the site logo also updates the favicon. The favicon uses a circular
  crop with a gold rim; if the logo cannot be loaded for rendering, the
  built-in circular favicon remains in use.
- Keep property originals and private customer information confidential.
- Do not delete a listing with viewing history unless the application
  explicitly permits the action and the owner has approved the business
  consequences.

## Operations and escalation

- Check the configured backup status and ensure PostgreSQL and both media roots
  are backed up together.
- Do not run a SQL migration, orphan-image deletion, bulk media rewrite, or
  account bootstrap against production without an approved change and a
  verified restore.
- If expected data or a feature is missing, capture the route, timestamp,
  account role, and non-sensitive error details. Do not send passwords,
  session cookies, contact records, or private images.

Email flows require private SMTP configuration and a staging delivery test.
Hosting storage, production database compatibility, redirect behavior, and
end-to-end administrator workflows remain unverified.

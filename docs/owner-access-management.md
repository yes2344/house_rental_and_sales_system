# Owner and delegated account management

> **Management API coverage is incomplete in Node.** This document describes
> the previous account-management behavior; the Django source and Django
> Admin UI have been removed. Check
> [`../backend/docs/API_MIGRATION_STATUS.md`](../backend/docs/API_MIGRATION_STATUS.md)
> before relying on any operation below.

## Platform administrator

The previous React app used a shared sign-in page for customers, agents,
delegated administrators, and superusers. Django Admin at `/admin/` is no
longer included. Do not assume that dashboard visibility provides
authorization; each replacement Node route must enforce permissions on the
server.

The one-time `npm run bootstrap:platform-owner` command creates the designated
Platform Owner account using the existing Node authentication schema and
password hashing. It requires `PLATFORM_OWNER_USERNAME`, `PLATFORM_OWNER_EMAIL`,
and `PLATFORM_OWNER_PASSWORD` in the private deployment environment. The
password must be at least 16 characters. Never commit these values, put them
in frontend files, or pass secrets as command-line arguments.

Run the command with no flags first; this performs a read-only preflight. It
will refuse to create an account if the username or email already belongs to
an account, if an active superuser or configured owner already exists, or if
the schema state is inconsistent. It never promotes an existing ordinary
account, resets a password, or transfers an existing owner. For the approved
initial setup only, set
`PLATFORM_OWNER_BOOTSTRAP_CONFIRM=create-platform-owner` in the private
environment and run `npm run bootstrap:platform-owner -- --apply`. The
transaction creates the active administrator/superuser profile and, when the
brokerage settings row already exists, assigns the owner pointer only when it
is empty. If the settings row is absent, the backend's existing active
superuser fallback identifies the new sole superuser as owner. Running the
setup again is a no-op only when the same account is already fully configured
as owner; otherwise it stops with a conflict.

Remove the temporary owner setup variables after successful initialization.
Choose a fresh, unique password through the secret manager; never reuse a
password exposed in a message or committed to source. The Platform Owner also
receives the existing administrator management privileges and can manage
their own profile through the account profile interface.

## Manage agents

1. The previous workflow required a platform owner or delegated administrator
   to open **Manage agents** from `/dashboard`.
2. The page and `/api/v1/admin/delegated-accounts/` can invite, inspect, update, or deactivate agent accounts only. Administrators cannot manage customers or other administrators through the application.
3. New agents receive the existing marketplace-operational permissions by default. The platform owner may separately grant an agent permission to manage public contact/social settings. Agent accounts cannot manage users.
4. Share the one-time invitation token privately. The token is displayed only once and is never written to audit records. The invitee opens `/accept-invitation`, pastes the token, and chooses a password. The invitation expires after 48 hours and can only be used once.
5. Agent assignments remain useful for attribution and workflows, but they do not restrict an approved agent's operational visibility or management scope. An agent who creates a listing is automatically assigned to it.

The project does not currently send invitation emails. Until an email provider is configured, the owner must securely relay the one-time token to the intended invitee.

## Permission behavior

Permissions are defined in `accounts.models.Profile.Permission`; the internal `AGENT` role name remains for compatibility. Delegated administrators can manage agent accounts but cannot grant owner-only permissions. Approved agents receive marketplace-operational permissions by role, including for older accounts whose saved permission list is incomplete. Agent management of listings and owner submissions is scoped to the assigned city. Property ownership or a prior listing submission alone does not grant management access. Public owner-announced listings require an approved submission and active agreement; agent-managed listings must be published and available.

The previous permission model reserved `settings.manage` for the platform
owner. Brokerage settings and homepage announcements require replacement Node
routes before their management flows are available.

Deactivating an account takes effect on subsequent authenticated requests. Role and account changes, including permission changes, and invitations are written to the audit log without recording passwords or invitation tokens.

## Verification

The previous Python checks no longer apply. Before relying on a replacement
management feature, run the Node backend tests and verify both allowed and
denied access for each role against a prepared disposable PostgreSQL database.

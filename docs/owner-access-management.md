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

No Node administrator bootstrap or account-management CLI is currently
provided. Do not create privileged accounts by editing production database
rows without a separately reviewed procedure.

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

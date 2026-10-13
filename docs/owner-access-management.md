# Owner and delegated account management

## Django administrator

Customers, brokers, delegated administrators, and Django superusers use the same React sign-in page. After sign-in, `/dashboard` shows actions permitted for that account. An active Django superuser has full platform-management permissions in the React/API application, including listings, viewing requests, locations, brokerage settings, moderation, reports, and broker-account management. Django Admin at `/admin/` remains available as an optional interface and uses Django's own session sign-in.

Create or recover the Django superuser locally with Django's built-in commands:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py changepassword YOUR_OWNER_USERNAME
```

Enter credentials only into the interactive terminal prompts. Do not put passwords in source files, environment templates, shell command arguments, or chat. Django Admin is restricted to active superusers. The React dashboard and API also verify superuser privileges on every protected operation; hiding a dashboard link is not an authorization control.

## Manage brokers

1. Sign in with an active Django superuser or an active delegated administrator and open **Manage brokers** from `/dashboard`.
2. The page and `/api/v1/admin/delegated-accounts/` can invite, inspect, update, or deactivate broker accounts only. Administrators cannot manage customers or other administrators through the application.
3. Broker invitations receive all marketplace-operational permissions by default. Approved brokers can manage listings and viewing requests across the marketplace, review reports, assign brokers, manage brokerage settings, and access operational statistics and audit records. Broker accounts cannot manage users.
4. Share the one-time invitation token privately. The token is displayed only once and is never written to audit records. The invitee opens `/accept-invitation`, pastes the token, and chooses a password. The invitation expires after 48 hours and can only be used once.
5. Broker assignments remain useful for attribution and workflows, but they do not restrict an approved broker's operational visibility or management scope. A broker who creates a listing is automatically assigned to it.

The project does not currently send invitation emails. Until an email provider is configured, the owner must securely relay the one-time token to the intended invitee.

## Permission behavior

Permissions are defined in `accounts.models.Profile.Permission`. Active Django superusers receive all platform-management permissions through the API. Delegated administrators can manage broker accounts only; approved brokers receive marketplace-operational permissions by role, including for older accounts whose saved permission list is incomplete. The current deployment is a single marketplace scope, not city- or territory-isolated: a broker with operational access can act on all broker-managed listings in this deployment. Add explicit broker territory boundaries before operating multiple city-specific teams in one shared deployment. Property ownership or a prior listing submission alone does not grant management access. Only published broker-managed listings appear in public search.

Approved brokers can use `/management/brokerage` to update the centrally displayed business name, phone, email, and social links, and to create, edit, publish, or unpublish homepage announcements. Public contact channels are displayed only when the brokerage has configured them; no fallback phone number, messaging account, or social handle is shown. Homepage announcements are broker-written and do not appear publicly until published.

Deactivating an account takes effect on subsequent authenticated requests. Broker operational permissions are granted by the approved broker role and are not individually configurable. Role and account changes and invitations are written to the audit log without recording passwords or invitation tokens.

## Verification

After pulling code or changing dependencies:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
```

Do not run migrations against production until a database backup and deployment window are arranged.

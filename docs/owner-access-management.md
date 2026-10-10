# Owner and delegated account management

## Initial owner account

The platform owner is the Django superuser and the only principal with platform-owner authority. Property owner accounts do not automatically manage listings, viewing requests, or brokerage settings. Provision or recover the platform-owner account locally with Django's built-in commands:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py changepassword YOUR_OWNER_USERNAME
```

Enter credentials only into the interactive terminal prompts. Do not put passwords in source files, environment templates, shell command arguments, or chat. Only the owner can sign in to Django Admin at `/admin/` or use the legacy owner portal's property pages. Viewing requests are managed in the broker workspace; the Django admin and legacy owner portal no longer expose viewing-request management. Delegated administrators have access only to broker-account management.

## Manage administrators and brokers

1. Sign in as the owner and open `/admin-portal/delegated-accounts/`.
2. The owner can invite administrators or brokers and deactivate either account type. Role-based permissions are fixed: delegated administrators manage broker accounts; approved brokers manage marketplace operations.
3. An active delegated administrator can use the same page and `/api/v1/admin/delegated-accounts/` to invite, inspect, update, or deactivate broker accounts only. Broker-account access is inherent to the administrator role and does not depend on a stored `users.manage` permission. Administrators cannot create or manage other administrators, customers, property listings, viewing requests, reports, announcements, or platform settings.
4. Administrator-created broker invitations receive all marketplace-operational permissions by default. Approved brokers can manage listings and viewing requests across the marketplace, review owner announcements and reports, assign brokers, manage brokerage settings, and access operational statistics and audit records. User and delegated-account management remain unavailable to brokers.
5. Share the one-time invitation token privately. The token is displayed only once and is never written to audit records. The invitee opens `/accept-invitation`, pastes the token, and chooses a password. The invitation expires after 48 hours and can only be used once.
6. Broker assignments remain useful for attribution and workflows, but they do not restrict an approved broker's operational visibility or management scope. A broker who creates a listing is automatically assigned to it.

The project does not currently send invitation emails. Until an email provider is configured, the owner must securely relay the one-time token to the intended invitee.

## Permission behavior

Permissions are defined in `accounts.models.Profile.Permission`. A delegated administrator can manage broker accounts only, even if a legacy permission record contains other permissions. Approved brokers receive marketplace-operational permissions by role, including for older accounts whose saved permission list is incomplete. Neither delegated administrators nor brokers can manage delegated accounts; that control remains platform-owner-only. The current deployment is a single marketplace scope, not city- or territory-isolated: a broker with operational access can act on all broker-managed listings in this deployment. Add explicit broker territory boundaries before operating multiple city-specific teams in one shared deployment. Property ownership or listing submission alone does not grant management access. Broker-managed listings display brokerage contact channels only. Owner-announced listings use the separate agreement-controlled public contact workflow described in [owner-announcements.md](./owner-announcements.md).

The brokerage contact page at `/management/brokerage` updates the centrally displayed business name, phone, email, messaging, and social links. Configure only channels the brokerage actually controls.

Deactivating an account takes effect on subsequent authenticated requests. Broker operational permissions are granted by the approved broker role and are not individually configurable. Role and account changes and invitations are written to the audit log without recording passwords or invitation tokens.

## Verification

After pulling code or changing dependencies:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
```

Do not run migrations against production until a database backup and deployment window are arranged.

# Owner and delegated account management

## Initial owner account

The platform owner is the Django superuser and the only principal with platform-owner authority. Property owner accounts do not automatically manage listings, viewing requests, or brokerage settings. Provision or recover the platform-owner account locally with Django's built-in commands:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py changepassword YOUR_OWNER_USERNAME
```

Enter credentials only into the interactive terminal prompts. Do not put passwords in source files, environment templates, shell command arguments, or chat. Only the owner can sign in to Django Admin at `/admin/` or use the legacy owner portal's property and viewing-request pages. Authorized administrators have access only to its delegated broker-account page.

## Manage administrators and brokers

1. Sign in as the owner and open `/admin-portal/delegated-accounts/`.
2. The owner can invite administrators or brokers, grant permissions, and deactivate either account type.
3. An active delegated administrator can use the same page and `/api/v1/admin/delegated-accounts/` to invite, inspect, update, or deactivate broker accounts only. Broker-account access is inherent to the administrator role and does not depend on a stored `users.manage` permission. Administrators cannot create or manage other administrators, customers, property listings, viewing requests, reports, announcements, or platform settings.
4. Administrator-created broker invitations receive assigned-listing, assigned-viewing, and owner-announcement-review permissions by default. Administrators can grant brokers only these broker-work permissions.
5. Share the one-time invitation token privately. The token is displayed only once and is never written to audit records. The invitee opens `/accept-invitation`, pastes the token, and chooses a password. The invitation expires after 48 hours and can only be used once.
6. Assign brokers only to the relevant properties. Assigned-work permissions do not grant access to other listings or viewing requests. A broker who creates a listing is automatically assigned to it.

The project does not currently send invitation emails. Until an email provider is configured, the owner must securely relay the one-time token to the intended invitee.

## Permission behavior

Permissions are a predefined list in `accounts.models.Profile.Permission`. An active staff account must also have the administrator profile role to manage broker accounts; administrators are restricted to that work even if a legacy permission record contains other permissions. The API reports effective role permissions so old administrator records without `users.manage` still display the correct access. Brokers handle assigned listings and viewing requests; API operations check both the relevant permission and property assignment. Property ownership or listing submission alone does not grant management access. Broker-managed listings display brokerage contact channels only. Owner-announced listings use the separate agreement-controlled public contact workflow described in [owner-announcements.md](./owner-announcements.md).

The brokerage contact page at `/management/brokerage` updates the centrally displayed business name, phone, email, messaging, and social links. Configure only channels the brokerage actually controls.

Deactivating an account or removing its permissions takes effect on subsequent authenticated requests. Permission changes and account invitations are written to the audit log without recording passwords or invitation tokens.

## Verification

After pulling code or changing dependencies:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
```

Do not run migrations against production until a database backup and deployment window are arranged.

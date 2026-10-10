# Owner and delegated account management

## Initial owner account

The platform owner is the Django superuser and the only principal with platform-owner authority. Property owner accounts do not automatically manage listings, viewing requests, or brokerage settings. Provision or recover the platform-owner account locally with Django's built-in commands:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py changepassword YOUR_OWNER_USERNAME
```

Enter credentials only into the interactive terminal prompts. Do not put passwords in source files, environment templates, shell command arguments, or chat. The owner can sign in to Django Admin at `/admin/`; ordinary staff accounts are explicitly blocked from that interface and from the legacy owner portal.

## Invite an administrator or broker

1. Sign in as the owner and open `/admin-portal/delegated-accounts/`.
2. Choose Administrator or Broker, enter a username and email, and select only the permissions needed for the role.
3. Share the one-time invitation token privately. The token is displayed only once and is never written to audit records.
4. The invitee opens `/accept-invitation`, pastes the token, and chooses a password. The invitation expires after 48 hours and can only be used once.
5. Assign brokers only to the relevant properties. Assigned-work permissions do not grant access to other listings or viewing requests.

The project does not currently send invitation emails. Until an email provider is configured, the owner must securely relay the one-time token to the intended invitee.

## Permission behavior

Permissions are a predefined list in `accounts.models.Profile.Permission`. A delegated account does not receive access just because `is_staff` is true. API operations check the specific permission and, for brokers, the property assignment. Listing and viewing-request operations are restricted to the platform broker and explicitly authorized staff; property ownership or listing submission alone does not grant management access. Broker-managed listings display brokerage contact channels only. Owner-announced listings use the separate agreement-controlled public contact workflow described in [owner-announcements.md](./owner-announcements.md). Only the platform owner can create delegated accounts or change their role, permissions, or active state.

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

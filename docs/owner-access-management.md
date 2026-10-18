# Owner and delegated account management

## Django administrator

Customers, agents, delegated administrators, and Django superusers use the same React sign-in page. After sign-in, `/dashboard` shows actions permitted for that account. Protected React pages and API operations enforce their permissions on the server; hiding a dashboard link is not an authorization control. Django Admin at `/admin/` remains available as an optional interface and uses Django's own session sign-in.

Create or recover the Django superuser locally with Django's built-in commands:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py changepassword YOUR_OWNER_USERNAME
```

Enter credentials only into the interactive terminal prompts. Do not put passwords in source files, environment templates, shell command arguments, or chat. Django Admin is restricted to active superusers. The React dashboard and API also verify superuser privileges on every protected operation; hiding a dashboard link is not an authorization control.

## Manage agents

1. Sign in with an active Django superuser or an active delegated administrator and open **Manage agents** from `/dashboard`.
2. The page and `/api/v1/admin/delegated-accounts/` can invite, inspect, update, or deactivate agent accounts only. Administrators cannot manage customers or other administrators through the application.
3. New agents receive the existing marketplace-operational permissions by default. The platform owner may separately grant an agent permission to manage public contact/social settings. Agent accounts cannot manage users.
4. Share the one-time invitation token privately. The token is displayed only once and is never written to audit records. The invitee opens `/accept-invitation`, pastes the token, and chooses a password. The invitation expires after 48 hours and can only be used once.
5. Agent assignments remain useful for attribution and workflows, but they do not restrict an approved agent's operational visibility or management scope. An agent who creates a listing is automatically assigned to it.

The project does not currently send invitation emails. Until an email provider is configured, the owner must securely relay the one-time token to the intended invitee.

## Permission behavior

Permissions are defined in `accounts.models.Profile.Permission`; the internal `AGENT` role name remains for compatibility. Delegated administrators can manage agent accounts but cannot grant owner-only permissions. Approved agents receive marketplace-operational permissions by role, including for older accounts whose saved permission list is incomplete. Agent management of listings and owner submissions is scoped to the assigned city. Property ownership or a prior listing submission alone does not grant management access. Public owner-announced listings require an approved submission and active agreement; agent-managed listings must be published and available.

Only the designated active Django superuser (the platform owner) can grant or revoke `settings.manage` on an agent account. Approved agents with that explicit permission, and the platform owner, can use `/management/brokerage` to update public business contact/social links and homepage announcements. Other superusers, delegated administrators, and other agents are denied by the settings API. Social links are stored per platform, require HTTPS, and can be disabled without deleting the saved URL. Public contact channels are displayed only when configured and enabled; no fallback phone number, messaging account, or social handle is shown. Homepage announcements remain unpublished until explicitly published.

Deactivating an account takes effect on subsequent authenticated requests. Role and account changes, including permission changes, and invitations are written to the audit log without recording passwords or invitation tokens.

## Verification

After pulling code or changing dependencies:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
```

Do not run migrations against production until a database backup and deployment window are arranged.

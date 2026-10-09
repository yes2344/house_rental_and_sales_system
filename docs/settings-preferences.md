# Personal settings and preferences

The Settings page at `/settings` currently manages personal display and accessibility preferences:

- `theme`: `light`, `dark`, or `system` (default).
- `locale`: `en` or `am` (default `en`).
- `density`: `comfortable` or `compact` (default `comfortable`).
- `reduced_motion`: a Boolean, default `false`. A false value still respects the browser's reduced-motion preference.

Anonymous visitors store these non-sensitive preferences in the browser's `localStorage` under `habesha-homes-guest-preferences`. They do not get an account or server-side profile created. Authenticated users use their own `UserPreferences` record and retain those values across devices. On sign-in, the account's saved preferences take precedence; guest preferences are not silently copied into the account.

The session-authenticated API exposes:

- `GET /api/v1/auth/preferences/`
- `PATCH /api/v1/auth/preferences/`
- `POST /api/v1/auth/preferences/reset/`

These endpoints operate only on `request.user`'s preferences. The API rejects unsupported fields and values; role, management permissions, global settings, and account security data are not writable through this API. Reset affects only the current user's preferences.

Dark mode is applied using shared theme tokens and follows the operating-system color scheme when `theme` is `system`. Compact density adjusts supported controls and panels. Reduced motion limits transitions and animations while preserving focus indicators and keyboard use.

The frontend has English and Amharic resource catalogs, but translation coverage is not complete across every screen. Property text and other user-generated content are never translated. Notification delivery configuration, password changes, session history, two-step verification, role-specific work preferences, and platform-wide settings are not implemented by this feature and are not presented as available controls.

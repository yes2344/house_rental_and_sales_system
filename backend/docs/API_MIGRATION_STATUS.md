# Node API coverage after Django removal

This inventory preserves the 73-route API surface from the previous Django
application as a checklist; Django source and runtime configuration have been
removed. The route list is historical, not an active fallback. Any row marked
Pending is unavailable until implemented in Node. Methods for pending rows
were captured from the prior API and still require behavior verification.
"Implemented" means a Node handler and automated tests exist, not that
production parity has been approved.

| Previous API path | Node path | Status |
|---|---|---|
| `homepage-notes/` | `GET /api/v1/homepage-notes/` | Pending |
| `public-pages/<slug:page>/` | `GET /api/v1/public-pages/:page/` | Pending |
| `brokerage/contact/` | `GET /api/v1/brokerage/contact/` | Pending |
| `reports/` | `POST /api/v1/reports/` | Pending |
| `auth/csrf/` | `GET /api/v1/auth/csrf/` | Implemented; unit tested |
| `auth/register/` | `POST /api/v1/auth/register/` | Implemented; validation tested |
| `auth/verify-email/` | `POST /api/v1/auth/verify-email/` | Pending |
| `auth/verify-email/resend/` | `POST /api/v1/auth/verify-email/resend/` | Pending |
| `auth/password-reset/` | `POST /api/v1/auth/password-reset/` | Pending |
| `auth/password-reset/confirm/` | `POST /api/v1/auth/password-reset/confirm/` | Pending |
| `auth/invitations/accept/` | `POST /api/v1/auth/invitations/accept/` | Pending |
| `auth/login/` | `POST /api/v1/auth/login/` | Implemented; unit tested |
| `auth/agent-onboarding/password/` | `POST /api/v1/auth/agent-onboarding/password/` | Pending |
| `auth/agent-onboarding/profile/` | `POST /api/v1/auth/agent-onboarding/profile/` | Pending |
| `auth/logout/` | `POST /api/v1/auth/logout/` | Implemented; unit tested |
| `auth/me/` | `GET, PATCH /api/v1/auth/me/` | Implemented; GET/session contract tested |
| `auth/preferences/` | `GET, PATCH /api/v1/auth/preferences/` | Implemented; validation tested |
| `auth/preferences/reset/` | `POST /api/v1/auth/preferences/reset/` | Implemented; not yet integration tested |
| `auth/activity/` | `GET /api/v1/auth/activity/` | Implemented; not yet integration tested |
| `favorites/` | `GET, POST /api/v1/favorites/` | Pending |
| `favorites/<int:property_id>/` | `DELETE /api/v1/favorites/:property_id/` | Pending |
| `amenities/` | `GET /api/v1/amenities/` | Implemented; local read-only DB exercised |
| `locations/` | `GET /api/v1/locations/` | Pending |
| `property-types/` | `GET /api/v1/property-types/` | Implemented |
| `management/locations/` | `GET, POST /api/v1/management/locations/` | Pending |
| `management/locations/<int:pk>/` | `GET, PATCH, DELETE /api/v1/management/locations/:pk/` | Pending |
| `notifications/` | `GET /api/v1/notifications/` | Pending |
| `notifications/<int:pk>/read/` | `POST /api/v1/notifications/:pk/read/` | Pending |
| `submissions/` | `GET, POST /api/v1/submissions/` | Pending |
| `submissions/bulk-delete/` | `POST /api/v1/submissions/bulk-delete/` | Pending |
| `submissions/<int:pk>/` | `GET, PATCH, DELETE /api/v1/submissions/:pk/` | Pending |
| `submissions/<int:submission_id>/images/` | `GET, POST /api/v1/submissions/:submission_id/images/` | Implemented; image upload tests use isolated storage and mocked PostgreSQL |
| `management/submissions/` | `GET /api/v1/management/submissions/` | Pending |
| `management/submissions/bulk-delete/` | `POST /api/v1/management/submissions/bulk-delete/` | Pending |
| `management/submissions/reviewers/` | `GET /api/v1/management/submissions/reviewers/` | Pending |
| `management/submissions/<int:pk>/` | `GET, PATCH /api/v1/management/submissions/:pk/` | Pending |
| `management/submissions/<int:pk>/assignment/` | `POST /api/v1/management/submissions/:pk/assignment/` | Pending |
| `management/submissions/<int:pk>/decision/` | `POST /api/v1/management/submissions/:pk/decision/` | Pending |
| `properties/` | `GET /api/v1/properties/` | Implemented; local read-only DB exercised |
| `properties/<slug:slug>/` | `GET /api/v1/properties/:slug/` | Implemented; local read-only DB exercised |
| `viewing-requests/` | `POST /api/v1/viewing-requests/` | Pending |
| `viewing-requests/receipt/` | `GET /api/v1/viewing-requests/receipt/` | Pending |
| `viewing-requests/mine/` | `GET /api/v1/viewing-requests/mine/` | Pending |
| `viewing-requests/mine/<int:pk>/` | `GET /api/v1/viewing-requests/mine/:pk/` | Pending |
| `viewing-requests/mine/<int:pk>/respond/` | `POST /api/v1/viewing-requests/mine/:pk/respond/` | Pending |
| `viewing-requests/mine/<int:pk>/cancel/` | `POST /api/v1/viewing-requests/mine/:pk/cancel/` | Pending |
| `management/properties/` | `GET /api/v1/management/properties/` | Implemented; listing and authorization tested |
| `management/properties/` | `POST /api/v1/management/properties/` | Pending |
| `management/properties/bulk-delete/` | `POST /api/v1/management/properties/bulk-delete/` | Pending |
| `management/homepage-notes/` | `GET, POST /api/v1/management/homepage-notes/` | Pending |
| `management/homepage-notes/<int:pk>/` | `GET, PATCH, DELETE /api/v1/management/homepage-notes/:pk/` | Pending |
| `management/public-pages/` | `GET /api/v1/management/public-pages/` | Pending |
| `management/public-pages/<slug:page>/` | `GET, PATCH /api/v1/management/public-pages/:page/` | Pending |
| `management/properties/<int:pk>/` | `GET, PATCH, DELETE /api/v1/management/properties/:pk/` | Pending |
| `management/properties/<int:pk>/publication/` | `POST /api/v1/management/properties/:pk/publication/` | Pending |
| `management/properties/<int:property_id>/images/` | `GET, POST /api/v1/management/properties/:property_id/images/` | Implemented; authorization and local upload tests use isolated storage and mocked PostgreSQL |
| `management/properties/<int:property_id>/images/<int:pk>/` | `GET, PATCH, DELETE /api/v1/management/properties/:property_id/images/:pk/` | Implemented for PATCH and DELETE; also supports PUT file replacement; tested with mocked PostgreSQL |
| `management/images/<int:pk>/original/` | `GET /api/v1/management/images/:pk/original/` | Implemented; original bytes remain private; route denial tested |
| `management/viewing-requests/` | `GET /api/v1/management/viewing-requests/` | Pending |
| `management/viewing-requests/<int:pk>/` | `GET /api/v1/management/viewing-requests/:pk/` | Pending |
| `management/viewing-requests/<int:pk>/action/` | `POST /api/v1/management/viewing-requests/:pk/action/` | Pending |
| `admin/users/` | `GET /api/v1/admin/users/` | Pending |
| `admin/users/<int:pk>/` | `GET, PATCH /api/v1/admin/users/:pk/` | Pending |
| `admin/public-accounts/` | `GET, POST /api/v1/admin/public-accounts/` | Pending |
| `admin/public-accounts/<int:pk>/` | `GET, PATCH, DELETE /api/v1/admin/public-accounts/:pk/` | Pending |
| `admin/delegated-accounts/` | `GET, POST /api/v1/admin/delegated-accounts/` | Pending |
| `admin/delegated-accounts/<int:pk>/` | `GET, PATCH, DELETE /api/v1/admin/delegated-accounts/:pk/` | Pending |
| `admin/properties/` | `GET /api/v1/admin/properties/` | Pending |
| `admin/properties/<int:pk>/` | `GET, PATCH /api/v1/admin/properties/:pk/` | Pending |
| `admin/properties/<int:property_id>/agents/` | `GET, POST /api/v1/admin/properties/:property_id/agents/` | Pending |
| `admin/properties/<int:property_id>/agents/<int:agent_id>/` | `DELETE /api/v1/admin/properties/:property_id/agents/:agent_id/` | Pending |
| `admin/reports/` | `GET /api/v1/admin/reports/` | Pending |
| `admin/reports/<int:pk>/` | `GET, PATCH /api/v1/admin/reports/:pk/` | Pending |
| `admin/audit-events/` | `GET /api/v1/admin/audit-events/` | Pending |

## Current implementation scope and limitations

- The frontend now sends all requests to Node. It no longer falls back to a
  Django service; pending routes return 404.
- Authentication/account handlers cover CSRF issuance, public registration,
  login, logout, current-account read/update, preferences, reset, and activity.
  Email verification, password reset, invitations, and agent onboarding remain
  pending.
- Existing `pbkdf2_sha256` hashes are verified without changing them. New
  registrations use the compatible PBKDF2-SHA256 encoding and 1,000,000
  rounds. Existing-hash verification and encoding are unit tested. The common
  password list and all attribute-similarity edge cases have not yet been
  ported.
- Public property SQL enforces the published/status and owner-agreement
  eligibility rules, validates filters, uses parameterized SQL, and returns
  DRF-shaped pagination. The richer Django natural-language search concept
  parser has not been ported; query terms currently perform literal text
  matching. Node local-media routes, safe image storage/serving, and the
  existing-media audit are implemented; real restart and full-stack media
  persistence testing remains pending.
- Rate-limit counters are process-local. A multi-instance deployment needs a
  shared store or an approved database-backed implementation before cutover.
- See [`../../docs/frontend-node-integration.md`](../../docs/frontend-node-integration.md)
  for the frontend's single Node API target and remaining route gaps.
- Live SQL smoke checks were read-only against the local PostgreSQL 18.6
  candidate; its production authority is still unconfirmed. PostgreSQL 13,
  media availability, and all mutation flows remain unverified.

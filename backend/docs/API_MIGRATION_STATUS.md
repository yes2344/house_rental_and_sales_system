# Node API coverage after Django removal

This inventory preserves the 73 URL patterns from the previous Django
application; Django source and runtime configuration have been removed. The
route list is historical, not an active fallback. The Node implementation now
has handlers for the listed paths and methods. Automated tests use mocked
PostgreSQL and do not certify behavior against the HahuCloud database.

| Previous API path | Node path | Status |
|---|---|---|
| `homepage-notes/` | `GET /api/v1/homepage-notes/` | Implemented; workflow tested |
| `public-pages/<slug:page>/` | `GET /api/v1/public-pages/:page/` | Implemented; workflow tested |
| `brokerage/contact/` | `GET, PATCH /api/v1/brokerage/contact/` | Implemented; validation, authorization, and update tested |
| `reports/` | `POST /api/v1/reports/` | Implemented; workflow tested |
| `auth/csrf/` | `GET /api/v1/auth/csrf/` | Implemented; unit tested |
| `auth/register/` | `POST /api/v1/auth/register/` | Implemented; validation tested |
| `auth/verify-email/` | `POST /api/v1/auth/verify-email/` | Implemented; workflow tested with mocked SMTP |
| `auth/verify-email/resend/` | `POST /api/v1/auth/verify-email/resend/` | Implemented; workflow tested with mocked SMTP |
| `auth/password-reset/` | `POST /api/v1/auth/password-reset/` | Implemented; workflow tested with mocked SMTP |
| `auth/password-reset/confirm/` | `POST /api/v1/auth/password-reset/confirm/` | Implemented; workflow tested |
| `auth/invitations/accept/` | `POST /api/v1/auth/invitations/accept/` | Implemented; workflow tested |
| `auth/login/` | `POST /api/v1/auth/login/` | Implemented; unit tested |
| `auth/agent-onboarding/password/` | `POST /api/v1/auth/agent-onboarding/password/` | Implemented; workflow tested |
| `auth/agent-onboarding/profile/` | `POST /api/v1/auth/agent-onboarding/profile/` | Implemented; workflow tested |
| `auth/logout/` | `POST /api/v1/auth/logout/` | Implemented; unit tested |
| `auth/me/` | `GET, PATCH /api/v1/auth/me/` | Implemented; GET/session contract tested |
| `auth/preferences/` | `GET, PATCH /api/v1/auth/preferences/` | Implemented; validation tested |
| `auth/preferences/reset/` | `POST /api/v1/auth/preferences/reset/` | Implemented; not yet integration tested |
| `auth/activity/` | `GET /api/v1/auth/activity/` | Implemented; not yet integration tested |
| `favorites/` | `GET, POST /api/v1/favorites/` | Implemented; workflow tested |
| `favorites/<int:property_id>/` | `DELETE /api/v1/favorites/:property_id/` | Implemented; ownership and deletion tested |
| `amenities/` | `GET /api/v1/amenities/` | Implemented; local read-only DB exercised |
| `locations/` | `GET /api/v1/locations/` | Implemented; query tested |
| `property-types/` | `GET /api/v1/property-types/` | Implemented |
| `management/locations/` | `GET, POST /api/v1/management/locations/` | Implemented; authorization and workflows tested |
| `management/locations/<int:pk>/` | `GET, PATCH, DELETE /api/v1/management/locations/:pk/` | Implemented; authorization and workflows tested |
| `notifications/` | `GET /api/v1/notifications/` | Implemented; recipient scope tested |
| `notifications/<int:pk>/read/` | `POST /api/v1/notifications/:pk/read/` | Implemented; recipient scope tested |
| `submissions/` | `GET, POST /api/v1/submissions/` | Implemented; workflow tested |
| `submissions/bulk-delete/` | `POST /api/v1/submissions/bulk-delete/` | Implemented; workflow tested |
| `submissions/<int:pk>/` | `GET, PATCH /api/v1/submissions/:pk/` | Implemented; ownership and update tested |
| `submissions/<int:submission_id>/images/` | `GET, POST /api/v1/submissions/:submission_id/images/` | Implemented; image upload tests use isolated storage and mocked PostgreSQL |
| `management/submissions/` | `GET /api/v1/management/submissions/` | Implemented; workflow tested |
| `management/submissions/bulk-delete/` | `POST /api/v1/management/submissions/bulk-delete/` | Implemented; workflow tested |
| `management/submissions/reviewers/` | `GET /api/v1/management/submissions/reviewers/` | Implemented; authorization tested |
| `management/submissions/<int:pk>/` | `GET /api/v1/management/submissions/:pk/` | Implemented; reviewer scope tested |
| `management/submissions/<int:pk>/assignment/` | `POST /api/v1/management/submissions/:pk/assignment/` | Implemented; workflow tested |
| `management/submissions/<int:pk>/decision/` | `POST /api/v1/management/submissions/:pk/decision/` | Implemented; workflow tested |
| `properties/` | `GET /api/v1/properties/` | Implemented; local read-only DB exercised |
| `properties/<slug:slug>/` | `GET /api/v1/properties/:slug/` | Implemented; local read-only DB exercised |
| `viewing-requests/` | `POST /api/v1/viewing-requests/` | Implemented; transaction and eligibility tested |
| `viewing-requests/receipt/` | `GET, POST /api/v1/viewing-requests/receipt/` | Implemented; private receipt workflow tested |
| `viewing-requests/mine/` | `GET /api/v1/viewing-requests/mine/` | Implemented; requester scope tested |
| `viewing-requests/mine/<int:pk>/` | `GET, PATCH, DELETE /api/v1/viewing-requests/mine/:pk/` | Implemented; ownership and soft-delete tested |
| `viewing-requests/mine/<int:pk>/respond/` | `POST /api/v1/viewing-requests/mine/:pk/respond/` | Implemented; workflow tested |
| `viewing-requests/mine/<int:pk>/cancel/` | `POST /api/v1/viewing-requests/mine/:pk/cancel/` | Implemented; workflow tested |
| `management/properties/` | `GET /api/v1/management/properties/` | Implemented; listing and authorization tested |
| `management/properties/` | `POST /api/v1/management/properties/` | Implemented; validation and workflow tested |
| `management/properties/bulk-delete/` | `POST /api/v1/management/properties/bulk-delete/` | Implemented; authorization and workflow tested |
| `management/homepage-notes/` | `GET, POST /api/v1/management/homepage-notes/` | Implemented; workflow tested |
| `management/homepage-notes/<int:pk>/` | `GET, PATCH, DELETE /api/v1/management/homepage-notes/:pk/` | Implemented; workflow tested |
| `management/public-pages/` | `GET /api/v1/management/public-pages/` | Implemented; authorization tested |
| `management/public-pages/<slug:page>/` | `GET, PATCH /api/v1/management/public-pages/:page/` | Implemented; validation and workflow tested |
| `management/properties/<int:pk>/` | `GET, PATCH, DELETE /api/v1/management/properties/:pk/` | Implemented; authorization and workflow tested |
| `management/properties/<int:pk>/publication/` | `POST /api/v1/management/properties/:pk/publication/` | Implemented; workflow tested |
| `management/properties/<int:property_id>/images/` | `GET, POST /api/v1/management/properties/:property_id/images/` | Implemented; authorization and local upload tests use isolated storage and mocked PostgreSQL |
| `management/properties/<int:property_id>/images/<int:pk>/` | `GET, PATCH, DELETE /api/v1/management/properties/:property_id/images/:pk/` | Implemented for PATCH and DELETE; also supports PUT file replacement; tested with mocked PostgreSQL |
| `management/images/<int:pk>/original/` | `GET /api/v1/management/images/:pk/original/` | Implemented; original bytes remain private; route denial tested |
| `management/viewing-requests/` | `GET /api/v1/management/viewing-requests/` | Implemented; scope tested |
| `management/viewing-requests/<int:pk>/` | `GET, PATCH /api/v1/management/viewing-requests/:pk/` | Implemented; workflow tested |
| `management/viewing-requests/<int:pk>/action/` | `POST /api/v1/management/viewing-requests/:pk/action/` | Implemented; workflow tested |
| `admin/users/` | `GET /api/v1/admin/users/` | Implemented; authorization tested |
| `admin/users/<int:pk>/` | `GET, PATCH /api/v1/admin/users/:pk/` | Implemented; validation and workflow tested |
| `admin/public-accounts/` | `GET, POST /api/v1/admin/public-accounts/` | Implemented; workflow tested |
| `admin/public-accounts/<int:pk>/` | `GET, PATCH, DELETE /api/v1/admin/public-accounts/:pk/` | Implemented; workflow tested |
| `admin/delegated-accounts/` | `GET, POST /api/v1/admin/delegated-accounts/` | Implemented; workflow tested |
| `admin/delegated-accounts/<int:pk>/` | `GET, PATCH, DELETE /api/v1/admin/delegated-accounts/:pk/` | Implemented; workflow tested |
| `admin/properties/` | `GET /api/v1/admin/properties/` | Implemented; authorization tested |
| `admin/properties/<int:pk>/` | `GET, PATCH /api/v1/admin/properties/:pk/` | Implemented; validation and workflow tested |
| `admin/properties/<int:property_id>/agents/` | `GET, POST /api/v1/admin/properties/:property_id/agents/` | Implemented; workflow tested |
| `admin/properties/<int:property_id>/agents/<int:agent_id>/` | `DELETE /api/v1/admin/properties/:property_id/agents/:agent_id/` | Implemented; workflow tested |
| `admin/reports/` | `GET /api/v1/admin/reports/` | Implemented; authorization tested |
| `admin/reports/<int:pk>/` | `GET, PATCH /api/v1/admin/reports/:pk/` | Implemented; workflow tested |
| `admin/audit-events/` | `GET /api/v1/admin/audit-events/` | Implemented; authorization tested |

## Current implementation scope and limitations

- The frontend now sends all requests to Node. It no longer falls back to a
  Django service.
- Authentication/account handlers cover CSRF issuance, public registration,
  login, logout, current-account read/update, preferences, reset, and activity.
  Email verification, password reset, invitations, and agent onboarding use
  SMTP, which still needs private production configuration and provider testing.
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
- HahuCloud PostgreSQL 13.23 is permitted by the version gates as a temporary
  compatibility exception after source review found no obvious PostgreSQL
  14/15-only application SQL. PostgreSQL 13 is end-of-life upstream, and the
  backend has not been integration-tested on PostgreSQL 13.23. Do not consider
  this full compatibility certification; verify on an isolated 13.23 instance
  and upgrade to an upstream-supported PostgreSQL major version as soon as the
  provider permits.
- The deployment target is an existing Django-derived schema; there is no
  empty-database bootstrap migration. The local PostgreSQL 18.6 catalog is not
  evidence about HahuCloud's schema. The additive Node migration is tested
  with mocked PostgreSQL and has not been applied to the target.
- HahuCloud must confirm that public and private media volumes are separate
  and persistent. A staging restart test, live SMTP test, and end-to-end
  mutation checks against a verified staging copy remain necessary.

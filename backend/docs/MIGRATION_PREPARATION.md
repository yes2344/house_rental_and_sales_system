# Infinity House migration preparation

## Preparation status

The repository evidence and an approved, read-only inspection of a local
PostgreSQL candidate are recorded here. No source-database writes or production
cutover were performed.

The checked-in Django configuration currently selects MySQL, not PostgreSQL:

- `house/settings.py` constructs `DATABASES` using required `MYSQL_*` values
  and the `django.db.backends.mysql` engine.
- The ignored root `.env` and checked-in `.env.example` contain MySQL
  configuration names. Their values and all secrets were deliberately not
  printed or copied.
- The ignored `.env.backup` contains a PostgreSQL URL candidate targeting
  `localhost:5432`, database `debre_markos_real_estate`. This is saved
  configuration, not proof that it is the authoritative production source.
- A read-only Node `pg` inspection connected to that candidate at `[::1]:5432`.
  It reported PostgreSQL `18.6`, database `debre_markos_real_estate`, schema
  `public`, and `transaction_read_only=on`. This identifies the local endpoint
  only; the user has not confirmed it is the authoritative production source.
- The inspecting role was `postgres`, a superuser. The commands used read-only
  transactions, but this role must not be used by the Node application. Create
  and approve a least-privilege application role before implementation.
- The catalog contains 34 tables, 291 columns, 142 indexes, 32 sequences, 47
  foreign keys, 34 primary keys, 24 unique constraints, 29 check constraints,
  and 250 NOT NULL constraints (also surfaced by PostgreSQL 18 catalogs).
  Exact catalog metadata is in
  [`POSTGRESQL_CATALOG_SNAPSHOT.md`](./POSTGRESQL_CATALOG_SNAPSHOT.md).
- A custom-format database backup was created and inspected. It was restored
  to the separate verification database
  `infinity_house_restore_verify_1792508779750`; source and restore each had
  34 tables and 955 total rows, with no table or row-count mismatches. The
  verification database remains in place; no cleanup was performed.
- The backup contains database data only. Media files were not included.
- The source server was PostgreSQL 18.6, so compatibility with PostgreSQL 13
  and restoration on PostgreSQL 13 remain unverified.

## Repository and branch

The React SPA is in `frontend/`; Node backend preparation is in `backend/`.
The backend is on branch `migration/node-postgres-preparation`, created from
the original `main` HEAD `f454271`. `main` was not moved. Pre-existing
uncommitted Node scaffold changes were carried onto the migration branch and
were not discarded.

## Current Django project apps

| Django app label | Source | Models |
|---|---|---|
| `accounts` | `accounts/models.py` | `Profile`, `UserPreferences`, `TabSessionToken`, `EmailVerificationToken`, `DelegatedAccountInvitation` |
| `properties` | `properties/models.py` | `Location`, `Amenity`, `Property`, `PropertyImage`, `PropertyAgentAssignment`, `ListingReport` |
| `viewings` | `viewings/models.py` | `ViewingRequest`, `ViewingRequestEvent` |
| `favorites` | `favorites/models.py` | `Favorite` |
| `owner_announcements` | `owner_announcements/models.py` | `OwnerAnnouncement`, `OwnerAnnouncementAgreement`, `OwnerAnnouncementEvent`, `InAppNotification` |
| `portal_admin` (Python package `admin`) | `admin/models.py` | `BrokerageSettings`, `SocialMediaLink`, `HomepageNote`, `PublicInformationPage`, `AdminAuditEvent` |
| `user` | `user/models.py` | No independent tables; compatibility re-exports of property and viewing models |

These are 23 project-owned models. The inspected candidate also contains the
implicit property/amenity join table and ten Django auth/contenttypes/session/
admin framework tables, including `auth_user`, `auth_group`,
`auth_permission`, `auth_group_permissions`, `auth_user_groups`,
`auth_user_user_permissions`, `django_content_type`, `django_migrations`,
`django_session`, and `django_admin_log`. The physical schema is captured in
[`POSTGRESQL_CATALOG_SNAPSHOT.md`](./POSTGRESQL_CATALOG_SNAPSHOT.md).

## Logical model/table and field inventory

Field types below describe Django model declarations. Observed PostgreSQL
types, defaults, identity/generated columns, constraints, indexes, and
sequences are captured separately in the catalog snapshot. The snapshot is
from the local candidate and has not been confirmed as the production schema.
`id` is the primary key unless otherwise noted.

### Accounts

| Table / model | Fields and relationships |
|---|---|
| `auth_user` / Django `User` | Built-in username/password/name/email/staff/active/superuser/login/joined columns and group/permission joins; exact deployed schema depends on Django migration history. |
| `accounts_profile` / `Profile` | `id BIGSERIAL`; `user_id` one-to-one FK to `auth_user`; `role` default customer; `phone`; nullable `assigned_city_id` FK to `properties_location`; `agent_approved=false`; `agent_onboarding_required=false`; `agent_password_changed=true`; `management_permissions JSON`; `created_at`; `updated_at`. Check constraints: role is customer/owner/agent/administrator; approval only applies to agents. |
| `accounts_userpreferences` / `UserPreferences` | `id`; one-to-one `user_id`; `theme` default system; `locale` default en; `density` default comfortable; `reduced_motion=false`; created/updated timestamps. |
| `accounts_tabsessiontoken` / `TabSessionToken` | `id`; `user_id` FK; unique `token_digest`; created/expiry/revocation timestamps. Index `(user_id, expires_at)`. |
| `accounts_emailverificationtoken` / `EmailVerificationToken` | `id`; `user_id` FK; email; unique `token_digest`; created/expiry timestamps. Index `(user_id, expires_at)`. |
| `accounts_delegatedaccountinvitation` / `DelegatedAccountInvitation` | `id`; `user_id` FK; unique `token_digest`; nullable `created_by_id` FK to user; expiry/accepted/created timestamps. Index `(user_id, expires_at)`. |

### Properties and locations

| Table / model | Fields and relationships |
|---|---|
| `properties_location` / `Location` | `id`; `name`, `name_am`; JSON aliases `aliases_en`, `aliases_am`; `slug`; `location_type`; nullable self-FK `parent_id` with PROTECT behavior; generated `root_slug_key`; active flag; display order; nullable decimal latitude/longitude. Unique sibling `(parent_id, slug)` and generated root-slug key; paired/range coordinate checks. Index `(parent_id, is_active, display_order)`. |
| `properties_amenity` / `Amenity` | `id`; unique `name`; `name_am`; unique `slug`. |
| `user_property` / `Property` | `id`; title; unique slug; indexed text location; nullable `administrative_location_id` FK to location with PROTECT; nullable coordinates; exact-location-public flag; property type default house; listing type default sale; price; rental frequency default empty; bedrooms/bathrooms/area_sqft defaults 0; nullable area value and area unit default empty; description/features; status default available; publication status default pending_review; service type default agent_managed; featured flag; nullable owner and submitted_by user FKs; advertising authorization and public-contact flags; moderation note; contact name/phone/email; created/updated timestamps. M2M amenities through `user_property_amenities`; assigned agents through `properties_propertyagentassignment`. |
| `user_propertyimage` / `PropertyImage` | `id`; `property_id` FK cascade; public image path; private original path; original filename/content type; caption; `is_primary=false`; generated `primary_property_key`; created timestamp. Unique generated primary slot per property; image count limited to 10 by application logic. |
| `properties_propertyagentassignment` / `PropertyAgentAssignment` | `id`; property and agent FKs cascade; nullable `granted_by_id` user FK; `granted_at`; unique `(property_id, agent_id)`. Index `(agent_id, granted_at)`. |
| `properties_listingreport` / `ListingReport` | `id`; nullable property FK set null; stored property title; reporter name/email; reason; details; status default pending; moderator notes; nullable reviewing-user FK and reviewed timestamp; created timestamp. Index `(status, created_at DESC)`. |
| `user_property_amenities` | Implicit M2M join table between `user_property` and `properties_amenity`; actual candidate columns, keys, and indexes are in the catalog snapshot. |

Property checks include positive price and area; valid property/status/
publication/rental values; sold/rented status compatible with listing type;
paired/ranged coordinates; area-unit/value consistency; and rental frequency
only for rental listings. Search indexes cover publication/status/listing/
creation and administrative-location/public status.

### Favorites, viewings, and owner announcements

| Table / model | Fields and relationships |
|---|---|
| `favorites_favorite` / `Favorite` | `id`; `user_id` FK; `property_id` FK; created timestamp. Unique `(user_id, property_id)`; index `(user_id, created_at DESC)`. |
| `user_viewingrequest` / `ViewingRequest` | `id`; property FK; nullable requester user FK; name/email/phone; preferred/proposed/scheduled date/time values; nullable unique receipt-token digest; guest-response and requester-deleted timestamps; message and agent notes; status default pending; generated nullable `active_requester_key`; created timestamp. Unique `(active_requester_key, property_id)`. |
| `viewings_viewingrequestevent` / `ViewingRequestEvent` | `id`; viewing-request FK; nullable actor user FK; event type; from/to status; nullable proposed date/time; message; created timestamp. |
| `owner_announcements_ownerannouncement` / `OwnerAnnouncement` | `id`; one-to-one property FK; submitter FK; owner and public contact fields; public visibility and authorization flags; accepted-terms timestamp; status default pending_review; agent feedback; submitted/reviewed/renewal timestamps; nullable reviewer and assigned-reviewer FKs; created/updated timestamps. Authorization check; indexes by status/submission, submitter/submission, reviewer/status. |
| `owner_announcements_ownerannouncementagreement` / `OwnerAnnouncementAgreement` | `id`; announcement FK; start/end dates; duration months; terms and renewal conditions; public visibility; status default active; generated nullable active-announcement key; approved-by FK; created timestamp. Checks for date order and duration 1–120; unique active-announcement key; index `(status, end_date)`. |
| `owner_announcements_ownerannouncementevent` / `OwnerAnnouncementEvent` | `id`; announcement FK; nullable actor FK; event type; from/to status; JSON details; created timestamp. Index `(announcement_id, created_at DESC)`. |
| `owner_announcements_inappnotification` / `InAppNotification` | `id`; recipient FK; nullable announcement FK; notification type/message; unique idempotency key; nullable read timestamp; created timestamp. Index `(recipient_id, read_at, created_at DESC)`. |

### Portal settings and content

| Table / model | Fields and relationships |
|---|---|
| `portal_admin_brokeragesettings` / `BrokerageSettings` | Small integer `id` constrained in application to singleton `1`; nullable platform-owner user FK; business/site names; copyright; logo/hero image paths; phone/email; WhatsApp/Telegram/Facebook/Instagram/TikTok/YouTube/LinkedIn URLs; updated timestamp. |
| `portal_admin_socialmedialink` / `SocialMediaLink` | `id`; brokerage FK; platform/url; enabled flag; order; timestamps. Unique `(brokerage_id, platform)`. |
| `portal_admin_homepagenote` / `HomepageNote` | `id`; title/text/image path; published flag; order; timestamps. |
| `portal_admin_publicinformationpage` / `PublicInformationPage` | `id`; unique page key; English/Amharic title, introduction, and body; updated timestamp. |
| `portal_admin_adminauditevent` / `AdminAuditEvent` | `id`; nullable actor FK; actor username snapshot; action/object type/object id; JSON changes; created timestamp. Index `(object_type, object_id)` and created timestamp descending. |

### Constraints, sequences, and migrations

IDs on most models are `BigAutoField` primary keys, backed by sequences on
PostgreSQL. The settings singleton uses a positive small integer key. The
candidate's foreign keys and other database constraints are listed in the
catalog snapshot; target-database parity still requires validation. ORM
behavior includes CASCADE, SET NULL, PROTECT, and one-to-one uniqueness.

The repository has 55 app migration files: accounts 9, portal_admin/admin 15,
properties 15, viewings 7, favorites 1, owner_announcements 4, and user 4.
Migrations contain data migrations and historical table-state preservation.
`properties/migrations/0015_mysql_generated_unique_keys.py` and
`viewings/migrations/0006_mysql_active_request_key.py` define generated-key
unique constraints. The current Django models use generated columns for root
location slugs, primary property images, active viewings, and active
agreements. PostgreSQL 13 supports stored generated columns, but the MySQL-
targeted migration history and actual deployed schema still require validation.

This model inventory is not a substitute for PostgreSQL catalogs. The Node
inspector added for Stage 2 reads column metadata, defaults, identities,
generated expressions, constraints/FKs/checks, indexes, sequences, and grants
in a read-only transaction, without reading application rows.

## Feature-to-Node mapping

Paths are under `backend/src/`. Endpoint-level progress is tracked in
[`API_MIGRATION_STATUS.md`](./API_MIGRATION_STATUS.md). Partial implementations
do not imply role/page parity or cutover readiness.

| Django source and functionality | Proposed Node replacement | Dependencies | Status | Required tests |
|---|---|---|---|---|
| `house/settings.py`, `house/urls.py`, `house/api_urls.py`; global settings and 73 versioned API routes | `src/config/`, `src/routes/index.js`, feature route modules, `src/app.js` | Environment validation, Express, API version/error contract | Health, initial account/session APIs, and public property browse APIs exist; 61 Django paths remain pending | Route/method/response parity; security headers; errors |
| `accounts/models.py`, `accounts/serializers.py`, `accounts/api_views.py`; registration, login/logout, account, email tokens, reset, invitation, onboarding, preferences, activity | `src/controllers/accountController.js`, `src/services/accountService.js`, account validators and auth/CSRF middleware | `pg`, Django PBKDF2, crypto, rate limiting, CSRF/CORS | Partial: CSRF, registration, login/logout, account read/update, preferences/reset, and activity routes exist; email verification/delivery, password reset, invitation, onboarding remain pending | Hash compatibility, auth lifecycle, token expiry/revocation, validation, rate limits |
| `accounts/authentication.py`, `accounts/permissions.py`, `accounts/middleware.py`; bearer authentication and object permissions | `src/middleware/{authenticate,csrf,rateLimit,cors}.js`, account services | Existing tab-scoped hashed bearer tokens; role/ownership lookups | Session authentication and account permission serialization exist; authorization enforcement for management resources is pending | Anonymous/role/owner/agent/admin matrix; CSRF/CORS; revoked tokens |
| `properties/models.py`, `properties/access.py`; listing/location/amenity/image/assignment/report data | `src/services/publicPropertyService.js` and future feature modules | Existing PostgreSQL schema, parameterized SQL, filesystem paths | Public listing read paths implemented; write, media, location management, and admin resources pending | Relationships/constraints, publication/access rules, path safety |
| `properties/views.py`, `properties/serializers.py`, `properties/filters.py`, `properties/search.py`, `properties/location_search.py`; listing/location search and management | `src/controllers/publicPropertyController.js`, `src/services/publicPropertyService.js`, property query validator; additional module routes pending | Query validation, pagination, bilingual search, permissions | Partial: public list/detail, amenities, property types implemented; management, locations, full search-concept parity remain pending | API contract, search/filter/order/pagination, role access |
| `properties/image_processing.py`, `properties/storage.py`; watermarks, originals, file cleanup | `src/modules/media/{routes,service,storage,imageProcessor}.js` | Local durable storage, image library, MIME/content validation | Pending | Upload limits, malformed files, watermarks, private originals, cleanup |
| `viewings/models.py`, `viewings/views.py`, `viewings/serializers.py`, `viewings/notifications.py` | `src/modules/viewings/{routes,controller,service,repository,validator}.js` | PostgreSQL transactions/locking, notification rules | Pending | Guest/customer/manager flows, duplicate active request, event history |
| `favorites/models.py`, `favorites/views.py`, `favorites/serializers.py` | `src/modules/favorites/` | Authentication and unique key | Pending | CRUD, duplicate/idempotency, access isolation |
| `owner_announcements/models.py`, `owner_announcements/api_views.py`, `owner_announcements/serializers.py` | `src/modules/announcements/` | Transactional review workflows, reviewer permissions, notifications | Pending | Owner/reviewer/admin lifecycle and agreement edge cases |
| `admin/models.py`, `admin/api_views.py`, `admin/serializers.py`, `admin/audit.py` | `src/modules/{admin,content,settings,audit}/` | Role checks, uploads, audit persistence | Pending | Admin object scopes, audit events, branding/content CRUD |
| `admin/views.py`, `admin/urls.py`, `admin/staff_forms.py`; legacy server-rendered portal | Keep React dashboards and map to Node APIs; retain URL compatibility as needed | Deployment/live-page confirmation | Pending | Legacy route and role parity |
| `user/views.py`, `user/urls.py`, `templates/user/*`; legacy public pages and viewing forms | Keep React routes; reproduce any live-only legacy pages in React or Express only after use is confirmed | Property/search/viewing APIs | Pending | Route redirects, search, guest flows |
| Django email backend and messages | `src/modules/email/` service behind configurable adapter | SMTP or explicitly approved alternative; core features must degrade clearly | Pending | Delivery failure paths; no silent success without send |
| Django signals/on-commit file cleanup and management commands | Explicit domain services and post-commit actions; scripts under `backend/scripts/` | Transactions and filesystem recovery | Pending | Atomic DB/file behavior; retries and cleanup |
| Django migrations | `backend/db/migrations/*.sql` plus migration runner/checksums | Actual catalog comparison and reviewed migration plan | Not started | PostgreSQL 13 clean/upgrade tests, no-drop assertions, row/ID/FK reconciliation |
| `frontend/src/api/*`, contexts, pages, guards | Preserve `frontend/`; switch API base URL only when endpoints pass parity | Existing response/error contract | Existing UI retained; proxy currently added | Frontend unit/integration, browser E2E by role and route |

## Django behaviors needing explicit replacements

- Built-in `auth_user`, groups, permissions, admin log, sessions, and
  `django_migrations` bookkeeping.
- Django PBKDF2 password encodings and validators. Existing hashes must remain
  verifiable; do not reset or replace them with bcrypt until a compatibility
  strategy is tested.
- DRF serializers, field-level validation, pagination/filter ordering,
  standardized exceptions, and API schema/docs.
- Opaque tab-scoped bearer tokens, SHA-256 token digests, revocation and
  expiration, CSRF-protected mutation requests, CORS policy, and rate limits.
- Django permission classes and row/object access filtering.
- `transaction.atomic`, `select_for_update`, database constraint handling,
  and `transaction.on_commit` file cleanup.
- Image validation, watermarking, private originals, static/media routing, and
  server-side file retention.
- Django admin/management portal, management commands, email delivery, and
  all explicit notification/workflow transitions.

## Stage 2 commands and backup gate

The local PostgreSQL inspection command is prepared as `npm run
inspect:database` from `backend/`. It requires backend-specific `.env`
configuration and creates an inspection-only pool with read-only transactions
and PostgreSQL's default-read-only setting. Its catalog queries are
parameterized and do not read application rows. The normal Node application
pool is write-capable for migrated operations and must only be pointed at an
approved non-production/test database or the explicitly approved source with a
least-privilege role. The saved URL candidate was
used once for the inspection, backup, and restore check without copying its
credentials into the backend or repository.

For a later approved inspection, copy `backend/.env.example` to
`backend/.env`, enter approved read-only PostgreSQL connection details
locally, and run `npm run inspect:database` from `backend/`. Do not start the
write-capable Node application with a read-only role. Configure that separately
with a least-privilege role only for an approved disposable test database or
after explicit source approval. The local `.env` is ignored by Git. Do not
copy or reuse the root Django `.env`.

Backup:

- File:
  `C:\Users\computer\AppData\Local\InfinityHouse\migration-backups\infinity-house-debre_markos_real_estate-2026-10-20T15-05-31-556Z-1512.dump`
- Format: PostgreSQL custom archive; size 166,644 bytes.
- SHA-256:
  `e4dc4ff9bc0569037c5ac2c6279a72b617ccdaf4357f9d42f7dac681ab58d69d`
- `pg_restore --list` succeeded and showed 321 archive entries.
- Restored to `infinity_house_restore_verify_1792508779750`, not over the
  source database. The restore was on the same PostgreSQL 18.6 instance, not
  PostgreSQL 13. Table and aggregate row counts matched (34 tables, 955 rows).
- The backup and restore checks are database-only; media paths and files need a
  separate inventory, backup, checksum, and restore test before cutover.

This verified backup is a preparation artifact, not proof that the candidate
database is production. Before migration writes or cutover, confirm the
authoritative source, arrange a current backup/retention policy, use a
least-privilege role, and restore-test on the intended PostgreSQL 13 target.
Do not point restore commands at production.

If the actual source is MySQL, pause the PostgreSQL backup plan: use an
appropriate MySQL backup and restore validation first, then obtain explicit
approval for a separate MySQL-to-PostgreSQL conversion plan. Do not silently
connect to a different database.

## Branch and rollback

Preparation branch: `migration/node-postgres-preparation`, created from
`main` at `f454271`. The original `main` ref remains available. See
`ROLLBACK.md` before any future cutover.

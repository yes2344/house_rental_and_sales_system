# SQL migration policy

The current deployable backend is Node.js and PostgreSQL; the former Django
application has been removed. The PostgreSQL schema snapshot and model
inventory were captured before that source removal. They are useful references
for existing databases, not a complete schema-creation migration for a new
database. No SQL migration has been applied to a live or production database.

The deployment target is an existing database. Node expects the established
application tables and does not initialize an empty database; a new empty
database is not a supported deployment target. The repository's PostgreSQL 18
catalog snapshot is from a separate local candidate, not the confirmed
HahuCloud database. HahuCloud's PostgreSQL 13.23
availability is treated as a temporary compatibility exception because the
reviewed application SQL showed no obvious PostgreSQL 14/15-only feature.
PostgreSQL 13 reached upstream end-of-life on November 13, 2025, and no
isolated PostgreSQL 13.23 integration test has been completed. This exception
is not an upstream support statement or a full compatibility claim. Verify
against an isolated PostgreSQL 13.23 instance and upgrade to an
upstream-supported major version as soon as the hosting provider permits.
Compare and verify the actual target catalog before connecting the
application. Run `npm run check:deployment` from `backend/` to perform a
read-only schema/runtime/media preflight.

The checked-in migrations add media-file metadata to the existing
`user_propertyimage` table, add a currency column to `user_property`, and make
property price nullable so negotiable listings can be stored without an
invented price.
Neither migration is applied automatically. Test both against a verified
restore of the target database; do not run them directly on production as
part of application startup. `npm run migrate` is a no-DDL preflight; after
review, backup, and isolated-restore verification, the explicit
`npm run migrate -- --apply` command records SHA-256 checksums and applies
pending migrations transactionally. Use a dedicated non-superuser migration
role with `CREATE` on `public`, `REFERENCES` on `public.user_propertyimage`,
and ownership of `public.user_property` (or membership in its owning role),
optionally supplied through `MIGRATION_DATABASE_URL`. Set
`APPLICATION_DATABASE_ROLE` to have the migration grant CRUD privileges on the
new metadata table to the non-superuser application role. The web process
never runs migrations automatically. Future SQL migrations must:

- be versioned, reviewed SQL files with a recorded checksum;
- be additive and backward-compatible with existing data;
- preserve current primary keys, foreign keys, sequence values, and records;
- include preconditions and post-migration checks for affected constraints;
- use transactions where PostgreSQL permits the operation;
- never drop, rename, truncate, or recreate existing tables without a
  separately approved plan and verified restorable backup;
- run first against a restored, isolated copy of the target PostgreSQL
  version.

Creating the migration-history table or applying any DDL to an existing
database requires an approved schema plan. The explicit migration command is
never run automatically by the web process. The checked-in
`001_media_file_metadata.sql`, `002_property_currency.sql`, and
`003_negotiable_property_price.sql` migrations are additive and have not been
applied to a live or production database. Catalog inspection uses a separate
read-only pool. Deployment readiness requires `user_property.currency` and a
nullable `user_property.price`; apply pending migrations to an isolated
verified restore before deploying code that depends on those schema changes.
The web process never applies migrations automatically.

The public About, Contact, and Property management page copy is stored in the
existing `portal_admin_publicinformationpage` table. To inspect and initialize
only missing default rows, run `npm run seed:public-pages` from `backend/` with
the intended database configured; this is a read-only dry run by default.
Review the reported database name and missing page slugs, then back up and
verify a restorable database copy before explicitly running
`npm run seed:public-pages -- --apply`. Existing page content is never replaced.
This data-only initializer is not run automatically by the web process.

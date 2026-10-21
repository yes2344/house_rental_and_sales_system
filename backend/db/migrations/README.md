# SQL migration policy

The current deployable backend is Node.js and PostgreSQL; the former Django
application has been removed. The PostgreSQL schema snapshot and model
inventory were captured before that source removal. They are useful references
for existing databases, not a complete schema-creation migration for a new
database. No SQL migration has been applied to a live or production database.

Node currently expects the existing PostgreSQL tables and column names. It
does not initialize an empty database. Compare and verify the target catalog
before connecting the application. Future SQL migrations must:

- be versioned, reviewed SQL files with a recorded checksum;
- be additive and backward-compatible with existing data;
- preserve current primary keys, foreign keys, sequence values, and records;
- include preconditions and post-migration checks for affected constraints;
- use transactions where PostgreSQL permits the operation;
- never drop, rename, truncate, or recreate existing tables without a
  separately approved plan and verified restorable backup;
- run first against a restored, isolated copy of the target PostgreSQL
  version.

Adding a migration-history table or applying any DDL to an existing database
requires an approved schema plan. The Node API currently connects in normal application mode, which can perform
explicitly implemented writes. The checked-in
`001_media_file_metadata.sql` migration is additive but has not been applied;
there is no automatic migration runner. Catalog inspection uses a separate
read-only pool.

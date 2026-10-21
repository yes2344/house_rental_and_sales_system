# SQL migration policy

No SQL migration has been created or run. The source database and actual
PostgreSQL schema have not been verified.

The migration plan is to keep and extend the existing PostgreSQL schema after
catalog comparison, rather than create parallel replacement tables. Future
migrations must:

- be versioned, reviewed SQL files with a recorded checksum;
- be additive and backward-compatible while Django and Node coexist;
- preserve current primary keys, foreign keys, sequence values, and records;
- include preconditions and post-migration checks for affected constraints;
- use transactions where PostgreSQL permits the operation;
- never drop, rename, truncate, or recreate existing tables without a
  separately approved plan and verified restorable backup;
- run first against a restored, isolated PostgreSQL 13 copy.

Adding a migration-history table or applying any DDL to an existing database
requires an approved schema plan. The Node API currently connects in
normal application mode, which can perform explicitly implemented writes.
No schema migration has been created or applied and no migration runner
exists. Catalog inspection uses a separate read-only pool.

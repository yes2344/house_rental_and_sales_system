# HahuCloud deployment

Use the root [`DEPLOY_HAHUCLOUD.md`](../DEPLOY_HAHUCLOUD.md) for the Node.js
and PostgreSQL deployment instructions.

HahuCloud's Node.js runtime, PostgreSQL reachability, persistent public/private
media storage, process manager, and TLS settings have not been verified. Check
those capabilities with the provider before uploading. The former
Python/Passenger/MySQL deployment files have been removed.

The intended existing database was reported as PostgreSQL 13.12. PostgreSQL 13
is upstream end-of-life; upgrade to a HahuCloud-supported PostgreSQL 15+ major
version before production. Follow the root deployment guide's backup, restore,
schema-preflight, migration, and persistent-volume checks.

The current Node API does not implement every endpoint still used by the
frontend, and a complete schema migration for a fresh PostgreSQL database is
not included. A passing health check only confirms API process and database
connectivity; it does not establish full production readiness.

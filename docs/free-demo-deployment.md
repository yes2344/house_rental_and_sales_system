# Free-demo deployment notes

The previous demo instructions are retired. The deployable source is now a
Node.js API with a React frontend and PostgreSQL connection configuration.
There is no one-click free-demo configuration or complete schema-creation
migration for an empty PostgreSQL database.

See the [HahuCloud deployment guide](../DEPLOY_HAHUCLOUD.md) for provider
requirements, environment variables, database readiness, media storage, and
frontend deployment. Those hosting capabilities have not been verified.

If an older demo deployment still exists, do not delete or reconfigure its
database or uploaded media as part of this code change. Identify which service
contains the authoritative data, take and verify backups, and prepare a
separately reviewed cross-database transfer and rollback plan before changing
or retiring it.

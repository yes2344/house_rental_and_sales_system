# Retired free-demo deployment instructions

The former demo instructions described a deployment backed by an external
PostgreSQL service. They are no longer applicable: the Django project now
requires MySQL and does not support PostgreSQL or SQLite as a fallback.

Use the current [HahuCloud deployment guide](../DEPLOY_HAHUCLOUD.md) for the
MySQL environment variables, staging and migration safeguards, media storage,
and frontend deployment steps.

If an older demo deployment still exists, do not delete or reconfigure its
database or uploaded media as part of this code change. Identify which service
contains the authoritative data, take and verify backups, and prepare a
separately reviewed cross-database transfer and rollback plan before changing
or retiring it.

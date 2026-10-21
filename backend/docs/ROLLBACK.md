# Node deployment rollback plan

This plan covers application releases only. It does not authorize changes to
production routing, database contents, media, DNS, or hosting configuration.

## Before a release

1. Record the deployed Node commit, frontend build, environment variable names
   (not their values), database schema state, and media snapshot.
2. Verify a restorable PostgreSQL backup and a separate restore test.
3. Back up public and private media independently and verify the copies.
4. Keep schema changes additive and backward compatible. Do not run schema
   changes automatically at web-process startup.
5. Define measurable rollback triggers, such as API error rates, failed
   authentication, data reconciliation mismatches, or inaccessible media.

## Roll back an application release

1. Stop or redirect traffic from the affected Node release and redeploy the
   previously verified Node application and matching frontend build.
2. Keep PostgreSQL changes and new writes intact. Do not restore a backup over
   a live database as a routine code rollback.
3. If the failed release wrote data, stop writes, compare affected rows and
   audit events, and prepare a reviewed reconciliation. Never discard writes
   silently.
4. Restore media routing only when the corresponding files have been verified.
   Do not delete files created by the failed release during rollback.
5. Run Node health checks and verify the API workflows supported by that
   release.
6. Preserve logs and the failed release for diagnosis.

There is no Django runtime in the current deployable source tree. Reverting
application code does not roll back database or media changes; those require
their own approved recovery plan.

# Migration rollback plan

This plan is preparatory. No production routing, database, or deployment
changes have been made.

## Before any future cutover

1. Preserve the current `main` ref and keep Django deployment artifacts
   available until Node parity is approved.
2. Verify a full, restorable database backup and a separate restore test.
   Preserve the media tree independently and verify checksums.
3. Keep the Node release and any schema changes additive and backward
   compatible. No destructive table operations are allowed in the cutover.
4. Record the current frontend/API deployment versions, environment variable
   names (not secret values), database schema version, and media snapshot.
5. Define a maintenance window and measurable rollback triggers, such as
   authentication failures, API error rate, data reconciliation mismatch, or
   missing media.

## Rollback sequence

1. Stop directing frontend/API traffic to Node and restore the prior API target
   and Django deployment configuration.
2. Keep PostgreSQL changes and newly written data intact. Do not restore a
   backup over a live database as a routine rollback.
3. If Node wrote data before rollback, stop writes, compare affected rows and
   audit/workflow events, and plan a reviewed reconciliation. Never discard
   those writes silently.
4. Restore media routing to the previous storage only if files are verified
   and a complete media copy exists. Do not delete Node-local media during
   rollback.
5. Run the original Django health and smoke tests, then verify login, listing
   browse/detail, favorites, viewing requests, admin access, and media.
6. Preserve logs and the failed Node release for diagnosis; do not remove
   migration files or database artifacts until the incident is resolved.

The new migration branch is based on `main` at `f454271`; returning the
application code to the original version can be done by deploying that
existing `main` revision. This does not roll back database or uploaded-file
changes, which require their own approved recovery plan.

# Local media storage and migration report

## Implementation

The Node API stores public, watermarked property images under
`MEDIA_ROOT\property_images` and private originals under
`PRIVATE_MEDIA_ROOT\private_property_images`. The two absolute roots are
configurable; production startup requires both to be explicitly configured.
The local defaults reuse the existing repository-level `media` and
`private-media` directories, outside `backend/src`.

The private root is never mounted as static content. Original-image requests
use the authenticated `/api/v1/management/images/:imageId/original/` route
and reproduce the existing manager, assigned-agent, and owner-submitter checks.
Public media is served with directory listing disabled, only JPEG/PNG/WebP
extensions allowed, and `X-Content-Type-Options: nosniff`.

Uploads use in-memory multipart parsing capped at one image and 10 MiB.
`sharp` decodes file content and selects JPEG, PNG, or WebP from the decoded
format; browser MIME and filename extensions are not trusted. New storage names
are random UUIDs. Public images are EXIF-oriented, re-encoded, and watermarked
using the current brokerage site name and phone; private originals retain the
uploaded bytes. File metadata is stored in the existing
`user_propertyimage` columns. No schema changes are required.

The existing model has no `display_order` column: Django orders images by
primary key, while the gallery presents the primary image first and then
primary-key order. The Node API keeps that same ordering and primary-image
behavior rather than introducing an unapproved schema change. The current
frontend uses the same image URL for gallery and thumbnail displays; there is
no separate thumbnail field or thumbnail-generation API in the existing
schema.

Implemented image API paths:

- `GET, POST /api/v1/submissions/:submissionId/images/`
- `GET, POST /api/v1/management/properties/:propertyId/images/`
- `GET, PATCH, PUT, DELETE /api/v1/management/properties/:propertyId/images/:imageId/`
- `GET /api/v1/management/images/:imageId/original/`

The PUT endpoint supports a managed image replacement while preserving its
record ID, caption, and primary status.

The additive SQL migration
[`../db/migrations/001_media_file_metadata.sql`](../db/migrations/001_media_file_metadata.sql)
stores byte counts and decoded dimensions for newly uploaded/replaced images.
It has not been applied, and existing rows have not been backfilled. Apply and
verify it only on an approved disposable PostgreSQL copy before enabling the
new upload metadata writes.

An administrator-only `GET /api/v1/admin/storage/` endpoint reports root
usage, filesystem space when available, missing/orphaned references, and
warning status against an explicitly configured `MEDIA_CAPACITY_BYTES`.
Configure `MEDIA_WARNING_PERCENT` to change the default 80% warning. An
unconfigured capacity is reported as unknown, not guessed from total disk
space.

## Existing-media audit

The audit used a read-only transaction against the saved PostgreSQL candidate
database, which the user confirmed as authoritative for this media migration.
It did not print credentials or modify database rows.

| Audit item | Result |
|---|---:|
| PostgreSQL candidate | 18.6; database `debre_markos_real_estate` |
| Property-image records | 75 |
| Existing public property-image references found locally | 75 / 75 |
| Existing private-original references found locally | 75 / 75 |
| Local brokerage logo and homepage hero references | 2 / 2 |
| Referenced files successfully decoded | 152 |
| Referenced corrupt/unreadable files | 0 |
| Audited references hosted on Cloudinary or another remote URL | 0 |
| Files currently in `media/` | 85 files; 57,126,104 bytes |
| Files currently in `private-media/` | 80 files; 75,938,564 bytes |

The two database branding references also decode successfully. There are no
homepage-note image records in the audited candidate schema. The difference
between the files present and the references audited against this database is
not treated as proof that files are disposable; no existing file was deleted.
The candidate database has not been confirmed as the authoritative database
for a previous deployment. The audit does not establish that this candidate
database is authoritative for HahuCloud or any current deployment. No attempt
was made to fetch remote assets.

## Backups and recovery

Back up PostgreSQL and both media roots together, using a coordinated snapshot
or maintenance window so the database references and files represent the same
point in time. Keep the private media archive access-controlled. Never put
database passwords in command-line arguments or commit credentials.

Example PowerShell procedure after configuring a protected PostgreSQL service
entry and absolute media-root environment variables:

```powershell
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backupRoot = Join-Path $env:LOCALAPPDATA 'InfinityHouse\backups'
New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null

pg_dump --format=custom --file (Join-Path $backupRoot "database-$stamp.dump") --dbname $env:PGSERVICE
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL backup failed.' }
pg_restore --list (Join-Path $backupRoot "database-$stamp.dump") | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL backup archive did not validate.' }

Compress-Archive -Path $env:MEDIA_ROOT,$env:PRIVATE_MEDIA_ROOT `
  -DestinationPath (Join-Path $backupRoot "media-$stamp.zip")
Get-FileHash (Join-Path $backupRoot "database-$stamp.dump") -Algorithm SHA256
Get-FileHash (Join-Path $backupRoot "media-$stamp.zip") -Algorithm SHA256
```

Verify restoration only into a separate disposable database, never over the
source database:

```powershell
createdb --maintenance-db $env:PGSERVICE $env:PGRESTORE_TEST_DATABASE
pg_restore --dbname $env:PGRESTORE_TEST_SERVICE `
  (Join-Path $backupRoot "database-$stamp.dump")
```

Keep checksums with the backup, verify the media archive can be listed and
extracted, and compare restored file counts and hashes before cutover. Back up
the PostgreSQL database and media volumes on the same schedule after launch.

## Orphan inspection

The cleanup tool is dry-run by default and only scans the two property-image
directories. Review the count and take a verified database/media backup before
deleting anything:

```powershell
Set-Location backend
node scripts/clean-orphaned-images.js
node scripts/clean-orphaned-images.js --delete
```

The script refuses unrecognized/non-local database paths rather than
silently treating them as missing files. Run it only with the intended
database configured. It must not be used to remove source images while an
alternate deployment may still refer to them.

## Outstanding risks

- The Django Cloudinary adapter and Python application have been removed.
- Production media-volume provisioning, permissions, backup, and restore have
  not been tested. The Node backend has not been verified against a HahuCloud
  database, and no production database writes were made during this work.
- `render.yaml` declares a free-tier Node web service without a persistent
  disk. Do not enable uploads there until persistent storage is provisioned.
- The automated upload tests use an isolated filesystem and mocked PostgreSQL
  responses. A disposable PostgreSQL restore test remains necessary before
  database-backed acceptance or cutover.
- PostgreSQL 13 compatibility is not validated here; the inspected candidate
  runs PostgreSQL 18.6.
- The claimed hosting allocation of 128 GB is not identifiable from repository
  configuration. See [`HOSTING_MEDIA_STORAGE.md`](./HOSTING_MEDIA_STORAGE.md)
  for the provider facts needed before selecting production paths or capacity.

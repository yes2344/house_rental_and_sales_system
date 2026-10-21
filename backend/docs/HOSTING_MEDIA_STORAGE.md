# Hosting media storage readiness

## What the repository can establish

- The Node API supports separate public and private roots configured with
  `MEDIA_ROOT` and `PRIVATE_MEDIA_ROOT`. Both must be absolute paths outside
  the application directory in production, and the roots may not overlap.
- Public, watermarked property images are saved below
  `MEDIA_ROOT\property_images`; private originals are saved below
  `PRIVATE_MEDIA_ROOT\private_property_images`. The private root is not served
  statically.
- New property image uploads are limited to one JPEG, PNG, or WebP file per
  request, at most 10 MiB per file, with a maximum of 10 images per property.
  The server decodes the file bytes, limits decode size to 50 million pixels,
  and rejects images below 256 x 160 pixels. Public files are re-encoded and
  watermarked; a private copy of the original bytes is retained.
- Node generates unique filenames. Existing `user_propertyimage` rows hold
  property relationship, public/private relative filenames, original filename
  and MIME type, caption, primary state, and creation time.
- The new additive
  [`001_media_file_metadata.sql`](../db/migrations/001_media_file_metadata.sql)
  migration stores public/original byte counts, detected type/extension,
  oriented image dimensions, and upload time for new and replaced images.
  **This migration has not been applied.** Existing images are not automatically
  backfilled. Do not enable uploads on a database before the migration has been
  reviewed and applied to a disposable PostgreSQL copy.
- Authenticated administrators can request
  `GET /api/v1/admin/storage/`. It reports files/bytes beneath both roots,
  filesystem capacity/free space where Node can obtain it, database-reference
  missing/orphan counts, and a configurable allocation warning. This is an
  on-demand report, not a background alert or deletion mechanism.

## Hosting capacity is unverified

No provider account, server shell, mount configuration, quota report, or
deployment environment describing the advertised 128 GB was available to
inspect. The checked-in [`render.yaml`](../../render.yaml) defines a **Render
free Node web service and does not provision persistent media storage**. It
must not be treated as evidence that uploads will persist. HahuCloud's storage
capabilities and mount path are also unverified. Therefore:

- The actual persistent media path is **not yet known or configured**.
- Write permission, free/allocated quota, inode/file/bandwidth limits, and
  persistence through restart, redeploy, and reboot are **not verified**.
- Whether database files and application data use the same quota or physical
  volume is **not verified**.
- Symlink and static-file-server behavior is **not verified**.
- No actual disk usage for the claimed hosting allocation can be reported.
- Never set `MEDIA_CAPACITY_BYTES=137438953472` merely because “128 GB” was
  advertised. First establish whether that is the app's quota or a shared
  server/disk capacity.

Before configuring production, obtain these answers from the hosting provider:

1. Is 128 GB total physical disk, a per-account quota, or a persistent volume
   allocated to this application? Is the figure decimal GB or GiB?
2. What is the exact absolute path of the persistent writable volume, and does
   it survive process restart, redeploy, rollback, and host reboot?
3. What is the writable owner/group, and can the Node process create
   directories/files there with restrictive permissions?
4. Does PostgreSQL share that same quota/volume? What other application data,
   logs, backups, build artifacts, and temporary files count toward it?
5. Are there per-file upload, request-body, bandwidth/egress, inode, or
   storage-growth limits? Does a reverse proxy impose a lower body-size limit
   than the 10 MiB application limit?
6. Are symlinks supported, and can the provider serve files from a mounted
   path or must Node serve public media itself?
7. What backup/restore schedule, retention, and point-in-time consistency are
   available for that disk and the PostgreSQL database?
8. Does the Node deployment runtime run continuously and support the required
   Node.js 20+ native/sharp binaries on the target architecture?

## Configuration after provider confirmation

Set both roots to separate persistent directories outside the app release
directory. For example only (not a verified hosting path):

```text
MEDIA_ROOT=/verified/persistent-volume/infinity-house/media
PRIVATE_MEDIA_ROOT=/verified/persistent-volume/infinity-house/private-media
MEDIA_CAPACITY_BYTES=<provider-confirmed app allocation in bytes>
MEDIA_WARNING_PERCENT=80
```

If the host assigns distinct subdirectory quotas, configure the provider's
actual application allocation, not the entire volume size. The status endpoint
calculates application media usage by scanning both configured roots, and
filesystem available/total values from the underlying mounted filesystem when
supported. The latter includes other consumers sharing that filesystem and is
not an application-only remaining-quota value. The configured warning is
based on media bytes divided by the explicit capacity setting. The status call
does not automatically notify administrators; production monitoring must poll
the endpoint through an approved internal monitor or add a notification path.

## Backups and acceptance status

Back up PostgreSQL and the complete public and private roots at a coordinated
point in time. See [`LOCAL_MEDIA_MIGRATION.md`](./LOCAL_MEDIA_MIGRATION.md) for
database/media backup commands and separate restore guidance. Keep private
media archives access-controlled. Do not prune orphan files automatically;
the report is read-only and displays the counts for review.

Upload, replace, delete, object permission, invalid/oversized file, and
watermark behavior have automated tests using temporary local storage and
mocked PostgreSQL. The 128 GB host's filesystem, live PostgreSQL metadata
migration, restart/redeploy persistence, hosting backup restore, proxy upload
limits, and actual capacity threshold have **not** been tested. Production
images must not be moved or removed until those tests pass on a disposable
deployment using the provider-confirmed volume.

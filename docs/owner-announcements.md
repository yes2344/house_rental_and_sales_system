# Retired owner property submissions

The marketplace is broker-managed. Public visitors and ordinary customer accounts cannot submit properties for review. The public website does not advertise property-owner submissions, and the owner submission and broker review pages are no longer routed.

Property managers continue to create and manage listings through `/management/listings` and the `/api/v1/management/properties/` endpoints. These endpoints retain their existing authentication, role, and object-level permission checks. Public search returns only published, available broker-managed listings.

Owner-announcement submission, review, agreement, renewal, and expiry-reminder endpoints have been removed. Existing `OwnerAnnouncement`, agreement, event, and related property data remain in the database for historical and audit purposes. No destructive schema migration or data operation was performed. Legacy owner-announced properties are excluded from public results regardless of their former approval or agreement state.

The `InAppNotification` model and authenticated notification endpoints remain because viewing-request workflows also use them. The old review permission identifier is retained for compatibility with existing profile JSON values, but does not provide access to the management workspace.

## Locations

`Location` remains a configurable parent/child hierarchy with English labels, optional Amharic labels, and aliases. Public clients can read active locations at `GET /api/v1/locations/`; authorized settings managers can manage them at `/api/v1/management/locations/`. Only locally verified places should be entered. Existing location records and aliases are unchanged.

## Expiry processing

The owner-announcement agreement expiry/reminder management command has been retired. Historical agreements and their stored statuses are preserved. This command must not be scheduled in deployment environments.

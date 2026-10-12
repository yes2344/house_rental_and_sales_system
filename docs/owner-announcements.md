# Owner property announcements

The owner-announcement service is separate from broker-managed listings:

1. An authenticated customer submits a property, their contact details, authorization confirmation, and optionally up to 10 photos.
2. The submission creates a property with `service_type=owner_announced` and `publication_status=pending_review`. It does not appear in public search.
3. Active brokers with `announcements.review` receive in-app notifications when an owner submits or resubmits a property. An authorized broker reviews it, records an agreement period, and explicitly chooses whether owner contact details and exact coordinates may be public.
4. The public property API and server-rendered listing pages show an owner-announced property only while its status is approved and an active agreement includes the current date. Contact details are separately gated by the agreement's public-contact choice.
5. Owners can request renewal, withdraw an announcement, review its status, and read in-app notifications. Brokers can review submissions, suspend an approved announcement, and request an owner-led renewal discussion for an expired announcement. Renewal discussion does not republish a listing; a new agreement must still be approved.

Private owner contact details are kept on `OwnerAnnouncement`; they are not copied to public property fields. Owners must still provide accurate details, and their authorization checkbox is a self-attestation, not document or identity verification. The current project has no email/phone verification, email delivery, or SMS provider. Notifications are in-app only, and owners' listings remain pending until broker approval.

## Broker announcement dashboard

The broker dashboard is backed by management endpoints protected by the `announcements.review` permission:

- `GET /api/v1/management/owner-announcements/` returns paginated announcements, real queue summary counts, and server-side `queue`, `search`, `location`, `property_type`, `listing_type`, `publication_status`, expiry, and ordering filters.
- `GET /api/v1/management/owner-announcements/{id}/` returns protected review details, including private owner contact information and agreement history.
- `POST /api/v1/management/owner-announcements/{id}/decision/` records a validated review decision. Approval requires the agreement dates/terms and explicit contact/location visibility choices.
- `POST /api/v1/management/owner-announcements/{id}/renewal/` lets a broker start renewal discussions only for an expired announcement. It records an audit event and notifies the owner without changing publication status.

The dashboard keeps filters and pagination in the URL, displays agreement dates and approaching expiries on compact responsive cards, and keeps review forms in the protected details dialog. Public property cards do not expose broker actions or private owner details.

## Locations

`Location` stores configurable parent/child administrative locations with English and optional Amharic labels. The location hierarchy starts empty; administrators must add only locally verified places. Public clients can read active locations at `GET /api/v1/locations/`; authorized settings managers can manage them at `/api/v1/management/locations/`. No Addis Ababa sub-city, woreda, neighborhood, address, or coordinate seed data is included.

## Deploying schema changes

Back up the configured database and review the generated migrations before applying them. Then, from the repository root:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
```

The migrations add optional location links and new tables/status choices; they do not delete existing property rows. The generated migrations must be deployed together.

## Agreement expiry and reminders

Run the following Django management command daily using the deployment scheduler (for Windows development, Task Scheduler; for production, the host's scheduler):

```powershell
.\.venv\Scripts\python.exe manage.py process_owner_announcement_agreements
```

The command sends in-app reminders 30, 7, and 1 days before an active agreement ends and changes ended agreements/listings to expired. Notification keys make repeated runs idempotent. If it is not scheduled, expired agreements still stop being publicly visible because public queries check the effective dates, but their stored status and reminders will not be updated.

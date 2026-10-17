# Owner property submissions

Authenticated customer and owner accounts can submit properties for review. Submissions use the existing `Property`, `OwnerAnnouncement`, agreement, event, and notification models; no duplicate listing or location tables are introduced.

## Owner workflow

- `POST /api/v1/submissions/` creates an owner-announced property in `pending_review`. It requires the submitter's contact details, confirmation of authority to advertise the property, and acceptance of the submission terms.
- `GET /api/v1/submissions/` lists only the authenticated submitter's submissions. `GET` and `PATCH /api/v1/submissions/<id>/` are restricted to that submitter; editing is allowed only after an agent requests corrections.
- `GET` and `POST /api/v1/submissions/<id>/images/` list or upload photos for the submitter's own pending or correction-requested property, using the existing property-image model and image limits.
- The owner page shows current status, feedback, and review history. Status changes and decisions create in-app notifications.

## Agent review

Accounts with the existing review management permission can use:

- `GET /api/v1/management/submissions/` with optional `status` and ordering filters.
- `GET /api/v1/management/submissions/<id>/` to review property information, images, private submitter contact details, agreement history, and status events.
- `POST /api/v1/management/submissions/<id>/decision/` with `action` set to `approve`, `reject`, or `request_corrections`.

Rejections and correction requests require an explanation. An agent cannot review their own submission. Agent queues are scoped to their assigned city; authorized administrators can review all submissions. Approval is transactional and requires a valid agreement start date, duration, and terms. It records the reviewer, agreement, event, notification, and administrative audit entry.

## Publication and contact privacy

New submissions cannot set publication status, service type, owner, submitter, or public contact fields. They remain hidden from public search and detail endpoints until an authorized agent approves them. Public access additionally requires an active agreement whose date range includes the current `Africa/Addis_Ababa` date and an available property status.

Submitter contact details are private and are not included in public property responses. Public owner-announced listings use the configured Habesha Home Center contact channels. The existing property serializer validates the configured location hierarchy, including requiring a sub-city/Kifle Ketema beneath a city administration.

Historical owner-announcement records and property data remain intact. Records that do not satisfy the current approval and active-agreement rules are not made public automatically. No destructive migration or data operation is part of this workflow.

## Locations

`Location` remains a configurable parent/child hierarchy with English labels, optional Amharic labels, and aliases. Public clients can read active locations at `GET /api/v1/locations/`; authorized settings managers can manage them at `/api/v1/management/locations/`. Only locally verified places should be entered.

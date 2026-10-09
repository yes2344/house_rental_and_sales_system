# Viewing requests and appointment coordination

## Lifecycle

1. A visitor submits a viewing request with a preferred date and optional time. An account is not required.
2. Only the platform broker or explicitly authorized staff can propose a date and time, or reject the request. Assigned brokers can act only on requests for their assigned properties.
3. A proposal is not a confirmed appointment. Only the visitor holding the private receipt token can accept or decline it.
4. Acceptance copies the proposal into the confirmed appointment fields. A visitor may decline a proposal; a manager can then offer a revised time.
5. Each submission, proposal, revision, rejection, and visitor decision is recorded in `ViewingRequestEvent`. Internal notes and contact details are not copied into the event history.

Appointment date/time values are local wall-clock values in `Africa/Addis_Ababa`. The API includes `appointment_timezone` with appointment data so clients can label the values correctly. Past dates and past times on the current local date are rejected; an expired proposal cannot be accepted.

## Guest receipt credential

`POST /api/v1/viewing-requests/` accepts the property ID, contact details, preferred date/time, and optional message. A successful response includes a random `receipt_token` once. Only its SHA-256 digest is stored. Keep the raw token private; the numeric request ID is not an authorization credential.

Use the token in the `X-Viewing-Receipt` header, never in a URL:

- `GET /api/v1/viewing-requests/receipt/` retrieves the limited, non-PII request status.
- `POST /api/v1/viewing-requests/receipt/` with `{"decision":"accept"}` or `{"decision":"decline"}` responds to a pending proposal.

Receipt responses are sent with `Cache-Control: no-store` and `Referrer-Policy: no-referrer`; the endpoints are rate-limited. Invalid tokens return the same not-found response regardless of the request ID. The React client offers a request-status page and keeps the credential out of the URL. The legacy Django form uses the same digest, status, and event behavior and also requires the token for guest retrieval.

## Management access

- Property owners and listing submitters do not receive viewing-request access from ownership or submission alone.
- Brokers need active approval, `viewings.manage_assigned`, and an assignment to the matching property.
- Delegated staff need `viewings.view_all` to read all requests or `viewings.manage_all` to make changes across all requests.
- Property permissions alone do not grant access to private requester details.
- The platform superuser retains owner-level access.

API management endpoints are `GET /api/v1/management/viewing-requests/` and `GET/PATCH /api/v1/management/viewing-requests/{id}/`. A manager PATCH can provide `proposed_date` and `proposed_time`, or `status: "rejected"`; it cannot set `status: "confirmed"` or write the confirmed schedule fields.

## Notifications and deployment

No email or SMS provider is configured. Managers must contact visitors through the contact details they submitted and ask them to check the status using their private token. Do not include the receipt token in audit logs, analytics, support tickets, or URLs.

Migration `viewings.0003_viewingrequest_guest_responded_at_and_more` adds nullable proposal/receipt fields and the event-history table without deleting or rewriting existing request data. Apply it through the normal deployment migration process:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
```

Back up the database and review the migration plan before applying migrations to production.

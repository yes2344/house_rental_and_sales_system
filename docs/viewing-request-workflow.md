# Viewing requests and appointment coordination

## Lifecycle and duplicate policy

1. A visitor signs in or creates an account before submitting a viewing request. The React client preserves the selected property through sign-in and registration.
2. A request records the signed-in requester, contact details, preferred date, optional preferred time, and optional message.
3. The broker can confirm the requested date/time when a preferred time was supplied, propose or revise a date/time, reject an open request, cancel an active request, or mark a confirmed viewing complete after its scheduled time.
4. The customer can accept or decline a broker proposal, or cancel an active request. Accepting a proposal copies its date/time into the confirmed schedule. A declined proposal remains open for further scheduling negotiation.
5. Every status and schedule change is retained in `ViewingRequestEvent`. Closed requests remain visible in the customer and broker histories.

Only one active request per customer/property pair is allowed. `pending`, `proposed`, `confirmed`, and `declined` are active; `rejected`, `cancelled`, and `completed` are terminal and permit a later new request. A PostgreSQL conditional unique constraint enforces this rule under concurrent submissions. Before that constraint is created, migration `viewings.0004_viewingrequestevent_message_and_more` closes any pre-existing duplicate active requests without deleting them and records the migration action in each request's history.

Appointment date/time values are local wall-clock values in `Africa/Addis_Ababa`. Request and proposal dates cannot be in the past, and a proposal cannot be accepted after its time has passed.

## Customer API

All routes below require the account's authenticated tab session. The numeric request ID is not an authorization credential; reads and actions are scoped to `request.user`.

- `POST /api/v1/viewing-requests/` creates a request for a published, available property. Repeated active requests return HTTP 409. The response contains only the request ID, status, and creation time.
- `GET /api/v1/viewing-requests/mine/?page=1&status=proposed` returns the customer's paginated, optionally status-filtered requests, including appointment and event history.
- `GET /api/v1/viewing-requests/mine/{id}/` retrieves one of that customer's requests.
- `POST /api/v1/viewing-requests/mine/{id}/respond/` with `{"decision":"accept"}` or `{"decision":"decline"}` responds to a live broker proposal.
- `POST /api/v1/viewing-requests/mine/{id}/cancel/` cancels an active request.

The protected React page is `/viewing-requests`; a sign-in redirect retains the original request URL and property query parameters. The request form can prefill contact data from the customer's account, and still lets the customer review or edit those details before submission.

## Legacy guest receipts

New guest requests are not accepted. The legacy private-receipt endpoints remain available only for old records with a stored receipt-token digest. They do not expose new authenticated requests, and the raw token is never stored in the database or placed in a URL. The legacy Django request form also requires a Django-authenticated session. No email or SMS integration is configured.

## Broker access, history, and notifications

Approved brokers have citywide viewing-request management access, consistent with the existing single-city broker workflow. Property owners, listing submitters, and delegated administrator accounts do not receive this access from ownership or staff status alone; the platform superuser retains platform-owner access.

- `GET /api/v1/management/viewing-requests/` lists requests the broker can manage.
- `GET/PATCH /api/v1/management/viewing-requests/{id}/` reads request details and proposes/revises a schedule or rejects an open request. The broker cannot directly accept the customer's proposed time through PATCH.
- `POST /api/v1/management/viewing-requests/{id}/action/` with `confirm_requested`, `cancel`, or `complete` performs the other broker transitions. Completion is rejected until the scheduled time has passed.

Submission and each subsequent customer/broker action create idempotent in-app notifications for the relevant brokers or requester. Notifications are in-app only; no external delivery provider is configured. Customer messages are part of the event history; private broker notes are not exposed in that history.

## Migration and deployment

Migration `viewings.0004_viewingrequestevent_message_and_more` adds cancellation/completion states, customer-visible event messages, and the race-safe active-request constraint. Apply it through the normal deployment migration process:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
```

Back up the database and review the migration plan before applying migrations to production.

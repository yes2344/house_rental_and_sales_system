# Viewing requests and appointment coordination

> **Not yet available in the Node API.** This document records the previous
> workflow and API contract for future implementation. The Django application
> and its migrations have been removed, so the documented routes currently
> return 404. See
> [`../backend/docs/API_MIGRATION_STATUS.md`](../backend/docs/API_MIGRATION_STATUS.md).

## Lifecycle and duplicate policy

1. A visitor signs in or creates an account before submitting a viewing request. The React client preserves the selected property through sign-in and registration.
2. A request records the signed-in requester, contact details, preferred date, optional preferred time, and optional message.
3. The agent can confirm the requested date/time when a preferred time was supplied, propose or revise a date/time, reject an open request, cancel an active request, or mark a confirmed viewing complete after its scheduled time.
4. The customer can accept or decline a agent proposal, or cancel an active request. Accepting a proposal copies its date/time into the confirmed schedule. A declined proposal remains open for further scheduling negotiation.
5. Every status and schedule change is retained in `ViewingRequestEvent`. Closed requests remain visible in the customer and agent histories.

Only one active request per customer/property pair is allowed. `pending`, `proposed`, `confirmed`, and `declined` are active; `rejected`, `cancelled`, and `completed` are terminal and permit a later new request. A generated active-request key and unique index previously enforced this rule
under concurrent submissions. Do not assume those constraints or the previous
application migration history are present in a new PostgreSQL database.

Appointment date/time values are local wall-clock values in `Africa/Addis_Ababa`. Request and proposal dates cannot be in the past, and a proposal cannot be accepted after its time has passed.

## Customer API

All routes below require the account's authenticated tab session. The numeric request ID is not an authorization credential; reads and actions are scoped to `request.user`.

- `POST /api/v1/viewing-requests/` creates a request for a published, available property. Repeated active requests return HTTP 409. The response contains only the request ID, status, and creation time.
- `GET /api/v1/viewing-requests/mine/?page=1&status=proposed` returns the customer's paginated, optionally status-filtered requests, including appointment and event history.
- `GET /api/v1/viewing-requests/mine/{id}/` retrieves one of that customer's requests.
- `POST /api/v1/viewing-requests/mine/{id}/respond/` with `{"decision":"accept"}` or `{"decision":"decline"}` responds to a live agent proposal.
- `POST /api/v1/viewing-requests/mine/{id}/cancel/` cancels an active request.

The protected React page is `/viewing-requests`; a sign-in redirect retains the original request URL and property query parameters. The request form can prefill contact data from the customer's account, and still lets the customer review or edit those details before submission.

## Legacy guest receipts

New guest requests are not accepted by the previous application. The legacy
private-receipt endpoints are not currently available in Node. No email or SMS
integration is configured.

## Agent access, history, and notifications

Approved agents have citywide viewing-request management access, consistent with the existing single-city agent workflow. Property owners, listing submitters, and delegated administrator accounts do not receive this access from ownership or staff status alone; the platform superuser retains platform-owner access.

- `GET /api/v1/management/viewing-requests/` lists requests the agent can manage.
- `GET/PATCH /api/v1/management/viewing-requests/{id}/` reads request details and proposes/revises a schedule or rejects an open request. The agent cannot directly accept the customer's proposed time through PATCH.
- `POST /api/v1/management/viewing-requests/{id}/action/` with `confirm_requested`, `cancel`, or `complete` performs the other agent transitions. Completion is rejected until the scheduled time has passed.

Submission and each subsequent customer/agent action create idempotent in-app notifications for the relevant agents or requester. Notifications are in-app only; no external delivery provider is configured. Customer messages are part of the event history; private agent notes are not exposed in that history.

## Migration and deployment

Implement the workflow in Node and add reviewed PostgreSQL schema changes
before enabling these features. Do not use the previous Django migration
commands; they are no longer in the repository.

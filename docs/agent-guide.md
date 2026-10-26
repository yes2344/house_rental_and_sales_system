# Agent guide

This guide is for approved real-estate agents using an assigned account.
Available screens and actions depend on server-side permissions and assignment
scope.

## Account safety

- Accept an invitation only through the official site and set a unique
  password.
- Never share your password, sign-in session, or invitation token.
- Do not use another agent's account or try to access customer or administrator
  records outside your assigned work.
- Contact the Platform Owner if onboarding, city scope, or permissions appear
  incorrect; do not bypass an access denial.

## Listing work

Use the management screens available to you to create or update listing
information and upload property images. Confirm addresses, prices, sale/rent
status, availability, and media before submitting for review. Agent-created
listings require administrator review before publication. Do not claim a
listing is public until you have confirmed its published state.

The API and tests support managed-property and image workflows, but this does
not certify production database, hosting-volume, or browser behavior. New
images are processed by the backend; private originals must remain private.
Report upload failures with the time, listing reference, and visible error,
not by sending the image if it contains sensitive information.

## Viewing requests and submissions

The Node API includes viewing-request management and submission review
endpoints. Use only the requests or submissions visible to your account and
follow the current state shown in the interface. Verify date/time and property
details before proposing or confirming an appointment. Keep customer
communications professional and within the approved workflow.

The previous Django workflow documentation may not match the current Node
implementation. Consult the [API coverage status](../backend/docs/API_MIGRATION_STATUS.md)
and [test matrix](./handover-test-matrix.md); production workflow testing is
still required.

## Escalation

Report incorrect listing data, access errors, missing uploads, or scheduling
problems to the Platform Owner. Do not try to repair production data,
reprocess images, or alter account permissions yourself.

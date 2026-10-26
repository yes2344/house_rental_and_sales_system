# Customer guide

This guide describes the customer-facing website. Availability of account,
email, and request workflows depends on production configuration; automated
tests do not prove that the live hosting environment is ready.

## Browse properties

Use the public website to browse listings and open a property page for its
details. Search and filtering are supported by the current Node property API;
the richer natural-language search behavior described in older material is
not fully ported. Confirm availability and all terms directly with Infinity
House before making a decision.

## Create and manage an account

Register and sign in using your own account. Keep your password private and
use the site's password-recovery flow if needed. Verification and password
reset messages require configured email delivery. If a message does not
arrive, contact the website owner through the published contact channels;
never send your password or reset token to an agent.

## Request a viewing or submit a property

Use the viewing-request form for an eligible published property. Review the
property, requested time, and contact details before submitting. Follow the
status shown in your account and contact the business if a request appears
stuck.

The site also provides owner property-submission and image-upload flows.
Submission is not publication: listings may require review and approval.
Upload only images you are authorized to share publicly, and do not upload
identity documents or unrelated private information.

## Privacy and support

Private account pages are configured as `noindex, follow` in generated
frontend HTML, but that does not make a page private; access control is
provided by authentication and authorization. Do not enter payment details or
sensitive information unless the website explicitly requests it through an
approved secure form.

For assistance, use the Contact page. The published social-profile URLs and
production support response process have not been independently verified in
this handover.

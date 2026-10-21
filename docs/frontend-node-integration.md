# Frontend-to-Node integration status

## Current state

The React application remains a split deployment during migration:

- Public property type options, property search/listing, property detail, and
  their public image URLs use Node and PostgreSQL through `/node-api`.
- Other API consumers still use `/api/v1` and the Django proxy. They have not
  been switched because equivalent Node endpoints, identity parity, and
  role-based authorization are not complete.
- In the local browser check, the Django proxy target at `127.0.0.1:8000` was
  unavailable (`ECONNREFUSED`). Its requests consequently fail; this does not
  establish that those requests would fail when Django is running.
- The PostgreSQL-backed property dataset includes entries explicitly titled
  `[SAMPLE LISTING - NOT REAL]`. They were returned by the public Node query.
  No records were changed or removed. Confirm whether these are permitted
  demonstration records before production cutover.

## Route-by-route status

“Not verified” means no browser and role-specific test was completed for that
route. A UI route guard is not proof of backend authorization.

| Page and route | API / database operation | UI role gate / expected role | Test and result | Outstanding issue |
|---|---|---|---|---|
| Home `/` | Node `GET /property-types/`, `GET /properties/` (PostgreSQL reads); Django `GET /locations/`, `/homepage-notes/`, `/brokerage/contact/`, `/auth/me/` | Public; optional signed-in header | Browser opened. Node listings/types returned data; Django calls failed because port 8000 refused connections. | Move remaining public reads to Node before standalone Node operation. |
| About `/about` | Django `GET /public-pages/about/`, `/brokerage/contact/` | Public | Not verified | Both endpoints pending in Node. |
| Contact `/contact` | Django `GET /public-pages/contact/`, `/brokerage/contact/` | Public | Not verified | Both endpoints pending in Node. |
| Property management information `/property-management` | Django `GET /public-pages/property-management/`, `/brokerage/contact/` | Public | Not verified | Both endpoints pending in Node. |
| Properties alias `/properties` | Redirects to `/` while preserving query string | Public | Route behavior not separately verified | Search results then use the tested Node property-list API. |
| Property detail `/properties/:slug` | Node `GET /properties/:slug/` and local `/media/...` (PostgreSQL and local files); Django brokerage contact | Public | Browser detail loaded 7 gallery images; 8 page images loaded, 0 broken. Node detail response contained required fields. | Brokerage-contact request still depends on Django. Sample/test-labelled data is present. |
| Viewing receipt `/viewing-requests/status` | Django `GET, POST /viewing-requests/receipt/` | Public receipt-token access | Not verified | Viewing-request APIs pending in Node. |
| Login `/login` | Django `GET /auth/csrf/`, `POST /auth/login/` | Public | Not verified | Node auth exists but UI still uses Django; no account identity/data parity test. |
| Verify email `/verify-email` | Django `POST /auth/verify-email/`, `/auth/verify-email/resend/` | Public token/email flow | Not verified | Node endpoints pending. |
| Forgot password `/forgot-password` | Django `POST /auth/password-reset/` | Public | Not verified | Node endpoint pending. |
| Reset password `/reset-password` | Django `POST /auth/password-reset/confirm/` | Public token flow | Not verified | Node endpoint pending. |
| Accept invitation `/accept-invitation` | Django `POST /auth/invitations/accept/` | Public invitation flow | Not verified | Node endpoint pending. |
| Register `/register` | Django `POST /auth/register/` | Public; registration role limited by current Django policy | Not verified | Node registration is implemented, but the UI and persistent identity remain Django-backed. |
| Settings `/settings` | Django `GET, PATCH /auth/preferences/`, `POST /auth/preferences/reset/` | Signed-in user | Not verified | Node preference handlers exist; frontend still calls Django. |
| Agent onboarding `/agent-onboarding` | Django agent onboarding password/profile endpoints and account APIs | Signed-in agent | Not verified | Node onboarding endpoints pending. |
| Submit property `/submissions/new` | Django locations and `POST /submissions/`; PostgreSQL writes in Django's configured database | Signed-in non-agent marketplace user | Not verified | Submission and location APIs pending in Node. |
| Edit submission `/submissions/:id/edit` | Django `GET, PATCH /submissions/:id/`; database read/write | Signed-in non-agent marketplace user; object ownership enforced by Django | Not verified | Node submission API pending. |
| My submissions `/my-submissions` | Django `GET /submissions/`; database read | Signed-in non-agent marketplace user | Not verified | Node submission API pending. |
| Dashboard `/dashboard` | Django management/admin endpoints; role-dependent PostgreSQL reads | `RequireDashboardAccess` | Not verified | Dashboard endpoint inventory and Node replacements are pending. |
| New viewing request `/viewing-requests/new` | Django `POST /viewing-requests/`; database write | Signed-in non-agent marketplace user | Not verified | Node viewing-request APIs pending. |
| Customer viewing requests `/viewing-requests` | Django `/viewing-requests/mine/` and item/respond/cancel endpoints | Signed-in non-agent marketplace user; owner-scoped | Not verified | Node viewing-request APIs pending. |
| Favorites `/favorites` | Django `GET, POST /favorites/`, `DELETE /favorites/:property_id/`; database read/write | Signed-in non-agent marketplace user | Not verified | Node favorites APIs pending. |
| Account `/account` | Django `/auth/me/`, `/auth/activity/` and account update; database read/write | Signed-in marketplace user | Not verified | Node account is not yet the frontend identity source. |
| Agent management `/management/agents` | Django `/admin/delegated-accounts/` and related account APIs | `RequireAgentAccountManager` | Not verified | Node admin/account APIs pending. |
| Public-account management `/management/public-accounts` | Django `/admin/public-accounts/` and related account APIs | `RequireAgentAccountManager` | Not verified | Node admin/account APIs pending. |
| Listing management `/management/listings` | Django `/management/properties/`; database read/write | `RequireListingManager` | Not verified | Node management-property APIs pending. |
| Create listing `/management/listings/new` | Django property management endpoint and image upload API | `RequireListingManager` | Not verified | Node property mutation API exists only for image operations; property CRUD pending. |
| Edit listing `/management/listings/:id/edit` | Django property management endpoint and image upload API | `RequireListingManager`; object authorization | Not verified | Node property CRUD pending. |
| Submission review `/management/submissions` | Django management-submission, reviewer, assignment, and decision APIs | `RequireListingManager` | Not verified | Node management-submission APIs pending. |
| Viewing management `/management/viewing-requests` | Django management viewing-request and action APIs | `RequireListingManager` | Not verified | Node management viewing APIs pending. |
| Brokerage settings `/management/brokerage` | Django `GET, PATCH /brokerage/contact/`; database read/write | `RequireSettingsManager` | Not verified | Node contact/settings API pending. |
| Site branding `/management/branding` | Django brokerage/branding multipart API; database and local-media operations | `RequireBrandingManager` | Not verified | Node branding API pending. |
| Location management `/management/locations` | Django management location CRUD; database read/write | `RequireLocationManager` | Not verified | Node location APIs pending. |
| Not found `*` | No API operation | Public | Not verified | None identified. |

## Verification performed

- `GET http://127.0.0.1:3000/api/v1/properties/?page=1&page_size=12` returned
  11 properties with the expected paginated response shape.
- `GET http://127.0.0.1:3000/api/v1/property-types/` returned 10 options.
- `GET http://127.0.0.1:3000/api/v1/properties/bahfkdabdju/` returned a
  property with 7 images and required detail fields.
- Browser detail check displayed the property gallery and found 8 loaded images
  on the page with 0 broken images.
- Vite proxy logs identify `homepage-notes`, `brokerage/contact`, `auth/me`,
  and `locations` as requests refused by the unavailable Django target.
- Existing validation: frontend production build passed; backend tests passed
  36/36. These are not substitutes for page-by-page, role-by-role tests.

## Cutover blockers

1. Implement and test the remaining frontend-consumed Node endpoints before
   switching their consumers or claiming the frontend is Node-only.
2. Establish which PostgreSQL database is authoritative and verify all
   accounts/IDs and foreign-key relationships against the active Django data.
3. Run role-based allowed and denied-action tests against Node for each
   protected route; frontend route guards alone do not provide authorization.
4. Decide how explicitly sample-labelled property rows should be treated
   without deleting or silently rewriting database data.
5. Complete browser tests for all routes, validation, loading/error/empty
   states, uploads, pagination, and persistence.

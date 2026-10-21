# PostgreSQL catalog snapshot

Read-only snapshot of database `debre_markos_real_estate`, schema `public`, server version `18.6`.
No application rows were queried. The full catalog report includes all discovered columns/defaults/identity/generated metadata, constraints, indexes, and sequences.

- Observed: 2026-10-20T15:09:15.439Z
- Transaction read-only: `on`
- Tables: 34; columns: 291; indexes: 142; sequences: 32.
- Constraints: 47 FOREIGN KEY; 250 NOT NULL; 34 PRIMARY KEY; 24 UNIQUE; 29 CHECK.

## Columns

### `accounts_delegatedaccountinvitation`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `id` | `bigint (int8)` | NO |  | identity BY DEFAULT |
| `token_digest` | `character varying (varchar)` | NO |  |  |
| `expires_at` | `timestamp with time zone (timestamptz)` | NO |  |  |
| `accepted_at` | `timestamp with time zone (timestamptz)` | YES |  |  |
| `created_at` | `timestamp with time zone (timestamptz)` | NO |  |  |
| `created_by_id` | `integer (int4)` | YES |  |  |
| `user_id` | `integer (int4)` | NO |  |  |

### `accounts_emailverificationtoken`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `id` | `bigint (int8)` | NO |  | identity BY DEFAULT |
| `email` | `character varying (varchar)` | NO |  |  |
| `token_digest` | `character varying (varchar)` | NO |  |  |
| `created_at` | `timestamp with time zone (timestamptz)` | NO |  |  |
| `expires_at` | `timestamp with time zone (timestamptz)` | NO |  |  |
| `user_id` | `integer (int4)` | NO |  |  |

### `accounts_profile`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `id` | `bigint (int8)` | NO |  | identity BY DEFAULT |
| `role` | `character varying (varchar)` | NO |  |  |
| `phone` | `character varying (varchar)` | NO |  |  |
| `agent_approved` | `boolean (bool)` | NO |  |  |
| `created_at` | `timestamp with time zone (timestamptz)` | NO |  |  |
| `updated_at` | `timestamp with time zone (timestamptz)` | NO |  |  |
| `user_id` | `integer (int4)` | NO |  |  |
| `management_permissions` | `jsonb` | NO |  |  |
| `agent_onboarding_required` | `boolean (bool)` | NO |  |  |
| `agent_password_changed` | `boolean (bool)` | NO |  |  |
| `assigned_city_id` | `bigint (int8)` | YES |  |  |

### `accounts_tabsessiontoken`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `id` | `bigint (int8)` | NO |  | identity BY DEFAULT |
| `token_digest` | `character varying (varchar)` | NO |  |  |
| `created_at` | `timestamp with time zone (timestamptz)` | NO |  |  |
| `expires_at` | `timestamp with time zone (timestamptz)` | NO |  |  |
| `revoked_at` | `timestamp with time zone (timestamptz)` | YES |  |  |
| `user_id` | `integer (int4)` | NO |  |  |

### `accounts_userpreferences`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `id` | `bigint (int8)` | NO |  | identity BY DEFAULT |
| `theme` | `character varying (varchar)` | NO |  |  |
| `locale` | `character varying (varchar)` | NO |  |  |
| `density` | `character varying (varchar)` | NO |  |  |
| `reduced_motion` | `boolean (bool)` | NO |  |  |
| `created_at` | `timestamp with time zone (timestamptz)` | NO |  |  |
| `updated_at` | `timestamp with time zone (timestamptz)` | NO |  |  |
| `user_id` | `integer (int4)` | NO |  |  |

### `auth_group`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `id` | `integer (int4)` | NO |  | identity BY DEFAULT |
| `name` | `character varying (varchar)` | NO |  |  |

### `auth_group_permissions`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `id` | `bigint (int8)` | NO |  | identity BY DEFAULT |
| `group_id` | `integer (int4)` | NO |  |  |
| `permission_id` | `integer (int4)` | NO |  |  |

### `auth_permission`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `id` | `integer (int4)` | NO |  | identity BY DEFAULT |
| `name` | `character varying (varchar)` | NO |  |  |
| `content_type_id` | `integer (int4)` | NO |  |  |
| `codename` | `character varying (varchar)` | NO |  |  |

### `auth_user`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `id` | `integer (int4)` | NO |  | identity BY DEFAULT |
| `password` | `character varying (varchar)` | NO |  |  |
| `last_login` | `timestamp with time zone (timestamptz)` | YES |  |  |
| `is_superuser` | `boolean (bool)` | NO |  |  |
| `username` | `character varying (varchar)` | NO |  |  |
| `first_name` | `character varying (varchar)` | NO |  |  |
| `last_name` | `character varying (varchar)` | NO |  |  |
| `email` | `character varying (varchar)` | NO |  |  |
| `is_staff` | `boolean (bool)` | NO |  |  |
| `is_active` | `boolean (bool)` | NO |  |  |
| `date_joined` | `timestamp with time zone (timestamptz)` | NO |  |  |

### `auth_user_groups`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `id` | `bigint (int8)` | NO |  | identity BY DEFAULT |
| `user_id` | `integer (int4)` | NO |  |  |
| `group_id` | `integer (int4)` | NO |  |  |

### `auth_user_user_permissions`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `id` | `bigint (int8)` | NO |  | identity BY DEFAULT |
| `user_id` | `integer (int4)` | NO |  |  |
| `permission_id` | `integer (int4)` | NO |  |  |

### `django_admin_log`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `id` | `integer (int4)` | NO |  | identity BY DEFAULT |
| `action_time` | `timestamp with time zone (timestamptz)` | NO |  |  |
| `object_id` | `text` | YES |  |  |
| `object_repr` | `character varying (varchar)` | NO |  |  |
| `action_flag` | `smallint (int2)` | NO |  |  |
| `change_message` | `text` | NO |  |  |
| `content_type_id` | `integer (int4)` | YES |  |  |
| `user_id` | `integer (int4)` | NO |  |  |

### `django_content_type`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `id` | `integer (int4)` | NO |  | identity BY DEFAULT |
| `app_label` | `character varying (varchar)` | NO |  |  |
| `model` | `character varying (varchar)` | NO |  |  |

### `django_migrations`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `id` | `bigint (int8)` | NO |  | identity BY DEFAULT |
| `app` | `character varying (varchar)` | NO |  |  |
| `name` | `character varying (varchar)` | NO |  |  |
| `applied` | `timestamp with time zone (timestamptz)` | NO |  |  |

### `django_session`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `session_key` | `character varying (varchar)` | NO |  |  |
| `session_data` | `text` | NO |  |  |
| `expire_date` | `timestamp with time zone (timestamptz)` | NO |  |  |

### `favorites_favorite`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `id` | `bigint (int8)` | NO |  | identity BY DEFAULT |
| `created_at` | `timestamp with time zone (timestamptz)` | NO |  |  |
| `property_id` | `bigint (int8)` | NO |  |  |
| `user_id` | `integer (int4)` | NO |  |  |

### `owner_announcements_inappnotification`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `id` | `bigint (int8)` | NO |  | identity BY DEFAULT |
| `notification_type` | `character varying (varchar)` | NO |  |  |
| `message` | `character varying (varchar)` | NO |  |  |
| `idempotency_key` | `character varying (varchar)` | NO |  |  |
| `read_at` | `timestamp with time zone (timestamptz)` | YES |  |  |
| `created_at` | `timestamp with time zone (timestamptz)` | NO |  |  |
| `recipient_id` | `integer (int4)` | NO |  |  |
| `announcement_id` | `bigint (int8)` | YES |  |  |

### `owner_announcements_ownerannouncement`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `id` | `bigint (int8)` | NO |  | identity BY DEFAULT |
| `owner_contact_name` | `character varying (varchar)` | NO |  |  |
| `owner_contact_phone` | `character varying (varchar)` | NO |  |  |
| `owner_contact_email` | `character varying (varchar)` | NO |  |  |
| `public_contact_name` | `character varying (varchar)` | NO |  |  |
| `public_contact_phone` | `character varying (varchar)` | NO |  |  |
| `public_contact_email` | `character varying (varchar)` | NO |  |  |
| `public_contact_visible` | `boolean (bool)` | NO |  |  |
| `authorization_confirmed` | `boolean (bool)` | NO |  |  |
| `terms_accepted_at` | `timestamp with time zone (timestamptz)` | NO |  |  |
| `status` | `character varying (varchar)` | NO |  |  |
| `agent_feedback` | `text` | NO |  |  |
| `submitted_at` | `timestamp with time zone (timestamptz)` | NO |  |  |
| `reviewed_at` | `timestamp with time zone (timestamptz)` | YES |  |  |
| `renewal_requested_at` | `timestamp with time zone (timestamptz)` | YES |  |  |
| `created_at` | `timestamp with time zone (timestamptz)` | NO |  |  |
| `updated_at` | `timestamp with time zone (timestamptz)` | NO |  |  |
| `property_id` | `bigint (int8)` | NO |  |  |
| `reviewed_by_id` | `integer (int4)` | YES |  |  |
| `submitter_id` | `integer (int4)` | NO |  |  |
| `assigned_reviewer_id` | `integer (int4)` | YES |  |  |

### `owner_announcements_ownerannouncementagreement`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `id` | `bigint (int8)` | NO |  | identity BY DEFAULT |
| `start_date` | `date` | NO |  |  |
| `end_date` | `date` | NO |  |  |
| `duration_months` | `smallint (int2)` | NO |  |  |
| `terms` | `text` | NO |  |  |
| `renewal_conditions` | `text` | NO |  |  |
| `public_contact_visible` | `boolean (bool)` | NO |  |  |
| `status` | `character varying (varchar)` | NO |  |  |
| `created_at` | `timestamp with time zone (timestamptz)` | NO |  |  |
| `announcement_id` | `bigint (int8)` | NO |  |  |
| `approved_by_id` | `integer (int4)` | NO |  |  |

### `owner_announcements_ownerannouncementevent`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `id` | `bigint (int8)` | NO |  | identity BY DEFAULT |
| `event_type` | `character varying (varchar)` | NO |  |  |
| `from_status` | `character varying (varchar)` | NO |  |  |
| `to_status` | `character varying (varchar)` | NO |  |  |
| `details` | `jsonb` | NO |  |  |
| `created_at` | `timestamp with time zone (timestamptz)` | NO |  |  |
| `actor_id` | `integer (int4)` | YES |  |  |
| `announcement_id` | `bigint (int8)` | NO |  |  |

### `portal_admin_adminauditevent`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `id` | `bigint (int8)` | NO |  | identity BY DEFAULT |
| `actor_username` | `character varying (varchar)` | NO |  |  |
| `action` | `character varying (varchar)` | NO |  |  |
| `object_type` | `character varying (varchar)` | NO |  |  |
| `object_id` | `character varying (varchar)` | NO |  |  |
| `changes` | `jsonb` | NO |  |  |
| `created_at` | `timestamp with time zone (timestamptz)` | NO |  |  |
| `actor_id` | `integer (int4)` | YES |  |  |

### `portal_admin_brokeragesettings`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `id` | `smallint (int2)` | NO |  |  |
| `business_name` | `character varying (varchar)` | NO |  |  |
| `phone` | `character varying (varchar)` | NO |  |  |
| `whatsapp_url` | `character varying (varchar)` | NO |  |  |
| `telegram_url` | `character varying (varchar)` | NO |  |  |
| `email` | `character varying (varchar)` | NO |  |  |
| `facebook_url` | `character varying (varchar)` | NO |  |  |
| `instagram_url` | `character varying (varchar)` | NO |  |  |
| `tiktok_url` | `character varying (varchar)` | NO |  |  |
| `youtube_url` | `character varying (varchar)` | NO |  |  |
| `linkedin_url` | `character varying (varchar)` | NO |  |  |
| `updated_at` | `timestamp with time zone (timestamptz)` | NO |  |  |
| `platform_owner_id` | `integer (int4)` | YES |  |  |
| `site_logo` | `character varying (varchar)` | NO |  |  |
| `site_name` | `character varying (varchar)` | NO |  |  |
| `homepage_hero_image` | `character varying (varchar)` | NO |  |  |
| `footer_copyright` | `character varying (varchar)` | NO |  |  |

### `portal_admin_homepagenote`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `id` | `bigint (int8)` | NO |  | identity BY DEFAULT |
| `title` | `character varying (varchar)` | NO |  |  |
| `text` | `text` | NO |  |  |
| `is_published` | `boolean (bool)` | NO |  |  |
| `display_order` | `integer (int4)` | NO |  |  |
| `created_at` | `timestamp with time zone (timestamptz)` | NO |  |  |
| `updated_at` | `timestamp with time zone (timestamptz)` | NO |  |  |
| `image` | `character varying (varchar)` | NO |  |  |

### `portal_admin_publicinformationpage`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `id` | `bigint (int8)` | NO |  | identity BY DEFAULT |
| `page` | `character varying (varchar)` | NO |  |  |
| `title_en` | `character varying (varchar)` | NO |  |  |
| `title_am` | `character varying (varchar)` | NO |  |  |
| `introduction_en` | `character varying (varchar)` | NO |  |  |
| `introduction_am` | `character varying (varchar)` | NO |  |  |
| `body_en` | `text` | NO |  |  |
| `body_am` | `text` | NO |  |  |
| `updated_at` | `timestamp with time zone (timestamptz)` | NO |  |  |

### `portal_admin_socialmedialink`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `id` | `bigint (int8)` | NO |  | identity BY DEFAULT |
| `platform` | `character varying (varchar)` | NO |  |  |
| `url` | `character varying (varchar)` | NO |  |  |
| `is_enabled` | `boolean (bool)` | NO |  |  |
| `display_order` | `integer (int4)` | NO |  |  |
| `created_at` | `timestamp with time zone (timestamptz)` | NO |  |  |
| `updated_at` | `timestamp with time zone (timestamptz)` | NO |  |  |
| `brokerage_id` | `smallint (int2)` | NO |  |  |

### `properties_amenity`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `id` | `bigint (int8)` | NO |  | identity BY DEFAULT |
| `name` | `character varying (varchar)` | NO |  |  |
| `name_am` | `character varying (varchar)` | NO |  |  |
| `slug` | `character varying (varchar)` | NO |  |  |

### `properties_listingreport`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `id` | `bigint (int8)` | NO |  | identity BY DEFAULT |
| `property_title` | `character varying (varchar)` | NO |  |  |
| `reporter_name` | `character varying (varchar)` | NO |  |  |
| `reporter_email` | `character varying (varchar)` | NO |  |  |
| `reason` | `character varying (varchar)` | NO |  |  |
| `details` | `text` | NO |  |  |
| `status` | `character varying (varchar)` | NO |  |  |
| `moderator_notes` | `text` | NO |  |  |
| `reviewed_at` | `timestamp with time zone (timestamptz)` | YES |  |  |
| `created_at` | `timestamp with time zone (timestamptz)` | NO |  |  |
| `property_id` | `bigint (int8)` | YES |  |  |
| `reviewed_by_id` | `integer (int4)` | YES |  |  |

### `properties_location`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `id` | `bigint (int8)` | NO |  | identity BY DEFAULT |
| `name` | `character varying (varchar)` | NO |  |  |
| `name_am` | `character varying (varchar)` | NO |  |  |
| `slug` | `character varying (varchar)` | NO |  |  |
| `location_type` | `character varying (varchar)` | NO |  |  |
| `is_active` | `boolean (bool)` | NO |  |  |
| `display_order` | `integer (int4)` | NO |  |  |
| `latitude` | `numeric` | YES |  |  |
| `longitude` | `numeric` | YES |  |  |
| `parent_id` | `bigint (int8)` | YES |  |  |
| `aliases_am` | `jsonb` | NO |  |  |
| `aliases_en` | `jsonb` | NO |  |  |

### `properties_propertyagentassignment`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `id` | `bigint (int8)` | NO |  | identity BY DEFAULT |
| `granted_at` | `timestamp with time zone (timestamptz)` | NO |  |  |
| `agent_id` | `integer (int4)` | NO |  |  |
| `granted_by_id` | `integer (int4)` | YES |  |  |
| `property_id` | `bigint (int8)` | NO |  |  |

### `user_property`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `id` | `bigint (int8)` | NO |  | identity BY DEFAULT |
| `title` | `character varying (varchar)` | NO |  |  |
| `slug` | `character varying (varchar)` | NO |  |  |
| `location` | `character varying (varchar)` | NO |  |  |
| `property_type` | `character varying (varchar)` | NO |  |  |
| `price` | `numeric` | NO |  |  |
| `bedrooms` | `integer (int4)` | NO |  |  |
| `bathrooms` | `integer (int4)` | NO |  |  |
| `area_sqft` | `integer (int4)` | NO |  |  |
| `description` | `text` | NO |  |  |
| `features` | `text` | NO |  |  |
| `status` | `character varying (varchar)` | NO |  |  |
| `is_featured` | `boolean (bool)` | NO |  |  |
| `created_at` | `timestamp with time zone (timestamptz)` | NO |  |  |
| `updated_at` | `timestamp with time zone (timestamptz)` | NO |  |  |
| `listing_type` | `character varying (varchar)` | NO |  |  |
| `contact_email` | `character varying (varchar)` | NO |  |  |
| `contact_name` | `character varying (varchar)` | NO |  |  |
| `contact_phone` | `character varying (varchar)` | NO |  |  |
| `owner_id` | `integer (int4)` | YES |  |  |
| `publication_status` | `character varying (varchar)` | NO |  |  |
| `advertising_authorized` | `boolean (bool)` | NO |  |  |
| `area_unit` | `character varying (varchar)` | NO |  |  |
| `area_value` | `numeric` | YES |  |  |
| `contact_publicly_visible` | `boolean (bool)` | NO |  |  |
| `moderation_note` | `text` | NO |  |  |
| `rental_frequency` | `character varying (varchar)` | NO |  |  |
| `submitted_by_id` | `integer (int4)` | YES |  |  |
| `exact_location_is_public` | `boolean (bool)` | NO |  |  |
| `latitude` | `numeric` | YES |  |  |
| `longitude` | `numeric` | YES |  |  |
| `service_type` | `character varying (varchar)` | NO |  |  |
| `administrative_location_id` | `bigint (int8)` | YES |  |  |

### `user_property_amenities`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `id` | `bigint (int8)` | NO |  | identity BY DEFAULT |
| `property_id` | `bigint (int8)` | NO |  |  |
| `amenity_id` | `bigint (int8)` | NO |  |  |

### `user_propertyimage`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `id` | `bigint (int8)` | NO |  | identity BY DEFAULT |
| `image` | `character varying (varchar)` | NO |  |  |
| `caption` | `character varying (varchar)` | NO |  |  |
| `is_primary` | `boolean (bool)` | NO |  |  |
| `created_at` | `timestamp with time zone (timestamptz)` | NO |  |  |
| `property_id` | `bigint (int8)` | NO |  |  |
| `original_content_type` | `character varying (varchar)` | NO |  |  |
| `original_filename` | `character varying (varchar)` | NO |  |  |
| `original_image` | `character varying (varchar)` | NO |  |  |

### `user_viewingrequest`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `id` | `bigint (int8)` | NO |  | identity BY DEFAULT |
| `full_name` | `character varying (varchar)` | NO |  |  |
| `email` | `character varying (varchar)` | NO |  |  |
| `phone` | `character varying (varchar)` | NO |  |  |
| `preferred_date` | `date` | NO |  |  |
| `message` | `text` | NO |  |  |
| `status` | `character varying (varchar)` | NO |  |  |
| `created_at` | `timestamp with time zone (timestamptz)` | NO |  |  |
| `property_id` | `bigint (int8)` | NO |  |  |
| `agent_notes` | `text` | NO |  |  |
| `preferred_time` | `time without time zone (time)` | YES |  |  |
| `scheduled_date` | `date` | YES |  |  |
| `scheduled_time` | `time without time zone (time)` | YES |  |  |
| `requester_id` | `integer (int4)` | YES |  |  |
| `guest_responded_at` | `timestamp with time zone (timestamptz)` | YES |  |  |
| `proposed_date` | `date` | YES |  |  |
| `proposed_time` | `time without time zone (time)` | YES |  |  |
| `receipt_token_digest` | `character varying (varchar)` | YES |  |  |
| `requester_deleted_at` | `timestamp with time zone (timestamptz)` | YES |  |  |

### `viewings_viewingrequestevent`

| Column | PostgreSQL type | Nullable | Default | Identity / generated |
|---|---|---:|---|---|
| `id` | `bigint (int8)` | NO |  | identity BY DEFAULT |
| `event_type` | `character varying (varchar)` | NO |  |  |
| `from_status` | `character varying (varchar)` | NO |  |  |
| `to_status` | `character varying (varchar)` | NO |  |  |
| `proposed_date` | `date` | YES |  |  |
| `proposed_time` | `time without time zone (time)` | YES |  |  |
| `created_at` | `timestamp with time zone (timestamptz)` | NO |  |  |
| `actor_id` | `integer (int4)` | YES |  |  |
| `viewing_request_id` | `bigint (int8)` | NO |  |  |
| `message` | `text` | NO |  |  |

## Constraints

| Table | Name | Type | Definition |
|---|---|---|---|
| `accounts_delegatedaccountinvitation` | `accounts_delegatedac_created_by_id_89f2753f_fk_auth_user` | FOREIGN KEY | `FOREIGN KEY (created_by_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED` |
| `accounts_delegatedaccountinvitation` | `accounts_delegatedac_user_id_5aff919c_fk_auth_user` | FOREIGN KEY | `FOREIGN KEY (user_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED` |
| `accounts_delegatedaccountinvitation` | `accounts_delegatedaccountinvitation_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `accounts_delegatedaccountinvitation` | `accounts_delegatedaccountinvitation_token_digest_key` | UNIQUE | `UNIQUE (token_digest)` |
| `accounts_emailverificationtoken` | `accounts_emailverifi_user_id_4ff4e6c5_fk_auth_user` | FOREIGN KEY | `FOREIGN KEY (user_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED` |
| `accounts_emailverificationtoken` | `accounts_emailverificationtoken_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `accounts_emailverificationtoken` | `accounts_emailverificationtoken_token_digest_key` | UNIQUE | `UNIQUE (token_digest)` |
| `accounts_profile` | `account_approval_requires_agent` | CHECK | `CHECK (role::text = 'agent'::text OR NOT agent_approved)` |
| `accounts_profile` | `account_profile_valid_role` | CHECK | `CHECK (role::text = ANY (ARRAY['customer'::character varying, 'owner'::character varying, 'agent'::character varying, 'administrator'::character varying]::text[]))` |
| `accounts_profile` | `accounts_profile_assigned_city_id_ad819e31_fk_propertie` | FOREIGN KEY | `FOREIGN KEY (assigned_city_id) REFERENCES properties_location(id) DEFERRABLE INITIALLY DEFERRED` |
| `accounts_profile` | `accounts_profile_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `accounts_profile` | `accounts_profile_user_id_49a85d32_fk_auth_user_id` | FOREIGN KEY | `FOREIGN KEY (user_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED` |
| `accounts_profile` | `accounts_profile_user_id_key` | UNIQUE | `UNIQUE (user_id)` |
| `accounts_tabsessiontoken` | `accounts_tabsessiontoken_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `accounts_tabsessiontoken` | `accounts_tabsessiontoken_token_digest_key` | UNIQUE | `UNIQUE (token_digest)` |
| `accounts_tabsessiontoken` | `accounts_tabsessiontoken_user_id_dbbf1207_fk_auth_user_id` | FOREIGN KEY | `FOREIGN KEY (user_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED` |
| `accounts_userpreferences` | `accounts_userpreferences_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `accounts_userpreferences` | `accounts_userpreferences_user_id_5ed5e4a1_fk_auth_user_id` | FOREIGN KEY | `FOREIGN KEY (user_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED` |
| `accounts_userpreferences` | `accounts_userpreferences_user_id_key` | UNIQUE | `UNIQUE (user_id)` |
| `auth_group` | `auth_group_name_key` | UNIQUE | `UNIQUE (name)` |
| `auth_group` | `auth_group_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `auth_group_permissions` | `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` | FOREIGN KEY | `FOREIGN KEY (permission_id) REFERENCES auth_permission(id) DEFERRABLE INITIALLY DEFERRED` |
| `auth_group_permissions` | `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` | FOREIGN KEY | `FOREIGN KEY (group_id) REFERENCES auth_group(id) DEFERRABLE INITIALLY DEFERRED` |
| `auth_group_permissions` | `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` | UNIQUE | `UNIQUE (group_id, permission_id)` |
| `auth_group_permissions` | `auth_group_permissions_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `auth_permission` | `auth_permission_content_type_id_2f476e4b_fk_django_co` | FOREIGN KEY | `FOREIGN KEY (content_type_id) REFERENCES django_content_type(id) DEFERRABLE INITIALLY DEFERRED` |
| `auth_permission` | `auth_permission_content_type_id_codename_01ab375a_uniq` | UNIQUE | `UNIQUE (content_type_id, codename)` |
| `auth_permission` | `auth_permission_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `auth_user` | `auth_user_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `auth_user` | `auth_user_username_key` | UNIQUE | `UNIQUE (username)` |
| `auth_user_groups` | `auth_user_groups_group_id_97559544_fk_auth_group_id` | FOREIGN KEY | `FOREIGN KEY (group_id) REFERENCES auth_group(id) DEFERRABLE INITIALLY DEFERRED` |
| `auth_user_groups` | `auth_user_groups_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `auth_user_groups` | `auth_user_groups_user_id_6a12ed8b_fk_auth_user_id` | FOREIGN KEY | `FOREIGN KEY (user_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED` |
| `auth_user_groups` | `auth_user_groups_user_id_group_id_94350c0c_uniq` | UNIQUE | `UNIQUE (user_id, group_id)` |
| `auth_user_user_permissions` | `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` | FOREIGN KEY | `FOREIGN KEY (permission_id) REFERENCES auth_permission(id) DEFERRABLE INITIALLY DEFERRED` |
| `auth_user_user_permissions` | `auth_user_user_permissions_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `auth_user_user_permissions` | `auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id` | FOREIGN KEY | `FOREIGN KEY (user_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED` |
| `auth_user_user_permissions` | `auth_user_user_permissions_user_id_permission_id_14a6b632_uniq` | UNIQUE | `UNIQUE (user_id, permission_id)` |
| `django_admin_log` | `django_admin_log_action_flag_check` | CHECK | `CHECK (action_flag >= 0)` |
| `django_admin_log` | `django_admin_log_content_type_id_c4bce8eb_fk_django_co` | FOREIGN KEY | `FOREIGN KEY (content_type_id) REFERENCES django_content_type(id) DEFERRABLE INITIALLY DEFERRED` |
| `django_admin_log` | `django_admin_log_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `django_admin_log` | `django_admin_log_user_id_c564eba6_fk_auth_user_id` | FOREIGN KEY | `FOREIGN KEY (user_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED` |
| `django_content_type` | `django_content_type_app_label_model_76bd3d3b_uniq` | UNIQUE | `UNIQUE (app_label, model)` |
| `django_content_type` | `django_content_type_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `django_migrations` | `django_migrations_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `django_session` | `django_session_pkey` | PRIMARY KEY | `PRIMARY KEY (session_key)` |
| `favorites_favorite` | `favorite_user_property_unique` | UNIQUE | `UNIQUE (user_id, property_id)` |
| `favorites_favorite` | `favorites_favorite_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `favorites_favorite` | `favorites_favorite_property_id_21ea4ca4_fk_user_property_id` | FOREIGN KEY | `FOREIGN KEY (property_id) REFERENCES user_property(id) DEFERRABLE INITIALLY DEFERRED` |
| `favorites_favorite` | `favorites_favorite_user_id_69ee5ed6_fk_auth_user_id` | FOREIGN KEY | `FOREIGN KEY (user_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED` |
| `owner_announcements_inappnotification` | `owner_announcements__announcement_id_469332ff_fk_owner_ann` | FOREIGN KEY | `FOREIGN KEY (announcement_id) REFERENCES owner_announcements_ownerannouncement(id) DEFERRABLE INITIALLY DEFERRED` |
| `owner_announcements_inappnotification` | `owner_announcements__recipient_id_b6e7d2da_fk_auth_user` | FOREIGN KEY | `FOREIGN KEY (recipient_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED` |
| `owner_announcements_inappnotification` | `owner_announcements_inappnotification_idempotency_key_key` | UNIQUE | `UNIQUE (idempotency_key)` |
| `owner_announcements_inappnotification` | `owner_announcements_inappnotification_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `owner_announcements_ownerannouncement` | `owner_announcement_authorized` | CHECK | `CHECK (authorization_confirmed)` |
| `owner_announcements_ownerannouncement` | `owner_announcements__assigned_reviewer_id_8166b215_fk_auth_user` | FOREIGN KEY | `FOREIGN KEY (assigned_reviewer_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED` |
| `owner_announcements_ownerannouncement` | `owner_announcements__property_id_bf8423db_fk_user_prop` | FOREIGN KEY | `FOREIGN KEY (property_id) REFERENCES user_property(id) DEFERRABLE INITIALLY DEFERRED` |
| `owner_announcements_ownerannouncement` | `owner_announcements__reviewed_by_id_17f7e024_fk_auth_user` | FOREIGN KEY | `FOREIGN KEY (reviewed_by_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED` |
| `owner_announcements_ownerannouncement` | `owner_announcements__submitter_id_11e91e06_fk_auth_user` | FOREIGN KEY | `FOREIGN KEY (submitter_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED` |
| `owner_announcements_ownerannouncement` | `owner_announcements_ownerannouncement_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `owner_announcements_ownerannouncement` | `owner_announcements_ownerannouncement_property_id_key` | UNIQUE | `UNIQUE (property_id)` |
| `owner_announcements_ownerannouncementagreement` | `owner_agreement_duration_range` | CHECK | `CHECK (duration_months >= 1 AND duration_months <= 120)` |
| `owner_announcements_ownerannouncementagreement` | `owner_agreement_valid_dates` | CHECK | `CHECK (end_date >= start_date)` |
| `owner_announcements_ownerannouncementagreement` | `owner_announcements__announcement_id_cdd0ad82_fk_owner_ann` | FOREIGN KEY | `FOREIGN KEY (announcement_id) REFERENCES owner_announcements_ownerannouncement(id) DEFERRABLE INITIALLY DEFERRED` |
| `owner_announcements_ownerannouncementagreement` | `owner_announcements__approved_by_id_62d36bbc_fk_auth_user` | FOREIGN KEY | `FOREIGN KEY (approved_by_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED` |
| `owner_announcements_ownerannouncementagreement` | `owner_announcements_ownerannouncementagre_duration_months_check` | CHECK | `CHECK (duration_months >= 0)` |
| `owner_announcements_ownerannouncementagreement` | `owner_announcements_ownerannouncementagreement_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `owner_announcements_ownerannouncementevent` | `owner_announcements__actor_id_778cd9de_fk_auth_user` | FOREIGN KEY | `FOREIGN KEY (actor_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED` |
| `owner_announcements_ownerannouncementevent` | `owner_announcements__announcement_id_7350c065_fk_owner_ann` | FOREIGN KEY | `FOREIGN KEY (announcement_id) REFERENCES owner_announcements_ownerannouncement(id) DEFERRABLE INITIALLY DEFERRED` |
| `owner_announcements_ownerannouncementevent` | `owner_announcements_ownerannouncementevent_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `portal_admin_adminauditevent` | `portal_admin_adminauditevent_actor_id_fd46c42d_fk_auth_user_id` | FOREIGN KEY | `FOREIGN KEY (actor_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED` |
| `portal_admin_adminauditevent` | `portal_admin_adminauditevent_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `portal_admin_brokeragesettings` | `portal_admin_brokera_platform_owner_id_a2ff37ca_fk_auth_user` | FOREIGN KEY | `FOREIGN KEY (platform_owner_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED` |
| `portal_admin_brokeragesettings` | `portal_admin_brokeragesettings_id_check` | CHECK | `CHECK (id >= 0)` |
| `portal_admin_brokeragesettings` | `portal_admin_brokeragesettings_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `portal_admin_homepagenote` | `portal_admin_homepagenote_display_order_check` | CHECK | `CHECK (display_order >= 0)` |
| `portal_admin_homepagenote` | `portal_admin_homepagenote_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `portal_admin_publicinformationpage` | `portal_admin_publicinformationpage_page_key` | UNIQUE | `UNIQUE (page)` |
| `portal_admin_publicinformationpage` | `portal_admin_publicinformationpage_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `portal_admin_socialmedialink` | `brokerage_unique_social_platform` | UNIQUE | `UNIQUE (brokerage_id, platform)` |
| `portal_admin_socialmedialink` | `portal_admin_socialm_brokerage_id_b3e0f5c2_fk_portal_ad` | FOREIGN KEY | `FOREIGN KEY (brokerage_id) REFERENCES portal_admin_brokeragesettings(id) DEFERRABLE INITIALLY DEFERRED` |
| `portal_admin_socialmedialink` | `portal_admin_socialmedialink_display_order_check` | CHECK | `CHECK (display_order >= 0)` |
| `portal_admin_socialmedialink` | `portal_admin_socialmedialink_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `properties_amenity` | `properties_amenity_name_key` | UNIQUE | `UNIQUE (name)` |
| `properties_amenity` | `properties_amenity_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `properties_amenity` | `properties_amenity_slug_key` | UNIQUE | `UNIQUE (slug)` |
| `properties_listingreport` | `properties_listingre_property_id_781f70aa_fk_user_prop` | FOREIGN KEY | `FOREIGN KEY (property_id) REFERENCES user_property(id) DEFERRABLE INITIALLY DEFERRED` |
| `properties_listingreport` | `properties_listingre_reviewed_by_id_1e4d566d_fk_auth_user` | FOREIGN KEY | `FOREIGN KEY (reviewed_by_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED` |
| `properties_listingreport` | `properties_listingreport_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `properties_location` | `location_coordinates_paired` | CHECK | `CHECK (latitude IS NULL AND longitude IS NULL OR latitude IS NOT NULL AND longitude IS NOT NULL)` |
| `properties_location` | `location_latitude_in_range` | CHECK | `CHECK (latitude IS NULL OR latitude >= '-90'::integer::numeric AND latitude <= 90::numeric)` |
| `properties_location` | `location_longitude_in_range` | CHECK | `CHECK (longitude IS NULL OR longitude >= '-180'::integer::numeric AND longitude <= 180::numeric)` |
| `properties_location` | `location_unique_sibling_slug` | UNIQUE | `UNIQUE (parent_id, slug)` |
| `properties_location` | `properties_location_display_order_check` | CHECK | `CHECK (display_order >= 0)` |
| `properties_location` | `properties_location_parent_id_4a5ab43e_fk_propertie` | FOREIGN KEY | `FOREIGN KEY (parent_id) REFERENCES properties_location(id) DEFERRABLE INITIALLY DEFERRED` |
| `properties_location` | `properties_location_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `properties_propertyagentassignment` | `properties_propertya_agent_id_855af66f_fk_auth_user` | FOREIGN KEY | `FOREIGN KEY (agent_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED` |
| `properties_propertyagentassignment` | `properties_propertyb_granted_by_id_b97c3340_fk_auth_user` | FOREIGN KEY | `FOREIGN KEY (granted_by_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED` |
| `properties_propertyagentassignment` | `properties_propertyb_property_id_2f2d29f2_fk_user_prop` | FOREIGN KEY | `FOREIGN KEY (property_id) REFERENCES user_property(id) DEFERRABLE INITIALLY DEFERRED` |
| `properties_propertyagentassignment` | `properties_propertybrokerassignment_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `properties_propertyagentassignment` | `property_agent_assignment_unique` | UNIQUE | `UNIQUE (property_id, agent_id)` |
| `user_property` | `property_area_positive` | CHECK | `CHECK (area_value IS NULL OR area_value > 0::numeric)` |
| `user_property` | `property_area_unit_matches_value` | CHECK | `CHECK (area_unit::text = ''::text AND area_value IS NULL OR (area_unit::text = ANY (ARRAY['sqm'::character varying, 'sqft'::character varying]::text[])) AND area_value > 0::numeric)` |
| `user_property` | `property_coordinates_paired` | CHECK | `CHECK (latitude IS NULL AND longitude IS NULL OR latitude IS NOT NULL AND longitude IS NOT NULL)` |
| `user_property` | `property_frequency_only_for_rent` | CHECK | `CHECK (listing_type::text = 'rent'::text OR rental_frequency::text = ''::text)` |
| `user_property` | `property_latitude_in_range` | CHECK | `CHECK (latitude IS NULL OR latitude >= '-90'::integer::numeric AND latitude <= 90::numeric)` |
| `user_property` | `property_longitude_in_range` | CHECK | `CHECK (longitude IS NULL OR longitude >= '-180'::integer::numeric AND longitude <= 180::numeric)` |
| `user_property` | `property_price_positive` | CHECK | `CHECK (price > 0::numeric)` |
| `user_property` | `property_status_listing_type_compatible` | CHECK | `CHECK ((status::text = ANY (ARRAY['active'::character varying, 'available'::character varying, 'inactive'::character varying]::text[])) OR listing_type::text = 'rent'::text AND status::text = 'rented'::text OR listing_type::text = 'sale'::text AND status::text = 'sold'::text)` |
| `user_property` | `property_valid_category` | CHECK | `CHECK (property_type::text = ANY (ARRAY['house'::character varying, 'villa'::character varying, 'apartment'::character varying, 'condominium'::character varying, 'land'::character varying, 'office'::character varying, 'shop'::character varying, 'warehouse'::character varying, 'commercial'::character varying, 'other'::character varying]::text[]))` |
| `user_property` | `property_valid_publication_status` | CHECK | `CHECK (publication_status::text = ANY (ARRAY['draft'::character varying, 'pending_review'::character varying, 'published'::character varying, 'rejected'::character varying, 'suspended'::character varying, 'expired'::character varying, 'withdrawn'::character varying]::text[]))` |
| `user_property` | `property_valid_rental_frequency` | CHECK | `CHECK (rental_frequency::text = ANY (ARRAY[''::character varying, 'daily'::character varying, 'weekly'::character varying, 'monthly'::character varying, 'yearly'::character varying]::text[]))` |
| `user_property` | `property_valid_status` | CHECK | `CHECK (status::text = ANY (ARRAY['active'::character varying, 'available'::character varying, 'rented'::character varying, 'sold'::character varying, 'inactive'::character varying]::text[]))` |
| `user_property` | `user_property_administrative_locat_0b47d06b_fk_propertie` | FOREIGN KEY | `FOREIGN KEY (administrative_location_id) REFERENCES properties_location(id) DEFERRABLE INITIALLY DEFERRED` |
| `user_property` | `user_property_area_sqft_check` | CHECK | `CHECK (area_sqft >= 0)` |
| `user_property` | `user_property_bathrooms_check` | CHECK | `CHECK (bathrooms >= 0)` |
| `user_property` | `user_property_bedrooms_check` | CHECK | `CHECK (bedrooms >= 0)` |
| `user_property` | `user_property_owner_id_8be83925_fk_auth_user_id` | FOREIGN KEY | `FOREIGN KEY (owner_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED` |
| `user_property` | `user_property_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `user_property` | `user_property_slug_key` | UNIQUE | `UNIQUE (slug)` |
| `user_property` | `user_property_submitted_by_id_b92d6b9e_fk_auth_user_id` | FOREIGN KEY | `FOREIGN KEY (submitted_by_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED` |
| `user_property_amenities` | `user_property_amenit_amenity_id_fcff3480_fk_propertie` | FOREIGN KEY | `FOREIGN KEY (amenity_id) REFERENCES properties_amenity(id) DEFERRABLE INITIALLY DEFERRED` |
| `user_property_amenities` | `user_property_amenit_property_id_c652f1f0_fk_user_prop` | FOREIGN KEY | `FOREIGN KEY (property_id) REFERENCES user_property(id) DEFERRABLE INITIALLY DEFERRED` |
| `user_property_amenities` | `user_property_amenities_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `user_property_amenities` | `user_property_amenities_property_id_amenity_id_fd4f98db_uniq` | UNIQUE | `UNIQUE (property_id, amenity_id)` |
| `user_propertyimage` | `user_propertyimage_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `user_propertyimage` | `user_propertyimage_property_id_cb6e114f_fk_user_property_id` | FOREIGN KEY | `FOREIGN KEY (property_id) REFERENCES user_property(id) DEFERRABLE INITIALLY DEFERRED` |
| `user_viewingrequest` | `user_viewingrequest_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `user_viewingrequest` | `user_viewingrequest_property_id_f6c71c7c_fk_user_property_id` | FOREIGN KEY | `FOREIGN KEY (property_id) REFERENCES user_property(id) DEFERRABLE INITIALLY DEFERRED` |
| `user_viewingrequest` | `user_viewingrequest_receipt_token_digest_key` | UNIQUE | `UNIQUE (receipt_token_digest)` |
| `user_viewingrequest` | `user_viewingrequest_requester_id_fc534092_fk_auth_user_id` | FOREIGN KEY | `FOREIGN KEY (requester_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED` |
| `viewings_viewingrequestevent` | `viewings_viewingrequ_viewing_request_id_2c7bf096_fk_user_view` | FOREIGN KEY | `FOREIGN KEY (viewing_request_id) REFERENCES user_viewingrequest(id) DEFERRABLE INITIALLY DEFERRED` |
| `viewings_viewingrequestevent` | `viewings_viewingrequestevent_actor_id_64e38bab_fk_auth_user_id` | FOREIGN KEY | `FOREIGN KEY (actor_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED` |
| `viewings_viewingrequestevent` | `viewings_viewingrequestevent_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |

NOT NULL constraints are represented by the column nullable values above; PostgreSQL 18 also reports these as catalog constraints.

## Indexes

| Table | Name | Definition |
|---|---|---|
| `accounts_delegatedaccountinvitation` | `account_invite_user_exp_idx` | `CREATE INDEX account_invite_user_exp_idx ON public.accounts_delegatedaccountinvitation USING btree (user_id, expires_at)` |
| `accounts_delegatedaccountinvitation` | `accounts_delegatedaccountinvitation_created_by_id_89f2753f` | `CREATE INDEX accounts_delegatedaccountinvitation_created_by_id_89f2753f ON public.accounts_delegatedaccountinvitation USING btree (created_by_id)` |
| `accounts_delegatedaccountinvitation` | `accounts_delegatedaccountinvitation_pkey` | `CREATE UNIQUE INDEX accounts_delegatedaccountinvitation_pkey ON public.accounts_delegatedaccountinvitation USING btree (id)` |
| `accounts_delegatedaccountinvitation` | `accounts_delegatedaccountinvitation_token_digest_06984afa_like` | `CREATE INDEX accounts_delegatedaccountinvitation_token_digest_06984afa_like ON public.accounts_delegatedaccountinvitation USING btree (token_digest varchar_pattern_ops)` |
| `accounts_delegatedaccountinvitation` | `accounts_delegatedaccountinvitation_token_digest_key` | `CREATE UNIQUE INDEX accounts_delegatedaccountinvitation_token_digest_key ON public.accounts_delegatedaccountinvitation USING btree (token_digest)` |
| `accounts_delegatedaccountinvitation` | `accounts_delegatedaccountinvitation_user_id_5aff919c` | `CREATE INDEX accounts_delegatedaccountinvitation_user_id_5aff919c ON public.accounts_delegatedaccountinvitation USING btree (user_id)` |
| `accounts_emailverificationtoken` | `account_verify_user_exp_idx` | `CREATE INDEX account_verify_user_exp_idx ON public.accounts_emailverificationtoken USING btree (user_id, expires_at)` |
| `accounts_emailverificationtoken` | `accounts_emailverificationtoken_expires_at_e76e5657` | `CREATE INDEX accounts_emailverificationtoken_expires_at_e76e5657 ON public.accounts_emailverificationtoken USING btree (expires_at)` |
| `accounts_emailverificationtoken` | `accounts_emailverificationtoken_pkey` | `CREATE UNIQUE INDEX accounts_emailverificationtoken_pkey ON public.accounts_emailverificationtoken USING btree (id)` |
| `accounts_emailverificationtoken` | `accounts_emailverificationtoken_token_digest_52376022_like` | `CREATE INDEX accounts_emailverificationtoken_token_digest_52376022_like ON public.accounts_emailverificationtoken USING btree (token_digest varchar_pattern_ops)` |
| `accounts_emailverificationtoken` | `accounts_emailverificationtoken_token_digest_key` | `CREATE UNIQUE INDEX accounts_emailverificationtoken_token_digest_key ON public.accounts_emailverificationtoken USING btree (token_digest)` |
| `accounts_emailverificationtoken` | `accounts_emailverificationtoken_user_id_4ff4e6c5` | `CREATE INDEX accounts_emailverificationtoken_user_id_4ff4e6c5 ON public.accounts_emailverificationtoken USING btree (user_id)` |
| `accounts_profile` | `accounts_profile_assigned_city_id_ad819e31` | `CREATE INDEX accounts_profile_assigned_city_id_ad819e31 ON public.accounts_profile USING btree (assigned_city_id)` |
| `accounts_profile` | `accounts_profile_pkey` | `CREATE UNIQUE INDEX accounts_profile_pkey ON public.accounts_profile USING btree (id)` |
| `accounts_profile` | `accounts_profile_user_id_key` | `CREATE UNIQUE INDEX accounts_profile_user_id_key ON public.accounts_profile USING btree (user_id)` |
| `accounts_tabsessiontoken` | `account_tab_token_user_exp_idx` | `CREATE INDEX account_tab_token_user_exp_idx ON public.accounts_tabsessiontoken USING btree (user_id, expires_at)` |
| `accounts_tabsessiontoken` | `accounts_tabsessiontoken_expires_at_10e43bf2` | `CREATE INDEX accounts_tabsessiontoken_expires_at_10e43bf2 ON public.accounts_tabsessiontoken USING btree (expires_at)` |
| `accounts_tabsessiontoken` | `accounts_tabsessiontoken_pkey` | `CREATE UNIQUE INDEX accounts_tabsessiontoken_pkey ON public.accounts_tabsessiontoken USING btree (id)` |
| `accounts_tabsessiontoken` | `accounts_tabsessiontoken_token_digest_7cd9eccd_like` | `CREATE INDEX accounts_tabsessiontoken_token_digest_7cd9eccd_like ON public.accounts_tabsessiontoken USING btree (token_digest varchar_pattern_ops)` |
| `accounts_tabsessiontoken` | `accounts_tabsessiontoken_token_digest_key` | `CREATE UNIQUE INDEX accounts_tabsessiontoken_token_digest_key ON public.accounts_tabsessiontoken USING btree (token_digest)` |
| `accounts_tabsessiontoken` | `accounts_tabsessiontoken_user_id_dbbf1207` | `CREATE INDEX accounts_tabsessiontoken_user_id_dbbf1207 ON public.accounts_tabsessiontoken USING btree (user_id)` |
| `accounts_userpreferences` | `accounts_userpreferences_pkey` | `CREATE UNIQUE INDEX accounts_userpreferences_pkey ON public.accounts_userpreferences USING btree (id)` |
| `accounts_userpreferences` | `accounts_userpreferences_user_id_key` | `CREATE UNIQUE INDEX accounts_userpreferences_user_id_key ON public.accounts_userpreferences USING btree (user_id)` |
| `auth_group` | `auth_group_name_a6ea08ec_like` | `CREATE INDEX auth_group_name_a6ea08ec_like ON public.auth_group USING btree (name varchar_pattern_ops)` |
| `auth_group` | `auth_group_name_key` | `CREATE UNIQUE INDEX auth_group_name_key ON public.auth_group USING btree (name)` |
| `auth_group` | `auth_group_pkey` | `CREATE UNIQUE INDEX auth_group_pkey ON public.auth_group USING btree (id)` |
| `auth_group_permissions` | `auth_group_permissions_group_id_b120cbf9` | `CREATE INDEX auth_group_permissions_group_id_b120cbf9 ON public.auth_group_permissions USING btree (group_id)` |
| `auth_group_permissions` | `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` | `CREATE UNIQUE INDEX auth_group_permissions_group_id_permission_id_0cd325b0_uniq ON public.auth_group_permissions USING btree (group_id, permission_id)` |
| `auth_group_permissions` | `auth_group_permissions_permission_id_84c5c92e` | `CREATE INDEX auth_group_permissions_permission_id_84c5c92e ON public.auth_group_permissions USING btree (permission_id)` |
| `auth_group_permissions` | `auth_group_permissions_pkey` | `CREATE UNIQUE INDEX auth_group_permissions_pkey ON public.auth_group_permissions USING btree (id)` |
| `auth_permission` | `auth_permission_content_type_id_2f476e4b` | `CREATE INDEX auth_permission_content_type_id_2f476e4b ON public.auth_permission USING btree (content_type_id)` |
| `auth_permission` | `auth_permission_content_type_id_codename_01ab375a_uniq` | `CREATE UNIQUE INDEX auth_permission_content_type_id_codename_01ab375a_uniq ON public.auth_permission USING btree (content_type_id, codename)` |
| `auth_permission` | `auth_permission_pkey` | `CREATE UNIQUE INDEX auth_permission_pkey ON public.auth_permission USING btree (id)` |
| `auth_user` | `auth_user_pkey` | `CREATE UNIQUE INDEX auth_user_pkey ON public.auth_user USING btree (id)` |
| `auth_user` | `auth_user_username_6821ab7c_like` | `CREATE INDEX auth_user_username_6821ab7c_like ON public.auth_user USING btree (username varchar_pattern_ops)` |
| `auth_user` | `auth_user_username_key` | `CREATE UNIQUE INDEX auth_user_username_key ON public.auth_user USING btree (username)` |
| `auth_user_groups` | `auth_user_groups_group_id_97559544` | `CREATE INDEX auth_user_groups_group_id_97559544 ON public.auth_user_groups USING btree (group_id)` |
| `auth_user_groups` | `auth_user_groups_pkey` | `CREATE UNIQUE INDEX auth_user_groups_pkey ON public.auth_user_groups USING btree (id)` |
| `auth_user_groups` | `auth_user_groups_user_id_6a12ed8b` | `CREATE INDEX auth_user_groups_user_id_6a12ed8b ON public.auth_user_groups USING btree (user_id)` |
| `auth_user_groups` | `auth_user_groups_user_id_group_id_94350c0c_uniq` | `CREATE UNIQUE INDEX auth_user_groups_user_id_group_id_94350c0c_uniq ON public.auth_user_groups USING btree (user_id, group_id)` |
| `auth_user_user_permissions` | `auth_user_user_permissions_permission_id_1fbb5f2c` | `CREATE INDEX auth_user_user_permissions_permission_id_1fbb5f2c ON public.auth_user_user_permissions USING btree (permission_id)` |
| `auth_user_user_permissions` | `auth_user_user_permissions_pkey` | `CREATE UNIQUE INDEX auth_user_user_permissions_pkey ON public.auth_user_user_permissions USING btree (id)` |
| `auth_user_user_permissions` | `auth_user_user_permissions_user_id_a95ead1b` | `CREATE INDEX auth_user_user_permissions_user_id_a95ead1b ON public.auth_user_user_permissions USING btree (user_id)` |
| `auth_user_user_permissions` | `auth_user_user_permissions_user_id_permission_id_14a6b632_uniq` | `CREATE UNIQUE INDEX auth_user_user_permissions_user_id_permission_id_14a6b632_uniq ON public.auth_user_user_permissions USING btree (user_id, permission_id)` |
| `django_admin_log` | `django_admin_log_content_type_id_c4bce8eb` | `CREATE INDEX django_admin_log_content_type_id_c4bce8eb ON public.django_admin_log USING btree (content_type_id)` |
| `django_admin_log` | `django_admin_log_pkey` | `CREATE UNIQUE INDEX django_admin_log_pkey ON public.django_admin_log USING btree (id)` |
| `django_admin_log` | `django_admin_log_user_id_c564eba6` | `CREATE INDEX django_admin_log_user_id_c564eba6 ON public.django_admin_log USING btree (user_id)` |
| `django_content_type` | `django_content_type_app_label_model_76bd3d3b_uniq` | `CREATE UNIQUE INDEX django_content_type_app_label_model_76bd3d3b_uniq ON public.django_content_type USING btree (app_label, model)` |
| `django_content_type` | `django_content_type_pkey` | `CREATE UNIQUE INDEX django_content_type_pkey ON public.django_content_type USING btree (id)` |
| `django_migrations` | `django_migrations_pkey` | `CREATE UNIQUE INDEX django_migrations_pkey ON public.django_migrations USING btree (id)` |
| `django_session` | `django_session_expire_date_a5c62663` | `CREATE INDEX django_session_expire_date_a5c62663 ON public.django_session USING btree (expire_date)` |
| `django_session` | `django_session_pkey` | `CREATE UNIQUE INDEX django_session_pkey ON public.django_session USING btree (session_key)` |
| `django_session` | `django_session_session_key_c0390e0f_like` | `CREATE INDEX django_session_session_key_c0390e0f_like ON public.django_session USING btree (session_key varchar_pattern_ops)` |
| `favorites_favorite` | `favorite_user_created_idx` | `CREATE INDEX favorite_user_created_idx ON public.favorites_favorite USING btree (user_id, created_at DESC)` |
| `favorites_favorite` | `favorite_user_property_unique` | `CREATE UNIQUE INDEX favorite_user_property_unique ON public.favorites_favorite USING btree (user_id, property_id)` |
| `favorites_favorite` | `favorites_favorite_pkey` | `CREATE UNIQUE INDEX favorites_favorite_pkey ON public.favorites_favorite USING btree (id)` |
| `favorites_favorite` | `favorites_favorite_property_id_21ea4ca4` | `CREATE INDEX favorites_favorite_property_id_21ea4ca4 ON public.favorites_favorite USING btree (property_id)` |
| `favorites_favorite` | `favorites_favorite_user_id_69ee5ed6` | `CREATE INDEX favorites_favorite_user_id_69ee5ed6 ON public.favorites_favorite USING btree (user_id)` |
| `owner_announcements_inappnotification` | `notify_recipient_read_idx` | `CREATE INDEX notify_recipient_read_idx ON public.owner_announcements_inappnotification USING btree (recipient_id, read_at, created_at DESC)` |
| `owner_announcements_inappnotification` | `owner_announcements_inap_idempotency_key_658950de_like` | `CREATE INDEX owner_announcements_inap_idempotency_key_658950de_like ON public.owner_announcements_inappnotification USING btree (idempotency_key varchar_pattern_ops)` |
| `owner_announcements_inappnotification` | `owner_announcements_inappnotification_announcement_id_469332ff` | `CREATE INDEX owner_announcements_inappnotification_announcement_id_469332ff ON public.owner_announcements_inappnotification USING btree (announcement_id)` |
| `owner_announcements_inappnotification` | `owner_announcements_inappnotification_idempotency_key_key` | `CREATE UNIQUE INDEX owner_announcements_inappnotification_idempotency_key_key ON public.owner_announcements_inappnotification USING btree (idempotency_key)` |
| `owner_announcements_inappnotification` | `owner_announcements_inappnotification_pkey` | `CREATE UNIQUE INDEX owner_announcements_inappnotification_pkey ON public.owner_announcements_inappnotification USING btree (id)` |
| `owner_announcements_inappnotification` | `owner_announcements_inappnotification_recipient_id_b6e7d2da` | `CREATE INDEX owner_announcements_inappnotification_recipient_id_b6e7d2da ON public.owner_announcements_inappnotification USING btree (recipient_id)` |
| `owner_announcements_ownerannouncement` | `owner_announce_owner_idx` | `CREATE INDEX owner_announce_owner_idx ON public.owner_announcements_ownerannouncement USING btree (submitter_id, submitted_at DESC)` |
| `owner_announcements_ownerannouncement` | `owner_announce_reviewer_idx` | `CREATE INDEX owner_announce_reviewer_idx ON public.owner_announcements_ownerannouncement USING btree (assigned_reviewer_id, status)` |
| `owner_announcements_ownerannouncement` | `owner_announce_status_idx` | `CREATE INDEX owner_announce_status_idx ON public.owner_announcements_ownerannouncement USING btree (status, submitted_at DESC)` |
| `owner_announcements_ownerannouncement` | `owner_announcements_ownera_assigned_reviewer_id_8166b215` | `CREATE INDEX owner_announcements_ownera_assigned_reviewer_id_8166b215 ON public.owner_announcements_ownerannouncement USING btree (assigned_reviewer_id)` |
| `owner_announcements_ownerannouncement` | `owner_announcements_ownerannouncement_pkey` | `CREATE UNIQUE INDEX owner_announcements_ownerannouncement_pkey ON public.owner_announcements_ownerannouncement USING btree (id)` |
| `owner_announcements_ownerannouncement` | `owner_announcements_ownerannouncement_property_id_key` | `CREATE UNIQUE INDEX owner_announcements_ownerannouncement_property_id_key ON public.owner_announcements_ownerannouncement USING btree (property_id)` |
| `owner_announcements_ownerannouncement` | `owner_announcements_ownerannouncement_reviewed_by_id_17f7e024` | `CREATE INDEX owner_announcements_ownerannouncement_reviewed_by_id_17f7e024 ON public.owner_announcements_ownerannouncement USING btree (reviewed_by_id)` |
| `owner_announcements_ownerannouncement` | `owner_announcements_ownerannouncement_submitter_id_11e91e06` | `CREATE INDEX owner_announcements_ownerannouncement_submitter_id_11e91e06 ON public.owner_announcements_ownerannouncement USING btree (submitter_id)` |
| `owner_announcements_ownerannouncementagreement` | `owner_agreement_expiry_idx` | `CREATE INDEX owner_agreement_expiry_idx ON public.owner_announcements_ownerannouncementagreement USING btree (status, end_date)` |
| `owner_announcements_ownerannouncementagreement` | `owner_announcement_one_active_agreement` | `CREATE UNIQUE INDEX owner_announcement_one_active_agreement ON public.owner_announcements_ownerannouncementagreement USING btree (announcement_id) WHERE ((status)::text = 'active'::text)` |
| `owner_announcements_ownerannouncementagreement` | `owner_announcements_ownera_announcement_id_cdd0ad82` | `CREATE INDEX owner_announcements_ownera_announcement_id_cdd0ad82 ON public.owner_announcements_ownerannouncementagreement USING btree (announcement_id)` |
| `owner_announcements_ownerannouncementagreement` | `owner_announcements_ownera_approved_by_id_62d36bbc` | `CREATE INDEX owner_announcements_ownera_approved_by_id_62d36bbc ON public.owner_announcements_ownerannouncementagreement USING btree (approved_by_id)` |
| `owner_announcements_ownerannouncementagreement` | `owner_announcements_ownerannouncementagreement_pkey` | `CREATE UNIQUE INDEX owner_announcements_ownerannouncementagreement_pkey ON public.owner_announcements_ownerannouncementagreement USING btree (id)` |
| `owner_announcements_ownerannouncementevent` | `owner_announce_event_idx` | `CREATE INDEX owner_announce_event_idx ON public.owner_announcements_ownerannouncementevent USING btree (announcement_id, created_at DESC)` |
| `owner_announcements_ownerannouncementevent` | `owner_announcements_ownera_announcement_id_7350c065` | `CREATE INDEX owner_announcements_ownera_announcement_id_7350c065 ON public.owner_announcements_ownerannouncementevent USING btree (announcement_id)` |
| `owner_announcements_ownerannouncementevent` | `owner_announcements_ownerannouncementevent_actor_id_778cd9de` | `CREATE INDEX owner_announcements_ownerannouncementevent_actor_id_778cd9de ON public.owner_announcements_ownerannouncementevent USING btree (actor_id)` |
| `owner_announcements_ownerannouncementevent` | `owner_announcements_ownerannouncementevent_pkey` | `CREATE UNIQUE INDEX owner_announcements_ownerannouncementevent_pkey ON public.owner_announcements_ownerannouncementevent USING btree (id)` |
| `portal_admin_adminauditevent` | `admin_audit_created_idx` | `CREATE INDEX admin_audit_created_idx ON public.portal_admin_adminauditevent USING btree (created_at DESC)` |
| `portal_admin_adminauditevent` | `admin_audit_object_idx` | `CREATE INDEX admin_audit_object_idx ON public.portal_admin_adminauditevent USING btree (object_type, object_id)` |
| `portal_admin_adminauditevent` | `portal_admin_adminauditevent_actor_id_fd46c42d` | `CREATE INDEX portal_admin_adminauditevent_actor_id_fd46c42d ON public.portal_admin_adminauditevent USING btree (actor_id)` |
| `portal_admin_adminauditevent` | `portal_admin_adminauditevent_pkey` | `CREATE UNIQUE INDEX portal_admin_adminauditevent_pkey ON public.portal_admin_adminauditevent USING btree (id)` |
| `portal_admin_brokeragesettings` | `portal_admin_brokeragesettings_pkey` | `CREATE UNIQUE INDEX portal_admin_brokeragesettings_pkey ON public.portal_admin_brokeragesettings USING btree (id)` |
| `portal_admin_brokeragesettings` | `portal_admin_brokeragesettings_platform_owner_id_a2ff37ca` | `CREATE INDEX portal_admin_brokeragesettings_platform_owner_id_a2ff37ca ON public.portal_admin_brokeragesettings USING btree (platform_owner_id)` |
| `portal_admin_homepagenote` | `portal_admin_homepagenote_pkey` | `CREATE UNIQUE INDEX portal_admin_homepagenote_pkey ON public.portal_admin_homepagenote USING btree (id)` |
| `portal_admin_publicinformationpage` | `portal_admin_publicinformationpage_page_75b7c766_like` | `CREATE INDEX portal_admin_publicinformationpage_page_75b7c766_like ON public.portal_admin_publicinformationpage USING btree (page varchar_pattern_ops)` |
| `portal_admin_publicinformationpage` | `portal_admin_publicinformationpage_page_key` | `CREATE UNIQUE INDEX portal_admin_publicinformationpage_page_key ON public.portal_admin_publicinformationpage USING btree (page)` |
| `portal_admin_publicinformationpage` | `portal_admin_publicinformationpage_pkey` | `CREATE UNIQUE INDEX portal_admin_publicinformationpage_pkey ON public.portal_admin_publicinformationpage USING btree (id)` |
| `portal_admin_socialmedialink` | `brokerage_unique_social_platform` | `CREATE UNIQUE INDEX brokerage_unique_social_platform ON public.portal_admin_socialmedialink USING btree (brokerage_id, platform)` |
| `portal_admin_socialmedialink` | `portal_admin_socialmedialink_brokerage_id_b3e0f5c2` | `CREATE INDEX portal_admin_socialmedialink_brokerage_id_b3e0f5c2 ON public.portal_admin_socialmedialink USING btree (brokerage_id)` |
| `portal_admin_socialmedialink` | `portal_admin_socialmedialink_pkey` | `CREATE UNIQUE INDEX portal_admin_socialmedialink_pkey ON public.portal_admin_socialmedialink USING btree (id)` |
| `properties_amenity` | `properties_amenity_name_01a1703a_like` | `CREATE INDEX properties_amenity_name_01a1703a_like ON public.properties_amenity USING btree (name varchar_pattern_ops)` |
| `properties_amenity` | `properties_amenity_name_key` | `CREATE UNIQUE INDEX properties_amenity_name_key ON public.properties_amenity USING btree (name)` |
| `properties_amenity` | `properties_amenity_pkey` | `CREATE UNIQUE INDEX properties_amenity_pkey ON public.properties_amenity USING btree (id)` |
| `properties_amenity` | `properties_amenity_slug_fadeef4e_like` | `CREATE INDEX properties_amenity_slug_fadeef4e_like ON public.properties_amenity USING btree (slug varchar_pattern_ops)` |
| `properties_amenity` | `properties_amenity_slug_key` | `CREATE UNIQUE INDEX properties_amenity_slug_key ON public.properties_amenity USING btree (slug)` |
| `properties_listingreport` | `listing_report_status_idx` | `CREATE INDEX listing_report_status_idx ON public.properties_listingreport USING btree (status, created_at DESC)` |
| `properties_listingreport` | `properties_listingreport_pkey` | `CREATE UNIQUE INDEX properties_listingreport_pkey ON public.properties_listingreport USING btree (id)` |
| `properties_listingreport` | `properties_listingreport_property_id_781f70aa` | `CREATE INDEX properties_listingreport_property_id_781f70aa ON public.properties_listingreport USING btree (property_id)` |
| `properties_listingreport` | `properties_listingreport_reviewed_by_id_1e4d566d` | `CREATE INDEX properties_listingreport_reviewed_by_id_1e4d566d ON public.properties_listingreport USING btree (reviewed_by_id)` |
| `properties_location` | `location_parent_active_idx` | `CREATE INDEX location_parent_active_idx ON public.properties_location USING btree (parent_id, is_active, display_order)` |
| `properties_location` | `location_unique_root_slug` | `CREATE UNIQUE INDEX location_unique_root_slug ON public.properties_location USING btree (slug) WHERE (parent_id IS NULL)` |
| `properties_location` | `location_unique_sibling_slug` | `CREATE UNIQUE INDEX location_unique_sibling_slug ON public.properties_location USING btree (parent_id, slug)` |
| `properties_location` | `properties_location_parent_id_4a5ab43e` | `CREATE INDEX properties_location_parent_id_4a5ab43e ON public.properties_location USING btree (parent_id)` |
| `properties_location` | `properties_location_pkey` | `CREATE UNIQUE INDEX properties_location_pkey ON public.properties_location USING btree (id)` |
| `properties_location` | `properties_location_slug_0dd71676` | `CREATE INDEX properties_location_slug_0dd71676 ON public.properties_location USING btree (slug)` |
| `properties_location` | `properties_location_slug_0dd71676_like` | `CREATE INDEX properties_location_slug_0dd71676_like ON public.properties_location USING btree (slug varchar_pattern_ops)` |
| `properties_propertyagentassignment` | `agent_assignment_user_idx` | `CREATE INDEX agent_assignment_user_idx ON public.properties_propertyagentassignment USING btree (agent_id, granted_at)` |
| `properties_propertyagentassignment` | `properties_propertybrokerassignment_broker_id_a1309a84` | `CREATE INDEX properties_propertybrokerassignment_broker_id_a1309a84 ON public.properties_propertyagentassignment USING btree (agent_id)` |
| `properties_propertyagentassignment` | `properties_propertybrokerassignment_granted_by_id_b97c3340` | `CREATE INDEX properties_propertybrokerassignment_granted_by_id_b97c3340 ON public.properties_propertyagentassignment USING btree (granted_by_id)` |
| `properties_propertyagentassignment` | `properties_propertybrokerassignment_pkey` | `CREATE UNIQUE INDEX properties_propertybrokerassignment_pkey ON public.properties_propertyagentassignment USING btree (id)` |
| `properties_propertyagentassignment` | `properties_propertybrokerassignment_property_id_2f2d29f2` | `CREATE INDEX properties_propertybrokerassignment_property_id_2f2d29f2 ON public.properties_propertyagentassignment USING btree (property_id)` |
| `properties_propertyagentassignment` | `property_agent_assignment_unique` | `CREATE UNIQUE INDEX property_agent_assignment_unique ON public.properties_propertyagentassignment USING btree (property_id, agent_id)` |
| `user_property` | `property_location_public_idx` | `CREATE INDEX property_location_public_idx ON public.user_property USING btree (administrative_location_id, publication_status, status)` |
| `user_property` | `property_public_search_idx` | `CREATE INDEX property_public_search_idx ON public.user_property USING btree (publication_status, status, listing_type, created_at DESC)` |
| `user_property` | `user_property_administrative_location_id_0b47d06b` | `CREATE INDEX user_property_administrative_location_id_0b47d06b ON public.user_property USING btree (administrative_location_id)` |
| `user_property` | `user_property_location_ed72cd31` | `CREATE INDEX user_property_location_ed72cd31 ON public.user_property USING btree (location)` |
| `user_property` | `user_property_location_ed72cd31_like` | `CREATE INDEX user_property_location_ed72cd31_like ON public.user_property USING btree (location varchar_pattern_ops)` |
| `user_property` | `user_property_owner_id_8be83925` | `CREATE INDEX user_property_owner_id_8be83925 ON public.user_property USING btree (owner_id)` |
| `user_property` | `user_property_pkey` | `CREATE UNIQUE INDEX user_property_pkey ON public.user_property USING btree (id)` |
| `user_property` | `user_property_slug_5da18b78_like` | `CREATE INDEX user_property_slug_5da18b78_like ON public.user_property USING btree (slug varchar_pattern_ops)` |
| `user_property` | `user_property_slug_key` | `CREATE UNIQUE INDEX user_property_slug_key ON public.user_property USING btree (slug)` |
| `user_property` | `user_property_submitted_by_id_b92d6b9e` | `CREATE INDEX user_property_submitted_by_id_b92d6b9e ON public.user_property USING btree (submitted_by_id)` |
| `user_property_amenities` | `user_property_amenities_amenity_id_fcff3480` | `CREATE INDEX user_property_amenities_amenity_id_fcff3480 ON public.user_property_amenities USING btree (amenity_id)` |
| `user_property_amenities` | `user_property_amenities_pkey` | `CREATE UNIQUE INDEX user_property_amenities_pkey ON public.user_property_amenities USING btree (id)` |
| `user_property_amenities` | `user_property_amenities_property_id_amenity_id_fd4f98db_uniq` | `CREATE UNIQUE INDEX user_property_amenities_property_id_amenity_id_fd4f98db_uniq ON public.user_property_amenities USING btree (property_id, amenity_id)` |
| `user_property_amenities` | `user_property_amenities_property_id_c652f1f0` | `CREATE INDEX user_property_amenities_property_id_c652f1f0 ON public.user_property_amenities USING btree (property_id)` |
| `user_propertyimage` | `property_image_one_primary_per_property` | `CREATE UNIQUE INDEX property_image_one_primary_per_property ON public.user_propertyimage USING btree (property_id) WHERE is_primary` |
| `user_propertyimage` | `user_propertyimage_pkey` | `CREATE UNIQUE INDEX user_propertyimage_pkey ON public.user_propertyimage USING btree (id)` |
| `user_propertyimage` | `user_propertyimage_property_id_cb6e114f` | `CREATE INDEX user_propertyimage_property_id_cb6e114f ON public.user_propertyimage USING btree (property_id)` |
| `user_viewingrequest` | `user_viewingrequest_pkey` | `CREATE UNIQUE INDEX user_viewingrequest_pkey ON public.user_viewingrequest USING btree (id)` |
| `user_viewingrequest` | `user_viewingrequest_property_id_f6c71c7c` | `CREATE INDEX user_viewingrequest_property_id_f6c71c7c ON public.user_viewingrequest USING btree (property_id)` |
| `user_viewingrequest` | `user_viewingrequest_receipt_token_digest_56ab2cf0_like` | `CREATE INDEX user_viewingrequest_receipt_token_digest_56ab2cf0_like ON public.user_viewingrequest USING btree (receipt_token_digest varchar_pattern_ops)` |
| `user_viewingrequest` | `user_viewingrequest_receipt_token_digest_key` | `CREATE UNIQUE INDEX user_viewingrequest_receipt_token_digest_key ON public.user_viewingrequest USING btree (receipt_token_digest)` |
| `user_viewingrequest` | `user_viewingrequest_requester_id_fc534092` | `CREATE INDEX user_viewingrequest_requester_id_fc534092 ON public.user_viewingrequest USING btree (requester_id)` |
| `user_viewingrequest` | `viewing_one_active_request_per_user_property` | `CREATE UNIQUE INDEX viewing_one_active_request_per_user_property ON public.user_viewingrequest USING btree (requester_id, property_id) WHERE ((requester_id IS NOT NULL) AND ((status)::text = ANY ((ARRAY['pending'::character varying, 'proposed'::character varying, 'confirmed'::character varying, 'declined'::character varying])::text[])))` |
| `viewings_viewingrequestevent` | `viewings_viewingrequestevent_actor_id_64e38bab` | `CREATE INDEX viewings_viewingrequestevent_actor_id_64e38bab ON public.viewings_viewingrequestevent USING btree (actor_id)` |
| `viewings_viewingrequestevent` | `viewings_viewingrequestevent_pkey` | `CREATE UNIQUE INDEX viewings_viewingrequestevent_pkey ON public.viewings_viewingrequestevent USING btree (id)` |
| `viewings_viewingrequestevent` | `viewings_viewingrequestevent_viewing_request_id_2c7bf096` | `CREATE INDEX viewings_viewingrequestevent_viewing_request_id_2c7bf096 ON public.viewings_viewingrequestevent USING btree (viewing_request_id)` |

## Sequences

| Name | Type | Start | Minimum | Maximum | Increment | Cache | Cycle |
|---|---|---:|---:|---:|---:|---:|---:|
| `accounts_delegatedaccountinvitation_id_seq` | `bigint` | 1 | 1 | 9223372036854775807 | 1 | 1 | false |
| `accounts_emailverificationtoken_id_seq` | `bigint` | 1 | 1 | 9223372036854775807 | 1 | 1 | false |
| `accounts_profile_id_seq` | `bigint` | 1 | 1 | 9223372036854775807 | 1 | 1 | false |
| `accounts_tabsessiontoken_id_seq` | `bigint` | 1 | 1 | 9223372036854775807 | 1 | 1 | false |
| `accounts_userpreferences_id_seq` | `bigint` | 1 | 1 | 9223372036854775807 | 1 | 1 | false |
| `auth_group_id_seq` | `integer` | 1 | 1 | 2147483647 | 1 | 1 | false |
| `auth_group_permissions_id_seq` | `bigint` | 1 | 1 | 9223372036854775807 | 1 | 1 | false |
| `auth_permission_id_seq` | `integer` | 1 | 1 | 2147483647 | 1 | 1 | false |
| `auth_user_groups_id_seq` | `bigint` | 1 | 1 | 9223372036854775807 | 1 | 1 | false |
| `auth_user_id_seq` | `integer` | 1 | 1 | 2147483647 | 1 | 1 | false |
| `auth_user_user_permissions_id_seq` | `bigint` | 1 | 1 | 9223372036854775807 | 1 | 1 | false |
| `django_admin_log_id_seq` | `integer` | 1 | 1 | 2147483647 | 1 | 1 | false |
| `django_content_type_id_seq` | `integer` | 1 | 1 | 2147483647 | 1 | 1 | false |
| `django_migrations_id_seq` | `bigint` | 1 | 1 | 9223372036854775807 | 1 | 1 | false |
| `favorites_favorite_id_seq` | `bigint` | 1 | 1 | 9223372036854775807 | 1 | 1 | false |
| `owner_announcements_inappnotification_id_seq` | `bigint` | 1 | 1 | 9223372036854775807 | 1 | 1 | false |
| `owner_announcements_ownerannouncement_id_seq` | `bigint` | 1 | 1 | 9223372036854775807 | 1 | 1 | false |
| `owner_announcements_ownerannouncementagreement_id_seq` | `bigint` | 1 | 1 | 9223372036854775807 | 1 | 1 | false |
| `owner_announcements_ownerannouncementevent_id_seq` | `bigint` | 1 | 1 | 9223372036854775807 | 1 | 1 | false |
| `portal_admin_adminauditevent_id_seq` | `bigint` | 1 | 1 | 9223372036854775807 | 1 | 1 | false |
| `portal_admin_homepagenote_id_seq` | `bigint` | 1 | 1 | 9223372036854775807 | 1 | 1 | false |
| `portal_admin_publicinformationpage_id_seq` | `bigint` | 1 | 1 | 9223372036854775807 | 1 | 1 | false |
| `portal_admin_socialmedialink_id_seq` | `bigint` | 1 | 1 | 9223372036854775807 | 1 | 1 | false |
| `properties_amenity_id_seq` | `bigint` | 1 | 1 | 9223372036854775807 | 1 | 1 | false |
| `properties_listingreport_id_seq` | `bigint` | 1 | 1 | 9223372036854775807 | 1 | 1 | false |
| `properties_location_id_seq` | `bigint` | 1 | 1 | 9223372036854775807 | 1 | 1 | false |
| `properties_propertybrokerassignment_id_seq` | `bigint` | 1 | 1 | 9223372036854775807 | 1 | 1 | false |
| `user_property_amenities_id_seq` | `bigint` | 1 | 1 | 9223372036854775807 | 1 | 1 | false |
| `user_property_id_seq` | `bigint` | 1 | 1 | 9223372036854775807 | 1 | 1 | false |
| `user_propertyimage_id_seq` | `bigint` | 1 | 1 | 9223372036854775807 | 1 | 1 | false |
| `user_viewingrequest_id_seq` | `bigint` | 1 | 1 | 9223372036854775807 | 1 | 1 | false |
| `viewings_viewingrequestevent_id_seq` | `bigint` | 1 | 1 | 9223372036854775807 | 1 | 1 | false |

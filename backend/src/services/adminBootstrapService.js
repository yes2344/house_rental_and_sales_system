import { hashPassword } from './passwordService.js';

const siteadminUsername = 'siteadmin';

export async function promoteExistingSiteadmin(client, { email, password, apply = false }) {
  const normalizedEmail = email.trim();
  const passwordHash = apply ? await hashPassword(password) : null;

  if (apply) {
    const lockKeys = [siteadminUsername, normalizedEmail].map((value) => value.toLocaleLowerCase()).sort();
    for (const lockKey of lockKeys) {
      await client.query('SELECT pg_advisory_xact_lock(hashtextextended($1, 0))', [lockKey]);
    }
  }

  const account = await client.query(
    `SELECT id, is_active
     FROM auth_user
     WHERE lower(username) = lower($1)
     ORDER BY id
     LIMIT 2${apply ? ' FOR UPDATE' : ''}`,
    [siteadminUsername],
  );
  if (account.rowCount !== 1) {
    throw new Error(
      account.rowCount === 0
        ? 'The existing siteadmin account was not found; no account was created.'
        : 'More than one account matches siteadmin; no changes were made.',
    );
  }
  if (!account.rows[0].is_active) {
    throw new Error('The existing siteadmin account is inactive; activate it separately before promotion.');
  }

  const emailOwner = await client.query(
    `SELECT id
     FROM auth_user
     WHERE lower(email) = lower($1)
       AND id <> $2
     LIMIT 1`,
    [normalizedEmail, account.rows[0].id],
  );
  if (emailOwner.rowCount > 0) {
    throw new Error('The requested email is already assigned to another account.');
  }

  if (!apply) return { status: 'ready', username: siteadminUsername };

  await client.query(
    `UPDATE auth_user
     SET email = $1,
         password = $2,
         is_staff = TRUE,
         is_superuser = TRUE
     WHERE id = $3
       AND is_active = TRUE`,
    [normalizedEmail, passwordHash, account.rows[0].id],
  );
  await client.query(
    `INSERT INTO accounts_profile
       (user_id, role, phone, management_permissions, agent_approved,
        agent_onboarding_required, agent_password_changed, created_at, updated_at)
     VALUES ($1, 'administrator', '', '[]'::jsonb, FALSE, FALSE, TRUE,
             CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
     ON CONFLICT (user_id) DO UPDATE
     SET role = 'administrator',
         management_permissions = '[]'::jsonb,
         agent_approved = FALSE,
         agent_onboarding_required = FALSE,
         agent_password_changed = TRUE,
         updated_at = CURRENT_TIMESTAMP`,
    [account.rows[0].id],
  );
  await client.query(
    `UPDATE accounts_tabsessiontoken
     SET revoked_at = CURRENT_TIMESTAMP
     WHERE user_id = $1
       AND revoked_at IS NULL`,
    [account.rows[0].id],
  );

  return { status: 'promoted', username: siteadminUsername };
}

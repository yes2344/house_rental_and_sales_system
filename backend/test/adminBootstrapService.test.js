import assert from 'node:assert/strict';
import { randomBytes } from 'node:crypto';
import { test } from 'node:test';
import { getAuthenticatedAccount, login } from '../src/services/accountService.js';
import { verifyPassword } from '../src/services/passwordService.js';
import { bootstrapPlatformOwner } from '../src/services/adminBootstrapService.js';

const config = {
  username: 'platformowner',
  email: 'owner@example.test',
  password: randomBytes(32).toString('hex'),
};

function makeClient({
  users = [],
  settingsExists = true,
  platformOwnerId = null,
} = {}) {
  const state = {
    users: structuredClone(users),
    settings: settingsExists ? { platform_owner_id: platformOwnerId } : null,
    nextId: 41,
    sessions: [],
  };
  const calls = [];

  async function query(text, values = []) {
    const sql = text.trim().replace(/\s+/g, ' ');
    calls.push({ sql, values });

    if (['BEGIN', 'BEGIN READ ONLY', 'COMMIT', 'ROLLBACK'].includes(sql)) {
      return { rows: [], rowCount: 0 };
    }
    if (sql.startsWith('SELECT pg_advisory_xact_lock')) return { rows: [], rowCount: 1 };
    if (sql.includes('FROM public.portal_admin_brokeragesettings')) {
      return state.settings ? { rows: [{ ...state.settings }], rowCount: 1 } : { rows: [], rowCount: 0 };
    }
    if (sql.includes('LEFT JOIN public.accounts_profile')) {
      const matches = state.users
        .filter((user) => user.username.toLowerCase() === values[0].toLowerCase()
          || user.email.toLowerCase() === values[1].toLowerCase())
        .sort((a, b) => a.id - b.id)
        .slice(0, 2)
        .map((user) => ({
          id: user.id,
          username: user.username,
          email: user.email,
          is_active: user.is_active,
          is_staff: user.is_staff,
          is_superuser: user.is_superuser,
          role: user.role ?? null,
        }));
      return { rows: matches, rowCount: matches.length };
    }
    if (sql.includes('WHERE is_active = TRUE AND is_superuser = TRUE')) {
      const activeOwners = state.users
        .filter((user) => user.is_active && user.is_superuser)
        .sort((a, b) => a.id - b.id)
        .map(({ id }) => ({ id }));
      return { rows: activeOwners, rowCount: activeOwners.length };
    }
    if (sql.startsWith('INSERT INTO public.auth_user')) {
      const [passwordHash, username, email] = values;
      const user = {
        id: state.nextId++,
        username,
        email,
        password: passwordHash,
        is_active: true,
        is_staff: true,
        is_superuser: true,
        role: null,
        management_permissions: [],
        agent_approved: false,
        agent_onboarding_required: false,
        agent_password_changed: true,
      };
      state.users.push(user);
      return { rows: [{ id: user.id }], rowCount: 1 };
    }
    if (sql.startsWith('INSERT INTO public.accounts_profile')) {
      const user = state.users.find(({ id }) => id === values[0]);
      Object.assign(user, {
        role: 'administrator',
        management_permissions: [],
        agent_approved: false,
        agent_onboarding_required: false,
        agent_password_changed: true,
      });
      return { rows: [], rowCount: 1 };
    }
    if (sql.startsWith('UPDATE public.portal_admin_brokeragesettings')) {
      if (!state.settings || state.settings.platform_owner_id !== null) {
        return { rows: [], rowCount: 0 };
      }
      state.settings.platform_owner_id = values[0];
      return { rows: [], rowCount: 1 };
    }
    if (sql.includes('FROM auth_user WHERE lower(email) = lower($1)')) {
      const matches = state.users
        .filter((user) => user.email.toLowerCase() === values[0].toLowerCase())
        .map((user) => ({ id: user.id, password: user.password }));
      return { rows: matches, rowCount: matches.length };
    }
    if (sql.startsWith('SELECT is_active FROM auth_user')) {
      const user = state.users.find(({ id }) => id === values[0]);
      return { rows: user ? [{ is_active: user.is_active }] : [], rowCount: user ? 1 : 0 };
    }
    if (sql.startsWith('SELECT account.id, account.username')) {
      const user = state.users.find(({ id }) => id === values[0]);
      if (!user) return { rows: [], rowCount: 0 };
      return {
        rows: [{
          id: user.id,
          username: user.username,
          email: user.email,
          first_name: '',
          last_name: '',
          is_active: user.is_active,
          is_staff: user.is_staff,
          is_superuser: user.is_superuser,
          role: user.role,
          phone: '',
          management_permissions: user.management_permissions,
          agent_approved: user.agent_approved,
          agent_onboarding_required: user.agent_onboarding_required,
          agent_password_changed: user.agent_password_changed,
          assigned_city_id: null,
          assigned_city_name: null,
          assigned_city_name_am: null,
          platform_owner_id: state.settings?.platform_owner_id ?? state.users
            .filter((account) => account.is_active && account.is_superuser)
            .sort((a, b) => a.id - b.id)[0]?.id ?? null,
        }],
        rowCount: 1,
      };
    }
    if (sql.startsWith('INSERT INTO accounts_tabsessiontoken')) {
      state.sessions.push(values);
      return { rows: [], rowCount: 1 };
    }
    return { rows: [], rowCount: 0 };
  }

  const client = {
    state,
    calls,
    query,
    connect: async () => ({ query, release() {} }),
  };
  return client;
}

test('platform owner dry run validates setup without changing data', async () => {
  const client = makeClient();

  const result = await bootstrapPlatformOwner(client, config);

  assert.deepEqual(result, { status: 'ready', username: config.username });
  assert.equal(client.state.users.length, 0);
  assert.equal(client.state.settings.platform_owner_id, null);
  assert.equal(client.calls.some(({ sql }) => /^(INSERT|UPDATE)/i.test(sql)), false);
  assert.equal(client.calls.some(({ sql }) => sql.includes('pg_advisory_xact_lock')), false);
});

test('platform owner creation uses the existing password hash and administrator profile', async () => {
  const client = makeClient();

  const result = await bootstrapPlatformOwner(client, { ...config, apply: true });
  const user = client.state.users[0];

  assert.deepEqual(result, { status: 'created', username: config.username });
  assert.equal(user.is_active, true);
  assert.equal(user.is_staff, true);
  assert.equal(user.is_superuser, true);
  assert.equal(user.role, 'administrator');
  assert.equal(client.state.settings.platform_owner_id, user.id);
  assert.equal(await verifyPassword(config.password, user.password), true);
  assert.ok(client.calls.some(({ sql }) => sql.startsWith('INSERT INTO public.accounts_profile')));
  assert.ok(client.calls.some(({ sql }) => sql.startsWith('UPDATE public.portal_admin_brokeragesettings')));
  assert.equal(JSON.stringify(client.calls).includes(config.password), false);
});

test('owner creation without an existing settings row relies on the existing owner fallback', async () => {
  const client = makeClient({ settingsExists: false });

  const result = await bootstrapPlatformOwner(client, { ...config, apply: true });

  assert.deepEqual(result, { status: 'created', username: config.username });
  assert.equal(client.state.users.length, 1);
  assert.equal(client.state.settings, null);
  assert.equal(
    client.calls.some(({ sql }) => sql.startsWith('UPDATE public.portal_admin_brokeragesettings')),
    false,
  );
});

test('created owner can sign in and receives owner plus administrator permissions', async () => {
  const client = makeClient();
  await bootstrapPlatformOwner(client, { ...config, apply: true });

  const result = await login(client, config.email, config.password);
  const account = await getAuthenticatedAccount(client, result.account.id);

  assert.equal(account.username, config.username);
  assert.equal(account.role, 'administrator');
  assert.equal(account.is_platform_owner, true);
  for (const permission of [
    'settings.manage',
    'staff.manage',
    'users.manage',
    'properties.moderate',
    'reports.review',
    'audit.view',
    'agents.assign',
    'announcements.review',
    'announcements.assign',
  ]) {
    assert.ok(account.management_permissions.includes(permission), `expected ${permission}`);
  }
  assert.ok(result.sessionToken.length > 30);
  assert.equal(Object.hasOwn(result.account, 'password'), false);
});

test('repeated setup is a no-op only for the already configured owner', async () => {
  const client = makeClient();
  await bootstrapPlatformOwner(client, { ...config, apply: true });
  const originalHash = client.state.users[0].password;
  const initialInsertCount = client.calls.filter(({ sql }) => sql.startsWith('INSERT INTO public.auth_user')).length;

  const result = await bootstrapPlatformOwner(client, {
    ...config,
    password: randomBytes(32).toString('hex'),
    apply: true,
  });

  assert.deepEqual(result, { status: 'already_configured', username: config.username });
  assert.equal(client.state.users.length, 1);
  assert.equal(client.state.users[0].password, originalHash);
  assert.equal(
    client.calls.filter(({ sql }) => sql.startsWith('INSERT INTO public.auth_user')).length,
    initialInsertCount,
  );
});

test('setup refuses existing username or email conflicts without modification', async (t) => {
  await t.test('username belongs to another account', async () => {
    const client = makeClient({
      users: [{
        id: 7, username: config.username, email: 'different@example.test',
        is_active: true, is_staff: false, is_superuser: false, role: 'customer',
      }],
    });
    await assert.rejects(
      bootstrapPlatformOwner(client, { ...config, apply: true }),
      /already matches/,
    );
    assert.equal(client.state.users.length, 1);
  });

  await t.test('email belongs to another account', async () => {
    const client = makeClient({
      users: [{
        id: 7, username: 'different-user', email: config.email,
        is_active: true, is_staff: false, is_superuser: false, role: 'customer',
      }],
    });
    await assert.rejects(
      bootstrapPlatformOwner(client, { ...config, apply: true }),
      /already matches/,
    );
    assert.equal(client.state.users.length, 1);
  });
});

test('setup refuses existing owners and never transfers the ownership pointer', async (t) => {
  await t.test('active superuser exists while no owner was requested', async () => {
    const client = makeClient({
      users: [{
        id: 3, username: 'existing-owner', email: 'existing@example.test',
        is_active: true, is_staff: true, is_superuser: true, role: 'administrator',
      }],
    });
    await assert.rejects(
      bootstrapPlatformOwner(client, { ...config, apply: true }),
      /already exists; ownership was not changed/,
    );
    assert.equal(client.state.users.length, 1);
  });

  await t.test('owner pointer already names another account', async () => {
    const client = makeClient({ platformOwnerId: 3 });
    await assert.rejects(
      bootstrapPlatformOwner(client, { ...config, apply: true }),
      /already exists; ownership was not changed/,
    );
    assert.equal(client.state.users.length, 0);
    assert.equal(client.state.settings.platform_owner_id, 3);
  });
});

test('setup rejects weak or malformed credentials', async (t) => {
  for (const overrides of [
    { username: '' },
    { email: 'not-an-email' },
    { password: 'short' },
  ]) {
    await t.test(JSON.stringify(Object.keys(overrides)), async () => {
      await assert.rejects(
        bootstrapPlatformOwner(makeClient(), { ...config, ...overrides }),
        /must satisfy account requirements/,
      );
    });
  }
});

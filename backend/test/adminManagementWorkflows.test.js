import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import express from 'express';
import { after, before, test } from 'node:test';
import { adminManagementWorkflowsRouter } from '../src/routes/adminManagementWorkflows.js';
import { errorHandler } from '../src/middleware/errorHandler.js';
import {
  homepageNotePatchSchema,
  managedPropertyPatchSchema,
} from '../src/validators/adminManagementWorkflows.js';

const token = 'api-parity-test-token';
const digest = createHash('sha256').update(token, 'utf8').digest('hex');
const csrf = 'same-origin-csrf-test-token';
let server;
let origin;
const transactionQueries = [];
const managedPropertyInsertQueries = [];
let testAccountRole = 'platform-owner';
const agentAccount = {
  id: 42,
  username: 'managed-agent',
  email: 'agent@example.test',
  first_name: 'Managed',
  last_name: 'Agent',
  is_active: true,
  is_staff: false,
  is_superuser: false,
  date_joined: '2026-01-01T00:00:00.000Z',
  role: 'agent',
  phone: '0911000000',
  assigned_city_id: 7,
  agent_approved: true,
  agent_onboarding_required: false,
  management_permissions: [],
};

const pool = {
  async query(sql, values = []) {
    if (sql.includes('FROM accounts_tabsessiontoken AS session')) {
      assert.equal(values[0], digest);
      return { rowCount: 1, rows: [{ session_id: 1, user_id: 3 }] };
    }
    if (sql.includes('FROM auth_user u LEFT JOIN accounts_profile p')) {
      return {
        rowCount: 1,
        rows: [{
          id: 3,
          username: 'workflow-admin',
          is_active: true,
          is_staff: !['agent', 'settings-manager'].includes(testAccountRole),
          is_superuser: testAccountRole === 'platform-owner',
          platform_owner_id: testAccountRole === 'platform-owner' ? 3 : null,
          role: ['agent', 'settings-manager'].includes(testAccountRole) ? 'agent' : 'administrator',
          agent_approved: testAccountRole === 'settings-manager',
          management_permissions: testAccountRole === 'settings-manager' ? ['settings.manage'] : [],
        }],
      };
    }
    if (sql.includes('FROM auth_user u JOIN accounts_profile p')) {
      return { rowCount: 1, rows: [{ ...agentAccount }] };
    }
    if (sql.includes('SELECT id FROM auth_user WHERE lower(username)')) {
      return { rowCount: 0, rows: [] };
    }
    if (sql.includes('FROM properties_location')) {
      return { rowCount: 1, rows: [{ id: 7 }] };
    }
    if (sql.includes('SELECT phone FROM accounts_profile')) {
      return { rowCount: 1, rows: [{ phone: '0911000000' }] };
    }
    if (sql.includes('FROM user_propertyimage')) {
      return { rowCount: 0, rows: [] };
    }
    if (sql.includes('FROM portal_admin_publicinformationpage ORDER BY page')) {
      return {
        rowCount: 3,
        rows: ['about', 'contact', 'property-management'].map((page) => ({
          page,
          title_en: page,
          title_am: page,
          introduction_en: 'Introduction',
          introduction_am: 'መግቢያ',
          body_en: '',
          body_am: '',
          updated_at: '2026-01-01T00:00:00.000Z',
        })),
      };
    }
    throw new Error(`Unexpected test SQL: ${sql}`);
  },
  async connect() {
    return {
      async query(sql, values = []) {
        transactionQueries.push({ sql, values });
        if (sql.includes('FROM auth_user AS u')) {
          return {
            rowCount: 1,
            rows: [{
              id: 3,
              username: 'workflow-admin',
              first_name: '',
              last_name: '',
              email: '',
              is_active: true,
              is_staff: true,
              is_superuser: false,
              role: 'administrator',
              phone: '0911000000',
              agent_approved: false,
              management_permissions: [],
              assigned_city_id: null,
            }],
          };
        }
        if (sql.includes('SELECT id FROM properties_location')) {
          return { rowCount: 1, rows: [{ id: 7 }] };
        }
        if (sql.includes('INSERT INTO user_property')) {
          managedPropertyInsertQueries.push({ sql, values });
          return {
            rowCount: 1,
            rows: [{
              id: 100,
              title: values[0],
              slug: values[1],
              location: values[2],
              administrative_location_id: values[3],
              property_type: values[4],
              listing_type: values[5],
              price: values[6],
              rental_frequency: values[7],
              bedrooms: values[8],
              bathrooms: values[9],
              area_sqft: values[10],
              area_value: values[11],
              area_unit: values[12],
              description: values[13],
              features: values[14],
              status: values[15],
              publication_status: 'pending_review',
              is_featured: false,
              submitted_by_id: 3,
              moderation_note: '',
              contact_name: values[17],
              contact_phone: values[18],
              contact_email: values[19],
            }],
          };
        }
        if (sql.includes('FROM auth_user u JOIN accounts_profile p')) {
          return { rowCount: 1, rows: [{ ...agentAccount }] };
        }
        return { rowCount: 1, rows: [] };
      },
      release() {},
    };
  },
};

before(async () => {
  const app = express();
  app.use(express.json());
  app.use('/api/v1', adminManagementWorkflowsRouter({ pool }));
  app.use(errorHandler({ logger: { error() {} } }));
  server = app.listen(0);
  await new Promise((resolve) => server.once('listening', resolve));
  origin = `http://127.0.0.1:${server.address().port}/api/v1`;
});

after(async () => {
  await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
});

test('management public pages list uses the authenticated workflow route', async () => {
  const response = await fetch(`${origin}/management/public-pages/`, {
    headers: { Authorization: ['Bearer', token].join(' ') },
  });
  assert.equal(response.status, 200);
  const data = await response.json();
  assert.equal(data.count, 3);
  assert.deepEqual(data.results.map((page) => page.page), ['about', 'contact', 'property-management']);
});

test('management public pages are available to administrators who are not platform owners', async () => {
  testAccountRole = 'administrator';
  try {
    const response = await fetch(`${origin}/management/public-pages/`, {
      headers: { Authorization: ['Bearer', token].join(' ') },
    });
    assert.equal(response.status, 200);
  } finally {
    testAccountRole = 'platform-owner';
  }
});

test('management public pages are available to approved platform managers', async () => {
  testAccountRole = 'settings-manager';
  try {
    const response = await fetch(`${origin}/management/public-pages/`, {
      headers: { Authorization: ['Bearer', token].join(' ') },
    });
    assert.equal(response.status, 200);
  } finally {
    testAccountRole = 'platform-owner';
  }
});

test('management public pages reject agents', async () => {
  testAccountRole = 'agent';
  try {
    const response = await fetch(`${origin}/management/public-pages/`, {
      headers: { Authorization: ['Bearer', token].join(' ') },
    });
    assert.equal(response.status, 403);
  } finally {
    testAccountRole = 'platform-owner';
  }
});

test('managed property creation supplies non-null privacy and authorization flags', async () => {
  managedPropertyInsertQueries.length = 0;
  const response = await fetch(`${origin}/management/properties/`, {
    method: 'POST',
    headers: {
      Authorization: ['Bearer', token].join(' '),
      Cookie: `csrftoken=${csrf}`,
      'X-CSRFToken': csrf,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      title: 'Regression property',
      location: 'Addis Ababa',
      administrative_location: 7,
      category: 'house',
      listing_type: 'sale',
      price: '100000',
      contact_name: 'Property contact',
    }),
  });

  assert.equal(response.status, 201);
  const insert = managedPropertyInsertQueries[0];
  assert.ok(insert);
  assert.match(insert.sql, /advertising_authorized,\s*contact_publicly_visible,\s*exact_location_is_public/);
  assert.match(insert.sql, /'agent_managed',FALSE,\$17,'',FALSE,FALSE,FALSE,\$18/);
});

test('management homepage note creation rejects invalid content before database writes', async () => {
  const response = await fetch(`${origin}/management/homepage-notes/`, {
    method: 'POST',
    headers: {
      Authorization: ['Bearer', token].join(' '),
      Cookie: `csrftoken=${csrf}`,
      'X-CSRFToken': csrf,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ text: '  ' }),
  });
  assert.equal(response.status, 400);
  assert.match((await response.json()).error.message, /validation/i);
});

test('saving a managed agent serializes management permissions as JSONB', async () => {
  transactionQueries.length = 0;
  const response = await fetch(`${origin}/admin/delegated-accounts/42/`, {
    method: 'PATCH',
    headers: {
      Authorization: ['Bearer', token].join(' '),
      Cookie: `csrftoken=${csrf}`,
      'X-CSRFToken': csrf,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      username: 'managed-agent',
      email: 'agent@example.test',
      first_name: 'Managed',
      last_name: 'Agent',
      phone: '0911000000',
      is_active: true,
      assigned_city_id: 7,
      management_permissions: ['announcements.review_assigned'],
    }),
  });

  assert.equal(response.status, 200);
  const profileUpdate = transactionQueries.find(({ sql }) =>
    sql.includes('UPDATE accounts_profile SET') && sql.includes('management_permissions ='));
  assert.ok(profileUpdate);
  assert.match(profileUpdate.sql, /management_permissions = \$3::jsonb/);
  assert.equal(profileUpdate.values[2], '["announcements.review_assigned"]');
});

test('admin management workflow router requires an authenticated account', async () => {
  const response = await fetch(`${origin}/management/public-pages/`);
  assert.equal(response.status, 401);
});

test('partial update schemas preserve omitted fields and reject unsupported fields', () => {
  assert.deepEqual(managedPropertyPatchSchema.parse({ status: 'inactive' }), { status: 'inactive' });
  assert.deepEqual(homepageNotePatchSchema.parse({ title: 'Updated' }), { title: 'Updated' });
  assert.equal(managedPropertyPatchSchema.safeParse({ is_featured: true }).success, false);
});

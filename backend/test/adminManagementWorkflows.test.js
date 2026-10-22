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
          is_staff: true,
          is_superuser: true,
          platform_owner_id: 3,
          role: 'administrator',
          agent_approved: false,
          management_permissions: [],
        }],
      };
    }
    if (sql.includes('FROM portal_admin_publicinformationpage ORDER BY page')) {
      return {
        rowCount: 1,
        rows: [{
          page: 'about',
          title_en: 'About',
          title_am: 'ስለ',
          introduction_en: 'Introduction',
          introduction_am: 'መግቢያ',
          body_en: '',
          body_am: '',
          updated_at: '2026-01-01T00:00:00.000Z',
        }],
      };
    }
    throw new Error(`Unexpected test SQL: ${sql}`);
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
    headers: { Authorization: `Bearer ${token}` },
  });
  assert.equal(response.status, 200);
  assert.deepEqual((await response.json()).results.map((page) => page.page), ['about']);
});

test('management homepage note creation rejects invalid content before database writes', async () => {
  const response = await fetch(`${origin}/management/homepage-notes/`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      Cookie: `csrftoken=${csrf}`,
      'X-CSRFToken': csrf,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ text: '  ' }),
  });
  assert.equal(response.status, 400);
  assert.match((await response.json()).error.message, /validation/i);
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

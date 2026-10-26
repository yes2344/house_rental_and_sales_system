import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import express from 'express';
import { createApp } from '../src/app.js';
import { errorHandler } from '../src/middleware/errorHandler.js';

let server;
let baseUrl;

function fakePool(queryFailure) {
  return {
    connect: async () => ({
      query: async (sql) => {
        if (sql === 'SELECT 1' && queryFailure) throw queryFailure;
        return { rows: [{ '?column?': 1 }] };
      },
      release() {},
    }),
  };
}

before(async () => {
  const app = createApp({ pool: fakePool() });
  server = app.listen(0, '127.0.0.1');
  await new Promise((resolve) => server.once('listening', resolve));
  baseUrl = `http://127.0.0.1:${server.address().port}`;
});

after(async () => {
  await new Promise((resolve, reject) => {
    server.close((error) => error ? reject(error) : resolve());
  });
});

test('health endpoint confirms PostgreSQL connectivity', async () => {
  const response = await fetch(`${baseUrl}/api/v1/health/`);
  assert.equal(response.status, 200);
  assert.match(response.headers.get('x-request-id') || '', /^[\da-f-]{36}$/i);
  assert.deepEqual(await response.json(), { status: 'ok', database: 'ok' });
});

test('production frontend origin can call the API with credentials', async () => {
  const response = await fetch(`${baseUrl}/api/v1/health/`, {
    headers: { Origin: 'https://infinityhouseproperties.com' },
  });
  assert.equal(response.status, 200);
  assert.equal(response.headers.get('access-control-allow-origin'), 'https://infinityhouseproperties.com');
  assert.equal(response.headers.get('access-control-allow-credentials'), 'true');
});

test('production frontend preflight allows only the API methods and headers', async () => {
  const response = await fetch(`${baseUrl}/api/v1/locations/`, {
    method: 'OPTIONS',
    headers: {
      Origin: 'https://infinityhouseproperties.com',
      'Access-Control-Request-Method': 'GET',
      'Access-Control-Request-Headers': 'authorization,content-type',
    },
  });
  assert.equal(response.status, 204);
  assert.equal(response.headers.get('access-control-allow-origin'), 'https://infinityhouseproperties.com');
  assert.equal(response.headers.get('access-control-allow-credentials'), 'true');
  assert.equal(response.headers.get('access-control-allow-methods'), 'GET, HEAD, POST, PUT, PATCH, DELETE, OPTIONS');
  assert.equal(response.headers.get('access-control-allow-headers'), 'Authorization, Content-Type, X-CSRFToken');
});

test('unconfigured origins remain rejected', async () => {
  const response = await fetch(`${baseUrl}/api/v1/health/`, {
    headers: { Origin: 'https://untrusted.example' },
  });
  assert.equal(response.status, 403);
  assert.equal(response.headers.get('access-control-allow-origin'), null);
  assert.deepEqual(await response.json(), {
    error: {
      status_code: 403,
      message: 'Origin is not allowed.',
      details: {},
    },
  });
});

test('authenticated endpoints retain their authentication requirement for the production origin', async () => {
  const response = await fetch(`${baseUrl}/api/v1/auth/me/`, {
    headers: { Origin: 'https://infinityhouseproperties.com' },
  });
  assert.equal(response.status, 401);
  assert.equal(response.headers.get('access-control-allow-origin'), 'https://infinityhouseproperties.com');
});

test('production CSRF cookies support the cross-site frontend with Secure protection', async () => {
  const previousNodeEnv = process.env.NODE_ENV;
  process.env.NODE_ENV = 'production';
  try {
    const response = await fetch(`${baseUrl}/api/v1/auth/csrf/`, {
      headers: { Origin: 'https://infinityhouseproperties.com' },
    });
    assert.equal(response.status, 200);
    assert.match(response.headers.get('set-cookie') ?? '', /SameSite=None; Secure/);
  } finally {
    if (previousNodeEnv === undefined) delete process.env.NODE_ENV;
    else process.env.NODE_ENV = previousNodeEnv;
  }
});

test('health endpoint reports database outages without claiming success', async () => {
  const errors = [];
  const app = createApp({
    pool: fakePool(new Error('connection refused')),
    logger: { error: (...values) => errors.push(values) },
  });
  const outageServer = app.listen(0, '127.0.0.1');
  await new Promise((resolve) => outageServer.once('listening', resolve));

  try {
    const response = await fetch(`http://127.0.0.1:${outageServer.address().port}/api/v1/health/`);
    assert.equal(response.status, 503);
    assert.equal((await response.json()).error.status_code, 503);
    assert.equal(errors.length, 1);
  } finally {
    await new Promise((resolve, reject) => {
      outageServer.close((error) => error ? reject(error) : resolve());
    });
  }
});

test('unknown API routes return a JSON 404', async () => {
  const response = await fetch(`${baseUrl}/api/v1/unknown/`);
  assert.equal(response.status, 404);
  assert.equal((await response.json()).error.status_code, 404);
});

test('unexpected API errors log method and pathname without query parameters', async () => {
  const errors = [];
  const app = express();
  app.get('/failure', (_request, _response, next) => {
    next(Object.assign(new Error('database failure'), { code: '22P02' }));
  });
  app.use(errorHandler({ logger: { error: (...values) => errors.push(values) } }));
  const errorServer = app.listen(0, '127.0.0.1');
  await new Promise((resolve) => errorServer.once('listening', resolve));

  try {
    const response = await fetch(`http://127.0.0.1:${errorServer.address().port}/failure?token=private`);
    assert.equal(response.status, 500);
    assert.deepEqual(errors, [[
      'Unhandled API error:',
      {
        method: 'GET',
        path: '/failure',
        status_code: 500,
        code: '22P02',
        sqlstate: '22P02',
      },
    ]]);
  } finally {
    await new Promise((resolve, reject) => {
      errorServer.close((error) => error ? reject(error) : resolve());
    });
  }
});

test('PostgreSQL errors log safe diagnostics without exposing error details', async () => {
  const errors = [];
  const app = express();
  const failures = [
    {
      path: '/failure/undefined-column',
      code: '42703',
      column: 'area_sqft',
    },
    {
      path: '/failure/value-too-long',
      code: '22001',
      column: 'title',
    },
  ];
  for (const failure of failures) {
    app.get(failure.path, (_request, _response, next) => {
      next(Object.assign(new Error('sensitive database message'), {
        code: failure.code,
        schema: 'public',
        table: 'user_property',
        column: failure.column,
        dataType: 'character varying',
        constraint: 'private_constraint',
        detail: 'submitted private value',
        query: 'INSERT with private values',
      }));
    });
  }
  app.use(errorHandler({ logger: { error: (...values) => errors.push(values) } }));
  const errorServer = app.listen(0, '127.0.0.1');
  await new Promise((resolve) => errorServer.once('listening', resolve));

  try {
    for (const failure of failures) {
      const response = await fetch(`http://127.0.0.1:${errorServer.address().port}${failure.path}`);
      assert.equal(response.status, 500);
      assert.deepEqual(await response.json(), {
        error: {
          status_code: 500,
          message: 'The server encountered an error.',
          details: {},
        },
      });
    }
    assert.deepEqual(errors, [[
      'Unhandled API error:',
      {
        method: 'GET',
        path: '/failure/undefined-column',
        status_code: 500,
        code: '42703',
        sqlstate: '42703',
        schema: 'public',
        table: 'user_property',
        column: 'area_sqft',
        dataType: 'character varying',
        constraint: 'private_constraint',
      },
    ], [
      'Unhandled API error:',
      {
        method: 'GET',
        path: '/failure/value-too-long',
        status_code: 500,
        code: '22001',
        sqlstate: '22001',
        schema: 'public',
        table: 'user_property',
        column: 'title',
        dataType: 'character varying',
        constraint: 'private_constraint',
      },
    ]]);
    assert.equal(JSON.stringify(errors).includes('submitted private value'), false);
    assert.equal(JSON.stringify(errors).includes('INSERT with private values'), false);
  } finally {
    await new Promise((resolve, reject) => {
      errorServer.close((error) => error ? reject(error) : resolve());
    });
  }
});

test('PostgreSQL missing-relation and not-null errors log only schema identifiers', async () => {
  const errors = [];
  const app = express();
  const failures = [
    {
      path: '/failure/missing-relation',
      code: '42P01',
      message: 'relation "public.user_property" does not exist',
      diagnostic: { missingRelation: 'public.user_property' },
    },
    {
      path: '/failure/not-null',
      code: '23502',
      message: 'null value in column "price" of relation "user_property" violates not-null constraint',
      diagnostic: { column: 'price', table: 'user_property' },
    },
  ];
  for (const failure of failures) {
    app.get(failure.path, (_request, _response, next) => {
      next(Object.assign(new Error(failure.message), { code: failure.code }));
    });
  }
  app.use(errorHandler({ logger: { error: (...values) => errors.push(values) } }));
  const errorServer = app.listen(0, '127.0.0.1');
  await new Promise((resolve) => errorServer.once('listening', resolve));

  try {
    for (const failure of failures) {
      const response = await fetch(`http://127.0.0.1:${errorServer.address().port}${failure.path}`);
      assert.equal(response.status, 500);
    }
    assert.deepEqual(errors.map(([, entry]) => {
      const diagnostic = entry.missingRelation
        ? { missingRelation: entry.missingRelation }
        : { column: entry.column, table: entry.table };
      return {
        method: entry.method,
        path: entry.path,
        code: entry.code,
        ...diagnostic,
      };
    }), failures.map((failure) => ({
      method: 'GET',
      path: failure.path,
      code: failure.code,
      ...failure.diagnostic,
    })));
  } finally {
    await new Promise((resolve, reject) => {
      errorServer.close((error) => error ? reject(error) : resolve());
    });
  }
});

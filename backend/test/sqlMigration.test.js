import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  runMediaMetadataMigration,
  runPropertyCurrencyMigration,
  runPropertyPriceNegotiableMigration,
} from '../src/services/sqlMigrationService.js';

function migrationClient({ version = 130023, readOnly = 'off', isSuperuser = false, failOnSql = false } = {}) {
  const calls = [];
  return {
    calls,
    async query(sql, values = []) {
      calls.push({ sql, values });
      if (sql.includes('FROM pg_roles')) {
        return {
          rows: [{
            database_name: 'existing_db',
            database_user: 'migration_user',
            server_version_num: version,
            transaction_read_only: readOnly,
            is_superuser: isSuperuser,
          }],
        };
      }
      if (sql.includes('FROM information_schema.columns')) return { rows: [{ data_type: 'bigint' }] };
      if (sql.includes('has_schema_privilege')) {
        return { rows: [{ can_create: true, can_reference: true }] };
      }
      if (sql.includes('to_regclass')) {
        return { rows: [{ history_exists: false, metadata_exists: false }] };
      }
      if (sql.includes('CREATE TABLE public.backend_media_file_metadata') && failOnSql) {
        throw new Error('simulated migration failure');
      }
      return { rows: [], rowCount: 0 };
    },
  };
}

const migration = {
  migrationName: '001_media_file_metadata',
  sql: 'CREATE TABLE public.backend_media_file_metadata (id bigint PRIMARY KEY)',
  checksum: 'checked-test-checksum',
};

function currencyMigrationClient({
  version = 130023,
  readOnly = 'off',
  isSuperuser = false,
  historyExists = false,
  propertyExists = true,
  currencyExists = false,
  appliedChecksum = null,
  failOnSql = false,
} = {}) {
  const calls = [];
  return {
    calls,
    async query(sql, values = []) {
      calls.push({ sql, values });
      if (sql.includes('FROM pg_roles')) {
        return {
          rows: [{
            database_name: 'existing_db',
            server_version_num: version,
            transaction_read_only: readOnly,
            is_superuser: isSuperuser,
          }],
        };
      }
      if (sql.includes('to_regclass')) {
        return { rows: [{ history_exists: historyExists, property_exists: propertyExists }] };
      }
      if (sql.includes('information_schema.columns')) {
        return {
          rows: currencyExists ? [{
            data_type: 'character varying',
            character_maximum_length: 3,
            is_nullable: 'NO',
          }] : [],
          rowCount: currencyExists ? 1 : 0,
        };
      }
      if (sql.includes('FROM public.backend_schema_migrations')) {
        return { rows: appliedChecksum ? [{ checksum: appliedChecksum }] : [] };
      }
      if (sql.includes('ALTER TABLE public.user_property') && failOnSql) {
        throw new Error('simulated currency migration failure');
      }
      return { rows: [], rowCount: 0 };
    },
  };
}

const currencyMigration = {
  migrationName: '002_property_currency',
  sql: 'ALTER TABLE public.user_property ADD COLUMN currency varchar(3)',
  checksum: 'checked-currency-checksum',
};

function negotiablePriceMigrationClient({
  version = 130023,
  readOnly = 'off',
  isSuperuser = false,
  propertyExists = true,
  historyExists = false,
  priceNullable = false,
  appliedChecksum = null,
  failOnSql = false,
} = {}) {
  const calls = [];
  return {
    calls,
    async query(sql, values = []) {
      calls.push({ sql, values });
      if (sql.includes('FROM pg_roles')) {
        return {
          rows: [{
            database_name: 'existing_db',
            server_version_num: version,
            transaction_read_only: readOnly,
            is_superuser: isSuperuser,
          }],
        };
      }
      if (sql.includes("to_regclass('public.user_property')")) {
        return { rows: [{ property_exists: propertyExists }] };
      }
      if (sql.includes('information_schema.columns')) {
        return {
          rows: propertyExists ? [{
            data_type: 'numeric',
            is_nullable: priceNullable ? 'YES' : 'NO',
          }] : [],
          rowCount: propertyExists ? 1 : 0,
        };
      }
      if (sql.includes('FROM pg_constraint')) return { rows: [{ '?column?': 1 }], rowCount: 1 };
      if (sql.includes("to_regclass('public.backend_schema_migrations')")) {
        return { rows: [{ history_exists: historyExists }] };
      }
      if (sql.includes('FROM public.backend_schema_migrations')) {
        return { rows: appliedChecksum ? [{ checksum: appliedChecksum }] : [] };
      }
      if (sql.includes('ALTER TABLE public.user_property') && failOnSql) {
        throw new Error('simulated negotiable price migration failure');
      }
      return { rows: [], rowCount: 0 };
    },
  };
}

const negotiablePriceMigration = {
  migrationName: '003_negotiable_property_price',
  sql: 'ALTER TABLE public.user_property ALTER COLUMN price DROP NOT NULL',
  checksum: 'checked-negotiable-price-checksum',
};

test('migration dry run verifies the target without executing DDL', async () => {
  const client = migrationClient();
  const result = await runMediaMetadataMigration(client, migration);

  assert.equal(result.status, 'pending');
  assert.equal(client.calls.some(({ sql }) => sql === migration.sql), false);
  assert.equal(client.calls.some(({ sql }) => sql === 'BEGIN'), false);
});

test('migration apply is transactional and records the checksum', async () => {
  const client = migrationClient();
  const result = await runMediaMetadataMigration(client, {
    ...migration,
    applicationRole: 'app_user',
    apply: true,
  });

  assert.equal(result.status, 'applied');
  assert.equal(client.calls[0].sql, 'BEGIN');
  assert.ok(client.calls.some(({ sql }) => sql === migration.sql));
  assert.ok(client.calls.some(({ sql }) =>
    sql.includes('GRANT SELECT, INSERT, UPDATE, DELETE')
    && sql.includes('TO "app_user"')));
  assert.ok(client.calls.some(({ sql, values }) =>
    sql.includes('INSERT INTO public.backend_schema_migrations')
    && values[0] === migration.migrationName
    && values[1] === migration.checksum));
  assert.equal(client.calls.at(-1).sql, 'COMMIT');
});

test('migration permits PostgreSQL 13.23 for the temporary compatibility exception', async () => {
  const client = migrationClient({ version: 130023 });

  const result = await runMediaMetadataMigration(client, { ...migration, apply: true });

  assert.equal(result.status, 'applied');
  assert.equal(result.target.server_version_num, 130023);
  assert.ok(client.calls.some(({ sql }) => sql === migration.sql));
  assert.equal(client.calls.at(-1).sql, 'COMMIT');
});

test('migration refuses PostgreSQL 12 before issuing DDL', async () => {
  const client = migrationClient({ version: 120022 });

  await assert.rejects(
    runMediaMetadataMigration(client, { ...migration, apply: true }),
    /PostgreSQL 13 or newer/,
  );
  assert.equal(client.calls.some(({ sql }) => sql === migration.sql), false);
  assert.equal(client.calls.at(-1).sql, 'ROLLBACK');
});

test('migration rolls back on a DDL failure', async () => {
  const client = migrationClient({ failOnSql: true });

  await assert.rejects(
    runMediaMetadataMigration(client, { ...migration, apply: true }),
    /simulated migration failure/,
  );
  assert.equal(client.calls.at(-1).sql, 'ROLLBACK');
});

test('property currency migration dry run verifies the target without executing DDL', async () => {
  const client = currencyMigrationClient();
  const result = await runPropertyCurrencyMigration(client, currencyMigration);

  assert.equal(result.status, 'pending');
  assert.equal(client.calls.some(({ sql }) => sql === currencyMigration.sql), false);
  assert.equal(client.calls.some(({ sql }) => sql === 'BEGIN'), false);
});

test('property currency migration applies transactionally and records its checksum', async () => {
  const client = currencyMigrationClient();
  const result = await runPropertyCurrencyMigration(client, {
    ...currencyMigration,
    apply: true,
  });

  assert.equal(result.status, 'applied');
  assert.ok(client.calls.some(({ sql }) => sql === currencyMigration.sql));
  assert.ok(client.calls.some(({ sql, values }) =>
    sql.includes('INSERT INTO public.backend_schema_migrations')
    && values[0] === currencyMigration.migrationName
    && values[1] === currencyMigration.checksum));
  assert.equal(client.calls.at(-1).sql, 'COMMIT');
});

test('property currency migration refuses an unrecorded currency column', async () => {
  const client = currencyMigrationClient({ currencyExists: true });

  await assert.rejects(
    runPropertyCurrencyMigration(client, currencyMigration),
    /exists without a migration record/,
  );
  assert.equal(client.calls.some(({ sql }) => sql === currencyMigration.sql), false);
});

test('negotiable price migration dry run verifies the target without executing DDL', async () => {
  const client = negotiablePriceMigrationClient();
  const result = await runPropertyPriceNegotiableMigration(client, negotiablePriceMigration);

  assert.equal(result.status, 'pending');
  assert.equal(client.calls.some(({ sql }) => sql === negotiablePriceMigration.sql), false);
  assert.equal(client.calls.some(({ sql }) => sql === 'BEGIN'), false);
});

test('negotiable price migration applies transactionally and records its checksum', async () => {
  const client = negotiablePriceMigrationClient();
  const result = await runPropertyPriceNegotiableMigration(client, {
    ...negotiablePriceMigration,
    apply: true,
  });

  assert.equal(result.status, 'applied');
  assert.ok(client.calls.some(({ sql }) => sql === negotiablePriceMigration.sql));
  assert.ok(client.calls.some(({ sql, values }) =>
    sql.includes('INSERT INTO public.backend_schema_migrations')
    && values[0] === negotiablePriceMigration.migrationName
    && values[1] === negotiablePriceMigration.checksum));
  assert.equal(client.calls.at(-1).sql, 'COMMIT');
});

test('negotiable price migration refuses a column changed without migration history', async () => {
  const client = negotiablePriceMigrationClient({ priceNullable: true });

  await assert.rejects(
    runPropertyPriceNegotiableMigration(client, negotiablePriceMigration),
    /already nullable without a migration record/,
  );
  assert.equal(client.calls.some(({ sql }) => sql === negotiablePriceMigration.sql), false);
});

test('negotiable price migration rolls back on a DDL failure', async () => {
  const client = negotiablePriceMigrationClient({ failOnSql: true });

  await assert.rejects(
    runPropertyPriceNegotiableMigration(client, {
      ...negotiablePriceMigration,
      apply: true,
    }),
    /simulated negotiable price migration failure/,
  );
  assert.equal(client.calls.at(-1).sql, 'ROLLBACK');
});

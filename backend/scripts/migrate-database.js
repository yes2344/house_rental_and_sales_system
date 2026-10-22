import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createPool } from '../src/db.js';
import { getDatabaseConfig } from '../src/config/env.js';
import { runMediaMetadataMigration } from '../src/services/sqlMigrationService.js';

const migrationName = '001_media_file_metadata';
const migrationPath = fileURLToPath(new URL('../db/migrations/001_media_file_metadata.sql', import.meta.url));
const sql = await readFile(migrationPath, 'utf8');
const checksum = createHash('sha256').update(sql).digest('hex');
const apply = process.argv.includes('--apply');
const unknownArguments = process.argv.slice(2).filter((argument) => argument !== '--apply');
if (unknownArguments.length > 0) {
  throw new Error(`Unsupported migration arguments: ${unknownArguments.join(', ')}`);
}

const pool = createPool(getDatabaseConfig({ migration: true }));
let client;
try {
  client = await pool.connect();
  const result = await runMediaMetadataMigration(client, {
    migrationName,
    sql,
    checksum,
    applicationRole: process.env.APPLICATION_DATABASE_ROLE?.trim() || undefined,
    apply,
  });
  console.info(JSON.stringify({ ...result, checksum, mode: apply ? 'apply' : 'dry-run' }, null, 2));
  if (!apply && result.status === 'pending') {
    console.info('No changes were made. Apply only after backup and isolated-restore verification with: npm run migrate -- --apply');
  }
} catch (error) {
  console.error('Database migration failed:', error.message);
  process.exitCode = 1;
} finally {
  client?.release();
  await pool.end();
}

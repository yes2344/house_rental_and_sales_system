import { writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const target = process.env.VITE_API_PROXY_TARGET?.replace(/\/+$/, '');

if (!target) {
  if (process.env.NETLIFY) {
    throw new Error('Set VITE_API_PROXY_TARGET to the Render backend origin in Netlify environment variables.');
  }
  process.exit(0);
}

const apiUrl = new URL(target);
if (apiUrl.protocol !== 'https:' || apiUrl.pathname !== '/') {
  throw new Error('VITE_API_PROXY_TARGET must be an HTTPS origin without a path.');
}

await writeFile(
  resolve('dist', '_redirects'),
  `/api/* ${target}/api/:splat 200!\n/media/* ${target}/media/:splat 200!\n/* /index.html 200\n`,
);

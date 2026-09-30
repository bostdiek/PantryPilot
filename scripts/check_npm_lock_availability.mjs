#!/usr/bin/env node
// Reports every package-lock.json entry whose tarball the configured npm
// registry cannot serve (for example, releases still held by a supply-chain
// quarantine proxy). Exits non-zero when any locked version is unavailable.
//
// Usage: node scripts/check_npm_lock_availability.mjs [path/to/package-lock.json] [registry-url]
// Defaults: apps/frontend/package-lock.json and `npm config get registry`.

import { execSync } from 'node:child_process';
import fs from 'node:fs';

const lockPath = process.argv[2] ?? 'apps/frontend/package-lock.json';
let registry =
  process.argv[3] ??
  execSync('npm config get registry', { encoding: 'utf8' }).trim();
if (!registry.endsWith('/')) registry += '/';

const lock = JSON.parse(fs.readFileSync(lockPath, 'utf8'));
const packages = new Map();
for (const [key, entry] of Object.entries(lock.packages ?? {})) {
  if (!key || !entry.version || entry.link || !entry.resolved) continue;
  const name =
    entry.name ?? key.slice(key.lastIndexOf('node_modules/') + 'node_modules/'.length);
  packages.set(`${name}@${entry.version}`, {
    name,
    version: entry.version,
    dev: Boolean(entry.dev),
  });
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function probe({ name, version }) {
  const basename = name.split('/').pop();
  const url = `${registry}${name}/-/${basename}-${version}.tgz`;
  let status = 'error';
  for (let attempt = 0; attempt < 5; attempt += 1) {
    try {
      // Some proxies reject HEAD, so request a single byte instead.
      const response = await fetch(url, {
        headers: { Range: 'bytes=0-0' },
        redirect: 'manual',
      });
      await response.body?.cancel();
      status = response.status;
      if (status !== 429 && status < 500) break;
    } catch (error) {
      status = error.cause?.code ?? String(error);
    }
    await sleep(500 * 2 ** attempt);
  }
  return status;
}

const items = [...packages.values()];
const unavailable = [];
let next = 0;
await Promise.all(
  Array.from({ length: 12 }, async () => {
    while (next < items.length) {
      const item = items[next++];
      const status = await probe(item);
      if (!(typeof status === 'number' && status >= 200 && status < 400)) {
        unavailable.push({ ...item, status });
      }
    }
  })
);

console.log(`Checked ${items.length} locked packages against ${registry}`);
if (unavailable.length === 0) {
  console.log('All locked versions are available.');
  process.exit(0);
}
console.log('Unavailable locked versions:');
for (const item of unavailable.sort((a, b) => a.name.localeCompare(b.name))) {
  console.log(
    `  ${item.status}  ${item.name}@${item.version}${item.dev ? ' (dev)' : ''}`
  );
}
process.exit(1);

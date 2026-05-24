#!/usr/bin/env node
/**
 * Cloudflare Pages caps single files at 25 MiB. The DuckDB-WASM blobs
 * Evidence ships with are ~33 MB (`duckdb-eh.wasm`) and ~38 MB
 * (`duckdb-mvp.wasm`) — both over the limit.
 *
 * Rather than self-host them via R2 + Workers, we point the in-browser
 * DuckDB loader at the public jsDelivr CDN copy of the same npm version
 * the build uses. The CDN serves them with `access-control-allow-origin: *`
 * and immutable cache headers, so this is functionally identical to local
 * hosting from the browser's perspective.
 *
 * What this script does:
 *   1. Read the installed `@duckdb/duckdb-wasm` version from package-lock.
 *   2. Find the two SvelteKit chunks that reference the local WASM assets.
 *   3. Rewrite the string literals to jsDelivr URLs pinned to that version.
 *   4. Delete the local 33 MB + 38 MB WASM files from build/.
 *
 * Re-running is safe (idempotent on already-patched chunks).
 *
 * Usage: invoked automatically by `npm run build:cdn-patched`.
 */
import { readFileSync, writeFileSync, readdirSync, statSync, unlinkSync } from 'node:fs';
import { join } from 'node:path';

const BUILD = 'build';
const ASSETS = join(BUILD, '_app/immutable/assets');
const CHUNKS = join(BUILD, '_app/immutable/chunks');

// 1. Discover the @duckdb/duckdb-wasm version that ships with this build.
const pkgLock = JSON.parse(readFileSync('package-lock.json', 'utf8'));
const duckdbPkg = Object.entries(pkgLock.packages ?? {}).find(([k]) =>
  k.endsWith('node_modules/@duckdb/duckdb-wasm'),
);
const duckdbVersion = duckdbPkg?.[1]?.version;
if (!duckdbVersion) {
  console.error('Could not determine @duckdb/duckdb-wasm version from lockfile');
  process.exit(1);
}
console.log(`[patch-wasm] @duckdb/duckdb-wasm version: ${duckdbVersion}`);

const cdn = (name) =>
  `https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@${duckdbVersion}/dist/${name}.wasm`;

// 2. Find all WASM files in assets/, build a name→CDN-URL map.
let assetFiles;
try {
  assetFiles = readdirSync(ASSETS);
} catch {
  console.log(`[patch-wasm] No assets dir (${ASSETS}) — nothing to do.`);
  process.exit(0);
}
const wasmAssets = assetFiles.filter((f) => f.endsWith('.wasm') && f.startsWith('duckdb-'));
if (wasmAssets.length === 0) {
  console.log('[patch-wasm] No duckdb-*.wasm files found — assuming already patched.');
  process.exit(0);
}

// Map: "/_app/immutable/assets/duckdb-eh.HASH.wasm" → "https://cdn.jsdelivr.net/.../duckdb-eh.wasm"
const replacements = new Map();
for (const f of wasmAssets) {
  // f looks like "duckdb-eh.9ubY-jlA.wasm" — variant is the first dash-segment.
  const variant = f.replace(/^duckdb-/, '').split('.')[0]; // "eh" or "mvp"
  const localUrl = `"/_app/immutable/assets/${f}"`;
  const cdnUrl = `"${cdn(`duckdb-${variant}`)}"`;
  replacements.set(localUrl, cdnUrl);
}

// 3. Patch every JS chunk that contains any of the local URLs.
let patchedFiles = 0;
let totalRepl = 0;
const chunkFiles = readdirSync(CHUNKS).filter((f) => f.endsWith('.js'));
for (const f of chunkFiles) {
  const p = join(CHUNKS, f);
  let src = readFileSync(p, 'utf8');
  let touched = false;
  for (const [from, to] of replacements) {
    if (src.includes(from)) {
      src = src.split(from).join(to);
      touched = true;
      totalRepl += 1;
    }
  }
  if (touched) {
    writeFileSync(p, src, 'utf8');
    patchedFiles += 1;
    console.log(`[patch-wasm] patched ${f}`);
  }
}
console.log(`[patch-wasm] ${totalRepl} string replacements across ${patchedFiles} chunks`);

// 4. Delete the local WASM files (saves 65+ MB and gets us under the 25 MB limit).
let freed = 0;
for (const f of wasmAssets) {
  const p = join(ASSETS, f);
  freed += statSync(p).size;
  unlinkSync(p);
  console.log(`[patch-wasm] deleted ${f}`);
}
console.log(`[patch-wasm] freed ${(freed / (1024 * 1024)).toFixed(1)} MB`);

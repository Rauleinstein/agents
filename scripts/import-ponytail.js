#!/usr/bin/env node
// Maintainer extraction only: pinned Git data, never upstream execution.
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { pathToFileURL } from 'node:url';
import { noLinks, validateCatalog } from '../agentsctl.js';
export const REVISION = '552acd5efd0aeae2583a12efe39373d2f076f25e';
export const SOURCE = 'https://github.com/DietrichGebert/ponytail';
export const NAMES = ['ponytail', 'ponytail-audit', 'ponytail-debt', 'ponytail-gain', 'ponytail-help', 'ponytail-review'];
const excluded = name => path.posix.basename(name) === 'AGENTS.md' || name.split('/').includes('.github');
const retained = name => !excluded(name) && (['LICENSE', 'README.md'].includes(name) || name.startsWith('benchmarks/') || NAMES.some(skill => name.startsWith('skills/' + skill + '/')));
const sha = data => createHash('sha256').update(data).digest('hex');
const encode = data => Buffer.from(JSON.stringify(data, null, 2) + '\n');
export function extract(source, repo) {
  if (![source, repo].every(p => typeof p === 'string' && path.isAbsolute(p))) throw new Error('explicit absolute roots required');
  source = path.resolve(source); repo = path.resolve(repo);
  const contains = (a, b) => { const relative = path.relative(a, b); return relative === '' || (!relative.startsWith('..' + path.sep) && relative !== '..' && !path.isAbsolute(relative)); };
  if (contains(source, repo) || contains(repo, source)) throw new Error('source/destination overlap');
  noLinks(source); noLinks(repo);
  const git = (...args) => execFileSync('git', ['-C', source, ...args], { maxBuffer: 16 * 1024 * 1024 });
  if (git('rev-parse', 'HEAD').toString().trim() !== REVISION) throw new Error('source revision mismatch');
  const entries = git('ls-tree', '-rz', '--full-tree', REVISION).toString().split('\0').filter(Boolean).map(entry => {
    const tab = entry.indexOf('\t'); return { name: entry.slice(tab + 1), metadata: entry.slice(0, tab).split(' ') };
  });
  const files = new Map(), hashes = {}, modes = {};
  // Exclude protected paths BEFORE reading content or inspecting ancestors.
  for (const { name, metadata } of entries.filter(e => retained(e.name))) {
    if (!['100644', '100755'].includes(metadata[0]) || metadata[1] !== 'blob') throw new Error('non-regular source: ' + name);
    const local = path.join(source, name); noLinks(local);
    if (!fs.lstatSync(local).isFile()) throw new Error('non-regular source: ' + name);
    const data = fs.readFileSync(local);
    if (!data.equals(git('show', REVISION + ':' + name))) throw new Error('dirty source: ' + name);
    const mode = parseInt(metadata[0], 8) & 0o777;
    files.set(name, { data, mode }); hashes[name] = sha(data); modes[name] = mode.toString(8);
  }
  for (const name of ['LICENSE', 'README.md', 'benchmarks/results/2026-06-18-agentic.md', ...NAMES.map(n => 'skills/' + n + '/SKILL.md')]) if (!files.has(name)) throw new Error('missing required resource: ' + name);
  const additions = ['IMPORT-PROVENANCE.json'];
  for (const name of NAMES) {
    const target = 'skills/' + name + '/LICENSE';
    if (!files.has(target)) { files.set(target, files.get('LICENSE')); additions.push(target); }
  }
  const evidence = { 'references/benchmark.md': 'benchmarks/results/2026-06-18-agentic.md', 'references/upstream-README.md': 'README.md' };
  for (const [relative, original] of Object.entries(evidence)) {
    const target = 'skills/ponytail-gain/' + relative;
    if (files.has(target)) throw new Error('packaging conflict: ' + target);
    files.set(target, files.get(original)); additions.push(target);
  }
  const manifest = { source: SOURCE, revision: REVISION, license: 'MIT', extraction_scope: 'Six complete canonical skill directories, LICENSE, README and complete benchmark source tree; not a full plugin distribution', exclusions: ['AGENTS.md', '.github/**', 'All other tracked paths outside extraction_scope (adapters, plugin manifests, hooks, installer, assets, examples and translations)'], excluded_paths: entries.filter(e => !retained(e.name)).map(e => e.name), upstream_sha256: hashes, upstream_modes: modes, packaging_additions: additions, evidence_copies: evidence };
  files.set('IMPORT-PROVENANCE.json', { data: encode(manifest), mode: 0o644 });
  const root = path.join(repo, 'vendor/ponytail'); noLinks(root);
  if (fs.existsSync(root)) throw new Error('extract into a new vendor/ponytail directory; reconcile existing source deliberately');
  const catalogPath = path.join(repo, 'catalog.json'), sidecarPath = path.join(repo, 'local-examples.json');
  for (const target of [catalogPath, sidecarPath]) { noLinks(target); if (!fs.lstatSync(target).isFile()) throw new Error('non-regular catalog/sidecar'); }
  const catalog = JSON.parse(fs.readFileSync(catalogPath)), sidecar = JSON.parse(fs.readFileSync(sidecarPath));
  if (!Array.isArray(sidecar)) throw new Error('sidecar must be an array');
  const items = NAMES.map(name => ({ id: name, kind: 'skill', name, path: 'vendor/ponytail/skills/' + name, harnesses: ['hermes', 'claude', 'codex', 'cursor'], provenance: { source: SOURCE, revision: REVISION, license: 'MIT', reviewed: true, original_path: 'skills/' + name + '/SKILL.md', maturity: 'optional', review_scope: 'Static canonical instruction/resource inventory and evidence packaging inspection; not a security audit', packaging_additions: additions.filter(p => p.startsWith('skills/' + name + '/')).map(p => p.slice(('skills/' + name + '/').length)), runtime_limits: 'Skill data only; plugin hooks, namespace invocation, configuration and auto-update semantics are not installed or verified. Benchmark claims are unverified upstream evidence, not endorsed.' } }));
  validateCatalog({ ...catalog, items: [...catalog.items, ...items] });
  validateCatalog({ version: 1, items: [...sidecar, ...items] });
  for (const name of files.keys()) { if (excluded(name)) throw new Error('protected path'); noLinks(path.join(root, name)); }
  // All required source and destination checks finish before any write.
  for (const [name, { data, mode }] of files) {
    const target = path.join(root, name); fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, data, { mode }); fs.chmodSync(target, mode);
  }
  fs.writeFileSync(catalogPath, encode({ ...catalog, items: [...catalog.items, ...items] }));
  fs.writeFileSync(sidecarPath, encode([...sidecar, ...items]));
  return { originals: Object.keys(hashes).length, packaging_additions: additions.length, skills: NAMES };
}
if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  try { if (process.argv.length !== 4) throw new Error('Usage: node scripts/import-ponytail.js <absolute-pinned-clone> <absolute-catalog-root>'); console.log(JSON.stringify(extract(process.argv[2], process.argv[3]))); }
  catch (error) { console.error(error.message); process.exitCode = 1; }
}

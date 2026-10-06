#!/usr/bin/env node
/** Import verified local pins. Consumes maintainer-generated output as data;
 * never fetches, initializes projects, executes upstream scripts, or runs hooks. */
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import os from 'node:os';
import { pathToFileURL } from 'node:url';

const sha256 = data => createHash('sha256').update(data).digest('hex');
export const HARNESS = Object.freeze(['hermes', 'claude', 'codex', 'cursor']);
export const PINS = Object.freeze({
  'mattpocock-skills': Object.freeze(['https://github.com/mattpocock/skills', '4588b32ecab9ecc9fc8cc6b6c5e7d675b6004b0d', '1.3.1']),
  'github-spec-kit': Object.freeze(['https://github.com/github/spec-kit', '2dda047809dd17fa56200408ce0228a2cfe08be7', '1.1.1.dev0']),
});
export function maturity(category) {
  const categories = { engineering: 'stable', productivity: 'stable', misc: 'optional', 'in-progress': 'experimental' };
  if (!Object.hasOwn(categories, category)) throw new Error(`unknown category: ${category}`);
  return categories[category];
}
function validateItems(items) {
  const ids = new Set();
  for (const item of items) {
    if (!item || typeof item !== 'object' || typeof item.id !== 'string' || !/^[a-z0-9._-]+$/.test(item.id) || ['.', '..'].includes(item.id) || item.id.startsWith('.agents-')) throw new Error('catalog entries require safe string ids');
    if (ids.has(item.id)) throw new Error(`duplicate catalog id: ${item.id}`);
    ids.add(item.id);
    if (!['skill', 'agent', 'plugin'].includes(item.kind)) throw new Error(`invalid kind: ${item.id}`);
    if (typeof item.name !== 'string' || !item.name) throw new Error(`unsafe name: ${item.id}`);
    if (typeof item.path !== 'string' || !item.path || path.posix.isAbsolute(item.path) || item.path.includes('\\') || item.path.split('/').some(part => !part || part === '.' || part === '..') || excluded(item.path)) throw new Error(`unsafe catalog path: ${item.id}`);
    if (!Array.isArray(item.harnesses) || !item.harnesses.length || new Set(item.harnesses).size !== item.harnesses.length || item.harnesses.some(h => !HARNESS.includes(h))) throw new Error(`invalid harnesses: ${item.id}`);
    const provenance = item.provenance;
    if (!provenance || ['source', 'revision', 'license'].some(key => typeof provenance[key] !== 'string' || !provenance[key]) || typeof provenance.reviewed !== 'boolean') throw new Error(`invalid provenance: ${item.id}`);
    if (!['stable', 'optional', 'experimental'].includes(provenance.maturity)) throw new Error(`invalid maturity: ${item.id}`);
  }
  return items;
}
export function mergeLocalExamples(items, repo) {
  const local = JSON.parse(regularFile(path.join(repo, 'local-examples.json')).toString());
  if (!Array.isArray(local)) throw new Error('local examples must be an array');
  return validateItems([...items, ...local]);
}
function git(source, ...args) {
  const result = spawnSync('git', ['-C', source, ...args], { maxBuffer: 64 * 1024 * 1024 });
  if (result.error || result.status !== 0) throw new Error(`git failed: ${result.error?.message || result.stderr.toString().trim()}`);
  return result.stdout;
}
const excluded = name => path.posix.basename(name) === 'AGENTS.md' || name.split('/').includes('.github');
const overlaps = (a, b) => a === b || a.startsWith(b + path.sep) || b.startsWith(a + path.sep);
function safeComponents(target) {
  const absolute = path.resolve(target);
  let current = path.parse(absolute).root;
  for (const part of absolute.slice(current.length).split(path.sep).filter(Boolean)) {
    current = path.join(current, part);
    let stat;
    try { stat = fs.lstatSync(current); } catch (error) { if (error.code === 'ENOENT') break; throw error; }
    if (stat.isSymbolicLink()) throw new Error(`symlink path component: ${current}`);
  }
}
function regularFile(target) {
  safeComponents(target);
  if (!fs.lstatSync(target).isFile()) throw new Error(`not a regular source: ${target}`);
  return fs.readFileSync(target);
}
function verifiedTree(source, pin) {
  safeComponents(source);
  const revision = git(source, 'rev-parse', 'HEAD').toString().trim();
  if (revision !== pin) throw new Error('source revision mismatch');
  const committed = new Map(git(source, 'ls-tree', '-rz', '--full-tree', pin).toString().split('\0').filter(Boolean).map(entry => {
    const tab = entry.indexOf('\t');
    return [entry.slice(tab + 1), entry.slice(0, tab).split(' ')];
  }));
  const names = git(source, 'ls-files', '-z').toString().split('\0').filter(name => name && !excluded(name));
  const expected = [...committed.keys()].filter(name => !excluded(name));
  if (names.length !== expected.length || expected.some(name => !names.includes(name))) throw new Error('dirty tracked inventory');
  const files = new Map(), manifest = {};
  for (const name of names) {
    const metadata = committed.get(name);
    if (!metadata || !['100644', '100755'].includes(metadata[0]) || metadata[1] !== 'blob') throw new Error(`not a regular committed source: ${name}`);
    const data = regularFile(path.join(source, name));
    if (!data.equals(git(source, 'show', `${pin}:${name}`))) throw new Error(`dirty tracked source: ${name}`);
    files.set(name, { data, mode: parseInt(metadata[0], 8) & 0o777 });
    manifest[name] = sha256(data);
  }
  return { files, manifest };
}
function writePlan(destination, files) {
  safeComponents(destination);
  for (const name of files.keys()) {
    if (excluded(name) || path.isAbsolute(name) || name.split('/').some(part => part === '..' || !part)) throw new Error(`unsafe destination: ${name}`);
    const target = path.join(destination, name);
    safeComponents(target);
    if (fs.existsSync(target) && !fs.lstatSync(target).isFile()) throw new Error(`not a regular destination: ${target}`);
  }
  for (const [name, { data, mode }] of files) {
    const target = path.join(destination, name);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, data, { mode });
    fs.chmodSync(target, mode);
  }
}
export function importTree(source, destination, pin) {
  source = path.resolve(source); destination = path.resolve(destination);
  if (overlaps(source, destination)) throw new Error('source/destination overlap');
  const { files, manifest } = verifiedTree(source, pin);
  writePlan(destination, files);
  return manifest;
}

export function expandSourceRoot(value) {
  if (typeof value !== 'string' || !value) throw new Error('paths must be absolute');
  const expanded = value === '~' ? os.homedir() : value.startsWith('~/') ? path.join(os.homedir(), value.slice(2)) : value;
  if (!path.isAbsolute(expanded)) throw new Error(`paths must be absolute: ${value}`);
  return path.resolve(expanded);
}
const comparePaths = (left, right) => {
  const a = left.split('/'), b = right.split('/');
  for (let i = 0; i < Math.min(a.length, b.length); i++) {
    if (a[i] !== b[i]) return a[i] < b[i] ? -1 : 1;
  }
  return a.length - b.length;
};
const jsonFile = value => ({ data: Buffer.from(JSON.stringify(value, null, 2) + '\n'), mode: 0o644 });
function generatedTree(directory, prefix = '') {
  safeComponents(directory);
  const files = new Map();
  for (const entry of fs.readdirSync(directory).sort()) {
    const name = prefix + entry;
    if (excluded(name)) continue;
    const target = path.join(directory, entry), stat = fs.lstatSync(target);
    if (stat.isDirectory()) {
      for (const [child, file] of generatedTree(target, name + '/')) files.set(child, file);
    } else {
      files.set(name, { data: regularFile(target), mode: stat.mode & 0o777 });
    }
  }
  return files;
}
/** The explicit programmatic pin table permits offline Git fixtures. CLI imports
 * always use PINS; there is deliberately no CLI pin override. */
export function run(matt, spec, generated, repo, pins = PINS) {
  [matt, spec, generated, repo] = [matt, spec, generated, repo].map(expandSourceRoot);
  for (const source of [matt, spec, generated]) {
    if (overlaps(source, repo)) throw new Error('source/generation/destination overlap');
    safeComponents(source);
  }
  safeComponents(repo);
  const items = [], trees = {}, files = new Map();
  for (const [label, source] of [['mattpocock-skills', matt], ['github-spec-kit', spec]]) {
    const [url, revision, version] = pins[label];
    const tree = verifiedTree(source, revision);
    trees[label] = tree;
    for (const [name, file] of tree.files) files.set(`vendor/${label}/${name}`, file);
    if (!tree.files.has('LICENSE')) throw new Error(`missing upstream LICENSE: ${label}`);
    files.set(`vendor/${label}/IMPORT-PROVENANCE.json`, jsonFile({ source: url, revision, version, license: 'MIT', exclusions: ['AGENTS.md', '.github/**'], upstream_sha256: tree.manifest }));
  }
  const mattTree = trees['mattpocock-skills'];
  for (const skill of [...mattTree.files.keys()].filter(name => /^skills\/[^/]+\/[^/]+\/SKILL\.md$/.test(name)).sort(comparePaths)) {
    const [, category, name] = skill.split('/'), directory = path.posix.dirname(skill), license = directory + '/LICENSE';
    const additions = mattTree.files.has(license) ? [] : ['LICENSE'];
    if (additions.length) files.set('vendor/mattpocock-skills/' + license, mattTree.files.get('LICENSE'));
    const [source, revision, version] = pins['mattpocock-skills'];
    items.push({ id: 'mattpocock-' + name, kind: 'skill', name, path: 'vendor/mattpocock-skills/' + directory, harnesses: name === 'git-guardrails-claude-code' ? ['claude'] : [...HARNESS], provenance: { source, revision, version, license: 'MIT', reviewed: true, original_path: skill, maturity: maturity(category), review_scope: 'Static instruction/resource inventory, dependency and packaging inspection; not a security audit', packaging_additions: additions } });
  }
  const specTree = trees['github-spec-kit'];
  const expected = [...specTree.files.keys()].filter(name => /^templates\/commands\/[^/]+\.md$/.test(name)).map(name => 'speckit-' + path.posix.basename(name, '.md')).sort();
  const skills = fs.readdirSync(generated).filter(name => name.startsWith('speckit-') && fs.existsSync(path.join(generated, name, 'SKILL.md'))).sort();
  if (skills.length !== 10 || JSON.stringify(skills) !== JSON.stringify(expected)) throw new Error('official generated skills must match all ten core commands');
  const generatedHashes = {};
  for (const name of skills) {
    const generatedFiles = generatedTree(path.join(generated, name));
    const destination = 'generated/github-spec-kit/generic/' + name;
    for (const [relative, file] of generatedFiles) files.set(destination + '/' + relative, file);
    files.set(destination + '/LICENSE', specTree.files.get('LICENSE'));
    generatedHashes[name + '/SKILL.md'] = sha256(generatedFiles.get('SKILL.md').data);
    const [source, revision, version] = pins['github-spec-kit'];
    items.push({ id: name, kind: 'skill', name, path: destination, harnesses: [...HARNESS], provenance: { source, revision, version, license: 'MIT', reviewed: true, original_path: 'templates/commands/' + name.slice('speckit-'.length) + '.md', maturity: 'stable', generator: 'Official specify init generic --skills --script sh', review_scope: 'Static generator, generated instruction, dependency closure and packaging inspection; not a security audit', packaging_additions: ['LICENSE'] } });
  }
  const [source, revision, version] = pins['github-spec-kit'];
  files.set('generated/github-spec-kit/GENERATION.json', jsonFile({ source, revision, version, command: 'specify init <disposable-project> --integration generic --integration-options="--commands-dir .agents/skills --skills" --script sh --non-interactive', generator: 'Official GenericIntegration._build_skill_content via CLI init; unmodified output plus separate LICENSE', generated_sha256: generatedHashes }));
  const merged = mergeLocalExamples(items, repo);
  files.set('catalog.json', jsonFile({ version: 1, items: merged }));
  const roots = { hermes: '~/.hermes/skills', claude: '~/.claude/skills', codex: '~/.agents/skills', cursor: '~/.agents/skills' };
  for (const [harness, root] of Object.entries(roots)) {
    const defaults = merged.filter(item => item.provenance.maturity === 'stable' && item.harnesses.includes(harness)).map(item => item.id);
    files.set(`environments/${harness}.json`, jsonFile({ harness, targets: { skill: root }, items: defaults }));
  }
  // Validate every source, sidecar, and destination before writing anything.
  // No deletion: unrelated files and protected agent policies remain untouched.
  writePlan(repo, files);
  return merged;
}

function cli(args) {
  const options = {};
  const usage = 'Usage: node scripts/import-upstreams.js --matt <absolute-path> --spec <absolute-path> --generated <absolute-path> --repo <absolute-path>';
  if (args.length === 1 && ['--help', '-h'].includes(args[0])) { console.log(usage); return; }
  for (let i = 0; i < args.length; i += 2) {
    const key = args[i].slice(2);
    if (!['matt', 'spec', 'generated', 'repo'].includes(key) || !args[i].startsWith('--') || !args[i + 1] || args[i + 1].startsWith('--') || Object.hasOwn(options, key)) throw new Error(usage);
    options[key] = args[i + 1];
  }
  if (Object.keys(options).length !== 4) throw new Error(usage);
  console.log('Imported', run(options.matt, options.spec, options.generated, options.repo).length, 'catalog artifacts');
}
if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  try { cli(process.argv.slice(2)); }
  catch (error) { console.error(error.message); process.exitCode = 1; }
}

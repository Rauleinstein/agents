import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { createHash, randomUUID } from 'node:crypto';
import { fileURLToPath } from 'node:url';

export const HARNESS = new Set(['hermes', 'claude', 'codex', 'cursor']);
export const KINDS = new Set(['skill', 'agent', 'plugin']);
export const PACKAGE_ROOT = fileURLToPath(new URL('./', import.meta.url));
export const VERSION = '0.1.0';
export class SafetyError extends Error {}
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const loneSurrogate = /[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/u;

export function requireSafe(condition, message) {
  if (!condition) throw new SafetyError(message);
}

export function text(value) {
  return typeof value === 'string' && Boolean(value.trim()) &&
    !value.includes('\0') && !loneSurrogate.test(value);
}

export function safeName(value) {
  requireSafe(text(value) && /^[a-z0-9._-]+$/.test(value) &&
    !['.', '..'].includes(value) && !value.startsWith('.agents-'),
  `invalid or reserved identifier/name: ${JSON.stringify(value)}`);
}

export function absolute(value) {
  requireSafe(text(value), 'path must be a nonempty string');
  if (value === '~' || value.startsWith('~/')) {
    value = (process.env.HOME || os.homedir()) + value.slice(1);
  }
  requireSafe(path.isAbsolute(value) && !value.split('/').includes('..'),
    `noncanonical absolute path: ${value}`);
  return path.resolve(value);
}

export function overlap(a, b) {
  a = path.resolve(a);
  b = path.resolve(b);
  return a === b || a.startsWith(b + path.sep) || b.startsWith(a + path.sep) ||
    a === path.parse(a).root || b === path.parse(b).root;
}

function stat(p) {
  try { return fs.lstatSync(p); }
  catch (error) {
    if (error.code === 'ENOENT') return null;
    throw error;
  }
}

export function noLinks(p) {
  p = path.resolve(p);
  const chain = [];
  for (let current = p; ; current = path.dirname(current)) {
    chain.push(current);
    if (current === path.dirname(current)) break;
  }
  for (const current of chain.reverse()) {
    const info = stat(current);
    if (!info) continue;
    requireSafe(!info.isSymbolicLink(), `symlink forbidden: ${current}`);
    if (current !== p) requireSafe(info.isDirectory(), `ancestor is not a directory: ${current}`);
  }
}

// Recursive descent retains decoded keys before JSON.parse could discard duplicates.
// Null-prototype objects also prevent __proto__ keys from changing object inheritance.
export function parseJSON(input) {
  let i = 0;
  const whitespace = () => { while (/[\x20\t\r\n]/.test(input[i] || '!')) i++; };
  const string = () => {
    const start = i++;
    while (i < input.length) {
      const character = input[i++];
      if (character === '"') {
        const result = JSON.parse(input.slice(start, i));
        requireSafe(!loneSurrogate.test(result), 'lone surrogate in JSON string');
        return result;
      }
      if (character === '\\') i++;
    }
    throw new SafetyError('unterminated JSON string');
  };
  const value = () => {
    whitespace();
    if (input[i] === '"') return string();
    if (input[i] === '{') {
      i++;
      whitespace();
      const result = Object.create(null), keys = new Set();
      if (input[i] === '}') { i++; return result; }
      for (;;) {
        whitespace();
        requireSafe(input[i] === '"', 'expected JSON key');
        const key = string();
        requireSafe(!keys.has(key), `duplicate JSON key: ${key}`);
        keys.add(key);
        whitespace();
        requireSafe(input[i++] === ':', 'expected colon');
        result[key] = value();
        whitespace();
        const character = input[i++];
        if (character === '}') return result;
        requireSafe(character === ',', 'expected comma');
      }
    }
    if (input[i] === '[') {
      i++;
      whitespace();
      const result = [];
      if (input[i] === ']') { i++; return result; }
      for (;;) {
        result.push(value());
        whitespace();
        const character = input[i++];
        if (character === ']') return result;
        requireSafe(character === ',', 'expected comma');
      }
    }
    const token = /^(?:true|false|null|-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)/.exec(input.slice(i));
    requireSafe(token, 'invalid JSON value');
    i += token[0].length;
    return JSON.parse(token[0]);
  };
  try {
    const result = value();
    whitespace();
    requireSafe(i === input.length, 'trailing JSON content');
    return result;
  } catch (error) {
    if (error instanceof SafetyError) throw error;
    throw new SafetyError(`invalid JSON: ${error.message}`);
  }
}

// No final-component link following; O_NONBLOCK prevents a swapped FIFO from hanging.
// This does not claim protection against hostile directory-ancestor races.
export function readRegular(p) {
  noLinks(p);
  requireSafe(stat(p)?.isFile(), `not a regular file: ${p}`);
  const fd = fs.openSync(p, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK);
  try {
    requireSafe(fs.fstatSync(fd).isFile(), `not a regular file: ${p}`);
    return fs.readFileSync(fd);
  } finally { fs.closeSync(fd); }
}

export function loadJSON(p) {
  noLinks(p);
  requireSafe(stat(p)?.isFile(), `JSON input must be a regular file: ${p}`);
  try { return parseJSON(new TextDecoder('utf-8', { fatal: true }).decode(readRegular(p))); }
  catch (error) { throw new SafetyError(`invalid JSON: ${p}: ${error.message}`); }
}

export function files(p) {
  const info = fs.lstatSync(p);
  requireSafe(!info.isSymbolicLink(), `symlink forbidden: ${p}`);
  if (info.isFile()) return [['', p]];
  requireSafe(info.isDirectory(), `not a regular file/directory: ${p}`);
  const result = [];
  const names = fs.readdirSync(p).sort((a, b) => Buffer.compare(Buffer.from(a), Buffer.from(b)));
  for (const child of names) {
    for (const [name, item] of files(path.join(p, child))) {
      result.push([child + (name ? '/' + name : ''), item]);
    }
  }
  return result;
}

// Python-compatible SHA-256: u64be name length, UTF-8 name, u64be data length, data.
// Empty directories are validated but do not contribute to the digest.
export function digest(p) {
  noLinks(p);
  const hash = createHash('sha256');
  for (const [name, item] of files(p)) {
    const encoded = Buffer.from(name), data = readRegular(item);
    const length = Buffer.alloc(8), size = Buffer.alloc(8);
    length.writeBigUInt64BE(BigInt(encoded.length));
    size.writeBigUInt64BE(BigInt(data.length));
    hash.update(length).update(encoded).update(size).update(data);
  }
  return hash.digest('hex');
}

export function validateCatalog(catalog) {
  requireSafe(object(catalog) && catalog.version === 1 && Array.isArray(catalog.items),
    'invalid catalog version/schema');
  const byId = new Map();
  for (const item of catalog.items) {
    requireSafe(object(item), 'catalog item must be an object');
    safeName(item.id);
    safeName(item.name);
    requireSafe(KINDS.has(item.kind), 'invalid artifact kind');
    requireSafe(text(item.path) && !path.isAbsolute(item.path) &&
      !item.path.split('/').some(part => ['.', '..', ''].includes(part)),
    'source must be a relative path without traversal');
    requireSafe(Array.isArray(item.harnesses) && item.harnesses.length > 0 &&
      item.harnesses.every(h => HARNESS.has(h)) && new Set(item.harnesses).size === item.harnesses.length,
    'invalid artifact harnesses');
    requireSafe(object(item.provenance) && item.provenance.reviewed === true &&
      ['source', 'revision', 'license'].every(key => text(item.provenance[key])),
    'artifact must have reviewed provenance');
    requireSafe(!byId.has(item.id), 'duplicate catalog id');
    byId.set(item.id, item);
  }
  return byId;
}

export function ownership(dest, meta, id, wanted) {
  noLinks(dest);
  noLinks(meta);
  if (stat(meta)) {
    const old = loadJSON(meta);
    requireSafe(object(old) && Object.keys(old).sort().join(',') === 'digest,id' &&
      old.id === id && typeof old.digest === 'string' && /^[a-f0-9]{64}$/.test(old.digest),
    `malformed/mismatched ownership: ${meta}`);
    requireSafe(stat(dest), `managed payload missing: ${dest}`);
    const current = digest(dest);
    requireSafe(current === old.digest, `local modifications: ${dest}`);
    return { action: current === wanted ? 'unchanged' : 'update', old: { id: old.id, digest: old.digest } };
  }
  requireSafe(!stat(dest), `unmanaged destination: ${dest}`);
  return { action: 'install', old: null };
}

export function prepare(env, repo) {
  repo = absolute(repo);
  noLinks(repo);
  const config = loadJSON(env), byId = validateCatalog(loadJSON(path.join(repo, 'catalog.json')));
  requireSafe(object(config), 'environment must be an object');
  requireSafe(HARNESS.has(config.harness), 'invalid environment harness');
  requireSafe(Array.isArray(config.items) && config.items.length > 0, 'items must be a nonempty list');
  for (const id of config.items) safeName(id);
  requireSafe(new Set(config.items).size === config.items.length, 'duplicate selected id');
  requireSafe(object(config.targets) && Object.keys(config.targets).length > 0,
    'targets must be a nonempty object');
  const roots = {};
  for (const [kind, value] of Object.entries(config.targets)) {
    requireSafe(KINDS.has(kind), 'invalid target kind');
    const root = absolute(value);
    noLinks(root);
    requireSafe(!stat(root) || stat(root).isDirectory(), `target must be a directory: ${root}`);
    requireSafe(!overlap(root, repo), 'target overlaps repository');
    requireSafe(!Object.values(roots).some(other => overlap(root, other)), 'target roots overlap');
    roots[kind] = root;
  }
  const plans = [], destinations = new Set();
  for (const id of config.items) {
    requireSafe(byId.has(id), `unknown catalog id: ${id}`);
    const item = byId.get(id);
    requireSafe(item.harnesses.includes(config.harness), `incompatible harness for ${id}`);
    requireSafe(roots[item.kind], `missing target for ${item.kind}`);
    const source = path.join(repo, item.path);
    noLinks(source);
    if (item.kind === 'agent') {
      requireSafe(['claude', 'cursor'].includes(config.harness) && stat(source)?.isFile() &&
        path.extname(source) === '.md' && item.name.endsWith('.md'),
      'native agents require compatible Markdown files and names');
    } else {
      requireSafe(stat(source)?.isDirectory(), `${item.kind} must be a directory`);
      if (item.kind === 'skill') {
        noLinks(path.join(source, 'SKILL.md'));
        requireSafe(stat(path.join(source, 'SKILL.md'))?.isFile(), 'skill directory requires SKILL.md');
      }
    }
    const root = roots[item.kind], dest = path.join(root, item.name);
    const meta = path.join(root, '.agents-managed', item.name + '.json');
    requireSafe(!destinations.has(dest), 'duplicate destination');
    destinations.add(dest);
    const wanted = digest(source);
    plans.push({ id, source, root, dest, meta, wanted, ...ownership(dest, meta, id, wanted) });
  }
  return { plans, roots: Object.values(roots).sort() };
}

export function recheck(plan) {
  requireSafe(JSON.stringify(ownership(plan.dest, plan.meta, plan.id, plan.wanted)) ===
    JSON.stringify({ action: plan.action, old: plan.old }), 'destination ownership changed; retry');
}

export function remove(p) {
  if (stat(p)?.isDirectory()) fs.rmSync(p, { recursive: true });
  else fs.unlinkSync(p);
}

// Copies files and directories only, never follows links or executes scripts/hooks.
export function copyPayload(source, dest) {
  noLinks(source);
  const info = fs.lstatSync(source);
  if (info.isDirectory()) {
    fs.mkdirSync(dest, { mode: info.mode });
    for (const name of fs.readdirSync(source)) copyPayload(path.join(source, name), path.join(dest, name));
  } else {
    requireSafe(info.isFile(), `not a regular file/directory: ${source}`);
    fs.writeFileSync(dest, readRegular(source), { flag: 'wx', mode: info.mode });
  }
}

// Injectable operations belong to this invocation; there are no mutable global hooks.
// The commit boundary is completion of BOTH renames (payload, then ownership).
export function replaceArtifact(plan, options = {}) {
  const token = randomUUID();
  const stage = path.join(plan.root, '.agents-stage-' + token);
  const backup = path.join(plan.root, '.agents-backup-' + token);
  const stagedMeta = path.join(plan.root, '.agents-metadata-' + token);
  const rename = options.rename || fs.renameSync, copy = options.copy || copyPayload;
  const rm = options.remove || remove, warn = options.warn || (message => console.error(message));
  let movedOld = false, installed = false, metadataWritten = false;
  const oldMeta = plan.old ? readRegular(plan.meta) : null;
  try {
    copy(plan.source, stage);
    requireSafe(digest(stage) === plan.wanted, 'source changed while staging');
    requireSafe(digest(plan.source) === plan.wanted, 'source changed after staging');
    noLinks(plan.meta);
    fs.mkdirSync(path.dirname(plan.meta), { recursive: true });
    fs.writeFileSync(stagedMeta, JSON.stringify({ id: plan.id, digest: plan.wanted }), { flag: 'wx' });
    recheck(plan);
    if (plan.old) { rename(plan.dest, backup); movedOld = true; }
    rename(stage, plan.dest);
    installed = true;
    rename(stagedMeta, plan.meta);
    metadataWritten = true;
  } catch (error) {
    if (installed) rm(plan.dest);
    if (movedOld) rename(backup, plan.dest);
    if (metadataWritten) {
      if (oldMeta === null) fs.unlinkSync(plan.meta);
      else { fs.writeFileSync(stagedMeta, oldMeta); rename(stagedMeta, plan.meta); }
    }
    throw error;
  } finally {
    for (const temporary of [stage, stagedMeta]) if (stat(temporary)) rm(temporary);
  }
  if (movedOld) {
    // A partially removed backup is no longer a safe rollback source.
    try { rm(backup); }
    catch (error) {
      warn(`warning: update committed; backup cleanup failed: ${backup}: ${error.message}; ` +
        'any remaining backup requires manual cleanup');
    }
  }
}

export function sync(env, repo = PACKAGE_ROOT, options = {}) {
  env = path.resolve(env);
  repo = absolute(path.resolve(repo));
  const first = prepare(env, repo);
  if (options.apply) {
    const acquired = [];
    try {
      for (const root of first.roots) {
        noLinks(root);
        fs.mkdirSync(root, { recursive: true });
        const lock = path.join(root, '.agents-sync.lock');
        try { fs.mkdirSync(lock); }
        catch (error) {
          if (error.code === 'EEXIST') throw new SafetyError(`target locked: ${root}`);
          throw error;
        }
        const info = fs.lstatSync(lock);
        acquired.push({ lock, ino: info.ino, dev: info.dev });
      }
      options.afterLocks?.(first);
      const refreshed = prepare(env, repo);
      requireSafe(JSON.stringify(first) === JSON.stringify(refreshed),
        'configuration or payload changed during lock acquisition; retry');
      options.afterPreflight?.(refreshed);
      for (const plan of refreshed.plans) {
        recheck(plan);
        requireSafe(digest(plan.source) === plan.wanted, 'source changed after preflight');
        if (plan.action !== 'unchanged') (options.replace || replaceArtifact)(plan, options);
      }
    } finally {
      for (const { lock, ino, dev } of acquired.reverse()) {
        const info = stat(lock);
        if (info && !info.isSymbolicLink() && info.ino === ino && info.dev === dev) fs.rmdirSync(lock);
      }
    }
  }
  return first.plans.map(plan => plan.action + ' ' + plan.id);
}

export function main(argv = process.argv.slice(2), options = {}) {
  const stdout = options.stdout || (message => process.stdout.write(message));
  const stderr = options.stderr || (message => process.stderr.write(message));
  const help = 'Usage: agentsctl sync (--harness hermes|claude|codex|cursor | --env PATH) ' +
    '[--repo PATH] [--apply]\nPreview is read-only; --apply writes reviewed artifacts.\n';
  try {
    requireSafe(Number(process.versions.node.split('.')[0]) >= 20, 'Node.js >=20 is required');
    if (argv.length === 1 && ['--version', '-v'].includes(argv[0])) { stdout(VERSION + '\n'); return 0; }
    if (argv.includes('--help') || argv.includes('-h')) { stdout(help); return 0; }
    requireSafe(argv[0] === 'sync', 'expected sync command');
    const args = {};
    for (let i = 1; i < argv.length; i++) {
      const key = argv[i];
      requireSafe(['--env', '--harness', '--repo', '--apply'].includes(key), `unknown argument: ${key}`);
      requireSafe(!(key in args), `duplicate argument: ${key}`);
      if (key === '--apply') args[key] = true;
      else {
        requireSafe(i + 1 < argv.length && !argv[i + 1].startsWith('--'), `missing value: ${key}`);
        args[key] = argv[++i];
      }
    }
    requireSafe(Boolean(args['--env']) !== Boolean(args['--harness']),
      'select exactly one of --harness or --env');
    if (args['--harness']) requireSafe(HARNESS.has(args['--harness']), 'invalid harness');
    const env = args['--env'] || path.join(PACKAGE_ROOT, 'environments', args['--harness'] + '.json');
    const lines = sync(env, args['--repo'] || PACKAGE_ROOT, {
      ...options, apply: Boolean(args['--apply']), warn: message => stderr(message + '\n'),
    });
    stdout(lines.join('\n') + '\n');
    return 0;
  } catch (error) {
    stderr(`error: ${error.message}\n`);
    return 2;
  }
}

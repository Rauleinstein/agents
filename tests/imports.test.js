import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';

const importerPath = path.resolve(import.meta.dirname, '../scripts/import-upstreams.js');
const scratch = process.env.TMPDIR || os.tmpdir();
function temporary(t) {
  const root = fs.mkdtempSync(path.join(scratch, 'agents-import-test-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  return root;
}
function git(root, ...args) {
  const result = spawnSync('git', ['-C', root, ...args], { encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
  return result.stdout.trim();
}
function fixture(t) {
  const root = temporary(t), source = path.join(root, 'source'), destination = path.join(root, 'destination');
  fs.mkdirSync(source);
  git(source, 'init', '-q');
  for (const [name, data] of Object.entries({ LICENSE: 'MIT fixture license\n', 'skills/engineering/demo/SKILL.md': '# fixture\n', 'skills/engineering/demo/references/data.bin': Buffer.from([0, 255, 42]), AGENTS: 'ordinary file\n', 'AGENTS.md': 'excluded\n', '.github/workflows/ci.yml': 'excluded\n' })) {
    fs.mkdirSync(path.dirname(path.join(source, name)), { recursive: true });
    fs.writeFileSync(path.join(source, name), data);
  }
  git(source, 'add', '.');
  git(source, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture');
  return { root, source, destination, pin: git(source, 'rev-parse', 'HEAD') };
}

test('native importer copies only verified tracked bytes and excludes policy/CI', async t => {
  assert.ok(fs.existsSync(importerPath), 'native Node importer must exist');
  const { importTree } = await import(pathToFileURL(importerPath));
  const f = fixture(t);
  fs.writeFileSync(path.join(f.source, 'untracked'), 'not imported');
  const manifest = importTree(f.source, f.destination, f.pin);
  assert.equal(Object.keys(manifest).length, 4);
  assert.deepEqual(fs.readFileSync(path.join(f.destination, 'skills/engineering/demo/references/data.bin')), Buffer.from([0, 255, 42]));
  assert.equal(fs.existsSync(path.join(f.destination, 'AGENTS.md')), false);
  assert.equal(fs.existsSync(path.join(f.destination, '.github')), false);
  assert.equal(fs.existsSync(path.join(f.destination, 'untracked')), false);
  assert.match(manifest.LICENSE, /^[a-f0-9]{64}$/);
});

for (const scenario of ['revision mismatch', 'dirty tracked bytes', 'tracked symlink', 'symlink ancestor', 'committed symlink replaced with regular file', 'committed gitlink', 'overlapping destination']) {
  test(`preflight rejects ${scenario} before creating output`, async t => {
    const { importTree } = await import(pathToFileURL(importerPath));
    const f = fixture(t);
    let pin = f.pin, destination = f.destination;
    if (scenario === 'revision mismatch') pin = '0'.repeat(40);
    if (scenario === 'dirty tracked bytes') fs.appendFileSync(path.join(f.source, 'skills/engineering/demo/SKILL.md'), 'dirty');
    if (scenario === 'tracked symlink' || scenario === 'committed symlink replaced with regular file') {
      fs.symlinkSync('LICENSE', path.join(f.source, 'link'));
      git(f.source, 'add', 'link');
      git(f.source, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'symlink');
      pin = git(f.source, 'rev-parse', 'HEAD');
      if (scenario === 'committed symlink replaced with regular file') {
        fs.unlinkSync(path.join(f.source, 'link'));
        fs.writeFileSync(path.join(f.source, 'link'), 'LICENSE');
      }
    }
    if (scenario === 'committed gitlink') {
      git(f.source, 'update-index', '--add', '--cacheinfo', `160000,${f.pin},submodule`);
      git(f.source, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'gitlink');
      pin = git(f.source, 'rev-parse', 'HEAD');
    }
    if (scenario === 'symlink ancestor') {
      fs.renameSync(path.join(f.source, 'skills'), path.join(f.root, 'outside'));
      fs.symlinkSync(path.join(f.root, 'outside'), path.join(f.source, 'skills'));
    }
    if (scenario === 'overlapping destination') destination = path.join(f.source, 'imported');
    assert.throws(() => importTree(f.source, destination, pin), /revision mismatch|dirty tracked|regular|symlink|overlap/);
    assert.equal(fs.existsSync(destination), false, 'preflight must not partially write');
  });
}

test('maturity is semantic and unknown categories are rejected', async () => {
  const { maturity } = await import(pathToFileURL(importerPath));
  assert.equal(typeof maturity, 'function', 'export semantic maturity helper');
  assert.equal(maturity('engineering'), 'stable');
  assert.equal(maturity('productivity'), 'stable');
  assert.equal(maturity('misc'), 'optional');
  assert.equal(maturity('in-progress'), 'experimental');
  assert.throws(() => maturity('new-category'), /unknown category/);
});

function localItem(id = 'local-example') {
  return { id, kind: 'skill', name: id, path: `skills/${id}`, harnesses: ['hermes', 'claude', 'codex', 'cursor'], provenance: { source: 'original', revision: 'v1', license: 'All rights reserved', reviewed: true, maturity: 'optional' } };
}
test('sidecar preserves original records and order, rejects collisions and malformed entries', async t => {
  const { mergeLocalExamples } = await import(pathToFileURL(importerPath));
  assert.equal(typeof mergeLocalExamples, 'function', 'export sidecar merge helper');
  const root = temporary(t), sidecar = path.join(root, 'local-examples.json');
  const first = localItem('upstream'), local = [localItem('first'), localItem('second')];
  fs.writeFileSync(sidecar, JSON.stringify(local));
  assert.deepEqual(mergeLocalExamples([first], root), [first, ...local]);
  for (const invalid of [[localItem('upstream')], [localItem('duplicate'), localItem('duplicate')], [localItem('../escape')], [localItem('.agents-manifest')], [{ ...localItem(), harnesses: ['unknown'] }], [{ ...localItem(), provenance: { ...localItem().provenance, maturity: 'beta' } }], [{ ...localItem(), path: '../outside' }], [{ ...localItem(), kind: 'unknown' }], [{ ...localItem(), provenance: { ...localItem().provenance, reviewed: 'true' } }], {}]) {
    fs.writeFileSync(sidecar, JSON.stringify(invalid));
    assert.throws(() => mergeLocalExamples([first], root), /duplicate|safe|array|harness|maturity|path|kind|provenance/);
  }
});

function fullFixture(t) {
  const matt = fixture(t), spec = fixture(t), repo = path.join(matt.root, 'repo'), generated = path.join(matt.root, 'maintainer-generated');
  for (const [name, data] of Object.entries({ 'skills/misc/git-guardrails-claude-code/SKILL.md': '# Fixture optional\n', 'skills/productivity/licensed/SKILL.md': '# Fixture stable\n', 'skills/productivity/licensed/LICENSE': 'Fixture native license\n', 'skills/in-progress/experimental/SKILL.md': '# Fixture experimental\n' })) {
    fs.mkdirSync(path.dirname(path.join(matt.source, name)), { recursive: true });
    fs.writeFileSync(path.join(matt.source, name), data);
  }
  const commands = ['analyze', 'checklist', 'clarify', 'constitution', 'implement', 'plan', 'specify', 'tasks', 'taskstoissues', 'extension'];
  fs.mkdirSync(path.join(spec.source, 'templates/commands'), { recursive: true });
  for (const name of commands) {
    fs.writeFileSync(path.join(spec.source, `templates/commands/${name}.md`), '# Fixture command\n');
    const directory = path.join(generated, `speckit-${name}`);
    fs.mkdirSync(path.join(directory, 'references'), { recursive: true });
    fs.writeFileSync(path.join(directory, 'SKILL.md'), '# Explicit test fixture, NOT official generator output\n');
    fs.writeFileSync(path.join(directory, 'references/data.txt'), 'fixture resource\n');
    fs.writeFileSync(path.join(directory, 'AGENTS.md'), 'never package policy\n');
  }
  for (const f of [matt, spec]) {
    git(f.source, 'add', '.');
    git(f.source, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'full fixture');
    f.pin = git(f.source, 'rev-parse', 'HEAD');
  }
  fs.mkdirSync(repo);
  const local = ['verify-before-reporting', 'claude-reviewer', 'cursor-reviewer', 'example-bundle'].map(localItem);
  fs.writeFileSync(path.join(repo, 'local-examples.json'), JSON.stringify(local));
  const pins = { 'mattpocock-skills': ['https://fixture.invalid/matt', matt.pin, 'fixture'], 'github-spec-kit': ['https://fixture.invalid/spec', spec.pin, 'fixture'] };
  return { matt, spec, repo, generated, local, pins };
}

test('full fixture import preserves licenses, resources, stable defaults and local IDs', async t => {
  const { run } = await import(pathToFileURL(importerPath));
  assert.equal(typeof run, 'function', 'export complete importer');
  const f = fullFixture(t);
  const items = run(f.matt.source, f.spec.source, f.generated, f.repo, f.pins);
  assert.equal(items.length, 18);
  assert.deepEqual(items.slice(-4), f.local);
  assert.deepEqual(items.find(item => item.id === 'mattpocock-git-guardrails-claude-code').harnesses, ['claude']);
  assert.equal(items.find(item => item.id === 'mattpocock-experimental').provenance.maturity, 'experimental');
  assert.deepEqual(items.find(item => item.id === 'mattpocock-licensed').provenance.packaging_additions, []);
  assert.deepEqual(items.find(item => item.id === 'mattpocock-demo').provenance.packaging_additions, ['LICENSE']);
  assert.equal(fs.readFileSync(path.join(f.repo, 'vendor/mattpocock-skills/skills/productivity/licensed/LICENSE'), 'utf8'), 'Fixture native license\n');
  assert.deepEqual(fs.readFileSync(path.join(f.repo, 'vendor/mattpocock-skills/skills/engineering/demo/LICENSE')), fs.readFileSync(path.join(f.matt.source, 'LICENSE')));
  assert.deepEqual(fs.readFileSync(path.join(f.repo, 'generated/github-spec-kit/generic/speckit-plan/LICENSE')), fs.readFileSync(path.join(f.spec.source, 'LICENSE')));
  assert.equal(fs.readFileSync(path.join(f.repo, 'generated/github-spec-kit/generic/speckit-plan/references/data.txt'), 'utf8'), 'fixture resource\n');
  assert.equal(fs.existsSync(path.join(f.repo, 'generated/github-spec-kit/generic/speckit-plan/AGENTS.md')), false);
  for (const harness of ['hermes', 'claude', 'codex', 'cursor']) {
    const config = JSON.parse(fs.readFileSync(path.join(f.repo, `environments/${harness}.json`)));
    assert.equal(config.harness, harness);
    assert.equal(config.items.length, 12);
    assert.ok(config.items.every(id => items.find(item => item.id === id).provenance.maturity === 'stable'));
  }
  const before = fs.readFileSync(path.join(f.repo, 'catalog.json'));
  run(f.matt.source, f.spec.source, f.generated, f.repo, f.pins);
  assert.deepEqual(fs.readFileSync(path.join(f.repo, 'catalog.json')), before, 'deterministic JSON');
});

for (const scenario of ['missing generated command', 'extra generated command', 'generated symlink', 'duplicate sidecar ID', 'destination symlink', 'destination overlaps generation', 'destination overlaps source', 'second source dirty']) {
  test(`full import rejects ${scenario} without partial output`, async t => {
    const { run } = await import(pathToFileURL(importerPath));
    const f = fullFixture(t);
    let destination = f.repo;
    if (scenario === 'missing generated command') fs.rmSync(path.join(f.generated, 'speckit-plan'), { recursive: true });
    if (scenario === 'extra generated command') {
      fs.mkdirSync(path.join(f.generated, 'speckit-extra'));
      fs.writeFileSync(path.join(f.generated, 'speckit-extra/SKILL.md'), '# Extra fixture\n');
    }
    if (scenario === 'generated symlink') fs.symlinkSync(f.spec.source, path.join(f.generated, 'speckit-plan/escape'));
    if (scenario === 'duplicate sidecar ID') fs.writeFileSync(path.join(f.repo, 'local-examples.json'), JSON.stringify([localItem('speckit-plan')]));
    if (scenario === 'destination symlink') {
      fs.mkdirSync(path.join(f.repo, 'vendor'));
      fs.symlinkSync(f.matt.source, path.join(f.repo, 'vendor/mattpocock-skills'));
    }
    if (scenario === 'destination overlaps generation') destination = f.generated;
    if (scenario === 'destination overlaps source') destination = f.matt.source;
    if (scenario === 'second source dirty') fs.appendFileSync(path.join(f.spec.source, 'LICENSE'), 'dirty');
    assert.throws(() => run(f.matt.source, f.spec.source, f.generated, destination, f.pins), /ten core commands|symlink|duplicate|overlap|dirty/);
    assert.equal(fs.existsSync(path.join(f.repo, 'catalog.json')), false);
    assert.equal(fs.existsSync(path.join(f.repo, 'vendor/github-spec-kit')), false);
    assert.equal(fs.existsSync(path.join(f.repo, 'generated')), false);
  });
}

test('CLI requires explicit absolute roots, fixes published pins, and never accepts pin overrides', async t => {
  const { expandSourceRoot } = await import(pathToFileURL(importerPath));
  assert.equal(expandSourceRoot('~/fixture'), path.join(os.homedir(), 'fixture'));
  assert.throws(() => expandSourceRoot('relative/path'), /absolute/);
  for (const args of [[], ['--unknown', '/somewhere'], ['--matt', '/one', '--matt', '/two'], ['--pin', 'fixture']]) {
    const result = spawnSync(process.execPath, [importerPath, ...args], { encoding: 'utf8' });
    assert.equal(result.status, 1);
    assert.match(result.stderr, /Usage:/);
  }
  const f = fullFixture(t);
  const args = ['--matt', f.matt.source, '--spec', f.spec.source, '--generated', f.generated, '--repo', f.repo];
  const result = spawnSync(process.execPath, [importerPath, ...args], { encoding: 'utf8' });
  assert.equal(result.status, 1);
  assert.match(result.stderr, /source revision mismatch/);
  assert.equal(fs.existsSync(path.join(f.repo, 'vendor')), false);
});

const realRepo = path.resolve(import.meta.dirname, '..');
const upstreamCache = path.join(os.homedir(), '.hermes/cache/scratch/agents-upstreams');
const realMatt = process.env.AGENTS_IMPORT_MATT || path.join(upstreamCache, 'mattpocock-research-4588b32');
const realSpec = process.env.AGENTS_IMPORT_SPEC || path.join(upstreamCache, 'spec-kit-research-2dda047');
const realGenerated = path.join(realRepo, 'generated/github-spec-kit/generic');
test('optional real pinned CLI reimport exactly preserves catalog, defaults, provenance and resources', { skip: !fs.existsSync(realMatt) || !fs.existsSync(realSpec) || !fs.existsSync(realGenerated) }, async t => {
  const destination = temporary(t);
  fs.copyFileSync(path.join(realRepo, 'local-examples.json'), path.join(destination, 'local-examples.json'));
  const result = spawnSync(process.execPath, [importerPath, '--matt', realMatt, '--spec', realSpec, '--generated', realGenerated, '--repo', destination], { encoding: 'utf8', timeout: 120000 });
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /Imported 52 catalog artifacts/);
  const catalog = JSON.parse(fs.readFileSync(path.join(destination, 'catalog.json')));
  assert.equal(catalog.items.length, 52);
  assert.equal(catalog.items.filter(item => item.provenance.source !== 'original').length, 48);
  assert.deepEqual(catalog.items.slice(-4), JSON.parse(fs.readFileSync(path.join(realRepo, 'local-examples.json'))));
  const jsonPaths = ['catalog.json', 'vendor/mattpocock-skills/IMPORT-PROVENANCE.json', 'vendor/github-spec-kit/IMPORT-PROVENANCE.json', 'generated/github-spec-kit/GENERATION.json', ...['hermes', 'claude', 'codex', 'cursor'].map(h => `environments/${h}.json`)];
  for (const relative of jsonPaths) assert.deepEqual(fs.readFileSync(path.join(destination, relative)), fs.readFileSync(path.join(realRepo, relative)), `byte-identical ${relative}`);
  for (const label of ['mattpocock-skills', 'github-spec-kit']) {
    const provenance = JSON.parse(fs.readFileSync(path.join(destination, `vendor/${label}/IMPORT-PROVENANCE.json`)));
    assert.equal(Object.keys(provenance.upstream_sha256).length, label === 'mattpocock-skills' ? 159 : 833);
    for (const name of Object.keys(provenance.upstream_sha256)) assert.deepEqual(fs.readFileSync(path.join(destination, `vendor/${label}/${name}`)), fs.readFileSync(path.join(realRepo, `vendor/${label}/${name}`)), `byte-identical ${label}/${name}`);
    assert.deepEqual(fs.readFileSync(path.join(destination, `vendor/${label}/LICENSE`)), fs.readFileSync(path.join(label === 'mattpocock-skills' ? realMatt : realSpec, 'LICENSE')));
  }
  for (const item of catalog.items.filter(item => item.provenance.source !== 'original')) {
    assert.deepEqual(fs.readFileSync(path.join(destination, item.path, 'LICENSE')), fs.readFileSync(path.join(realRepo, item.path, 'LICENSE')));
    assert.deepEqual(fs.readFileSync(path.join(destination, item.path, 'SKILL.md')), fs.readFileSync(path.join(realRepo, item.path, 'SKILL.md')));
  }
  for (const harness of ['hermes', 'claude', 'codex', 'cursor']) {
    const config = JSON.parse(fs.readFileSync(path.join(destination, `environments/${harness}.json`)));
    assert.equal(config.items.length, 37);
    assert.ok(config.items.every(id => catalog.items.find(item => item.id === id).provenance.maturity === 'stable'));
  }
});

test('excluded nested policies and CI symlinks are never read or copied', async t => {
  const { importTree } = await import(pathToFileURL(importerPath));
  const f = fixture(t);
  fs.mkdirSync(path.join(f.source, 'nested'));
  fs.symlinkSync('/not-a-real-target', path.join(f.source, 'nested/AGENTS.md'));
  fs.symlinkSync('/not-a-real-target', path.join(f.source, '.github/broken'));
  git(f.source, 'add', '.');
  git(f.source, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'excluded');
  const manifest = importTree(f.source, f.destination, git(f.source, 'rev-parse', 'HEAD'));
  assert.equal(Object.keys(manifest).length, 4);
});

import test from 'node:test';
import { createHash } from 'node:crypto';
import { fs, path, assert, ctl, ROOT, temp, json, writeJSON, cli } from './helpers.js';
import { extract } from '../scripts/import-ponytail.js';
const names = ['ponytail', 'ponytail-audit', 'ponytail-debt', 'ponytail-gain', 'ponytail-help', 'ponytail-review'];
const source = 'https://github.com/DietrichGebert/ponytail';
const revision = '552acd5efd0aeae2583a12efe39373d2f076f25e';
const hash = data => createHash('sha256').update(data).digest('hex');
test('Ponytail extraction rejects relative and overlapping roots before writes', () => {
  assert.throws(() => extract('relative', ROOT), /absolute/);
  for (const [sourceRoot, destination] of [[ROOT, ROOT], [ROOT, path.join(ROOT, 'nested')], [ROOT, '/'], ['/', ROOT]]) assert.throws(() => extract(sourceRoot, destination), /overlap/);
});
const pinnedClone = path.join(process.env.TMPDIR || '/', 'ponytail-552acd5');
test('optional pinned Ponytail extraction reproduces all source bytes and modes in scratch without modifying base defaults', { skip: !fs.existsSync(path.join(pinnedClone, '.git')) }, t => {
  const destination = temp(t);
  writeJSON(path.join(destination, 'catalog.json'), { version: 1, items: [] });
  writeJSON(path.join(destination, 'local-examples.json'), []);
  fs.mkdirSync(path.join(destination, 'environments'));
  fs.writeFileSync(path.join(destination, 'environments/sentinel.json'), 'unchanged\n');
  assert.deepEqual(extract(pinnedClone, destination), { originals: 35, packaging_additions: 9, skills: names });
  const manifest = json(path.join(destination, 'vendor/ponytail/IMPORT-PROVENANCE.json'));
  assert.deepEqual(fs.readFileSync(path.join(destination, 'vendor/ponytail/IMPORT-PROVENANCE.json')), fs.readFileSync(path.join(ROOT, 'vendor/ponytail/IMPORT-PROVENANCE.json')));
  for (const relative of Object.keys(manifest.upstream_sha256)) {
    const target = path.join(destination, 'vendor/ponytail', relative);
    assert.deepEqual(fs.readFileSync(target), fs.readFileSync(path.join(pinnedClone, relative)));
    assert.equal(fs.statSync(target).mode & 0o777, parseInt(manifest.upstream_modes[relative], 8));
  }
  assert.equal(ctl.digest(path.join(destination, 'vendor/ponytail')), ctl.digest(path.join(ROOT, 'vendor/ponytail')));
  assert.equal(fs.readFileSync(path.join(destination, 'environments/sentinel.json'), 'utf8'), 'unchanged\n');
  const catalogBefore = fs.readFileSync(path.join(destination, 'catalog.json'));
  assert.throws(() => extract(pinnedClone, destination), /new vendor/);
  assert.deepEqual(fs.readFileSync(path.join(destination, 'catalog.json')), catalogBefore);
});
test('six canonical Ponytail skills are optional pinned byte-preserved artifacts with resource evidence', () => {
  const catalog = json(path.join(ROOT, 'catalog.json')).items;
  const items = catalog.filter(i => i.provenance.source === source);
  assert.deepEqual(items.map(i => i.id), names);
  const root = path.join(ROOT, 'vendor/ponytail');
  const manifest = json(path.join(root, 'IMPORT-PROVENANCE.json'));
  assert.equal(manifest.source, source);
  assert.equal(manifest.revision, revision);
  assert.equal(manifest.license, 'MIT');
  assert.equal(Object.keys(manifest.upstream_sha256).length, 35);
  for (const [name, digest] of Object.entries(manifest.upstream_sha256)) {
    assert.equal(hash(fs.readFileSync(path.join(root, name))), digest, name);
    assert.ok(!name.split('/').includes('.github') && path.basename(name) !== 'AGENTS.md');
    assert.equal(fs.statSync(path.join(root, name)).mode & 0o777, parseInt(manifest.upstream_modes[name], 8));
  }
  assert.equal(ctl.files(root).length, Object.keys(manifest.upstream_sha256).length + manifest.packaging_additions.length);
  for (const item of items) {
    assert.equal(item.kind, 'skill'); assert.equal(item.name, item.id);
    assert.equal(item.path, 'vendor/ponytail/skills/' + item.id);
    assert.deepEqual(item.harnesses, ['hermes', 'claude', 'codex', 'cursor']);
    assert.equal(item.provenance.maturity, 'optional');
    assert.equal(item.provenance.revision, revision);
    assert.match(item.provenance.review_scope, /not a security audit/);
    assert.equal(hash(fs.readFileSync(path.join(ROOT, item.path, 'SKILL.md'))), manifest.upstream_sha256['skills/' + item.id + '/SKILL.md']);
    assert.deepEqual(fs.readFileSync(path.join(ROOT, item.path, 'LICENSE')), fs.readFileSync(path.join(root, 'LICENSE')));
  }
  const gain = path.join(root, 'skills/ponytail-gain');
  for (const [copy, original] of [['references/benchmark.md', 'benchmarks/results/2026-06-18-agentic.md'], ['references/upstream-README.md', 'README.md']]) {
    assert.deepEqual(fs.readFileSync(path.join(gain, copy)), fs.readFileSync(path.join(root, original)));
    assert.ok(manifest.packaging_additions.includes('skills/ponytail-gain/' + copy));
    assert.ok(!Object.hasOwn(manifest.upstream_sha256, 'skills/ponytail-gain/' + copy));
  }
  assert.deepEqual(json(path.join(ROOT, 'local-examples.json')).filter(i => i.provenance.source === source), items);
  for (const harness of ['hermes', 'claude', 'codex', 'cursor']) {
    const environment = json(path.join(ROOT, 'environments/' + harness + '.json'));
    assert.equal(environment.items.length, 37);
    assert.ok(names.every(name => !environment.items.includes(name)));
  }
});
test('six optional Ponytail payloads deploy only in scratch with digest readback and idempotence on four harnesses', t => {
  const base = temp(t);
  const items = json(path.join(ROOT, 'catalog.json')).items.filter(i => names.includes(i.id));
  assert.equal(items.length, 6);
  for (const harness of ['hermes', 'claude', 'codex', 'cursor']) {
    const target = path.join(base, harness, 'skills'), env = path.join(base, harness + '.json');
    writeJSON(env, { harness, items: names, targets: { skill: target } });
    const run = apply => cli(['sync', '--repo', ROOT, '--env', env, ...(apply ? ['--apply'] : [])], { cwd: base });
    let result = run(false); assert.equal(result.status, 0, result.stderr);
    assert.equal(result.stdout, names.map(n => 'install ' + n + '\n').join(''));
    assert.ok(!fs.existsSync(target));
    result = run(true); assert.equal(result.status, 0, result.stderr);
    for (const item of items) {
      const dest = path.join(target, item.name), digest = ctl.digest(path.join(ROOT, item.path));
      assert.equal(ctl.digest(dest), digest);
      assert.deepEqual(json(path.join(target, '.agents-managed', item.name + '.json')), { id: item.id, digest });
      if (item.id === 'ponytail-gain') assert.ok(fs.existsSync(path.join(dest, 'references/benchmark.md')));
    }
    result = run(true); assert.equal(result.status, 0, result.stderr);
    assert.equal(result.stdout, names.map(n => 'unchanged ' + n + '\n').join(''));
  }
});

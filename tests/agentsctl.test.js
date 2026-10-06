import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
const ROOT = fileURLToPath(new URL('../', import.meta.url));
const ctl = await import('../agentsctl.js').catch(() => ({}));
const scratch = process.env.TMPDIR;
function temp(t) { assert.ok(scratch && path.isAbsolute(scratch)); const p=fs.mkdtempSync(path.join(scratch,'agents-test-')); t.after(()=>fs.rmSync(p,{recursive:true,force:true})); return p; }
test('digest preserves original Python length-prefixed fixture hashes',t=>{
 assert.equal(typeof ctl.digest,'function'); const p=temp(t); fs.writeFileSync(path.join(p,'a'),'one');
 assert.equal(ctl.digest(p),'cb066707e66dd3c4b4af6dfaab1015d5e73ebb109cd0cf09040de67696655337');
 assert.equal(ctl.digest(path.join(p,'a')),'03e9eab2eb2a53c5bfd929b370cae2f170e00250429bc700ef990de40f0397b3');
 fs.mkdirSync(path.join(p,'empty')); assert.equal(ctl.digest(p),'cb066707e66dd3c4b4af6dfaab1015d5e73ebb109cd0cf09040de67696655337');
 fs.writeFileSync(path.join(p,'é'),'two'); fs.writeFileSync(path.join(p,'😀'),'three');
 assert.equal(ctl.digest(p),'ba443132065c94cf6aa067ce6f0fde877f83ec4321487ccaa078de9a02832092');
 fs.renameSync(path.join(p,'a'),path.join(p,'b')); assert.notEqual(ctl.digest(p),'ba443132065c94cf6aa067ce6f0fde877f83ec4321487ccaa078de9a02832092');
});
test('preview is read only; install repeat and update read back ownership',t=>{const f=fixture(t);assert.equal(typeof ctl.sync,'function');assert.deepEqual(f.sync(),['install sample']);assert.ok(!fs.existsSync(f.target));assert.deepEqual(f.sync(true),['install sample']);assert.deepEqual(f.sync(true),['unchanged sample']);fs.writeFileSync(path.join(f.source,'SKILL.md'),'# changed');assert.deepEqual(f.sync(true),['update sample']);assert.equal(fs.readFileSync(path.join(f.target,'sample/SKILL.md'),'utf8'),'# changed');assert.deepEqual(JSON.parse(fs.readFileSync(path.join(f.target,'.agents-managed/sample.json'))),{id:'sample',digest:ctl.digest(f.source)});});
export function fixture(t){ const base=temp(t),repo=path.join(base,'repo'),source=path.join(repo,'skills/sample'),target=path.join(base,'target'),env=path.join(base,'env.json'); fs.mkdirSync(source,{recursive:true});fs.writeFileSync(path.join(source,'SKILL.md'),'# sample');
 const catalog={version:1,items:[{id:'sample',kind:'skill',name:'sample',path:'skills/sample',harnesses:['hermes','claude','cursor','codex'],provenance:{source:'https://example.test',revision:'abc',license:'MIT',reviewed:true}}]},environment={harness:'hermes',targets:{skill:target},items:['sample']};
 const f={base,repo,source,target,env,catalog,environment,save(){fs.writeFileSync(path.join(repo,'catalog.json'),JSON.stringify(f.catalog));fs.writeFileSync(env,JSON.stringify(f.environment));},sync(apply=false,options={}){return ctl.sync(env,repo,{apply,...options});}};f.save();return f; }

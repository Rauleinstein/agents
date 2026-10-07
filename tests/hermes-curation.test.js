import test from 'node:test';
import {fs,path,assert,ctl,ROOT,temp,json,writeJSON,cli} from './helpers.js';
import {mergeLocalExamples} from '../scripts/import-upstreams.js';
const origins = {
 'web-app-delivery':'software-development/web-app-delivery-workflows/SKILL.md',
 'atomic-git-delivery':'software-development/atomic-git-delivery/SKILL.md',
 'expo-android-builds':'software-development/expo-android-builds/SKILL.md',
 'auth-deployment-debugging':'software-development/auth-deployment-debugging/SKILL.md',
 'react-runtime-resilience':'software-development/react-web-app-surface-patterns/SKILL.md',
 'safe-cli-installation':'software-development/cli-tool-installation-patterns/SKILL.md',
 'godot-project-verification':'software-development/godot-2d-project-patterns/SKILL.md',
 'playwright-smoke-suites':'software-development/playwright-smoke-suites/SKILL.md',
 'grounded-citations':'research/grounded-citations/SKILL.md',
 'image-generation':'openclaw-imports/nano-banana/SKILL.md',
 'frontend-design':'openclaw-imports/frontend-design/SKILL.md',
 'video-artifact-verification':'creative/remotion-video-production/SKILL.md'
};
const ids=Object.keys(origins).map(n=>'hermes-'+n);
const harnesses=['hermes','claude','codex','cursor'];
const scope='Independently authored portable workflow from local skill review; not a security audit';
const safeguards={
 'web-app-delivery':['canonical public endpoint','real host','backup','without pruning','explicit approval'],
 'atomic-git-delivery':['untracked','independently usable','divergence','Never force-push','remote branch SHA'],
 'expo-android-builds':['Java','CMake','snapshot','packaged Android manifest','checksum','Do not upload'],
 'auth-deployment-debugging':['OAuth callback','SameSite','host vault','session hydration','intended permission','Never read .env'],
 'react-runtime-resilience':['Abort superseded','sequence/version guards','session hydration','cache keys','first-response HTML'],
 'safe-cli-installation':['Pin the requested version','lifecycle hooks','neutral working directory','non-mutating help','Do not auto-approve'],
 'godot-project-verification':['rejecting symlinks','isolated snapshot','Never delete scene nodes','authored bytes','real rendered state'],
 'playwright-smoke-suites':['preserve the broader','semantic role/label','auth storage snapshots','disposable accounts','test mode only','Never disable assertions'],
 'grounded-citations':['exact requested URL','verbatim supporting passages','Map every factual claim','does not support a broader claim','No command-line runtime'],
 'image-generation':['available image tools','usage rights','explicit cost approval','unique task-local','Decode the returned file','never copy the first'],
 'frontend-design':['visual brief','semantic tokens','real content','keyboard-operable','reduced-motion','actual browser screenshots'],
 'video-artifact-verification':['licenses','Remotion package compatibility','real continuous product session','actual gameplay footage','real ffprobe output','first, middle and last frames']
};
function selected(){return json(path.join(ROOT,'catalog.json')).items.filter(i=>i.provenance.source==='local-hermes-curation');}
test('twelve portable Hermes workflows have explicit optional provenance, private-data boundaries and self-contained notices',()=>{
 const items=selected(); assert.deepEqual(items.map(i=>i.id),ids);
 const guide=fs.readFileSync(path.join(ROOT,'docs/hermes-curation.md'),'utf8');
 for(const item of items){
  assert.equal(item.kind,'skill'); assert.equal(item.name,item.id); assert.equal(item.path,'skills/'+item.id);
  assert.deepEqual(item.harnesses,harnesses);
  const {source_sha256, ...provenance}=item.provenance;
  assert.match(source_sha256 ?? '',/^[a-f0-9]{64}$/,'reviewed source hash: '+item.id);
  assert.deepEqual(provenance,{source:'local-hermes-curation',revision:'v1',license:'All rights reserved',reviewed:true,maturity:'optional',review_scope:scope,original_path:origins[item.id.slice(7)],original_license:['image-generation','frontend-design','playwright-smoke-suites'].includes(item.id.slice(7))?'undeclared':'MIT (declared in source frontmatter; not independently verified)'});
  const dir=path.join(ROOT,item.path); assert.deepEqual(fs.readdirSync(dir).sort(),['LICENSE','SKILL.md']);
  const body=fs.readFileSync(path.join(dir,'SKILL.md'),'utf8');
  assert.ok(body.startsWith('---\nname: '+item.id+'\ndescription: Use when '));
  assert.match(body,/author: Hermes Agent\nlicense: All rights reserved/);
  for(const token of safeguards[item.id.slice(7)])assert.ok(body.includes(token),item.id+' missing safeguard '+token);
  assert.doesNotMatch(body,/https?:\/\/|[\w.+-]+@[\w.-]+\.[a-z]{2,}|\b(?:user|account|host)[_-]?id\s*[:=]\s*[0-9a-f]{8,}/i);
  const length=body.trimEnd().split('\n').length; assert.ok(length>=40&&length<=90,item.id+' line count '+length);
  for(const heading of ['## Scope','## Workflow','## Verification','## Risks and stop conditions','## Tools'])assert.ok(body.includes(heading),item.id+' '+heading);
  assert.doesNotMatch(body,/(?:\/(?:home|Users)\/[^/\s]+|[A-Za-z]:[\\/]Users[\\/]|\.hermes\/\.env|--yolo|curl[^\n]*\|\s*(?:sh|bash)|\]\((?:references|scripts)\/)/);
  assert.match(fs.readFileSync(path.join(dir,'LICENSE'),'utf8'),/All rights reserved/);
  assert.ok(guide.includes('`'+item.id+'`')&&guide.includes(item.provenance.original_path));
 }
 assert.match(guide,/views.*not.*executions/i); assert.match(guide,/recency.*unreliable/i);
 assert.match(guide,/not.*snapshot/i); assert.match(guide,/licens/i);
});
test('Hermes curations survive base sidecar merging without changing defaults or upstream manifests',()=>{
 const catalog=json(path.join(ROOT,'catalog.json')).items,local=json(path.join(ROOT,'local-examples.json'));
 assert.equal(catalog.length,70); assert.equal(local.length,22);
 assert.equal(local.filter(i=>i.provenance.source==='original').length,4);
 assert.equal(local.filter(i=>i.id.startsWith('ponytail')).length,6);
 assert.deepEqual(local.filter(i=>i.provenance.source==='local-hermes-curation'),selected());
 const optional=new Set(local.map(i=>i.id)),base=catalog.filter(i=>!optional.has(i.id));
 assert.equal(base.length,48); assert.deepEqual(mergeLocalExamples(base,ROOT),catalog);
 for(const h of harnesses){const env=json(path.join(ROOT,'environments/'+h+'.json'));assert.equal(env.items.length,37);assert.ok(ids.every(id=>!env.items.includes(id)));}
 const manifests=fs.readdirSync(path.join(ROOT,'vendor')).filter(n=>fs.existsSync(path.join(ROOT,'vendor',n,'IMPORT-PROVENANCE.json')));
 assert.equal(manifests.length,3);
});
test('all twelve Hermes payloads preview, deploy and read back ownership idempotently in four disposable harnesses',t=>{
 const items=selected();assert.equal(items.length,12);const base=temp(t);
 for(const harness of harnesses){
  const target=path.join(base,harness,'skills'),env=path.join(base,harness+'.json');
  writeJSON(env,{harness,items:ids,targets:{skill:target}});
  const run=apply=>cli(['sync','--repo',ROOT,'--env',env,...(apply?['--apply']:[])],{cwd:base});
  let result=run(false);assert.equal(result.status,0,result.stderr);assert.equal(result.stdout,ids.map(id=>'install '+id+'\n').join(''));assert.ok(!fs.existsSync(target));
  result=run(true);assert.equal(result.status,0,result.stderr);
  for(const item of items){const dest=path.join(target,item.name),digest=ctl.digest(path.join(ROOT,item.path));assert.equal(ctl.digest(dest),digest);assert.deepEqual(json(path.join(target,'.agents-managed',item.name+'.json')),{id:item.id,digest});}
  result=run(true);assert.equal(result.status,0,result.stderr);assert.equal(result.stdout,ids.map(id=>'unchanged '+id+'\n').join(''));
 }
});

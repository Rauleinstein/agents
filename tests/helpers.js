import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import * as ctl from '../agentsctl.js';
export {fs,path,assert,ctl};
export const ROOT=fileURLToPath(new URL('../',import.meta.url));
export function temp(t){const base=process.env.TMPDIR;assert.ok(base&&path.isAbsolute(base),'TMPDIR must be absolute');ctl.noLinks(base);assert.ok(fs.statSync(base).isDirectory());const p=fs.mkdtempSync(path.join(base,'agents-test-'));t.after(()=>fs.rmSync(p,{recursive:true,force:true}));return p;}
export const json=p=>JSON.parse(fs.readFileSync(p,'utf8'));
export const writeJSON=(p,value)=>fs.writeFileSync(p,JSON.stringify(value));
export function cli(args,options={}){return spawnSync(process.execPath,[path.join(ROOT,'bin/agentsctl.js'),...args],{encoding:'utf8',...options});}
export function fixture(t){const base=temp(t),repo=path.join(base,'repo'),source=path.join(repo,'skills/sample'),target=path.join(base,'target'),env=path.join(base,'env.json');fs.mkdirSync(source,{recursive:true});fs.writeFileSync(path.join(source,'SKILL.md'),'# sample');const f={base,repo,source,target,env,catalog:{version:1,items:[{id:'sample',kind:'skill',name:'sample',path:'skills/sample',harnesses:['hermes','claude','cursor','codex'],provenance:{source:'https://example.test',revision:'abc',license:'MIT',reviewed:true}}]},environment:{harness:'hermes',targets:{skill:target},items:['sample']},save(){writeJSON(path.join(repo,'catalog.json'),f.catalog);writeJSON(env,f.environment);},sync(apply=false,options={}){return ctl.sync(env,repo,{apply,...options});}};f.save();return f;}
export function addPlugin(f){const item={...structuredClone(f.catalog.items[0]),id:'plugin',kind:'plugin',name:'plugin'};f.catalog.items.push(item);f.environment.items.push('plugin');const other=path.join(f.base,'z-plugins');f.environment.targets.plugin=other;f.save();return other;}

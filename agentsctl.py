"""Reviewed artifact staging; Python 3.11+ standard library only."""
import hashlib
from pathlib import Path
import stat
import json
import shutil
import os
import uuid


def load_json(path):
    return json.loads(Path(path).read_text())


HARNESS = {'hermes', 'claude', 'codex', 'cursor'}
KINDS = {'skill', 'agent', 'plugin'}


def require(condition, message):
    if not condition:
        raise SafetyError(message)


def safe_name(value):
    import re
    require(isinstance(value, str) and bool(re.fullmatch(r'[a-z0-9._-]+', value))
            and value not in {'.', '..'} and not value.startswith('.agents-'),
            f'invalid or reserved identifier/name: {value!r}')


def text(value):
    return isinstance(value, str) and bool(value.strip()) and '\x00' not in value


def overlap(a, b):
    return a == b or a in b.parents or b in a.parents


def absolute(value):
    require(text(value), 'path must be a nonempty string')
    path = Path(value).expanduser()
    require(path.is_absolute() and '..' not in path.parts, f'noncanonical absolute path: {value}')
    return path


def validate_catalog(catalog):
    require(isinstance(catalog, dict) and type(catalog.get('version')) is int
            and catalog['version'] == 1 and isinstance(catalog.get('items'), list), 'invalid catalog version/schema')
    by_id = {}
    for item in catalog['items']:
        require(isinstance(item, dict), 'catalog item must be an object')
        safe_name(item.get('id'))
        safe_name(item.get('name'))
        require(item.get('kind') in KINDS if isinstance(item.get('kind'), str) else False, 'invalid artifact kind')
        require(text(item.get('path')), 'invalid source path')
        path = Path(item['path'])
        require(not path.is_absolute() and not any(p in {'.', '..', ''} for p in item['path'].split('/')),
                'source must be a relative path without traversal')
        harnesses = item.get('harnesses')
        require(isinstance(harnesses, list) and bool(harnesses) and all(isinstance(h, str) and h in HARNESS for h in harnesses)
                and len(set(harnesses)) == len(harnesses), 'invalid artifact harnesses')
        provenance = item.get('provenance')
        require(isinstance(provenance, dict) and provenance.get('reviewed') is True
                and all(text(provenance.get(k)) for k in ('source', 'revision', 'license')), 'artifact must have reviewed provenance')
        require(item['id'] not in by_id, 'duplicate catalog id')
        by_id[item['id']] = item
    return by_id


def prepare(env, repo):
    repo = absolute(str(repo))
    config = load_json(env)
    by_id = validate_catalog(load_json(repo / 'catalog.json'))
    require(isinstance(config, dict), 'environment must be an object')
    harness = config.get('harness')
    require(isinstance(harness, str) and harness in HARNESS, 'invalid environment harness')
    selected = config.get('items')
    require(isinstance(selected, list) and bool(selected), 'items must be a nonempty list')
    for identifier in selected:
        safe_name(identifier)
    require(len(set(selected)) == len(selected), 'duplicate selected id')
    targets = config.get('targets')
    require(isinstance(targets, dict) and bool(targets), 'targets must be a nonempty object')
    roots = {}
    for kind, value in targets.items():
        require(kind in KINDS, 'invalid target kind')
        root = absolute(value)
        require(not overlap(root, repo), 'target overlaps repository')
        require(not any(overlap(root, other) for other in roots.values()), 'target roots overlap')
        roots[kind] = root
    plans, destinations = [], set()
    for identifier in selected:
        require(identifier in by_id, f'unknown catalog id: {identifier}')
        item = by_id[identifier]
        require(harness in item['harnesses'], f'incompatible harness for {identifier}')
        require(item['kind'] in roots, f'missing target for {item["kind"]}')
        source = repo / item['path']
        if item['kind'] == 'agent':
            require(harness in {'claude', 'cursor'} and source.is_file() and source.suffix == '.md'
                    and item['name'].endswith('.md'), 'native agents require compatible Markdown files and names')
        else:
            require(source.is_dir(), f'{item["kind"]} must be a directory')
            if item['kind'] == 'skill':
                require((source / 'SKILL.md').is_file(), 'skill directory requires SKILL.md')
        root = roots[item['kind']]
        dest = root / item['name']
        require(dest not in destinations, 'duplicate destination')
        destinations.add(dest)
        meta = root / '.agents-managed' / (item['name'] + '.json')
        wanted = digest(source)
        action, old = ownership(dest, meta, identifier, wanted)
        plans.append(dict(id=identifier, source=source, root=root, dest=dest, meta=meta, wanted=wanted, action=action, old=old))
    return plans


def ownership(dest, meta, identifier, wanted):
    if meta.exists():
        old = load_json(meta)
        current = digest(dest)
        return ('unchanged' if current == wanted else 'update'), old
    return 'install', None


def replace_artifact(plan):
    root, dest, meta = plan['root'], plan['dest'], plan['meta']
    stage = root / ('.agents-stage-' + uuid.uuid4().hex)
    if plan['source'].is_dir():
        shutil.copytree(plan['source'], stage)
    else:
        shutil.copyfile(plan['source'], stage)
    if dest.exists():
        remove(dest)
    os.replace(stage, dest)
    meta.parent.mkdir(exist_ok=True)
    meta.write_text(json.dumps(dict(id=plan['id'], digest=plan['wanted'])))


def remove(path):
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def sync(env, repo, apply=False):
    plans = prepare(Path(env), Path(repo))
    if apply:
        for plan in plans:
            plan['root'].mkdir(parents=True, exist_ok=True)
            if plan['action'] != 'unchanged':
                replace_artifact(plan)
    return [p['action'] + ' ' + p['id'] for p in plans]


class SafetyError(ValueError):
    """Invalid configuration or unsafe filesystem state."""


def files(path):
    """Return regular payload files, rejecting links and special files."""
    mode = path.lstat().st_mode
    if stat.S_ISREG(mode):
        return [("", path)]
    if not stat.S_ISDIR(mode):
        raise SafetyError(f"not a regular file/directory: {path}")
    result = []
    for child in sorted(path.iterdir()):
        for name, item in files(child):
            result.append((child.name + ('/' + name if name else ''), item))
    return result


def digest(path):
    h = hashlib.sha256()
    for name, item in files(Path(path)):
        encoded = name.encode('utf-8')
        data = item.read_bytes()
        h.update(len(encoded).to_bytes(8, 'big'))
        h.update(encoded)
        h.update(len(data).to_bytes(8, 'big'))
        h.update(data)
    return h.hexdigest()

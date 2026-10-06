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


def prepare(env, repo):
    config = load_json(env)
    catalog = load_json(repo / 'catalog.json')
    by_id = {item['id']: item for item in catalog['items']}
    plans = []
    for identifier in config['items']:
        item = by_id[identifier]
        source = repo / item['path']
        root = Path(config['targets'][item['kind']]).expanduser()
        dest = root / item['name']
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

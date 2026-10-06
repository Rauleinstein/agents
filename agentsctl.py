"""Reviewed artifact staging; Python 3.11+ standard library only."""
import hashlib
from pathlib import Path
import stat
import json
import shutil
import os
import uuid


def no_links(path):
    """Check the whole existing ancestry without resolving away links."""
    path = Path(path)
    for part in [*reversed(path.parents), path]:
        try:
            mode = part.lstat().st_mode
        except FileNotFoundError:
            continue
        require(not stat.S_ISLNK(mode), f'symlink forbidden: {part}')
        if part != path:
            require(stat.S_ISDIR(mode), f'ancestor is not a directory: {part}')


def load_json(path):
    path = Path(path)
    no_links(path)
    require(path.is_file(), f'JSON input must be a regular file: {path}')
    try:
        return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique_object)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise SafetyError(f'invalid JSON: {path}: {exc}') from exc


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f'duplicate JSON key: {key}')
        result[key] = value
    return result


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
    try:
        path = Path(value).expanduser()
    except RuntimeError as exc:
        raise SafetyError(f'cannot expand home directory: {value}') from exc
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
        no_links(root)
        require(not root.exists() or root.is_dir(), f'target must be a directory: {root}')
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
    return plans, tuple(sorted(roots.values()))


def ownership(dest, meta, identifier, wanted):
    no_links(dest)
    no_links(meta)
    if meta.exists():
        old = load_json(meta)
        require(isinstance(old, dict) and set(old) == {'id', 'digest'}
                and old['id'] == identifier and isinstance(old['digest'], str)
                and len(old['digest']) == 64 and all(c in '0123456789abcdef' for c in old['digest']),
                f'malformed/mismatched ownership: {meta}')
        require(dest.exists(), f'managed payload missing: {dest}')
        current = digest(dest)
        require(current == old['digest'], f'local modifications: {dest}')
        return ('unchanged' if current == wanted else 'update'), old
    require(not dest.exists(), f'unmanaged destination: {dest}')
    return 'install', None


def recheck(plan):
    action, old = ownership(plan['dest'], plan['meta'], plan['id'], plan['wanted'])
    require((action, old) == (plan['action'], plan['old']), 'destination ownership changed; retry')


def replace_artifact(plan):
    """Per-artifact swap with rollback on handled exceptions, not crash recovery."""
    root, dest, meta = plan['root'], plan['dest'], plan['meta']
    token = uuid.uuid4().hex
    stage = root / ('.agents-stage-' + token)
    backup = root / ('.agents-backup-' + token)
    staged_meta = root / ('.agents-metadata-' + token)
    moved_old = installed = metadata_written = False
    old_meta = meta.read_bytes() if plan['old'] is not None else None
    try:
        # symlinks=True avoids following a newly introduced source link.
        no_links(plan['source'])
        if plan['source'].is_dir():
            shutil.copytree(plan['source'], stage, symlinks=True)
        else:
            shutil.copyfile(plan['source'], stage, follow_symlinks=False)
        require(digest(stage) == plan['wanted'], 'source changed while staging')
        require(digest(plan['source']) == plan['wanted'], 'source changed after staging')
        meta.parent.mkdir(exist_ok=True)
        staged_meta.write_text(json.dumps(dict(id=plan['id'], digest=plan['wanted'])), encoding='utf-8')
        # Last ownership/hash check immediately before the payload rename.
        recheck(plan)
        if plan['old'] is not None:
            os.replace(dest, backup)
            moved_old = True
        os.replace(stage, dest)
        installed = True
        os.replace(staged_meta, meta)
        metadata_written = True
    except Exception:
        # Exceptions are re-raised; rollback errors remain visible as well.
        if installed:
            remove(dest)
        if moved_old:
            os.replace(backup, dest)
        if metadata_written:
            if old_meta is None:
                meta.unlink()
            else:
                staged_meta.write_bytes(old_meta)
                os.replace(staged_meta, meta)
        raise
    finally:
        for temporary in (stage, staged_meta):
            if temporary.exists() or temporary.is_symlink():
                remove(temporary)
    if moved_old:
        remove(backup)


def remove(path):
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def sync(env, repo, apply=False):
    env, repo = Path(env).absolute(), Path(repo).absolute()
    plans, roots = prepare(env, repo)
    if apply:
        acquired = []
        try:
            for root in roots:
                no_links(root)
                root.mkdir(parents=True, exist_ok=True)
                lock = root / '.agents-sync.lock'
                try:
                    lock.mkdir()
                except FileExistsError as exc:
                    raise SafetyError(f'target locked: {root}') from exc
                acquired.append((lock, lock.stat().st_ino))
            refreshed, refreshed_roots = prepare(env, repo)
            require((refreshed, refreshed_roots) == (plans, roots), 'configuration or payload changed during lock acquisition; retry')
            for plan in refreshed:
                recheck(plan)
                require(digest(plan['source']) == plan['wanted'], 'source changed after preflight')
                if plan['action'] != 'unchanged':
                    replace_artifact(plan)
        finally:
            for lock, inode in reversed(acquired):
                # Never delete a replacement lock owned by another process.
                if lock.exists() and not lock.is_symlink() and lock.stat().st_ino == inode:
                    lock.rmdir()
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
    no_links(Path(path))
    h = hashlib.sha256()
    for name, item in files(Path(path)):
        encoded = name.encode('utf-8')
        data = item.read_bytes()
        h.update(len(encoded).to_bytes(8, 'big'))
        h.update(encoded)
        h.update(len(data).to_bytes(8, 'big'))
        h.update(data)
    return h.hexdigest()


def main(argv=None):
    import argparse
    import sys
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    command = sub.add_parser('sync', help='preview or apply reviewed catalog artifacts')
    command.add_argument('--env', required=True, type=Path)
    command.add_argument('--repo', type=Path, default=Path(__file__).absolute().parent)
    command.add_argument('--apply', action='store_true', help='write staged artifacts; default is read-only')
    args = parser.parse_args(argv)
    try:
        for line in sync(args.env, args.repo, apply=args.apply):
            print(line)
    except (SafetyError, OSError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

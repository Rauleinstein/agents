"""Import verified local pins; never fetch, initialize projects, or run hooks."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

PINS = {'mattpocock-skills': ('https://github.com/mattpocock/skills', '4588b32ecab9ecc9fc8cc6b6c5e7d675b6004b0d', '1.3.1'), 'github-spec-kit': ('https://github.com/github/spec-kit', '2dda047809dd17fa56200408ce0228a2cfe08be7', '1.1.1.dev0')}
HARNESS = ['hermes', 'claude', 'codex', 'cursor']


def maturity(category):
    categories = {'engineering': 'stable', 'productivity': 'stable', 'misc': 'optional', 'in-progress': 'experimental'}
    if category not in categories:
        raise ValueError(f'unknown category: {category}')
    return categories[category]


def import_tree(source, destination, pin):
    revision = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != pin:
        raise ValueError('source revision mismatch')
    names = subprocess.check_output(['git', '-C', str(source), 'ls-files', '-z']).decode().split('\0')
    manifest = {}
    for name in names:
        # Protected agent policy files and CI are deliberately outside packaging scope.
        if not name or Path(name).name == 'AGENTS.md' or '.github' in Path(name).parts:
            continue
        src = source / name
        if src.is_symlink() or not src.is_file():
            raise ValueError(f'not a regular tracked source: {name}')
        data = src.read_bytes()
        committed = subprocess.check_output(['git', '-C', str(source), 'show', f'{pin}:{name}'])
        if data != committed:
            raise ValueError(f'dirty tracked source: {name}')
        dst = destination / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        manifest[name] = hashlib.sha256(data).hexdigest()
    return manifest


def merge_local_examples(items, repo):
    """Append the ordered original sidecar; reject conflicts before catalog writes."""
    local = json.loads((repo / 'local-examples.json').read_text())
    if not isinstance(local, list):
        raise ValueError('local examples must be an array')
    merged = [*items, *local]
    ids = set()
    import re
    for item in merged:
        if (not isinstance(item, dict) or not isinstance(item.get('id'), str)
                or not re.fullmatch(r'[a-z0-9._-]+', item['id'])
                or item['id'] in {'.', '..'} or item['id'].startswith('.agents-')):
            raise ValueError('catalog entries require safe string ids')
        if item['id'] in ids:
            raise ValueError('duplicate catalog id: ' + item['id'])
        ids.add(item['id'])
    return merged


def run(matt, spec, generated, repo):
    items, manifests = [], {}
    for label, source in [('mattpocock-skills', matt), ('github-spec-kit', spec)]:
        url, revision, version = PINS[label]
        destination = repo / 'vendor' / label
        manifests[label] = import_tree(source, destination, revision)
        (destination / 'IMPORT-PROVENANCE.json').write_text(json.dumps({'source': url, 'revision': revision, 'version': version, 'license': 'MIT', 'exclusions': ['AGENTS.md', '.github/**'], 'upstream_sha256': manifests[label]}, indent=2) + '\n')
    for skill in sorted((repo / 'vendor/mattpocock-skills/skills').glob('*/*/SKILL.md')):
        directory = skill.parent
        category = directory.parent.name
        name = directory.name
        license_path = directory / 'LICENSE'
        if not license_path.exists():
            shutil.copy2(repo / 'vendor/mattpocock-skills/LICENSE', license_path)
        url, revision, version = PINS['mattpocock-skills']
        items.append({'id': 'mattpocock-' + name, 'kind': 'skill', 'name': name, 'path': str(directory.relative_to(repo)), 'harnesses': ['claude'] if name == 'git-guardrails-claude-code' else HARNESS, 'provenance': {'source': url, 'revision': revision, 'version': version, 'license': 'MIT', 'reviewed': True, 'original_path': str(skill.relative_to(repo / 'vendor/mattpocock-skills')), 'maturity': maturity(category), 'review_scope': 'Static instruction/resource inventory, dependency and packaging inspection; not a security audit', 'packaging_additions': ['LICENSE'] if str(license_path.relative_to(repo / 'vendor/mattpocock-skills')) not in manifests['mattpocock-skills'] else []}})
    skills = sorted(generated.glob('speckit-*/SKILL.md'))
    expected = {'speckit-' + p.stem for p in (spec / 'templates/commands').glob('*.md')}
    if {p.parent.name for p in skills} != expected or len(skills) != 10:
        raise ValueError('official generated skills must match all ten core commands')
    for skill in skills:
        name = skill.parent.name
        dst = repo / 'generated/github-spec-kit/generic' / name
        shutil.copytree(skill.parent, dst, dirs_exist_ok=True)
        shutil.copy2(spec / 'LICENSE', dst / 'LICENSE')
        url, revision, version = PINS['github-spec-kit']
        items.append({'id': name, 'kind': 'skill', 'name': name, 'path': str(dst.relative_to(repo)), 'harnesses': HARNESS, 'provenance': {'source': url, 'revision': revision, 'version': version, 'license': 'MIT', 'reviewed': True, 'original_path': 'templates/commands/' + name.removeprefix('speckit-') + '.md', 'maturity': 'stable', 'generator': 'Official specify init generic --skills --script sh', 'review_scope': 'Static generator, generated instruction, dependency closure and packaging inspection; not a security audit', 'packaging_additions': ['LICENSE']}})
    generation = {'source': PINS['github-spec-kit'][0], 'revision': PINS['github-spec-kit'][1], 'version': PINS['github-spec-kit'][2], 'command': 'specify init <disposable-project> --integration generic --integration-options="--commands-dir .agents/skills --skills" --script sh --non-interactive', 'generator': 'Official GenericIntegration._build_skill_content via CLI init; unmodified output plus separate LICENSE', 'generated_sha256': {p.parent.name + '/SKILL.md': hashlib.sha256(p.read_bytes()).hexdigest() for p in skills}}
    (repo / 'generated/github-spec-kit/GENERATION.json').write_text(json.dumps(generation, indent=2) + '\n')
    items = merge_local_examples(items, repo)
    (repo / 'catalog.json').write_text(json.dumps({'version': 1, 'items': items}, indent=2) + '\n')
    defaults = [i['id'] for i in items if i['provenance']['maturity'] == 'stable']
    roots = {'hermes': '~/.hermes/skills', 'claude': '~/.claude/skills', 'codex': '~/.agents/skills', 'cursor': '~/.agents/skills'}
    (repo / 'environments').mkdir(exist_ok=True)
    for harness, root in roots.items():
        config = {'harness': harness, 'targets': {'skill': root}, 'items': defaults}
        (repo / 'environments' / (harness + '.json')).write_text(json.dumps(config, indent=2) + '\n')
    return items


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('matt', 'spec', 'generated', 'repo'):
        parser.add_argument('--' + arg, type=Path, required=True)
    args = parser.parse_args()
    print('Imported', len(run(args.matt, args.spec, args.generated, args.repo)), 'catalog artifacts')

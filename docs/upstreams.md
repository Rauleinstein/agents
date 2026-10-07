# Pinned upstreams and reproducible setup

The catalog installer, importer and tests are native Node tools. They do not invoke Python. The Python commands below belong only to the separately retained official third-party Spec Kit CLI, for optional scaffold initialization or regenerating upstream skills. Do not confuse that toolkit with an installer runtime dependency.

## Provenance

| Upstream | Revision | Version | License |
|---|---|---|---|
| https://github.com/mattpocock/skills | `4588b32ecab9ecc9fc8cc6b6c5e7d675b6004b0d` | 1.3.1 | MIT, Copyright (c) 2026 Matt Pocock |
| https://github.com/github/spec-kit | `2dda047809dd17fa56200408ce0228a2cfe08be7` | 1.1.1.dev0 | MIT, Copyright GitHub, Inc. |
| https://github.com/DietrichGebert/ponytail | `552acd5efd0aeae2583a12efe39373d2f076f25e` | Commit-pinned extraction | MIT, Copyright (c) 2026 DietrichGebert |

`vendor/*/IMPORT-PROVENANCE.json` records SHA-256 hashes for every imported original file, original revision, license, version and exclusions. Matt retains 159 upstream files, including its README, LICENSE, full 38-skill tree and supporting resources. Spec Kit retains 833 upstream files, including README, LICENSE, pyproject, source, templates, scripts, integrations, extensions, presets, bundles, workflows and tests. These are source files, not a globally installed executable.

Only tracked regular files with bytes matching `git show <pin>:<path>` are imported. `.git`, untracked caches and build output are not copied. Protected `AGENTS.md` files and all `.github/**` files are deliberately excluded; contributor instructions and CI are not required for consumer generation. GitHub's two committed contributor SKILL.md files are therefore not catalog entries. No policy files or CI workflows are created by this import.

Original imported files remain byte-identical. Packaging adds `IMPORT-PROVENANCE.json` at each vendor root and, where absent, upstream MIT text as `LICENSE` inside each Matt skill directory. Catalog provenance explicitly identifies those additions. Generated Spec Kit skill directories also carry a separate upstream LICENSE; rendered SKILL.md bytes are unchanged. Upstream per-skill LICENSE and CREDITS files are preserved, not replaced.

`reviewed: true` means static instruction/resource inventory, generator and packaging/dependency inspection. It does **not** mean a security audit. Skills are executable instructions for a later agent: some instruct it to write configuration, install hooks, run shell commands, invoke extension hooks, call external services or create issues. Importing/staging has executed none of these skill instructions or hooks. The trusted official Python initialization path was inspected and run only inside disposable scratch projects, without extensions/presets. Runtime approvals and project policy still apply.

## Official consumer generation, verified

The installed pinned CLI reports that `init` uses bundled assets without downloading release templates. Its `--help` confirms `--integration`, `--integration-options`, `--script` and `--non-interactive`. Generic skills mode renders via the official `GenericIntegration._build_skill_content()` implementation: it resolves script paths, command references, arguments, skills frontmatter and hook invocation separators. This is not template renaming or a third-party conversion.

Create an isolated CLI environment (Python 3.11+ and uv required); substitute an absolute scratch/tool directory of your choice for `$TOOLS`:

```sh
REPO=/absolute/path/to/agents
TOOLS=/absolute/path/to/scratch/spec-kit-tools
uv venv "$TOOLS"
uv pip install --python "$TOOLS/bin/python" "$REPO/vendor/github-spec-kit"
"$TOOLS/bin/specify" init /absolute/path/to/disposable-project \
  --integration generic \
  --integration-options="--commands-dir .agents/skills --skills" \
  --script sh --non-interactive
```

This exact init option set succeeded for both the original pinned checkout installation and a wheel built from the vendored toolkit. Both returned `Project ready`; **all ten generated SKILL.md files were byte-identical** between the two installations. The generated names are:

- speckit-analyze
- speckit-checklist
- speckit-clarify
- speckit-constitution
- speckit-converge
- speckit-implement
- speckit-plan
- speckit-specify
- speckit-tasks
- speckit-taskstoissues

`generated/github-spec-kit/GENERATION.json` records the command, revision, generator and output hashes. Intentional runtime `$ARGUMENTS` and hook display variables are not unresolved generator tokens. `.specify/scripts/bash` references resolve to retained official scripts; command placeholders have been rendered. A toolkit wheel is built from retained pyproject force-include resources. Third-party Python dependency versions are **not** locked by this repository; uv may need network access to obtain them. CLI source and template revision are pinned, not the entire package ecosystem.

## Initialize an actual consumer project

Use the same isolated CLI installed above, from the **consumer** repository (not the catalog):

```sh
"$TOOLS/bin/specify" init --here --integration generic \
  --integration-options="--commands-dir .agents/skills --skills" \
  --script sh --non-interactive
```

For a nonempty project, inspect existing `.specify/` and project-local skills first. `--force` explicitly permits the official CLI to merge/overwrite scaffolding; only add it after reviewing that scope. The new-project invocation above was executed; `--here` is the documented help-supported equivalent, not separately exercised here. Initialization supplies scripts, templates, memory/constitution, workflow registry and integration metadata. Generated skills may be available globally through this catalog but their commands run relative to the current project, which must contain that infrastructure. Project-local duplicate skills may shadow global copies: retain the same pin or choose one discovery source deliberately.

Do **not** use the official Hermes integration for catalog maintenance: at this revision it targets `Path.home()/.hermes/skills` without named-profile awareness, and teardown can delete matching speckit skill directories. Generic mode confines generation to the consumer/scratch project. No real home profiles were initialized during this import.

## Re-import with deliberate review

Use clean local clones checked out at the exact pins above, and generate the disposable project with the matching installed official CLI before running:

```sh
node scripts/import-upstreams.js \
  --matt /absolute/path/to/pinned-matt-clone \
  --spec /absolute/path/to/pinned-spec-kit-clone \
  --generated /absolute/path/to/disposable-project/.agents/skills \
  --repo /absolute/path/to/agents
npm test
```

The Node helper copies local verified sources; it does not fetch or initialize projects, and does not activate anything. Its generated-directory input is trusted maintainer output, not an authenticated substitute for running the official generator: verify the CLI revision and compare a clean reproduction before accepting changes. It rebuilds the 48 base upstream entries and four base environments, then preserves explicitly listed optional artifacts from `local-examples.json` (22 optional records): four originals, six external Ponytail skills and twelve independently authored Hermes-inspired curations. Duplicate IDs and upstream-ID conflicts are rejected. The sidecar preserves records, not absent payloads: retain the corresponding optional payload directories when rebuilding imports. Other hand-added catalog entries must be reconciled deliberately rather than assumed preserved. It does not prune old files on version changes; import a new pin into clean staging, inspect diffs and removals, then integrate. Changing `PINS` requires a fresh review, not just a successful test.

Optional misc skills and experimental in-progress skills are available by adding their catalog IDs to a private environment. Check harness support first: `mattpocock-git-guardrails-claude-code` supports Claude only. There is no automatic plugin/hook activation.

## Optional local Hermes curation

Twelve independently authored portable workflows use `local-hermes-curation` attribution rather than upstream snapshot pins. Only relative source SKILL.md paths and observed license declarations are recorded; no private active-Hermes snapshots, source resources or personal usage telemetry are retained. New text carries All rights reserved notices, not inferred MIT grants. See [selection, licensing and runtime boundaries](hermes-curation.md). These records are optional and do not change the three upstream manifests or any default environment.

## Optional Ponytail extraction

`vendor/ponytail/` retains **35 original tracked files**: six complete canonical skill directories (one SKILL.md each), root README/LICENSE, and all 27 benchmark files. Each retained file was compared with `git show` at the exact pin; its SHA-256 and Git file mode are recorded in `IMPORT-PROVENANCE.json`. No symlinks are accepted. Protected `AGENTS.md` and every `.github` path component are excluded before reading content or writing. The manifest explicitly lists excluded paths and extraction scope.

This is a bounded skill/evidence archive, **not a full upstream plugin distribution**. Unneeded adapters, plugin manifests, hooks, installers, assets, translations and examples are omitted. The retained benchmark source includes its Caveman control as evidence, never as a catalog entry; duplicate `.openclaw/skills` adapters are omitted. README links to omitted assets/installers describe the original repository; consult the pinned upstream for those non-runtime materials. No canonical skill requires an executable local resource. Audit/help reference the sibling skills by name; gain cites the README and `benchmarks/results/2026-06-18-agentic.md`.

Nine packaging additions are distinct from original hashes: the manifest, six copied upstream MIT `LICENSE` notices and two byte-identical gain evidence snapshots (`references/benchmark.md`, `references/upstream-README.md`). The snapshots travel with the deployed gain payload; its unchanged SKILL.md still describes the original root source paths. Benchmark report reproduction links resolve in the retained root benchmark tree, not necessarily from a relocated snapshot. No benchmark was run; claims are upstream data, not independently verified or endorsed.

Reproduce into a clean staging catalog with existing `catalog.json` and `local-examples.json` (empty version-1 catalog/sidecar are supported):

```sh
node scripts/import-ponytail.js /absolute/path/to/ponytail-at-the-pin /absolute/path/to/staging-catalog
```

The native Node maintainer extractor requires the exact Git HEAD, verifies retained regular-file bytes and committed modes, checks source/destination overlap and symlink ancestors, validates merged catalog/sidecar entries, and refuses an existing `vendor/ponytail` tree rather than silently overwriting it. It changes only that tree and catalog/sidecar records, never base environments. It does not fetch, run upstream code, install packages or activate hooks. For a future pin, review the new resource closure and exclusions deliberately, then update tests and metadata.

All six entries are optional and advertise four-harness **payload compatibility**, not verified native discovery or identical invocation semantics. The unchanged help's plugin namespace commands, default-mode environment/config behavior, session auto-activation and auto-update depend on upstream plugin runtimes which are not included or activated. The main prompt's persistence and minimal-test instructions are untrusted imported data, not maintenance policy; consumer acceptance/security/verification requirements still govern. Review/audit explicitly exclude correctness, security and performance review. No real profile was changed.

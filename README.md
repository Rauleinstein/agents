# Agents — shared agent artifacts

A pinned, inspectable catalog for Hermes, Claude Code, Codex and Cursor. The installer and maintainer import tool use **Node.js 20+**, with no Python runtime or third-party npm dependencies. Installation copies reviewed files; it never executes skill instructions, hooks, or plugin activation commands.

## Run with npx

Use the public GitHub source without cloning it manually or installing globally:

```sh
# Preview only; no harness directories are written.
npx --yes --package=github:Rauleinstein/agents agentsctl sync --harness cursor

# Apply after reviewing the preview and selected destination.
npx --yes --package=github:Rauleinstein/agents agentsctl sync --harness cursor --apply
```

Choose `hermes`, `claude`, `codex`, or `cursor`. `npx` downloads the package into npm's cache; the CLI itself remains preview-only until `--apply`. This is a GitHub-distributed package, **not a package published to the npm registry**. Use `github:Rauleinstein/agents#<commit>` to pin the installer revision instead of following the branch.

For explicit machine/project configuration:

```sh
npx --yes --package=github:Rauleinstein/agents agentsctl sync --env /absolute/path/to/environment.json
```

From a local checkout:

```sh
node bin/agentsctl.js sync --harness codex
node bin/agentsctl.js sync --env environments/workstation.local.json --apply
```

Bundled harness configurations resolve relative to the installed package, not the current working directory. `--env` chooses an explicit JSON environment; do not combine it with `--harness`.

## Included base

| Source | Catalog skills | Default | Other |
|---|---:|---:|---|
| Matt Pocock skills v1.3.1 | 38 | 27 (20 engineering + 7 productivity) | 4 optional misc; 7 experimental in-progress |
| GitHub Spec Kit v1.1.1.dev0 | 10 official generated consumer workflow skills | 10 | Contributor skills are not the consumer workflow |
| Total upstream | 48 | 37 | All four environments select the same 37 |

Six optional [Ponytail skills](https://github.com/DietrichGebert/ponytail), pinned at `552acd5efd0aeae2583a12efe39373d2f076f25e`, four optional originals and twelve independently authored [Hermes-inspired workflows](docs/hermes-curation.md) bring the catalog to **70 entries** (67 skills, two agents, one inert plugin). The originals are `verify-before-reporting`, `claude-reviewer`, `cursor-reviewer`, and `example-bundle` (an inert plugin fixture, not a runnable plugin). `local-examples.json` preserves all 22 optional records, including the external Ponytail artifacts and local curations; its filename does not imply they are all originals. None are selected by default; all four environments remain byte-identical with 37 selections.

The Hermes-inspired entries cover web delivery, atomic Git delivery, Expo Android builds, auth diagnostics, React runtime resilience, safe CLI installation, Godot verification, Playwright smoke suites, grounded citations, image generation, frontend design and video verification. They are portable procedural text, not private active-profile snapshots or official Hermes bundles. Each carries explicit local-review attribution and an All rights reserved notice; source license declarations do not grant redistribution rights for private content. Static review and verified sandbox staging do not prove consumer runtime execution.

| Optional Ponytail skill | Purpose |
|---|---|
| `ponytail` | Minimal-code/YAGNI guidance with lite/full/ultra levels |
| `ponytail-audit` | Repo-wide over-engineering report |
| `ponytail-debt` | Ledger of deliberate `ponytail:` shortcuts |
| `ponytail-gain` | Display upstream benchmark scoreboard, not live repo savings |
| `ponytail-help` | Upstream command reference |
| `ponytail-review` | Diff-focused complexity review, not correctness/security review |

Only canonical `skills/<name>/SKILL.md` files are cataloged, not duplicate OpenClaw adapters or the benchmark Caveman control. Original bytes are unchanged, MIT licenses are included, and `ponytail-gain/references/` includes separately marked benchmark/README snapshots. The complete benchmark source is retained as inert provenance data. Upstream benchmark claims are unverified and **not endorsed**. See [extraction scope and limits](docs/upstreams.md#optional-ponytail-extraction).

Matt IDs use `mattpocock-<name>`, while directories/frontmatter preserve upstream names. Spec Kit IDs and directories use `speckit-<command>`. Original resources, metadata, credits and MIT notices are retained; each imported skill carries its LICENSE.

## Environments and ownership

| Harness | Default skill target |
|---|---|
| Hermes | `~/.hermes/skills` |
| Claude Code | `~/.claude/skills` |
| Codex | `~/.agents/skills` |
| Cursor | `~/.agents/skills` |

Codex and Cursor intentionally share artifacts and ownership records. Applying the second configuration is idempotent. For a named Hermes profile, explicitly select its directory in your environment file; the default configuration never infers another profile.

Copy a bundled configuration into your own ignored `environments/<name>.local.json` to change selection/targets. Native agent examples require an `agent` target; plugins require a separate `plugin` staging root. Requested Cursor paths are `~/.agents/agents` and `~/.agents/staged/cursor`, not `.cursor`.

Unmanaged existing payloads, modified managed content, mismatched metadata, symlinks and overlapping targets are conflicts. There is no force overwrite. Preserve and reconcile local content manually. The CLI validates every selected item before writing, then locks target roots and checks ownership again.

Replacement/rollback is **per artifact**, not a whole-environment or hard-crash transaction. An artifact commits when its payload and metadata are both replaced. Handled pre-commit failures attempt rollback; rollback failures remain visible. Failed cleanup of an old backup after commit emits a stderr warning while keeping the committed update. Cleanup can partially delete a backup, so it is not guaranteed complete. Cooperative locks do not prevent other editors/installers from changing files.

Metadata uses the same payload digest format as the original implementation, so existing managed installations remain recognizable. Paths/provenance require valid Unicode without lone surrogate code points. Invalid input returns exit status 2 with a controlled error.

## Updates

For a local checkout:

```sh
git pull --ff-only
node bin/agentsctl.js sync --harness cursor
node bin/agentsctl.js sync --harness cursor --apply
```

For npx, select the newly reviewed Git revision and repeat preview/apply. Upstream sources do not track mutable branches automatically: importing a new upstream pin is an explicit maintenance operation. See [provenance and reproduction](docs/upstreams.md).

## Deployment is not activation

Matt's native `disable-model-invocation`, slash commands and orchestration instructions are preserved; filesystem deployment does not prove each harness implements identical invocation semantics. Run its setup workflow deliberately in a consumer project before using tracker/domain-dependent flows. The optional Claude git guardrail is not enabled by copying it.

**Spec Kit requires project-local `.specify/` infrastructure.** Installing its ten skills does not initialize a project. Our installer/importer/tests need only Node; the separately vendored official Spec Kit CLI still has its upstream Python dependencies. They are retained as third-party source for provenance and optional regeneration, not used by `agentsctl`. See the documented official setup in [docs/upstreams.md](docs/upstreams.md).

Native Claude agent files conventionally use `~/.claude/agents`. Native Cursor discovery at the requested `~/.agents/agents` path remains unverified; do not silently create `.cursor` copies or change settings. A read-only prompt does not enforce tool permissions. Plugin activation, hooks, cloud sync, dependency installation and service restarts are always separate actions.

Ponytail's unchanged help describes plugin namespaces, session hooks, config resolution and auto-update. Copying these skills supplies **none of that plugin runtime** and does not activate a mode. Host-specific invocation/frontmatter behavior is unverified. The main prompt asks for persistent activation and minimal testing; this extraction does not adopt those rules as catalog policy or replace acceptance, security or verification requirements. Add individual IDs to a private environment only after reviewing the prompt and host support.

## Verify locally

Tests require an existing absolute `TMPDIR` with no symlink in its ancestry. CI sets it to `runner.temp`. For a local checkout, prepare a dedicated scratch directory first:

```sh
mkdir -p "$PWD/.test-scratch"
export TMPDIR="$(node --input-type=module -e 'import fs from "node:fs"; console.log(fs.realpathSync(".test-scratch"))')"
npm test
node bin/agentsctl.js --help
npm pack --pack-destination "$TMPDIR"
```

Tests use disposable scratch roots, never real profiles. CI runs Node 20/22/24 on Ubuntu/macOS. Upstream manifests verify original bytes and generated hashes. Package tests check the actual npm tarball, not just local source files. Static review is not a security audit or full interactive harness workflow verification.

See [.project/STATUS.md](.project/STATUS.md) for delivery evidence and remaining limits.

# Central agent catalog

A pinned, inspectable source for skills shared by Hermes, Claude Code, Codex and Cursor. `agentsctl.py` previews or copies catalog payloads; it does not run their instructions, install a CLI, execute hooks, or activate plugins.

## Included base

| Source | Catalog skills | Default | Other |
|---|---:|---:|---|
| Matt Pocock skills v1.3.1 | 38 | 27 (20 engineering + 7 productivity) | 4 optional misc; 7 experimental in-progress |
| GitHub Spec Kit v1.1.1.dev0 | 10 official generated consumer workflow skills | 10 | Contributor skills are not the consumer workflow |
| Total upstream | 48 | 37 | Each of four environment examples selects the same 37 |

The catalog also includes four optional original examples: `verify-before-reporting`, `claude-reviewer`, `cursor-reviewer`, and `example-bundle` (inert plugin fixture). These bring the catalog to **52 entries** without changing the base selection. They persist through re-import via `local-examples.json`. Select them explicitly in an ignored `environments/<name>.local.json`; agent entries need an `agent` target and the plugin fixture needs a separate `plugin` staging target. Cursor uses `~/.agents/agents` and `~/.agents/staged/cursor`, not `.cursor`. Native subagent discovery at the requested path remains unverified.

Matt catalog IDs are `mattpocock-<name>` while installation directories and native frontmatter retain upstream names. Spec Kit IDs and directories are `speckit-<command>`. Full skill resources, metadata, credits and MIT notices are retained. Each imported skill carries a LICENSE file.

## Preview, then apply

From this repository:

```sh
python agentsctl.py sync --env environments/codex.json
python agentsctl.py sync --env environments/codex.json --apply
```

Choose `hermes.json`, `claude.json`, `codex.json` or `cursor.json`, or copy an example into your own environment configuration. These examples are not activated automatically.

| Harness | Skill target |
|---|---|
| Hermes | `~/.hermes/skills` |
| Claude Code | `~/.claude/skills` |
| Codex | `~/.agents/skills` |
| Cursor | `~/.agents/skills` (requested shared layout, not `.cursor`) |

Codex and Cursor share IDs, payloads and ownership metadata: applying the second environment is idempotent. For a named Hermes profile, explicitly change the target to that profile's skill directory; the default example is not profile-aware. Never aim two different artifacts with the same native name at one root.

An unmanaged existing directory, locally modified managed payload, mismatched metadata, symlink or overlapping target is a conflict, not permission to overwrite. There is no force mode. Reconcile manually after preserving your local version. Preview is read-only. Apply preflights all items and locks target roots, but replacement/rollback is **per artifact**, not a crash-atomic transaction across the whole environment.

Each artifact commits when both its new payload and ownership metadata have been replaced. Handled failures before that boundary attempt to restore the original payload and metadata; rollback errors remain visible. After commit, failure to remove the old `.agents-backup-*` is **successful installation/update with a warning on stderr**, not a failed update or a rollback. The warning names the backup and reports the cleanup error. Preserve the committed payload and metadata; inspect and manually remove any remaining backup. Directory cleanup can partially delete a backup before failing, so remaining backup contents are not guaranteed to be a complete original. There is no crash-recovery guarantee.

Configuration paths and provenance strings must contain valid Unicode without lone surrogate code points (including surrogateescape values). Malformed input is rejected during preflight with CLI exit status 2, before target writes.

For reviewed repository updates:

```sh
git pull --ff-only
python agentsctl.py sync --env environments/codex.json
python agentsctl.py sync --env environments/codex.json --apply
```

`git pull` updates the central repository, not live upstream imports; revisions remain pinned until deliberately re-imported and reviewed.

## Use, rather than just copy

Matt's explicit user-invocation skills preserve `disable-model-invocation: true`. Slash command and argument-hint behavior differs by harness; copying files is not proof of every harness's discovery or invocation semantics. Run the upstream `setup-matt-pocock-skills` workflow in a consumer project to choose its issue tracker, labels and domain-document layout before using ticket-driven engineering flows. That workflow and some optional skills change project configuration: review and approve those changes separately. The `git-guardrails-claude-code` skill is optional and Claude-only; merely copying its script does not enable hooks.

**Spec Kit needs project-local `.specify/` infrastructure. Central skills alone are not a working Spec Kit project.** See [setup and reproduction](docs/upstreams.md) for the verified pinned CLI command; initialize each consumer project, never this catalog repo. Start with constitution → specify → clarify (optional) → plan → tasks → analyze (optional) → implement; converge appends remaining work. `taskstoissues` needs a configured GitHub/MCP integration and permission to create issues.

Native agents are a separate artifact kind. Claude's conventional agent target is `~/.claude/agents`; the requested Cursor staging target is `~/.agents/agents`, but discovery there is unverified (consulted Cursor documentation described `.cursor`, `.claude` and `.codex` subagent paths, not `.agents/agents`). A read-only reviewer prompt is not an enforced permission boundary. Plugins should target separate inert staging roots, such as `~/.agents/staged/cursor`; native activation is manual. No agents or plugins are enabled by these base environments.

## Verification

Tests require `TMPDIR` to name an existing absolute directory with no symlink in its ancestry. CI supplies `runner.temp`. For a local checkout, use a dedicated directory (especially on macOS, where `/tmp` can be a symlink):

```sh
mkdir -p "$PWD/.test-scratch"
export TMPDIR="$(python -c 'from pathlib import Path; print(Path(".test-scratch").resolve())')"
python -m unittest discover -v
```

Integration tests use temporary roots under `$TMPDIR`, deploy all default skills, read back digests/ownership metadata, test shared-root idempotence and refuse unmanaged conflicts. Upstream manifests verify byte preservation; generated manifests verify rendered content. Tests do not write real user skill profiles. Static review is **not a security audit**, nor a full interactive end-to-end workflow test in each harness.

See [upstream provenance and maintenance](docs/upstreams.md) and [.project/STATUS.md](.project/STATUS.md).

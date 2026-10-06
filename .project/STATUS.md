# Agents catalog — project status

- **Type:** tool
- **State:** active
- **Priority:** P2
- **Purpose:** reviewed central artifacts with explicit, safe deployment to Hermes, Claude Code, Codex and Cursor.
- **GitHub repository:** https://github.com/Rauleinstein/agents (private; repository visibility and remote `main` verified).
- **Next action:** approve one consumer environment and validate skill discovery; initialize `.specify/` in any project that will use Spec Kit.

## Delivered implementation

- Version-1 catalog with **52 entries**: 38 Matt Pocock skills, 10 official generated Spec Kit consumer skills, and four optional original examples.
- Default selection: **37 upstream skills** per environment (27 Matt stable + 10 Spec Kit). Four Matt misc skills are optional; seven in-progress skills are experimental.
- Exact pins: Matt `4588b32ecab9ecc9fc8cc6b6c5e7d675b6004b0d` (1.3.1); Spec Kit `2dda047809dd17fa56200408ce0228a2cfe08be7` (1.1.1.dev0).
- 159 original Matt files and 833 original Spec Kit files retained byte-for-byte with manifests and MIT notices. All ten generated skills were reproduced byte-identically using original and vendored official CLI builds in scratch projects.
- Preview-first installer, ownership/hash checks, unmanaged/local-edit protection, target locks and per-artifact atomic replacement.
- Native Markdown agent deployment and inert plugin staging. Original examples persist through re-import via `local-examples.json`.
- Independent specification and quality reviews passed after fixing Unicode-path error handling and clarifying committed-backup cleanup warnings.

## Observed verification

`python3 -m unittest discover -q`: **59 tests passed** on Linux/Python 3.14.7. Tests deploy and read back all default packages in disposable roots, verify shared Codex/Cursor idempotence, native examples and plugin non-execution. `git diff --check` passed.

GitHub Actions configuration covers Ubuntu and macOS on Python 3.11 and 3.14; remote run results must be read back for the delivered commit, not inferred from local tests.

## Boundaries

- No real harness profiles, hooks, cloud sync or native plugin activation changed.
- Cursor and Codex share `~/.agents/skills`; requested Cursor agent path is `~/.agents/agents`. Native discovery at that agent path is not verified.
- Consumer Spec Kit projects need separate `.specify/` initialization; skill copying alone does not supply project scaffolding.
- Matt setup, tracker changes and skill-specific commands remain explicit consumer actions.
- Pre-commit handled failures roll back per artifact. Post-commit backup cleanup failures warn while keeping the committed install; no whole-batch or hard-crash transaction guarantee.
- Cooperative locks do not stop other editors/installers. No force overwrite or destructive uninstall.
- Static review is not a security audit. Vendored CLI source is pinned; Python dependency versions are not locked.
- Protected `AGENTS.md` creation was denied and was not retried. Vendor policy files and `.github/**` were excluded; this project's own CI workflow is separate.
- Re-import accepts trusted maintainer-generated output and preserves explicit `local-examples.json` entries; other hand-added entries and new pins require clean staging and deliberate diff/removal review.

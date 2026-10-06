# Agents catalog — project status

- **Type:** tool
- **State:** active
- **Priority:** P2
- **Purpose:** reviewed central artifacts with explicit, safe deployment to Hermes, Claude Code, Codex and Cursor.
- **GitHub repository:** https://github.com/Rauleinstein/agents — public visibility verified through both GitHub CLI and unauthenticated API.
- **Runtime:** Node.js 20+; no first-party Python installer, importer or tests.
- **Next action:** approve one consumer environment and validate skill discovery; initialize `.specify/` in any project that will use Spec Kit.

## Implementation

- Native Node installer, executable `agentsctl` bin, and npm package metadata. GitHub distribution supports npx; no npm-registry publication has been performed.
- `sync --harness <name>` resolves bundled configuration relative to the package. Explicit `--env` supports custom selection and destinations. Preview-only unless `--apply`.
- Version-1 catalog with **52 entries**: 38 Matt Pocock skills, 10 official generated Spec Kit consumer skills, and four optional originals.
- Default selection: **37 upstream skills** per environment (27 stable Matt + 10 Spec Kit). Four Matt misc skills are optional; seven in-progress skills are experimental.
- Exact pins: Matt `4588b32ecab9ecc9fc8cc6b6c5e7d675b6004b0d` (1.3.1); Spec Kit `2dda047809dd17fa56200408ce0228a2cfe08be7` (1.1.1.dev0).
- 159 original Matt files and 833 original Spec Kit files retained byte-for-byte with manifests and MIT notices. Generated Spec Kit instructions retain verified official output hashes.
- Ownership digests remain compatible with previous installations. Schema checks, duplicate JSON-key rejection, Unicode validation, unmanaged/local-edit protection, sorted target locks and pre-commit rollback are tested.
- Native agent deployment and inert plugin staging. Original entries survive re-import through `local-examples.json`.
- Node maintainer importer verifies Git pins, tracked bytes, resource closure and generation inventory before writing. It never initializes consumer projects or runs hooks.
- Packaging-only `.npmignore` overrides retain original files otherwise omitted by nested upstream ignore rules.

## Observed local verification

`npm test`: **127 tests passed** on Linux/Node v26.7.0, including real npm-tarball inspection and isolated offline npx preview/apply/idempotence. Manifest tests verify upstream files, generated skills and all 37 default packages per harness. Tests never install into real profiles. `git diff --check` passed.

Delivery commit `03b7124c0c4c042e1157baa4d96a35afb442d98c` was read back from public GitHub. CI run https://github.com/Rauleinstein/agents/actions/runs/37458411127 passed all six Node 20/22/24 jobs on Ubuntu/macOS, with no Python setup. A fresh `git archive` export passed all 127 tests. Commit-pinned HTTPS GitHub npx execution with isolated HOME/cache and no Git credentials verified 37 preview actions, 37 installs, 37 unchanged actions on repetition, and all 37 installed payload/ownership hashes. No real profile changed.

## Boundaries

- Official vendored Spec Kit contains Python source as immutable third-party material. Its optional CLI initialization/regeneration still has upstream Python dependencies; our installer, importer, tests and npx execution do not use them.
- No real harness profiles, hooks, cloud sync or native plugin activation changed.
- Cursor and Codex share `~/.agents/skills`; requested Cursor agent path is `~/.agents/agents`. Native discovery at that agent path is unverified.
- Consumer Spec Kit projects need separate `.specify/` initialization; copying skills is not scaffold initialization.
- Matt setup, tracker changes and skill instructions remain explicit consumer actions.
- Handled pre-commit failures roll back per artifact. Post-commit backup-cleanup failures warn while retaining the committed installation. No whole-batch or hard-crash transaction guarantee.
- Cooperative locks do not stop other editors/installers. No force overwrite or destructive uninstall.
- Static review is not a security audit. First-party code has no npm dependencies; optional upstream Python dependencies are not locked.
- Protected `AGENTS.md` creation was denied and was not retried. Vendored policy files and `.github/**` were excluded; project CI is separate.
- Deliberate re-import accepts trusted maintainer-generated output and preserves explicit originals; new upstream pins and other hand-added entries need review.

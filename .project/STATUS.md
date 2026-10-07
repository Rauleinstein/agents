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
- Version-1 catalog with **70 entries** (67 skills, two agents, one inert plugin): 38 Matt Pocock skills, 10 official generated Spec Kit consumer skills, six optional canonical Ponytail skills, four optional originals and twelve independently authored optional Hermes-inspired workflows.
- Default selection: **37 upstream skills** per environment (27 stable Matt + 10 Spec Kit). Four Matt misc skills are optional; seven in-progress skills are experimental.
- Exact pins: Matt `4588b32ecab9ecc9fc8cc6b6c5e7d675b6004b0d` (1.3.1); Spec Kit `2dda047809dd17fa56200408ce0228a2cfe08be7` (1.1.1.dev0).
- 159 original Matt files and 833 original Spec Kit files retained byte-for-byte with manifests and MIT notices. Generated Spec Kit instructions retain verified official output hashes.
- Ponytail pin `552acd5efd0aeae2583a12efe39373d2f076f25e`: 35 original files retained with SHA-256 and Git modes (six canonical skills, README/LICENSE, complete 27-file benchmark tree). Nine explicit packaging additions: manifest, six MIT notices and two gain evidence snapshots. No duplicate adapter catalog entries.
- Ownership digests remain compatible with previous installations. Schema checks, duplicate JSON-key rejection, Unicode validation, unmanaged/local-edit protection, sorted target locks and pre-commit rollback are tested.
- Native agent deployment and inert plugin staging. 22 optional records (four originals, six external Ponytail skills and twelve local Hermes curations) survive re-import through `local-examples.json`; retain their payloads alongside records.
- Node maintainer importer verifies Git pins, tracked bytes, resource closure and generation inventory before writing. It never initializes consumer projects or runs hooks.
- Packaging-only `.npmignore` overrides retain original files otherwise omitted by nested upstream ignore rules.

## Observed local verification

Hermes curation baseline: **131 passed, 0 failed, 0 skipped** before these changes. New acceptance tests first failed because all twelve entries were absent (0 of 12; catalog 58 rather than 70). Final local `npm test`: **134 passed, 0 failed, 0 skipped**, including provenance/privacy/safeguard checks, 12 optional deployments across all four scratch harnesses with ownership readback and idempotence, real pinned base re-import retaining all 22 sidecar records/payloads, and actual npm-tarball digest checks for every catalog payload and all three upstream manifests. `git diff --check` passed. Preservation verification compared 1,121 pre-existing files outside the eight explicitly edited catalog/docs/test files, plus all 58 prior catalog and 10 prior sidecar records; previous payloads, Ponytail importer/tests and four 37-selection environments remained unchanged. The new workflows were statically reviewed, not executed in consumer projects. This curation is local-only, with no new-content CI, commit, push, publication or real-profile changes.

Prior Ponytail baseline: **127 tests passed** on Linux/Node v26.7.0. Ponytail extraction local `npm test`: **131 passed, 0 failed, 0 skipped**, including four new Ponytail tests for extraction boundaries, pinned scratch reproduction, manifests/resource evidence and six optional deployments across four harnesses. Initial RED: both new acceptance tests failed with missing Ponytail entries (0 of 6). GREEN includes byte/mode preservation, gain evidence deployment, ownership digest readback, idempotence, real pinned base re-import retaining all ten optional records/payloads, and actual npm-tarball verification of all three manifests and every catalog payload. `git diff --check` passed. Tests never install into real profiles.

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
- Ponytail is optional immutable skill data, not installed plugin runtime: no auto-activation, hooks, config handling, plugin namespaces or auto-update verified. Benchmark claims are unverified upstream data, not endorsed. Its persistence/minimal-test rules do not replace catalog acceptance/security/verification policy.
- User authorized commit and public push of the six Ponytail artifacts and twelve portable curations after review. Local checks above cover this addition; historical GitHub/CI evidence refers to the prior catalog revision, not this delivery. Verify the new remote SHA, package and CI before claiming the addition is published and validated. No real-profile installation is authorized by catalog publication.
- Vendored Ponytail benchmarks are retained evidence only. They include agent permission bypass, paid API calls, source uploads and dynamic code execution; do not run them as packaging or release checks.

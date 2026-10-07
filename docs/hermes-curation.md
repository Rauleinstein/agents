# Optional Hermes-inspired workflows

## Selection and review

These twelve workflows were selected after a read-only review of local Hermes skill instructions. Frequent-use families guided the delivery, runtime, Git, image and build choices; lower-frequency but useful verification patterns complement them. Local usage counts are skill views, not proven executions or successful outcomes. Recency is unreliable and is not a ranking signal here. Detailed personal usage telemetry is deliberately not included.

This is independently authored portable instruction text, not a raw snapshot or a copy of an active Hermes configuration. The names identify workflow families, not official Hermes distribution or endorsement. The source paths below are relative review attribution only: consumers do not need those local files. No private paths, hosts, account identities, incident stories or supporting source resources were imported.

## Included workflows

| Catalog ID | Reviewed source SKILL.md (relative) | Selection rationale |
|---|---|---|
| `hermes-web-app-delivery` | `software-development/web-app-delivery-workflows/SKILL.md` | Endpoint and deployed identity checks for frequent delivery work |
| `hermes-atomic-git-delivery` | `software-development/atomic-git-delivery/SKILL.md` | Coherent Git boundaries while protecting concurrent edits |
| `hermes-expo-android-builds` | `software-development/expo-android-builds/SKILL.md` | Real Android artifacts and embedded version authority |
| `hermes-auth-deployment-debugging` | `software-development/auth-deployment-debugging/SKILL.md` | Host/callback/session evidence without credential disclosure |
| `hermes-react-runtime-resilience` | `software-development/react-web-app-surface-patterns/SKILL.md` | Async races, auth hydration and deployment cache drift |
| `hermes-safe-cli-installation` | `software-development/cli-tool-installation-patterns/SKILL.md` | Installation separated from risky initialization |
| `hermes-godot-project-verification` | `software-development/godot-2d-project-patterns/SKILL.md` | Import and gameplay evidence without authored-resource mutation |
| `hermes-playwright-smoke-suites` | `software-development/playwright-smoke-suites/SKILL.md` | A practical fast lane that preserves full-suite coverage |
| `hermes-grounded-citations` | `research/grounded-citations/SKILL.md` | Claim-level evidence and auditable source attribution |
| `hermes-image-generation` | `openclaw-imports/nano-banana/SKILL.md` | Provider-neutral visual output with cost and rights boundaries |
| `hermes-frontend-design` | `openclaw-imports/frontend-design/SKILL.md` | Coherent accessible UI grounded in actual content |
| `hermes-video-artifact-verification` | `creative/remotion-video-production/SKILL.md` | Playable rendered deliverables with source-footage verification |

## Provenance and licensing

Each entry uses `source: local-hermes-curation`, `revision: v1`, `maturity: optional` and the review scope “Independently authored portable workflow from local skill review; not a security audit”. `reviewed: true` means static authored-instruction, privacy, dependency and packaging review, not that every described workflow was executed or that it is security-audited.

`source_sha256` records the SHA-256 of the reviewed source SKILL.md bytes; it identifies the reviewed local input without distributing that input or promising unchanged future source files. It does not authenticate the source's license or imply that the new workflow is byte-identical.

`original_license` records only the inspected frontmatter declaration: nine sources declare MIT; three do not declare a license there. Those declarations were not independently validated against upstream rights or private additions. They are not authorization to republish the original content. Source resources, original paragraphs and active-profile snapshots are not distributed. The new text carries an **All rights reserved** notice, consistent with existing original catalog examples; no MIT grant or relicensing is inferred. Obtain rights review and owner authorization before broader redistribution or changing that notice. The catalog package remains UNLICENSED.

## Opt-in deployment

All twelve entries support four-harness payload staging, not verified identical invocation or native discovery. They are absent from every bundled default environment, which retains the same 37 selections. Add desired IDs to an explicitly approved private environment with a dedicated destination. Preview first, review ownership/conflicts, and apply only when that target is authorized. No real profile was changed in this curation.

The `local-examples.json` sidecar now preserves 22 optional records: four original examples, six Ponytail artifacts and these twelve curations. Base re-import retains records; keep their payload directories too. The three byte-preserved upstream manifests remain separate from this local authorship attribution.

## Runtime safeguards and verified boundaries

The skills are procedural and self-contained: each directory holds only SKILL.md and its notice. Named tools are optional prerequisites, not automatic installation permission. Project paths, engine binaries and output paths are caller-supplied approved values. Read-only examples are documentation, not commands executed by packaging review.

Production changes, commits/pushes, installs, paid generation, account mutations, uploads and publication retain separate approval scopes. Passwords and verification codes use only host-managed secure entry. Secret files and user data are not diagnostic inputs. Imported/project hooks are untrusted until explicitly reviewed; staging never executes them.

Acceptance tests cover metadata, notices, privacy patterns, default exclusion, sidecar merging, scratch-only deployment with ownership digest readback and repeated idempotence across all four harnesses. Existing package tests verify the actual npm tarball and pinned base re-import verifies retained payloads. These checks prove packaging and staging, not browser login, Android builds, Godot playability, image generation or video rendering in a consumer project. No new-content CI or publication is claimed by local tests.

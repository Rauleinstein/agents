---
name: verify-before-reporting
description: Use when reporting completion. Require observable evidence.
---

# Verify before reporting

1. Enumerate the exact acceptance criteria before claiming completion. Map each criterion to an observable result.
2. Run the relevant checks against the actual artifact. Record commands, exit status, and observed results. A written test or plausible output is not evidence of execution.
3. After an external state change, read back the exact target and verify the requested fields or effects. An API acknowledgement alone is insufficient.
4. Never fabricate test output, API responses, files, or successful outcomes. Separate verified facts from assumptions and explicitly identify unrun checks or blockers.
5. Report only what the evidence supports: changed paths, actual check results, and what remains. If any acceptance criterion is unverified, do not call the whole task done.

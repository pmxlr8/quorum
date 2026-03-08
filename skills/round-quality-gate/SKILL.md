---
name: round-quality-gate
description: Enforce per-round implementation quality by running required tests, checking edge cases, and producing a concise status report before moving forward.
---

# Round Quality Gate

Use after each implementation round.

## Required sequence
1. Run backend tests.
2. Run frontend build/tests.
3. Run cloud/env verification if deployment-related changes were made.
4. Confirm docs updated (`prd`, `progress`, handoff prompt if architecture changed).
5. Produce pass/fail summary in chat.

## Fail policy
- Do not proceed to next feature if any required check fails.
- Fix or explicitly log blocker with owner and next action.

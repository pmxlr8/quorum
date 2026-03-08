# Implementation Bootstrap

This folder is now prepped for agentic implementation.

## Start Here
1. Read `CLAUDE.md`.
2. Read `progress/progress.txt`.
3. Open `prd/tasks-war-room.md`.
4. Execute next eligible `P0` task.

## Structure
- `technical_doc.md`: corrected technical specification (v2 updates applied)
- `technical_doc_brutal_review.md`: red-team critique and improvement notes
- `CLAUDE.md`: session controller and project standards
- `prd/`: task graph and acceptance criteria
- `progress/`: append-only session log
- `decision-docs/`: architecture decisions and rationale
- `skills/`: reusable task workflows
- `quality/`: style/pattern enforcement and review guardrails
- `.github/workflows/`: CI checks for doc/contract drift

## Ground Rules Before Coding
- Do not start implementation until next `P0` task is selected from PRD.
- Any new architecture choice requires a decision doc.
- Any contract change requires updates in docs and tests.

---
name: prd-task-executor
description: Execute one PRD task end-to-end with dependency checks, implementation, tests, progress update, and commit discipline.
---

# PRD Task Executor

Use this when implementing a specific task from `prd/tasks-war-room.md`.

## Workflow
1. Read `progress/progress.txt` and `prd/tasks-war-room.md`.
2. Select next pending task whose dependencies are done.
3. Implement task acceptance criteria only.
4. Add or update tests in same session.
5. Run tests and capture command/input/expected/actual.
6. Append progress entry with task ID and files touched.

## Guardrails
- Do not silently expand scope.
- If blocked by dependency, mark blocked and pick next eligible task.
- Keep contracts synchronized with `technical_doc.md`.

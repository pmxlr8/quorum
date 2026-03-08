---
name: task-orchestrator
description: Build and maintain dependency-safe execution order across P0/P1/P2 tasks and parallel work streams.
---

# Task Orchestrator

Use this when planning sequencing, handoffs, or parallel agent execution.

## Workflow
1. Parse PRD tasks with statuses and dependencies.
2. Build ready queue (all dependencies done).
3. Prioritize: P0 first, then critical-path shortest completion.
4. Assign independent tasks to parallel streams.
5. Emit a compact run plan (now/next/later + blockers).

## Output Format
- `Now`: task IDs executable immediately
- `Blocked`: task IDs + missing dependency
- `Parallel lanes`: backend/frontend/test lanes

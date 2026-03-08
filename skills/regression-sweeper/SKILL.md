---
name: regression-sweeper
description: Add and execute edge-case and regression tests for changed modules, prioritizing websocket contracts, routing, and state transitions.
---

# Regression Sweeper

Use when backend contracts/events or routing logic changes.

## Focus areas
- Unsupported/invalid WS events
- Enum mismatch cases
- Session lifecycle connect/disconnect cleanup
- Ordering-sensitive events (`agent_speaking` before transcript updates)
- Fallback behaviors when external dependencies are unavailable

## Output
- New tests added
- Tests run with exact command and result
- Regression risks remaining

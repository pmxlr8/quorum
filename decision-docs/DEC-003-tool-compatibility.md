# Decision: ADK Tool Compatibility and Delegation Pattern

## Date
2026-03-08

## Problem
Built-in Gemini tool combinations may be constrained depending on ADK/runtime versions.

## Options
- Attach all tools directly to each board agent
- Use specialist-tool agents and delegate from orchestrator

## Decision
Use specialist-tool agents:
- search specialist: owns `google_search`
- compute specialist: owns `code_executor`
Board agents request specialist work via orchestrator.

## Trade-off
- More orchestration code
- Fewer runtime compatibility failures and clearer ownership

## Follow-up
Add integration tests proving delegation path for at least one finance and one legal query.

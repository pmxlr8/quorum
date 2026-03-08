# Style and Pattern Enforcement (Bug-Bot Rules)

These checks are mandatory for all PRs and agent-generated changes.

## Architecture Rules
- Do not hardcode model IDs or secrets.
- Do not mix runtime session state with persistent user/template data.
- Use REST for file bytes upload; WS for realtime events.
- Keep a single canonical enum for votes: `yes|no|abstain`.

## Backend Rules
- No blocking I/O inside async request/websocket handlers.
- No untyped API payload dicts in public handlers.
- No direct Firestore calls from route handlers when repository utility exists.
- No `print()` logging in runtime modules.

## Frontend Rules
- No WS event handling in view components; route through store/actions.
- No array index as React key in transcript or agent lists.
- No `any` types in event contracts.
- Do not create duplicate local state for server-authoritative entities.

## Testing Rules
- Must import real modules under test.
- Only mock external boundaries.
- Every test run summary must include input and output details.

## PR Review Checklist
- Contracts changed? Update `technical_doc.md` + tests.
- New decision made? Add `decision-docs/DEC-xxx-*.md`.
- Task completed? Update `progress/progress.txt`.

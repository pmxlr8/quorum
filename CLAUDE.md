# Virtual War Room - CLAUDE.md

This is a living operating manual for AI-assisted development in this repository.
Update this file when patterns, decisions, or constraints change.

## Project Snapshot
- Product: Virtual War Room (Live Agents track)
- Stack: FastAPI + ADK (backend), React + TypeScript (frontend), Firestore + Cloud Storage, Cloud Run
- Region: `us-central1`
- Live model strategy: use env var `LIVE_MODEL_ID`; default `gemini-2.5-flash-native-audio-preview-12-2025`

## How to Work (Session Controller)
1. Read [`progress/progress.txt`](progress/progress.txt) and [`prd/tasks-war-room.md`](prd/tasks-war-room.md).
2. Pick the next `P0` task with all dependencies completed.
3. Implement code and tests in the same session.
4. Run relevant checks and summarize exact input/output of test runs.
5. Append session notes to progress log (append-only).
6. Commit with task IDs in commit message.

## Non-Negotiable Rules
- Never use stale model IDs. Resolve all model names from env vars.
- Keep one audio input contract end-to-end (PCM16 16kHz for MVP).
- Never duplicate production logic in tests.
- Only mock external boundaries (Gemini API, GCP services, network calls).
- Keep runtime `session_state` minimal and transient. Persistent data belongs in Firestore.
- Do not add new API/event enums without updating shared schema docs and tests.

## Shared Contracts
- Voice input: base64 PCM16 mono at 16kHz via WS `audio` event.
- Voice output: PCM audio chunks from Live API streamed to frontend queue.
- Upload path: REST `/api/upload` for bytes; WS only for notify/progress events.
- Vote enum (canonical): `yes | no | abstain`.

## Coding Standards
- Python: type hints required, Black formatting, isort ordering.
- TypeScript: `strict` mode, avoid `any`, runtime schema validation for WS events.
- API models: use explicit Pydantic models, avoid untyped dicts in endpoints.
- Logging: structured logs only; no `print()` in backend runtime.

## Testing Standards
- Feature tasks must include test tasks.
- For each test run, record:
  - command
  - scenario input
  - expected output
  - actual output
- Minimum before demo: unit tests for routing/callbacks + one full E2E rehearsal script.

## Required Docs To Keep Updated
- [`technical_doc.md`](technical_doc.md)
- [`prd/tasks-war-room.md`](prd/tasks-war-room.md)
- [`progress/progress.txt`](progress/progress.txt)
- [`decision-docs/`](decision-docs)
- [`quality/style-enforcement.md`](quality/style-enforcement.md)

## Skill Routing (Local Skills)
Use these skills when relevant:
- `skills/prd-task-executor` for task pickup/execution flow
- `skills/task-orchestrator` for dependency-aware planning
- `skills/decision-recorder` for writing decision docs
- `skills/voice-pipeline-debugger` for voice/live issues
- `skills/hackathon-deploy` for Cloud Run deploy sequence
- `skills/test-output-summarizer` for test evidence and regression summaries

## Quick Commands
```bash
# backend
cd backend && pip install -r requirements.txt && cd .. && uvicorn backend.api.main:app --reload --port 8000

# frontend
cd frontend && npm install && npm run dev

# tests
pytest -q
npm test
```

## Commit Format
- `feat: <summary> (BACK-XXX)`
- `fix: <summary> (FRONT-XXX)`
- `test: <summary> (TEST-XXX)`
- `docs: <summary> (INFRA-XXX)`

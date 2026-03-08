# SESSION HANDOFF PROMPT (Use if chat/session is lost)

Paste this into a new agent session:

You are continuing the **Virtual War Room** hackathon build.
Work ONLY inside:
`/Users/lappy/Desktop/Google X Columbia`

## Mission
Ship a deployable Live Agents-track demo on Google Cloud with:
1) realtime voice roundtrip,
2) multi-agent turn-taking,
3) document upload + analysis,
4) vote flow,
5) stable Cloud Run deployment.

## Read these files first (in order)
1. `CLAUDE.md`
2. `progress/progress.txt`
3. `prd/tasks-war-room.md`
4. `technical_doc.md`
5. `decision-docs/*.md`
6. `infra/CLOUD_SETUP.md`
7. `infra/LOCAL_GCLOUD_SETUP.md`

## Current implementation status
- Completed: INFRA-000, BACK-001, BACK-002, FRONT-001.
- In progress: BACK-003 (currently using `backend/services/live_bridge.py` stub), FRONT-002 (AudioWorklet path in place, tune and harden).
- Not started: BACK-004 onward and FRONT-003 onward.

## Existing code map
- Backend entry: `backend/api/main.py`
- WebSocket endpoint: `backend/api/ws.py`
- Session manager: `backend/services/session_manager.py`
- Live bridge stub (must replace): `backend/services/live_bridge.py`
- Event schemas: `backend/models/events.py`
- Backend tests: `backend/tests/`
- Frontend app: `frontend/src/app/App.tsx`
- WS store: `frontend/src/store/wsStore.ts`
- Voice capture: `frontend/src/hooks/useVoiceCapture.ts`
- Audio playback: `frontend/src/hooks/useAudioPlayer.ts`
- Audio worklet: `frontend/src/worklets/pcm-processor.js`
- Deploy script: `infra/deploy_cloud_run.sh`

## Non-negotiable contracts
- Voice input contract: PCM16 mono 16kHz, base64 over WS event `{type:"audio",data:"..."}`
- Vote enum: `yes|no|abstain`
- Upload bytes via REST, not WS file blobs
- Model IDs via env vars only
- Keep session_state transient and minimal

## Required next implementation steps (strict order)
1. Finish BACK-003 by replacing stub bridge with real ADK/Gemini Live runner.
2. Keep BACK-003 tests green + add one integration test for audio event parsing.
3. Implement BACK-004 orchestrator + 3 board agents with deterministic routing baseline.
4. Implement FRONT-003 war-room layout and bind to existing WS events.
5. Implement FRONT-004 raise-hand + transcript UX.
6. Then proceed to BACK-006/007 (upload+analysis), BACK-008 (vote), FRONT-005/006.

## Testing requirements every task
- Backend: `source backend/.venv/bin/activate && pytest -q backend/tests`
- Frontend: `cd frontend && npm run build`
- Record test command + input + expected + actual in `progress/progress.txt`

## Cloud setup and billing mode
- Use Vertex mode for hackathon credits:
  - `AUTH_MODE=vertex`
  - no API key required for deploy path
- Project ID from hackathon init:
  - `gcloud-hackathon-3xfig8zhh2usd`

## Local gcloud usage notes
- `gcloud` installed locally.
- Use repo-local config to avoid permission issues:
  - `export CLOUDSDK_CONFIG=/Users/lappy/Desktop/Google X Columbia/.gcloud`
- Verify with:
  - `infra/verify_local_env.sh`

## Git workflow
- Commit after each meaningful task phase.
- Use task IDs in commit messages.
- Remote is `origin https://github.com/pmxlr8/quorum.git`.
- Push to `main` when checks pass.

## If blocked
- Add a decision doc in `decision-docs/` using template.
- Log blocker and fallback in `progress/progress.txt`.
- Never silently change contracts.


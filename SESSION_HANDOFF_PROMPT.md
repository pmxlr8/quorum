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
- Completed: BACK-003 baseline Gemini Live integration with robust fallback and startup-failure handling.
- Completed: FRONT-003 baseline and major UX pass (status diagnostics strip, mission card, improved controls/transcript).
- In progress: BACK-004 (routing baseline), FRONT-004 (raise-hand/event richness), BACK-005 (callback/state richness).
- Not started: BACK-006+ / FRONT-005+ document and vote persistence lanes.

## Existing code map
- Backend entry: `backend/api/main.py`
- WebSocket endpoint: `backend/api/ws.py`
- Session manager: `backend/services/session_manager.py`
- Live bridge stub (must replace): `backend/services/live_bridge.py`
- Live bridge implementation: `backend/services/live_bridge.py`
- Event schemas: `backend/models/events.py`
- Backend tests: `backend/tests/`
- Frontend app: `frontend/src/app/App.tsx`
- Frontend styles/theme: `frontend/src/app/warroom.css`
- WS store: `frontend/src/store/wsStore.ts`
- Voice capture: `frontend/src/hooks/useVoiceCapture.ts`
- Audio playback: `frontend/src/hooks/useAudioPlayer.ts`
- Audio worklet: `frontend/src/worklets/pcm-processor.js`
- Deploy script: `infra/deploy_cloud_run.sh`

## Current runtime truth (as of 2026-03-08)
- Vertex configuration is wired and read from `backend/.env` (and fallback `.env`).
- Health endpoint now reports runtime auth/model info:
  - `live_client_ready`, `auth_mode`, `project`, `location`.
- Local frontend should use:
  - `VITE_API_BASE_URL=http://127.0.0.1:8000`
  - `VITE_WS_BASE_URL=ws://127.0.0.1:8000`
- Default Live model updated to:
  - `gemini-live-2.5-flash-native-audio`

## Known resolved issues
- WS send race fixed via outbound queue in frontend store.
- Duplicate dev-mount behavior reduced by removing `React.StrictMode` in frontend boot.
- Audio replay queue duplication fixed (`useAudioPlayer` now processes only new chunks).
- Mic transcript spam in fallback mode removed (stub audio no longer emits per-chunk transcript).
- WS startup no longer crashes app when Live connect fails; app falls back with clear system message.

## Non-negotiable contracts
- Voice input contract: PCM16 mono 16kHz, base64 over WS event `{type:"audio",data:"..."}`
- Vote enum: `yes|no|abstain`
- Upload bytes via REST, not WS file blobs
- Model IDs via env vars only
- Keep session_state transient and minimal

## Required next implementation steps (strict order)
1. Continue BACK-004 from deterministic routing baseline to full ADK orchestrator + board-agent transfer behavior.
2. Implement BACK-005 callback-driven transcript state + raise-hand events.
3. Complete FRONT-004 raise-hand UX and explicit event controls in UI.
4. Start BACK-006/007 document ingest + analysis lane.
5. Then proceed to BACK-008 + FRONT-006 voting loop.

## Testing requirements every task
- Backend: `source backend/.venv/bin/activate && pytest -q backend/tests`
- Frontend: `cd frontend && npm run build`
- Record test command + input + expected + actual in `progress/progress.txt`

## Cloud setup and billing mode
- Use Vertex mode for hackathon credits:
  - `GOOGLE_GENAI_USE_VERTEXAI=true`
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

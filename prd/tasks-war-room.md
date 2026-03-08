# PRD - Virtual War Room Implementation Tasks

Status legend: `pending | in_progress | blocked | done`
Priority: `P0 | P1 | P2`

## Phase 0 - Project Guardrails

INFRA-000 (P0)
- Status: done
- Dependencies: none
- Acceptance Criteria:
  - `CLAUDE.md` exists and reflects current architecture/contracts
  - `progress/progress.txt` append-only template exists
  - `decision-docs/` initialized with baseline decisions
  - style enforcement rules documented

## Phase 1 - Voice Core

BACK-001 (P0)
- Status: done
- Dependencies: INFRA-000
- Acceptance Criteria:
  - FastAPI app bootstrapped with `/health`
  - lifecycle startup/shutdown hooks implemented

BACK-002 (P0)
- Status: done
- Dependencies: BACK-001
- Acceptance Criteria:
  - `/ws/{session_id}` established with connection manager
  - per-session queue and graceful disconnect cleanup

BACK-003 (P0)
- Status: in_progress
- Dependencies: BACK-002
- Acceptance Criteria:
  - Live runner wired with `LIVE_MODEL_ID`
  - inbound PCM16 audio events forwarded correctly
  - output audio events streamed to client

FRONT-001 (P0)
- Status: done
- Dependencies: INFRA-000
- Acceptance Criteria:
  - React + TS scaffold with strict mode
  - WS client store with reconnect

FRONT-002 (P0)
- Status: in_progress
- Dependencies: FRONT-001, BACK-003
- Acceptance Criteria:
  - AudioWorklet PCM capture in 100ms chunks
  - outbound audio event contract matches backend
  - audio playback queue handles interruption

## Phase 2 - Multi-Agent Meeting Loop

BACK-004 (P0)
- Status: pending
- Dependencies: BACK-003
- Acceptance Criteria:
  - orchestrator + 3 board agents configured
  - agent routing works for tech/finance/legal intents

BACK-005 (P0)
- Status: pending
- Dependencies: BACK-004
- Acceptance Criteria:
  - `after_model_callback` updates transcript
  - raise-hand events generated and broadcast

FRONT-003 (P0)
- Status: pending
- Dependencies: FRONT-001
- Acceptance Criteria:
  - 3-panel war-room layout renders
  - per-agent state: idle/speaking/raised/away

FRONT-004 (P0)
- Status: pending
- Dependencies: FRONT-003, BACK-005
- Acceptance Criteria:
  - raise-hand banner + grant turn interaction
  - transcript panel updates live

## Phase 3 - Documents + Decisions

BACK-006 (P0)
- Status: pending
- Dependencies: BACK-001
- Acceptance Criteria:
  - REST upload endpoint for PDF/PNG/JPG/MP4
  - object persisted to Cloud Storage

BACK-007 (P0)
- Status: pending
- Dependencies: BACK-006, BACK-004
- Acceptance Criteria:
  - read/analyze document tool integrated
  - document summary event emitted

BACK-008 (P0)
- Status: pending
- Dependencies: BACK-005
- Acceptance Criteria:
  - canonical vote enum `yes|no|abstain`
  - deterministic aggregation + idempotent vote writes

FRONT-005 (P0)
- Status: pending
- Dependencies: FRONT-003, BACK-007
- Acceptance Criteria:
  - document drop UI + upload progress + summary cards

FRONT-006 (P0)
- Status: pending
- Dependencies: FRONT-004, BACK-008
- Acceptance Criteria:
  - vote overlay and result rendering
  - user veto action uses canonical enum

## Phase 4 - Persistence + Demo Hardening

BACK-009 (P0)
- Status: pending
- Dependencies: BACK-005
- Acceptance Criteria:
  - transcript save to Firestore + markdown in Cloud Storage
  - autosave cadence + end-of-meeting save

TEST-001 (P0)
- Status: pending
- Dependencies: BACK-003
- Acceptance Criteria:
  - voice roundtrip script reports latency and pass/fail

TEST-002 (P0)
- Status: pending
- Dependencies: BACK-004, BACK-005
- Acceptance Criteria:
  - routing and callback tests with real module imports

TEST-003 (P0)
- Status: pending
- Dependencies: FRONT-004, FRONT-006
- Acceptance Criteria:
  - frontend behavior tests for raise-hand and vote flow

TEST-004 (P0)
- Status: pending
- Dependencies: all P0 tasks
- Acceptance Criteria:
  - end-to-end demo rehearsal checklist passes twice

## Stretch

BACK-010 (P1)
- Status: pending
- Dependencies: BACK-008
- Acceptance Criteria:
  - homework mode with progress events

FRONT-007 (P1)
- Status: pending
- Dependencies: BACK-010
- Acceptance Criteria:
  - homework panel with todo injection

BACK-011 (P1)
- Status: pending
- Dependencies: BACK-001
- Acceptance Criteria:
  - persona CRUD + prompt enhancement with `gemini-2.5-flash`

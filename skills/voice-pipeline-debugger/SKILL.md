---
name: voice-pipeline-debugger
description: Diagnose and fix Live API voice roundtrip failures across browser capture, websocket transport, ADK forwarding, and playback.
---

# Voice Pipeline Debugger

Use when mic capture, recognition, or playback fails.

## Checklist
1. Verify model ID and credentials are present.
2. Verify client audio format (PCM16, 16kHz mono).
3. Verify WS event payload sizes and ordering.
4. Verify server wraps audio as `audio/pcm;rate=16000`.
5. Verify output chunks are queued and interrupt handling clears queue.
6. Measure and log latency breakdown.

## Required Output
- Root cause
- Fix applied
- Before/after latency and behavior

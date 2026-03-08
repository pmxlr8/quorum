# Decision: Browser-to-Live Audio Contract

## Date
2026-03-08

## Options
- MediaRecorder WebM/Opus transport
- AudioWorklet raw PCM transport

## Decision
Use AudioWorklet PCM16 mono at 16kHz, chunked at 100ms, base64 over WS for MVP.

## Trade-off
- More frontend implementation complexity
- Fewer codec mismatches and lower debug risk during hackathon execution

## Contract
Client -> server:
- event: `audio`
- payload: base64 PCM16 bytes
- mime when wrapped to Live API: `audio/pcm;rate=16000`

Server -> client:
- event: `audio_chunk`
- payload: output chunks from Live API audio response

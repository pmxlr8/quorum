# Virtual War Room Technical Doc: Brutal Verification & Critique

Date reviewed: 2026-03-08
Reviewed file: `technical_doc.md`

## 1) Executive Verdict

Current doc quality: **6.5/10**

- **Strong**: product concept, UX differentiation, clear task decomposition, demo-centered thinking.
- **Weak**: several **implementation-breaking inconsistencies**, at least one **likely deprecated model usage**, and a few **ADK/tool constraints** that can invalidate the architecture if not fixed.
- **Win likelihood right now**: medium.
- **Win likelihood after fixes below**: high.

If you ship exactly this spec without corrections, you have a real risk of demo failure in the voice/tool pipeline.

---

## 2) Verified “Newest Tech” Check (What is current vs stale)

## Model and API reality check

1. **`gemini-live-2.5-flash-native-audio` appears invalid / non-canonical model ID**
- Your doc uses this string in multiple places.
- Official Gemini model docs list **Gemini 2.5 Flash Live** as:
  - `gemini-2.5-flash-native-audio-preview-12-2025`
  - `gemini-2.5-flash-native-audio-preview-09-2025`
- Impact: hard runtime failure if wrong model string is used.

2. **Legacy Live models in your assumptions were shut down**
- `gemini-live-2.5-flash-preview` and `gemini-2.0-flash-live-001` were shut down Dec 9, 2025.
- Impact: any fallback path or copied snippets using these IDs will fail.

3. **`gemini-flash-2.0` for persona enhancement is risky/outdated as of March 2026**
- Deprecations page lists Gemini 2.0 Flash family with shutdown “earliest February 2026”.
- Your doc uses `gemini-flash-2.0` for prompt enhancement.
- Impact: avoid possible immediate breakage. Move to `gemini-2.5-flash` (or latest approved alias strategy).

4. **ADK built-in tool limitation likely conflicts with your tool plan**
- ADK docs for Gemini API tools (e.g., code execution / Vertex AI Search) explicitly warn about a **single-tool-per-agent limitation**.
- Your plan gives agents many tools simultaneously (`google_search`, `code_executor`, plus multiple custom tools).
- Impact: architecture risk. You may need tool-router sub-agents or staged delegation.

---

## 3) Critical Technical Findings (ordered by severity)

## CRITICAL-1: Audio format contract is internally contradictory
- File refs:
  - MediaRecorder/WebM input: line ~156
  - Then wrapped as PCM blob: line ~161
  - Client event says PCM 16kHz: line ~527
  - Decision says MVP is WebM path: line ~1408

Why this is bad:
- WebM/Opus bytes are **not** PCM bytes. You cannot relabel encoded Opus bytes as `audio/pcm;rate=16000`.
- This is the highest-risk bug in the doc: it will produce silent failures or garbage recognition.

Fix:
- Pick one pipeline and keep it consistent end-to-end:
  - Option A: send true PCM16 chunks from `AudioWorklet` and label as PCM.
  - Option B: keep WebM/Opus and decode server-side before forwarding as required format.
- Do not combine A and B in the same data-flow spec.

## CRITICAL-2: Model IDs are not production-safe in doc
- File refs: lines ~195, ~786, ~946 use `gemini-live-2.5-flash-native-audio`.
- Fix immediately to a currently listed model ID; parameterize through env var so you can swap quickly.

## CRITICAL-3: Vote schema mismatch across layers
- File refs:
  - Product flow: Yes/No/Abstain (line ~33)
  - Tool API: yes/no/abstain (line ~545)
  - Client event: approve/reject/delay (line ~532)
- Why this is bad: inconsistent enum mapping leads to wrong tallies and UI drift.
- Fix: define one canonical enum and one explicit mapping layer.

## CRITICAL-4: ADK built-in tool coexistence likely invalid
- File refs: lines ~251-252 and ~1072-1075 assume direct coexistence.
- Why this is bad: if single-tool limitation applies in your ADK version, this design breaks at runtime.
- Fix: create specialist sub-agents (e.g., `search_agent`, `code_agent`) each with one built-in tool, and let orchestrator delegate.

## CRITICAL-5: Session state mixes transient runtime and persistent user data
- File refs: lines ~467-498.
- Why this is bad: memory bloat, accidental overwrite, concurrency bugs.
- Fix: remove `user:saved_personas`, `user:meeting_rooms`, `app:board_templates` from session runtime state. Keep in Firestore only.

---

## 4) High-Risk Design Smells (not instantly fatal, but dangerous)

1. **Reasoning leakage strategy is risky**
- You store/show `agent_reasoning` (line ~484, ~519).
- This can leak prompt internals and create compliance/safety issues.
- Recommendation: store private chain-of-thought internally only. Expose concise “explanation summary” generated separately.

2. **Redundant upload paths**
- You have both `/api/upload` and WS `upload_document` events.
- Recommendation: use REST for upload bytes; WS only for progress/notifications/events.

3. **Base64 audio over JSON for every chunk**
- Works, but expensive in overhead and latency.
- Recommendation: for MVP keep it, but set strict chunk size and backpressure policy. Consider binary frames later.

4. **Cloud Run stateful WS assumptions are under-specified**
- You use in-memory session/event bus; reconnect may land on new instance.
- Recommendation: add Redis/Firestore-backed session event state for reconnect resilience, or force short demo sessions on one instance.

5. **“Public read on /transcripts/ prefix” is overexposed**
- Sensitive meeting content should not default to public read.
- Use signed URLs with TTL.

---

## 5) Redundant Calls / Over-Nesting / “Looks Off”

## Redundant API/event patterns
- `upload_document` over WS duplicates `/api/upload`.
- `session_broadcast_tool` + direct callback broadcast can duplicate responsibilities.
- `reasoning_update` event can be extremely noisy; likely unnecessary at token-level granularity.

## Over-nested structures
- `session_state['current_vote']['votes'][agent]['reason']` nesting is okay, but add typed model instead of open dicts.
- `away_agents` with embedded mutable todo lists and progress is okay for runtime, but should be normalized when persisted.

## Naming inconsistencies
- `google_search` vs `web_search` appears in different sections.
- `transfer_to_agent()` and `AgentTool` both used without clear rules.

## Data contract mismatches
- Audio input says WebM in one place and PCM in another.
- Vote values mismatch.
- Document support says PDF/image/video but `read_document_tool` naming implies doc/image only.

---

## 6) Hard Recommendations to Make This Winnable

## A) Stabilize the core demo path (P0)
1. Lock one valid Live model ID in env: `LIVE_MODEL_ID`.
2. Lock one audio format pipeline only (prefer true PCM16 via AudioWorklet for determinism).
3. Remove built-in tool conflicts for MVP (ship without code executor if needed).
4. Freeze enums for vote/actions/events in a shared schema file used by backend + frontend tests.

## B) Simplify architecture for 12-hour reliability
1. Keep only 3 WS inbound event types for MVP: `audio`, `text`, `grant_speaking_turn`.
2. Route all file bytes through REST upload.
3. Keep session state minimal: meeting, transcript, raised_hands, away_agents, vote.
4. Disable homework mode in first demo pass unless core loop is fully stable by hour 8.

## C) Add judge-visible quality multipliers
1. “Decision ledger” panel: every recommendation gets confidence, assumptions, and risk class.
2. “Challenge mode” toggle: agents must present strongest counterargument before final vote.
3. “Source-backed claims” chip on each factual statement (especially CFO/Legal outputs).
4. “Interrupt intent UX”: explicit barge-in indicator + low-latency response meter.

---

## 7) Brutal Product Critique

What is currently weak from a judge perspective:
- Could look like “multi-persona chat” unless debate quality is visibly real.
- Heavy feature list can dilute reliability; judges reward live robustness more than breadth.
- Internal reasoning surfacing may appear gimmicky and unsafe if noisy or contradictory.

What will make judges say “this should win”:
- Flawless live turn-taking and interruptions.
- Agents disagree with each other in a useful, non-scripted way.
- Document drop instantly changes the board’s recommendations with concrete evidence.
- Final vote outputs a crisp, executive-ready action memo.

---

## 8) Proposed Priority Recut (if you want highest win probability)

1. **Must ship**
- Real-time voice loop
- Distinct agent identities
- Raise-hand + grant turn
- Doc drop + evidence-aware response
- Final vote + one-page decision summary

2. **Ship only if stable**
- Homework mode
- Persona builder
- Persistent room management

3. **Cut aggressively if unstable**
- Live reasoning stream
- Complex multi-panel side features
- Extra tools beyond core search/evidence retrieval

---

## 9) Concrete Edits Required in `technical_doc.md`

1. Replace all `gemini-live-2.5-flash-native-audio` references with a currently valid model ID strategy.
2. Replace `gemini-flash-2.0` persona enhancement with `gemini-2.5-flash` (or controlled alias).
3. Rewrite audio data flow to one consistent codec path.
4. Unify vote enums across product, WS, and tool contracts.
5. Remove persistent user/template blobs from runtime session state.
6. Resolve `google_search` vs `web_search` naming to one tool contract.
7. Add a “tool limitation compatibility” section for ADK built-ins and your workaround.
8. Add Cloud Run reconnect/session-affinity constraints and state synchronization approach.

---

## 10) Verified Sources

- Gemini API release notes (model launches/shutdowns): https://ai.google.dev/gemini-api/docs/changelog
- Gemini API deprecations (2.0 family status, live model replacements): https://ai.google.dev/gemini-api/docs/deprecations
- Gemini model catalog (current model codes incl Live): https://ai.google.dev/gemini-api/docs/models/gemini
- Live API guide (native audio capabilities and setup): https://ai.google.dev/gemini-api/docs/live-guide
- Live API / multimodal live guide (implementation approaches): https://ai.google.dev/api/multimodal-live
- Ephemeral tokens for Live API: https://ai.google.dev/gemini-api/docs/ephemeral-tokens
- ADK callbacks reference: https://google.github.io/adk-docs/callbacks/
- ADK API reference (callback signatures): https://google.github.io/adk-docs/api-reference/python/google-adk.html
- ADK Gemini tools overview: https://google.github.io/adk-docs/tools/gemini-api/
- ADK code execution tool limitation note: https://google.github.io/adk-docs/tools/gemini-api/code-execution/
- Cloud Run WebSockets guidance: https://cloud.google.com/run/docs/triggering/websockets
- Cloud Run session affinity: https://cloud.google.com/run/docs/configuring/session-affinity
- Firestore locations and location immutability: https://cloud.google.com/firestore/docs/locations
- Firestore best-practice on location placement: https://docs.cloud.google.com/firestore/native/docs/best-practices


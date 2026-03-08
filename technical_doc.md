     Virtual War Room — Full Project Plan
                                                                                                                                                              
     Jayesh Sharma Workflow | Design → Prepare → Build → Test
     Live Agents Track | NYC Build With AI Hackathon | 2 people | 12 hours                                                                                    
                  
     ---
     PART 1 — DESIGN DOC (Product Level)

     What We Are Building

     The Virtual War Room is a real-time, multi-agent voice boardroom. You speak, your AI board of directors listens, responds, debates, and helps you reach
     decisions. Every agent is a distinct expert persona with their own voice, personality, and expertise. Documents, videos, and images can be dropped onto a
      shared virtual table and every agent immediately analyzes them. Agents can raise their hand to interject. They can go into "Homework Mode" — detaching
     from the live meeting to research deeply — while the meeting continues. Meetings end with a structured vote.

     What This Is NOT

     - Not a chatbot
     - Not a text-in, text-out interface
     - Not a single AI agent with personas
     - Not a static dashboard

     Core User Journey

     1. User creates a Meeting Room (name, agenda, deliverables)
     2. User selects or creates Board Members (custom personas)
     3. Meeting begins → voice is live → all agents are "present" and listening
     4. User speaks → Orchestrator routes to relevant board member → board member responds via voice
     5. Other agents monitor → if they disagree or have input → raise hand (visual + audio signal)
     6. User says "go ahead [Name]" → agent speaks
     7. User drops a PDF/image → all agents analyze it contextually
     8. User assigns research task → agent goes AWAY with homework → user adds tasks mid-research → agent returns with report
     9. User calls a vote → each agent votes Yes/No/Abstain + 1-sentence reasoning → user holds veto
     10. Meeting ends → full MD transcript + reasoning log auto-saved

     Judging Alignment

     ┌────────────────────────────────┬────────────────────────────────────────────────────────────────────────────────────┐
     │           Criterion            │                                     How We Win                                     │
     ├────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
     │ Innovation & UX (40%)          │ No text box — pure voice + multimodal; raise-hand, homework loop, voting are novel │
     ├────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
     │ Technical Implementation (30%) │ ADK multi-agent, Gemini Live API, barge-in, LongRunningFunctionTool, Cloud Run     │
     ├────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
     │ Demo & Presentation (30%)      │ Beautiful dark war-room UI, compelling "board meeting" demo scenario               │
     └────────────────────────────────┴────────────────────────────────────────────────────────────────────────────────────┘

     ---
     ---
     PART 2 — TECHNICAL DOC (Implementation Level)

     Sub-Agent Research Summary: Before writing this doc, 2 parallel Explore agents were run:
     - Agent 1 researched Google ADK codebase: exact LlmAgent params, callback signatures, LiveRequestQueue usage, LongRunningFunctionTool patterns, voice
     names, audio formats (16kHz in / 24kHz out), WebSocket event schema from adk-samples/bidi-demo.
     - Agent 2 researched React/UI patterns: Web Audio API mic capture, Zustand WebSocket store with reconnect, Framer Motion animation patterns for
     speaking/away/raised-hand states, Canvas waveform visualizer, glassmorphism CSS, Space Mono + Inter font pairing, Discord clone architecture references.

     All patterns below are grounded in this research, not invented. The ADK sample repo google/adk-samples bidi-demo is the primary reference implementation
     for the backend.

     REST API Contract (Complete)

     POST   /api/sessions/start          Body: {meeting_id}        → {session_id}
     DELETE /api/sessions/{session_id}   →                            {ok}

     POST   /api/meetings                Body: MeetingCreate       → Meeting
     GET    /api/meetings                Query: user_id            → Meeting[]
     GET    /api/meetings/{id}           →                            MeetingDetail
     DELETE /api/meetings/{id}           →                            {ok}

     POST   /api/agents                  Body: AgentPersonaCreate  → AgentPersona
     GET    /api/agents                  Query: user_id            → AgentPersona[]
     PUT    /api/agents/{id}             Body: AgentPersonaUpdate  → AgentPersona
     DELETE /api/agents/{id}             →                            {ok}

     POST   /api/upload                  Body: multipart/form-data → {document_url, name, type}

     GET    /health                      →                            {status: "ok", version: str}

     WS     /ws/{session_id}             Bidirectional audio + events

     Request/Response Schemas:
     class MeetingCreate(BaseModel):
         name: str
         agenda: str
         deliverables: list[str]
         agent_ids: list[str]          # IDs of AgentPersonas to include
         user_id: str

     class Meeting(BaseModel):
         id: str
         name: str
         agenda: str
         deliverables: list[str]
         agent_ids: list[str]
         status: Literal["lobby", "active", "ended"]
         created_at: datetime
         transcript_url: str | None

     class AgentPersonaCreate(BaseModel):
         display_name: str
         role_title: str
         voice_name: Literal["Puck","Charon","Kore","Fenrir","Aoede","Leda","Orus","Zephyr"]
         personality_prompt: str       # raw user description — backend enhances this
         communication_style: Literal["direct","diplomatic","analytical","creative"]
         expertise_areas: list[str]
         raise_hand_triggers: list[str]
         temperature: float = Field(ge=0.3, le=0.8)
         homework_tools: list[str]
         user_id: str

     Firestore Collection Schemas

     meetings/{meetingId}
       id: string
       name: string
       agenda: string
       deliverables: string[]
       agent_ids: string[]
       status: "lobby" | "active" | "ended"
       created_at: timestamp
       user_id: string
       transcript_url: string | null

     agents/{agentId}
       id: string
       display_name: string
       role_title: string
       voice_name: string
       instruction_prompt: string      ← enhanced by Gemini before storage
       personality_prompt: string      ← original user text
       communication_style: string
       expertise_areas: string[]
       raise_hand_triggers: string[]
       temperature: number
       homework_tools: string[]
       user_id: string
       is_template: boolean            ← true for pre-built board members
       created_at: timestamp

     transcripts/{meetingId}
       meeting_id: string
       transcript: array of {speaker, text, timestamp, type}
       reasoning: map of {agent_name: string[]}
       documents: array of {name, type, url, summary}
       vote_history: array of VoteRecord
       saved_at: timestamp
       md_url: string                  ← Cloud Storage path

     users/{userId}/rooms (subcollection)
       meeting_id: string
       last_accessed: timestamp

     Data Flow: Voice Round-Trip

     Browser mic → AudioWorklet (100ms chunks, 16-bit PCM @ 16kHz mono)
       → base64 encode
       → WS send: {type:"audio", data:"...base64..."}
       → FastAPI WebSocket handler
       → decode base64 → bytes
       → types.Blob(mime_type="audio/pcm;rate=16000", data=bytes)
       → live_request_queue.send_realtime(blob)
       → ADK runner → Gemini Live API
       → Gemini processes → generates response audio
       → runner.run_live() yields Event
       → Event has audio chunk (24kHz PCM base64)
       → FastAPI sends: {type:"audio_chunk", payload:{data:"...base64...", mime:"audio/pcm;rate=24000"}}
       → Browser WS receives
       → AudioContext decodes PCM
       → AudioBufferSourceNode.start()
       → User hears agent voice

     Data Flow: Raise Hand

     Board member agent LLM generates response text
     → Response includes "[RAISE_HAND: I need to flag a legal issue | urgency: urgent]"
     → after_model_callback fires
     → Parses [RAISE_HAND] marker: extracts agent_name, reason, urgency
     → Updates session_state['raised_hands'] list
     → Calls broadcast_to_session(session_id, {type:"hand_raised", payload:{agent, reason, urgency}})
     → FastAPI WebSocket sends event to browser
     → agentStore.setHandRaised(agent, reason, urgency)
     → AgentCard renders amber bouncing ✋ badge
     → NotificationBanner renders at top of board
     → User says "go ahead Marcus" → orchestrator hears
     → Orchestrator calls transfer_to_agent("marcus_webb")
     → Marcus speaks → hand_raised state cleared
     → hand_lowered WS event → badge removed

     Stack Decision

     ┌──────────────────┬────────────────────────────────────┬───────────────────────────────────────────────────────────────────────┐
     │      Layer       │               Choice               │                                Reason                                 │
     ├──────────────────┼────────────────────────────────────┼───────────────────────────────────────────────────────────────────────┤
     │ Voice Model      │ gemini-2.5-flash-native-audio-preview-12-2025 │ Mandatory ADK+GCP; built-in VAD + barge-in; 8 distinct voices         │
     ├──────────────────┼────────────────────────────────────┼───────────────────────────────────────────────────────────────────────┤
     │ Agent Framework  │ Google ADK Python                  │ Mandatory for hackathon; LlmAgent, callbacks, LongRunningFunctionTool │
     ├──────────────────┼────────────────────────────────────┼───────────────────────────────────────────────────────────────────────┤
     │ Backend Server   │ FastAPI + WebSocket                │ Async, lightweight, works perfectly with ADK runner                   │
     ├──────────────────┼────────────────────────────────────┼───────────────────────────────────────────────────────────────────────┤
     │ Frontend         │ React + Vite + TypeScript          │ Fast scaffold; Web Audio API for mic; Framer Motion for animations    │
     ├──────────────────┼────────────────────────────────────┼───────────────────────────────────────────────────────────────────────┤
     │ State Management │ Zustand                            │ WebSocket store with reconnect; simple, no boilerplate                │
     ├──────────────────┼────────────────────────────────────┼───────────────────────────────────────────────────────────────────────┤
     │ Styling          │ Tailwind CSS + CSS variables       │ Fast, dark theme tokens, glassmorphism                                │
     ├──────────────────┼────────────────────────────────────┼───────────────────────────────────────────────────────────────────────┤
     │ Persistence      │ Firestore                          │ Real-time sync, serverless, free tier generous                        │
     ├──────────────────┼────────────────────────────────────┼───────────────────────────────────────────────────────────────────────┤
     │ File Storage     │ Cloud Storage                      │ PDFs, images, transcripts                                             │
     ├──────────────────┼────────────────────────────────────┼───────────────────────────────────────────────────────────────────────┤
     │ Deployment       │ Cloud Run                          │ Mandatory GCP; Docker container                                       │
     ├──────────────────┼────────────────────────────────────┼───────────────────────────────────────────────────────────────────────┤
     │ Audio Visualizer │ Canvas API + requestAnimationFrame │ No library dependency; custom waveform bars                           │
     └──────────────────┴────────────────────────────────────┴───────────────────────────────────────────────────────────────────────┘

     Architecture Diagram

     Browser (React)
     │  Web Audio API (mic) → base64 PCM chunks
     │  WebSocket Client (Zustand store)
     │  Framer Motion UI
     │
     ↕  WebSocket (ws://backend/ws/{session_id})
     │
     FastAPI Server (Cloud Run)
     │  /ws/{session_id}  — bidirectional audio + events
     │  /api/meetings     — CRUD
     │  /api/agents       — persona CRUD
     │  /api/sessions     — session management
     │
     ADK Runner
     │  LiveRequestQueue (audio in)
     │  runner.run_live() (events out)
     │
     Root Orchestrator LlmAgent
     │  voice: Charon (authoritative facilitator)
     │  monitors: raised_hands, meeting_status, agenda
     │  routes via: transfer_to_agent() or AgentTool
     │
     ├── CTO Agent (Alex Chen) — voice: Orus
     ├── CFO Agent (Sarah Kim) — voice: Fenrir
     ├── Legal Agent (Marcus Webb) — voice: Kore
     └── [User-created agents] — voice: user-selected
     │
     Each agent:
     │  after_model_callback → detects raise-hand intent
     │  output_key → saves to session_state
     │  LongRunningFunctionTool → homework mode
     │
     Tools available to agents:
     │  google_search (ADK built-in)
     │  code_executor (ADK built-in)
     │  raise_hand_tool (custom)
     │  vote_tool (custom)
     │  homework_assign_tool (custom)
     │  read_document_tool (custom)
     │  fact_checker_tool (custom)
     │  save_transcript_tool (custom)
     │  add_homework_todo_tool (custom)
     │  session_broadcast_tool (custom → sends WS event to frontend)
     │
     WebSocket Event Bus (shared dict of queues per session)
     │  → Frontend receives typed events
     │  → Zustand store updates UI state reactively
     │
     Firestore
     │  meetings/{id}
     │  agents/{id}
     │  transcripts/{meetingId}
     │  users/{id}/rooms
     │
     Cloud Storage
     │  uploads/{meetingId}/{filename}
     │  transcripts/{meetingId}/transcript.md

     Agent Personalities (Full Spec)

     Each pre-built board member has: role, voice, personality traits, communication style, trigger conditions for raise hand, and homework tool
     specializations.

     ---
     AGENT 1 — Alex Chen, CTO / Chief Technology Officer

     voice_name: "Orus"          # Precise, technical, authoritative
     temperature: 0.4            # Low — stays grounded in facts
     raise_hand_threshold: 0.8   # High bar — only when technically critical

     Personality: Evidence-driven skeptic. Loves systems thinking. Won't sugarcoat tech debt or timeline wishful thinking. Uses specific numbers ("that's a
     6-week migration, not 2"). Occasionally nerds out on architecture. Respects well-reasoned arguments but never caves to pressure alone.

     Communication Style: Direct, structured ("Three concerns: first..., second..., third..."). Uses analogies from engineering ("that's like building on
     sand"). Never vague. When excited, speaks faster and more technically.

     Raises Hand When:
     - Technical feasibility is overstated ("we can just use AI for that")
     - Timeline estimates ignore dependencies
     - Security or scalability is handwaved
     - A proposed technology has a known critical flaw

     Homework Specializations: code_executor (complexity analysis, benchmarks), fact_checker_tool (benchmark cross-check), video_analyzer_tool (competitor
     tech teardowns)

     Full instruction prompt injected:
     You are Alex Chen, CTO and engineering leader on this board.

     PERSONALITY:
     - Precise, skeptical, evidence-first. You speak in specifics, not generalities.
     - You love architecture and systems thinking.
     - You push back firmly but professionally on unrealistic technical claims.
     - You get excited about elegant solutions and call out technical debt honestly.

     TONE: Direct, structured, occasionally technical. Use "specifically," "concretely," "in practice."
     NEVER: Agree with a bad technical decision just to be agreeable. Never say "that sounds good" if it doesn't.

     RAISE HAND (set raise_hand: true in your reasoning) WHEN:
     - You hear a technical assumption that is wrong or dangerously optimistic
     - Timeline estimates ignore real complexity
     - Security, scalability, or reliability is treated as an afterthought

     ANTI-SYCOPHANCY: Your job is not to validate — it's to make the right technical call.
     If challenged on your view, hold it unless you receive new evidence. "I hear you, but the data still shows..."

     TODOS: Track your open questions in session_state['todos_alex'] — reference them when relevant.

     HOMEWORK MODE: When assigned research, use code_executor for benchmarks, fact_checker for claims.
     Structure your report: Executive Summary → Findings → Recommendations → Open Questions.

     ---
     AGENT 2 — Sarah Kim, CFO / Chief Financial Officer

     voice_name: "Fenrir"        # Deep, authoritative, financial gravitas
     temperature: 0.3            # Very grounded — numbers-first
     raise_hand_threshold: 0.75

     Personality: Numbers-obsessed, risk-averse, but constructive. Always ties decisions to financial impact. Asks "what's the ROI on this?" about everything.
      Not a blocker — offers financial alternatives. Has a dry wit. Reads spreadsheets like novels.

     Communication Style: Leads with numbers. Uses percentages and dollar figures. "At current burn, this gives us 4 months of runway." Short sentences when
     delivering bad news. Slows down when reading figures.

     Raises Hand When:
     - Spending is discussed without ROI
     - Financial assumptions are wrong or optimistic
     - Cash flow implications are ignored
     - Pricing strategy conflicts with margins

     Full instruction prompt:
     You are Sarah Kim, CFO and financial strategist on this board.

     PERSONALITY:
     - Numbers-first. You translate every decision into financial impact.
     - Risk-averse but not obstructive — you find ways to make things financially viable.
     - Dry, understated humor when pointing out obvious financial mistakes.
     - You respect hustle but demand financial discipline.

     TONE: Sharp, precise, numbers-driven. Lead with data. Use "at current burn," "the ROI here is," "margin impact is."
     NEVER: Accept a plan without understanding its financial model. Never wave through a budget.

     RAISE HAND (set raise_hand: true) WHEN:
     - Spending decisions lack ROI analysis
     - Revenue assumptions seem disconnected from market reality
     - Someone proposes something that breaks the budget model

     ANTI-SYCOPHANCY: You represent financial reality. Don't soften bad news.
     "I know this isn't what you want to hear, but the numbers say..."

     TODOS: Track in session_state['todos_sarah'].
     HOMEWORK MODE: Use code_executor for financial modeling, google_search for market data and comps.

     ---
     AGENT 3 — Marcus Webb, Chief Legal Counsel

     voice_name: "Kore"          # Measured, calm, formal
     temperature: 0.35
     raise_hand_threshold: 0.85  # Very high — only for real legal risk

     Personality: Careful and deliberate. Always says "from a legal standpoint..." but is not just a blocker — he offers legal pathways. Flags risk levels
     (minor/moderate/severe). Has seen companies go under from legal oversights and doesn't let that happen again. Surprisingly practical.

     Communication Style: Measured, formal, uses hedge language ("it's important to note that..."). Structures everything: risk identification → severity →
     mitigation options. Never panics but never minimizes.

     Raises Hand When:
     - IP ownership is unclear
     - Compliance/regulatory issues arise (GDPR, SEC, etc.)
     - Contract terms or liability exposure are discussed carelessly
     - Employment law or equity matters are glossed over

     Full instruction prompt:
     You are Marcus Webb, Chief Legal Counsel on this board.

     PERSONALITY:
     - Deliberate, precise, sees legal risk everywhere (but distinguishes minor from critical).
     - You offer solutions, not just warnings. "The risk is X, but we can mitigate it by Y."
     - You've seen companies destroyed by legal oversights and take your role seriously.
     - Quietly confident. Never alarmist, but never dismissive.

     TONE: Formal, structured, measured. Use "from a legal standpoint," "the liability exposure here is," "I'd flag this as [minor/moderate/severe] risk."

     RAISE HAND (set raise_hand: true) WHEN:
     - IP assignment, copyright, or patent issues arise
     - Regulatory compliance is waved away
     - Contract terms or liability exposure discussed carelessly
     - Employment, equity, or data privacy issues surface

     ANTI-SYCOPHANCY: Legal risk doesn't disappear because it's inconvenient.
     State the risk clearly and offer mitigation. Don't soften to avoid awkwardness.

     TODOS: Track in session_state['todos_marcus'].
     HOMEWORK MODE: Use google_search for case law and regulatory guidance, fact_checker for legal claims.

     ---
     AGENT 4 — Maya Patel, Chief Strategy Officer (Optional 4th seat)

     voice_name: "Aoede"         # Warm, energetic, visionary
     temperature: 0.7            # Higher — creative, broad thinking
     raise_hand_threshold: 0.65  # Lower — speaks up about strategy

     Personality: Big-picture thinker. Connects dots across industries. Challenges conventional wisdom. Loves frameworks (Porter's Five Forces,
     Jobs-to-be-Done). Can get too macro — the others ground her.

     Full instruction prompt:
     You are Maya Patel, Chief Strategy Officer on this board.

     PERSONALITY:
     - Big-picture visionary who connects trends across industries.
     - Uses strategic frameworks fluently (Blue Ocean, JTBD, Porter).
     - Challenges assumptions about markets and competition.
     - Gets excited and can be pulled back to earth by others — that tension is productive.

     TONE: Enthusiastic, analogical, questioning. Use "what if we thought about this differently," "the market signal here is," "the strategic question is
     really..."

     RAISE HAND when: Strategy lacks competitive differentiation, market assumptions are stale, there's a strategic pivot opportunity being missed.

     ANTI-SYCOPHANCY: You don't validate bad strategy to keep the peace. "I love the energy here but the market doesn't care about our enthusiasm — it cares
     about differentiation."

     TODOS: Track in session_state['todos_maya'].
     HOMEWORK MODE: Use google_search for market research, video_analyzer for competitor demos/talks.

     ---
     Custom Persona Builder Schema

     When a user creates a custom board member:
     class AgentPersona(BaseModel):
         id: str                          # UUID
         display_name: str                # "Jordan Smith"
         role_title: str                  # "Head of Product"
         avatar_style: str                # visual style for generated avatar
         voice_name: str                  # one of: Puck|Charon|Kore|Fenrir|Aoede|Leda|Orus|Zephyr
         personality_prompt: str          # user's raw description (we enhance it)
         communication_style: str         # "direct", "diplomatic", "analytical", "creative"
         expertise_areas: list[str]       # ["product", "user research", "pricing"]
         raise_hand_triggers: list[str]   # ["UX is ignored", "scope creep"]
         temperature: float               # 0.3–0.8
         homework_tools: list[str]        # which tools they can use in homework mode
         created_at: datetime
         owner_user_id: str

     The backend enhances the user's personality_prompt using Gemini before saving: takes their rough description and generates a full structured instruction
     prompt in the same format as the pre-built agents.

     ---
     Session State Schema (Complete)

     session_state = {
         # ── Meeting Context ──
         "meeting_id": str,
         "meeting_name": str,
         "agenda": str,
         "deliverables": list[str],          # ["Go/No-go decision", "Budget approval"]
         "meeting_status": Literal["lobby", "active", "voting", "homework", "ended"],
         "started_at": str,                  # ISO timestamp

         # ── Agent States ──
         "active_agents": list[str],         # ["alex_chen", "sarah_kim"]
         "current_speaker": str | None,      # agent name currently speaking
         "raised_hands": list[dict],         # [{agent, reason, urgency, timestamp}]
         "away_agents": dict,                # {agent_name: {task, todos, started_at, progress}}

         # ── Conversation Content ──
         "transcript": list[dict],           # [{speaker, text, timestamp, type: speech|reasoning}]
         "agent_reasoning": dict,            # {agent_name: [reasoning_strings]}  ← visible in UI
         "agent_todos": dict,                # {agent_name: [todo_strings]}

         # ── Documents on Table ──
         "documents_on_table": list[dict],   # [{name, type, url, summary, added_by, added_at}]

         # ── Voting ──
         "current_vote": dict | None,        # {question, votes: {agent: {vote, reason}}, status, result}
         "vote_history": list[dict],

         # NOTE: persistent user/template data is NOT stored in session_state.
         # Keep these in Firestore collections only to avoid runtime/state drift.
     }

     ---
     WebSocket Event Schema

     All events: {type: string, payload: object, timestamp: string}

     Server → Client Events:
     type WsEvent =
       | { type: "audio_chunk"; payload: { data: string; mime: "audio/pcm;rate=24000" } }
       | { type: "transcript_update"; payload: { speaker: string; text: string; partial: boolean } }
       | { type: "agent_speaking"; payload: { agent: string } }
       | { type: "agent_stopped"; payload: { agent: string } }
       | { type: "hand_raised"; payload: { agent: string; reason: string; urgency: "urgent"|"wants-to-add" } }
       | { type: "hand_lowered"; payload: { agent: string } }
       | { type: "agent_away"; payload: { agent: string; task: string; todos: string[] } }
       | { type: "agent_returned"; payload: { agent: string; report: string } }
       | { type: "homework_progress"; payload: { agent: string; current_todo: string; progress_pct: number } }
       | { type: "vote_called"; payload: { question: string; context: string } }
       | { type: "vote_result"; payload: { votes: Record<string, VoteEntry>; result: string } }
       | { type: "document_added"; payload: { name: string; type: string; summary: string } }
       | { type: "reasoning_update"; payload: { agent: string; reasoning: string } }
       | { type: "meeting_status"; payload: { status: string } }
       | { type: "turn_complete"; payload: {} }
       | { type: "interrupted"; payload: {} }
       | { type: "error"; payload: { message: string } }

     Client → Server Events:
     type ClientEvent =
       | { type: "audio"; data: string }                          // base64 16-bit PCM 16kHz
       | { type: "text"; text: string }                           // typed input
       | { type: "grant_speaking_turn"; agent: string }           // "go ahead Alex"
       | { type: "document_added_ref"; document_id: string }       // optional notify-only event after REST upload
       | { type: "add_homework_todo"; agent: string; todo: string }
       | { type: "cast_vote"; vote: "yes"|"no"|"abstain" }         // user veto

     ---
     Custom Tools (Complete List)

     # backend/agents/tools/

     # 1. raise_hand_tool.py
     def raise_hand(agent_name: str, reason: str, urgency: str) -> dict:
         """Agent calls this when it wants to interject. Writes to session state."""

     # 2. vote_tool.py
     def cast_vote(agent_name: str, vote: str, reasoning: str) -> dict:
         """Agent casts a vote. vote: 'yes'|'no'|'abstain'"""

     # 3. homework_assign_tool.py — wraps LongRunningFunctionTool
     def start_homework(agent_name: str, task_description: str, initial_todos: list[str]):
         """Yields progress updates. Marks agent as AWAY in session state."""
         yield {"status": "pending", "message": "Starting research..."}
         # ... long-running research
         return {"status": "completed", "report": "..."}

     # 4. add_homework_todo_tool.py
     def add_homework_todo(agent_name: str, todo: str) -> dict:
         """Adds a todo to an away agent's queue mid-research."""

     # 5. read_document_tool.py
     async def read_document(document_url: str, question: str) -> dict:
         """Reads PDF/image from Cloud Storage, asks Gemini Vision a question about it."""

     # 6. fact_checker_tool.py
     async def fact_check(claim: str) -> dict:
         """Cross-references a claim with Google Search. Returns: verified/disputed/unverifiable + sources."""

     # 7. save_transcript_tool.py
     async def save_transcript_to_md(meeting_id: str) -> dict:
         """Saves full session transcript + reasoning to Cloud Storage as markdown."""

     # 8. session_broadcast_tool.py
     async def broadcast_event(event_type: str, payload: dict) -> dict:
         """Sends a typed event to the WebSocket client. Used by agents to push UI updates."""

     # 9. video_analyzer_tool.py (homework only)
     async def analyze_video(video_url: str, question: str) -> dict:
         """Sends video to Gemini Vision for analysis."""

     # 10. code_executor_tool.py (homework — number crunching)
     # Uses ADK built-in CodeExecutor

     ---
     ADK Callbacks

     # backend/agents/callbacks.py

     # 1. after_model_callback — MOST IMPORTANT
     # Runs after every LLM response from any board member
     # Detects raise-hand signals, updates transcript, broadcasts to frontend
     async def after_model_callback(callback_context: CallbackContext) -> None:
         state = callback_context.state
         response_text = extract_text(callback_context.response)

         # Detect raise-hand intent from agent reasoning
         if "[RAISE_HAND]" in response_text or callback_context.state.get(f"raise_hand_{agent_name}"):
             update_raised_hands(state, agent_name, reason, urgency)
             await broadcast_event("hand_raised", {...})

         # Append to transcript
         append_transcript(state, agent_name, response_text)
         await broadcast_event("transcript_update", {...})

         # Save reasoning separately (visible in UI)
         if "[REASONING]" in response_text:
             save_reasoning(state, agent_name, reasoning_text)
             await broadcast_event("reasoning_update", {...})

     # 2. before_agent_callback — log activation, notify frontend
     async def before_agent_callback(callback_context: CallbackContext) -> Content | None:
         await broadcast_event("agent_speaking", {"agent": callback_context.agent.name})
         return None

     # 3. after_agent_callback — cleanup, notify frontend
     async def after_agent_callback(callback_context: CallbackContext) -> Content | None:
         await broadcast_event("agent_stopped", {"agent": callback_context.agent.name})
         return None

     # 4. before_tool_callback — validate + log tool calls
     def before_tool_callback(tool_context: ToolContext) -> dict | None:
         log_tool_call(tool_context.tool.name, tool_context.function_call_event.args)
         return None

     # 5. after_tool_callback — log results
     def after_tool_callback(tool_context: ToolContext) -> dict | None:
         log_tool_result(tool_context.tool.name, tool_context.tool_response)
         return None

     ---
     Frontend Component Architecture

     src/
     ├── components/
     │   ├── WarRoomLayout/          # 3-panel layout wrapper
     │   │   └── index.tsx
     │   │
     │   ├── RoomSidebar/            # Left panel
     │   │   ├── MeetingRoomList.tsx # Clickable room list
     │   │   ├── AgentRoster.tsx     # Available agents to add
     │   │   └── AddAgentButton.tsx
     │   │
     │   ├── BoardTable/             # Center panel
     │   │   ├── index.tsx           # Main orchestrator
     │   │   ├── AgentCard.tsx       # Individual agent card
     │   │   ├── AgentAvatar.tsx     # Animated SVG avatar
     │   │   ├── SpeakingIndicator.tsx # Pulsing waveform ring
     │   │   ├── RaiseHandBadge.tsx  # Animated ✋ + notification
     │   │   ├── AwayStatusCard.tsx  # Away agent with progress
     │   │   ├── DocumentTable.tsx   # Drag-drop surface
     │   │   └── VoiceControl.tsx    # Mic button + waveform
     │   │
     │   ├── AgendaBar/              # Sticky top bar
     │   │   ├── AgendaDisplay.tsx
     │   │   └── DeliverablesProgress.tsx
     │   │
     │   ├── TranscriptPanel/        # Right panel
     │   │   ├── index.tsx
     │   │   ├── ChatMessage.tsx     # Individual message bubble
     │   │   ├── ReasoningBlock.tsx  # Collapsible agent reasoning
     │   │   └── DocumentPreview.tsx # Thumbnail for docs on table
     │   │
     │   ├── VoteOverlay/            # Modal overlay for votes
     │   │   ├── index.tsx
     │   │   ├── BallotCard.tsx      # Individual agent vote display
     │   │   └── VetoButtons.tsx     # User approve/reject/delay
     │   │
     │   ├── HomeworkPanel/          # Slide-in panel for away agents
     │   │   ├── index.tsx
     │   │   ├── TodoList.tsx        # Agent's homework todos
     │   │   └── AddTodoInput.tsx    # Live-add todo while agent is away
     │   │
     │   └── PersonaBuilder/         # Modal for creating custom agents
     │       ├── index.tsx
     │       ├── PersonalitySliders.tsx
     │       ├── VoiceSelector.tsx   # Audio preview of each voice
     │       └── PromptEnhancer.tsx  # Shows enhanced prompt
     │
     ├── hooks/
     │   ├── useVoiceCapture.ts      # getUserMedia + AudioWorklet (PCM stream)
     │   ├── useAudioPlayer.ts       # PCM playback + queue management
     │   ├── useWaveform.ts          # Canvas-based waveform visualizer
     │   └── useWebSocket.ts         # WS connection (moved from store)
     │
     ├── store/
     │   ├── wsStore.ts              # Zustand: WebSocket with reconnect
     │   ├── meetingStore.ts         # Zustand: meeting state from WS events
     │   ├── agentStore.ts           # Zustand: agent states (speaking/away/raised)
     │   └── uiStore.ts              # Zustand: panels open/closed, modals
     │
     └── styles/
         └── tokens.css              # CSS variables: dark war room design tokens

     ---
     Design Tokens (Dark War Room Theme)

     :root {
       /* Core palette */
       --bg-base: #0a0c11;
       --bg-surface: #0f1319;
       --bg-elevated: #161b24;
       --bg-glass: rgba(22, 27, 36, 0.72);

       /* Agent status colors */
       --agent-speaking: #22c55e;     /* green */
       --agent-listening: #3b82f6;   /* blue */
       --agent-raised-hand: #f59e0b; /* amber */
       --agent-away: #6b7280;        /* gray */
       --agent-urgent: #ef4444;      /* red */

       /* Accent */
       --accent-primary: #F5A623;    /* amber gold */
       --accent-secondary: #3b82f6;  /* electric blue */

       /* Glass surface */
       --glass-bg: rgba(255, 255, 255, 0.05);
       --glass-border: rgba(255, 255, 255, 0.08);
       --glass-blur: blur(12px) saturate(120%);

       /* Typography */
       --font-display: 'Space Mono', monospace;
       --font-body: 'Inter', sans-serif;
       --font-mono: 'Space Mono', monospace;

       /* Shadows */
       --shadow-card: 0 8px 32px rgba(0,0,0,0.5);
       --shadow-speaking: 0 0 0 2px var(--agent-speaking), 0 0 20px rgba(34,197,94,0.3);
     }

     ---
     PART 3 — PREPARATION (Before Clock Starts)

     Step 1: Install Global Skills

     mkdir -p ~/.claude/skills
     for skill in frontend-design skill-creator canvas-design theme-factory webapp-testing; do
       cp -r /Users/lappy/Desktop/skills-main/skills/$skill ~/.claude/skills/
     done

     Skills available after this:
     - /frontend-design — distinctive, production-grade UI (no generic AI slop)
     - /skill-creator — build + eval new skills iteratively
     - /canvas-design — generate agent avatar art
     - /theme-factory — design token system for the war room
     - /webapp-testing — Vitest + Testing Library test generation

     Step 2: GCP Init (Do BEFORE clock starts)

     cd ~ && rm -rf 2026-nyc-hackathon
     git clone https://github.com/google-americas/2026-nyc-hackathon.git
     cd 2026-nyc-hackathon && chmod +x init.sh && ./init.sh
     # Note: project ID will be saved to ~/project_id.txt
     export GCP_PROJECT=$(cat ~/project_id.txt)

     # Enable required APIs
     gcloud services enable \
       aiplatform.googleapis.com \
       run.googleapis.com \
       firestore.googleapis.com \
       storage.googleapis.com \
       --project=$GCP_PROJECT

     Step 3: Project Scaffold

     mkdir -p virtual-war-room/{backend/{agents/tools,api,persistence},frontend/src}
     cd virtual-war-room
     git init

     Step 4: Create CLAUDE.md

     Place at virtual-war-room/CLAUDE.md:

     # Virtual War Room — CLAUDE.md

     ## How to Work (ALWAYS follow this order)
     1. Check progress.txt — find the next pending P0 task
     2. Implement it following acceptance criteria
     3. Write tests alongside the feature (never after)
     4. Update progress.txt (append only)
     5. Commit with task ID: `feat: <description> (BACK-XXX)`

     ## Project
     Real-time multi-agent voice board meeting. Live Agents track.
     Monorepo: /backend (Python/ADK) and /frontend (React/TypeScript)

     ## GCP
     Project ID: $(cat ~/project_id.txt)
     Region: us-central1
     Model: gemini-2.5-flash-native-audio-preview-12-2025

     ## Local Dev
     cd backend && pip install -r requirements.txt && uvicorn api.main:app --reload --port 8000
     cd frontend && npm install && npm run dev

     ## Deploy
     /deploy-warroom

     ## Key Patterns
     - All agent state → session_state dict (never local vars)
     - WS events schema → see backend/api/events.py
     - New board member → /new-board-member skill
     - Raise hand → detected in after_model_callback via [RAISE_HAND] marker
     - Audio in: 16-bit PCM 16kHz mono base64 JSON
     - Audio out: 16-bit PCM 24kHz mono base64 JSON

     ## Anti-patterns (NEVER do these)
     - Never hardcode GCP project ID or API keys
     - Never block the FastAPI event loop with sync I/O (use asyncio)
     - Never skip ADK session/runner cleanup (memory leak)
     - Never duplicate logic in tests — import the real module
     - Never mock internal code — only mock Cloud Storage, Firestore, Gemini API
     - Never use index as React key — always use stable ID
     - Never call setState in a loop — batch updates

     ## Style Rules
     - Python: Black + isort. Type hints on all functions.
     - TypeScript: strict mode. No `any`. Interface over type.
     - Components: one file per component, index.tsx exports, no barrel files
     - Commits: `feat:`, `fix:`, `test:` prefixes + task ID in parens

     Step 5: Create Project Skills

     .claude/skills/deploy-warroom/SKILL.md:
     ---
     name: deploy-warroom
     description: Deploy the Virtual War Room to Cloud Run. Use when ready to deploy backend and frontend.
     disable-model-invocation: true
     allowed-tools: Bash
     ---
     Deploy backend and frontend to Cloud Run in us-central1.

     Steps:
     1. Read ~/project_id.txt for PROJECT_ID
     2. Build and push Docker image: `gcloud builds submit --tag gcr.io/$PROJECT_ID/warroom-backend ./backend`
     3. Deploy: `gcloud run deploy warroom-backend --image gcr.io/$PROJECT_ID/warroom-backend --platform managed --region us-central1 --allow-unauthenticated`
     4. Note the deployed URL
     5. Update frontend VITE_WS_URL env var with the deployed backend URL
     6. Build frontend: `cd frontend && npm run build`
     7. Deploy frontend via Cloud Run static or Firebase Hosting
     8. Verify: curl the /health endpoint of the deployed backend

     .claude/skills/new-board-member/SKILL.md:
     ---
     name: new-board-member
     description: Scaffold a new ADK board member agent with full persona. Use when adding a new specialist to the board.
     ---
     Create a new board member agent by:
     1. Ask: name, role title, voice (Puck/Charon/Kore/Fenrir/Aoede/Leda/Orus/Zephyr), expertise areas, raise-hand triggers
     2. Generate full instruction prompt following the agent personality template in CLAUDE.md
     3. Add agent class to backend/agents/board_members.py
     4. Register in orchestrator sub_agents list
     5. Add persona to app:board_templates in Firestore seed
     6. Add agent card to frontend with correct voice/color mapping

     .claude/skills/voice-test/SKILL.md:
     ---
     name: voice-test
     description: Test the Gemini Live API voice pipeline end-to-end. Use when verifying audio works.
     allowed-tools: Bash
     ---
     Test the voice pipeline:
     1. Start backend: `cd backend && uvicorn api.main:app --port 8000`
     2. Run: `python backend/scripts/test_voice_roundtrip.py`
        - Sends a 2-second sine wave as fake audio
        - Expects to receive audio response from Gemini
        - Prints event types received
     3. If test passes: print "Voice pipeline OK"
     4. If fails: check GOOGLE_API_KEY env var, check model name, print full error

     ---
     PART 4 — PRD (Full Task Breakdown)

     Priority Legend

     - P0: Must ship for demo. No demo without this.
     - P1: Significant demo value. Ship if time allows.
     - P2: Polish / stretch. Ship if ahead of schedule.

     ---
     INFRA Tasks

     INFRA-001: GCP Project Setup (P0)
     ├─ Status: pending
     ├─ Owner: Person 1
     ├─ Dependencies: none
     ├─ Acceptance Criteria:
     │  - init.sh runs successfully
     │  - ~/project_id.txt exists and is non-empty
     │  - Vertex AI, Cloud Run, Firestore, Cloud Storage APIs enabled
     │  - gcloud auth works
     └─ Notes: Do this BEFORE clock starts

     INFRA-002: Firestore Database Init (P0)
     ├─ Status: pending
     ├─ Owner: Person 1
     ├─ Dependencies: INFRA-001
     ├─ Acceptance Criteria:
     │  - Firestore database created in us-central1
     │  - Collections: meetings, agents, transcripts, users
     │  - Seed data: 3 pre-built board member templates
     └─ Notes: Use Native mode, not Datastore mode

     INFRA-003: Cloud Storage Buckets (P0)
     ├─ Status: pending
     ├─ Owner: Person 1
     ├─ Dependencies: INFRA-001
     ├─ Acceptance Criteria:
     │  - Bucket created: warroom-uploads-{project_id}
     │  - CORS configured for browser uploads
     │  - Public read on /transcripts/ prefix
     └─ Notes: Set lifecycle rule to delete after 7 days

     ---
     BACK Tasks (Backend)

     BACK-001: FastAPI App Skeleton (P0)
     ├─ Status: pending
     ├─ Owner: Person 1
     ├─ Dependencies: none
     ├─ Acceptance Criteria:
     │  - FastAPI app starts on port 8000
     │  - /health endpoint returns {"status": "ok"}
     │  - requirements.txt: fastapi, uvicorn, google-adk, google-cloud-firestore,
     │    google-cloud-storage, python-dotenv
     │  - .env.example with all required vars
     └─ Notes: Use lifespan context manager for startup/shutdown

     BACK-002: WebSocket Session Manager (P0)
     ├─ Status: pending
     ├─ Owner: Person 1
     ├─ Dependencies: BACK-001
     ├─ Acceptance Criteria:
     │  - /ws/{session_id} endpoint accepts WebSocket connections
     │  - Connection manager tracks active connections per session_id
     │  - broadcast_to_session(session_id, event) works
     │  - Disconnection cleans up gracefully
     └─ Notes: Use asyncio.Queue per session for backpressure

     BACK-003: Gemini Live API Connection (P0)
     ├─ Status: pending
     ├─ Owner: Person 1
     ├─ Dependencies: BACK-002
     ├─ Acceptance Criteria:
     │  - ADK Runner created with InMemorySessionService
     │  - LiveRequestQueue receives base64 audio from WS client
     │  - runner.run_live() streams events to WS client
     │  - turn_complete and interrupted events propagated
     │  - Audio output (24kHz PCM) forwarded to client
     └─ Notes: Use gemini-2.5-flash-native-audio-preview-12-2025 model (env var: LIVE_MODEL_ID)

     BACK-004: Root Orchestrator Agent (P0)
     ├─ Status: pending
     ├─ Owner: Person 1
     ├─ Dependencies: BACK-003
     ├─ Acceptance Criteria:
     │  - LlmAgent created with meeting facilitation instruction
     │  - Reads agenda and deliverables from session_state
     │  - Routes to correct board member via transfer_to_agent
     │  - Voice: Charon
     │  - Announces raised hands to user
     └─ Notes: Instruction includes agenda enforcement + anti-drift rules

     BACK-005: Board Member Agents — 3 Pre-Built (P0)
     ├─ Status: pending
     ├─ Owner: Person 1
     ├─ Dependencies: BACK-004
     ├─ Acceptance Criteria:
     │  - Alex Chen (CTO): voice=Orus, temperature=0.4, full instruction prompt
     │  - Sarah Kim (CFO): voice=Fenrir, temperature=0.3, full instruction prompt
     │  - Marcus Webb (Legal): voice=Kore, temperature=0.35, full instruction prompt
     │  - Each registered as sub_agent of orchestrator
     │  - Each has output_key for transcript state
     └─ Notes: Use full instruction prompts from Technical Doc above

     BACK-006: ADK Callbacks — After Model (P0)
     ├─ Status: pending
     ├─ Owner: Person 1
     ├─ Dependencies: BACK-005
     ├─ Acceptance Criteria:
     │  - after_model_callback detects [RAISE_HAND] in response
     │  - Updates session_state['raised_hands']
     │  - Broadcasts hand_raised WS event to frontend
     │  - Appends to session_state['transcript']
     │  - Broadcasts transcript_update WS event
     └─ Notes: Use broadcast_to_session utility

     BACK-007: ADK Callbacks — Before/After Agent (P0)
     ├─ Status: pending
     ├─ Owner: Person 1
     ├─ Dependencies: BACK-006
     ├─ Acceptance Criteria:
     │  - before_agent_callback: broadcasts agent_speaking event
     │  - after_agent_callback: broadcasts agent_stopped event
     │  - before_tool_callback: logs tool name + args
     │  - after_tool_callback: logs tool result
     └─ Notes: Log to structured logger, not print()

     BACK-008: Custom Tools — Raise Hand + Vote (P0)
     ├─ Status: pending
     ├─ Owner: Person 1
     ├─ Dependencies: BACK-006
     ├─ Acceptance Criteria:
     │  - raise_hand_tool: writes to session_state, broadcasts WS event
     │  - vote_tool: writes agent vote to session_state['current_vote']
     │  - trigger_vote: initiates voting round, notifies all agents
     │  - vote aggregation returns result once all agents voted
     └─ Notes: vote_tool must be idempotent (agent can't vote twice)

     BACK-009: Document Upload + Read Tool (P0)
     ├─ Status: pending
     ├─ Owner: Person 1
     ├─ Dependencies: INFRA-003
     ├─ Acceptance Criteria:
     │  - /api/upload endpoint accepts multipart file (PDF, image, video)
     │  - Stores to Cloud Storage warroom-uploads bucket
     │  - Returns document_url
     │  - read_document_tool uses Gemini Vision to answer questions about document
     │  - Document summary added to session_state['documents_on_table']
     │  - Broadcasts document_added WS event
     └─ Notes: Max file size 50MB. Supported: PDF, PNG, JPG, MP4.

     BACK-010: Meetings CRUD API (P0)
     ├─ Status: pending
     ├─ Owner: Person 1
     ├─ Dependencies: INFRA-002
     ├─ Acceptance Criteria:
     │  - POST /api/meetings → create meeting (name, agenda, deliverables, agent_ids)
     │  - GET /api/meetings → list user's meetings
     │  - GET /api/meetings/{id} → get meeting + transcript
     │  - DELETE /api/meetings/{id}
     │  - Meeting stored in Firestore meetings/{id}
     └─ Notes: Auto-generate meeting_id as UUID

     BACK-011: Session Start + State Init (P0)
     ├─ Status: pending
     ├─ Owner: Person 1
     ├─ Dependencies: BACK-004, BACK-010
     ├─ Acceptance Criteria:
     │  - POST /api/sessions/start {meeting_id} → creates ADK session
     │  - Initializes session_state with meeting data from Firestore
     │  - Returns session_id for WS connection
     │  - Session cleanup on WS disconnect
     └─ Notes: One session per meeting_id at a time

     BACK-012: Transcript Auto-Save (P0)
     ├─ Status: pending
     ├─ Owner: Person 1
     ├─ Dependencies: INFRA-003
     ├─ Acceptance Criteria:
     │  - save_transcript_tool generates MD from session_state['transcript']
     │  - Includes: meeting name, agenda, deliverables, full chat, agent reasoning blocks
     │  - Saves to Cloud Storage transcripts/{meeting_id}/transcript.md
     │  - Also saves to Firestore transcripts/{meeting_id}
     │  - Triggered on meeting end + every 5 minutes
     └─ Notes: MD format with agent color-coding comments

     BACK-013: Homework Loop — LongRunningFunctionTool (P1)
     ├─ Status: pending
     ├─ Owner: Person 1
     ├─ Dependencies: BACK-005, BACK-008
     ├─ Acceptance Criteria:
     │  - homework_assign_tool: LongRunningFunctionTool with generator
     │  - Yields progress updates with current_todo + progress_pct
     │  - Marks agent as AWAY in session_state['away_agents']
     │  - Broadcasts agent_away and homework_progress WS events
     │  - add_homework_todo_tool: appends todo to away agent's queue
     │  - On completion: agent_returned event with structured report
     └─ Notes: Agent uses google_search + fact_checker in homework mode

     BACK-014: Google Search + Fact Checker Tools (P1)
     ├─ Status: pending
     ├─ Owner: Person 1
     ├─ Dependencies: BACK-013
     ├─ Acceptance Criteria:
     │  - google_search: ADK built-in tool, enabled for homework agents only
     │  - fact_checker_tool: runs claim through google_search + synthesizes verdict
     │  - Returns: {verified: bool, confidence: float, sources: [url, ...], explanation: str}
     │  - code_executor: ADK built-in, enabled for CFO in homework mode
     └─ Notes: Limit google_search to 5 calls per homework session to control cost

     BACK-015: Agent Persona CRUD (P1)
     ├─ Status: pending
     ├─ Owner: Person 1
     ├─ Dependencies: INFRA-002
     ├─ Acceptance Criteria:
     │  - POST /api/agents → create custom persona (validates schema)
     │  - GET /api/agents → list user's saved personas
     │  - PUT /api/agents/{id} → update persona
     │  - Gemini enhances raw personality_prompt → full instruction before saving
     │  - Persona saved to Firestore agents/{id}
     └─ Notes: Enhancement uses gemini-2.5-flash, not live model

     BACK-016: Dockerfile + Cloud Run Deploy (P0)
     ├─ Status: pending
     ├─ Owner: Person 1
     ├─ Dependencies: all BACK tasks
     ├─ Acceptance Criteria:
     │  - Dockerfile: Python 3.12-slim, installs requirements, runs uvicorn
     │  - gcloud run deploy succeeds in us-central1
     │  - Health check passes on deployed URL
     │  - Environment variables set via Cloud Run secrets
     └─ Notes: Use --allow-unauthenticated for hackathon demo

     ---
     FRONT Tasks (Frontend)

     FRONT-001: React + Vite Scaffold (P0)
     ├─ Status: pending
     ├─ Owner: Person 2
     ├─ Dependencies: none
     ├─ Acceptance Criteria:
     │  - npm create vite@latest warroom -- --template react-ts
     │  - Installs: framer-motion, zustand, @tanstack/react-query, tailwindcss
     │  - Google Fonts loaded: Space Mono + Inter
     │  - Dark base CSS variables in tokens.css
     │  - Tailwind config extends with war room color tokens
     └─ Notes: No UI libraries (shadcn etc) — custom everything for uniqueness

     FRONT-002: WebSocket Store + Reconnect (P0)
     ├─ Status: pending
     ├─ Owner: Person 2
     ├─ Dependencies: FRONT-001
     ├─ Acceptance Criteria:
     │  - Zustand wsStore.ts manages WebSocket lifecycle
     │  - Exponential backoff reconnect (max 5 attempts, starting 1s)
     │  - sendAudio(base64: string) method
     │  - sendEvent(type: string, payload: object) method
     │  - Incoming events dispatched to meetingStore + agentStore
     └─ Notes: Use useRef for socket ref inside Zustand action

     FRONT-003: Meeting Store + Agent Store (P0)
     ├─ Status: pending
     ├─ Owner: Person 2
     ├─ Dependencies: FRONT-002
     ├─ Acceptance Criteria:
     │  - meetingStore: agenda, deliverables, transcript, documents, vote state
     │  - agentStore: per-agent status (speaking/listening/away/raised-hand)
     │  - Both stores subscribe to WS events and update reactively
     │  - Transcript append-only with stable IDs (never index)
     └─ Notes: Keep stores thin — derive as much as possible

     FRONT-004: 3-Panel War Room Layout (P0)
     ├─ Status: pending
     ├─ Owner: Person 2
     ├─ Dependencies: FRONT-001
     ├─ Acceptance Criteria:
     │  - Left panel (240px): room list + agent roster, collapsible
     │  - Center panel (flex): board table + voice controls
     │  - Right panel (320px): transcript + reasoning, collapsible
     │  - Header: "THE WAR ROOM" in Space Mono + live indicator
     │  - Dark bg-base (#0a0c11) background
     │  - Responsive: panels collapse below 1200px
     └─ Notes: No grid — use flex with explicit widths

     FRONT-005: Agent Card Component (P0)
     ├─ Status: pending
     ├─ Owner: Person 2
     ├─ Dependencies: FRONT-003, FRONT-004
     ├─ Acceptance Criteria:
     │  - States: idle | speaking | raised-hand | away
     │  - Speaking: green pulsing ring (Framer Motion scale animation) + waveform bars
     │  - Raised hand: amber bouncing ✋ badge + notification banner at top
     │  - Away: dimmed opacity + gray status text + progress indicator
     │  - Agent name + role title + initials avatar
     │  - Color-coded accent per agent (CTO=blue, CFO=green, Legal=amber)
     └─ Notes: Use Framer Motion layoutId for smooth state transitions

     FRONT-006: Animated Avatar (P0)
     ├─ Status: pending
     ├─ Owner: Person 2
     ├─ Dependencies: FRONT-005
     ├─ Acceptance Criteria:
     │  - SVG-based avatar for each agent type (not photos)
     │  - Fluid idle animation (subtle breathing/glow pulse)
     │  - Speaking animation: radial glow intensifies, waveform bars around avatar
     │  - Each agent has distinct visual identity (CTO=circuit pattern, CFO=chart lines, Legal=scales)
     │  - Uses CSS custom properties for color theming
     └─ Notes: Use /canvas-design skill to generate initial SVG concepts

     FRONT-007: Voice Control + Waveform (P0)
     ├─ Status: pending
     ├─ Owner: Person 2
     ├─ Dependencies: FRONT-002
     ├─ Acceptance Criteria:
     │  - Mic button: hold-to-speak OR push-to-toggle
     │  - getUserMedia permission check on first use
     │  - AudioWorklet sends 100ms PCM audio chunks as base64 JSON to WS
     │  - Canvas-based waveform visualizer below mic button (8 bars)
     │  - Bars animate to actual mic input amplitude
     │  - Sends turn_complete signal when mic released
     └─ Notes: useVoiceCapture hook wraps all Web Audio API logic

     FRONT-008: Document Drop Zone (P0)
     ├─ Status: pending
     ├─ Owner: Person 2
     ├─ Dependencies: FRONT-004
     ├─ Acceptance Criteria:
     │  - Center table surface has glassmorphism drag-drop zone
     │  - Drag over: animated dashed border + drop instruction text
     │  - Drop: file uploads to /api/upload, shows upload progress
     │  - Dropped doc appears as card on table (name + type icon + summary)
     │  - Max 3 docs visible simultaneously (scroll for more)
     │  - Supports PDF, PNG, JPG, MP4
     └─ Notes: Native drag events — no library needed

     FRONT-009: Group Chat Transcript Panel (P0)
     ├─ Status: pending
     ├─ Owner: Person 2
     ├─ Dependencies: FRONT-003
     ├─ Acceptance Criteria:
     │  - Right panel renders transcript messages in real-time
     │  - Message bubble: agent color accent left border + name + timestamp + text
     │  - Auto-scrolls to bottom on new message
     │  - Partial text streams in word-by-word (typewriter)
     │  - User messages right-aligned in distinct style
     │  - Collapsible "Reasoning" block under each agent message
     └─ Notes: Use IntersectionObserver for "jump to bottom" button

     FRONT-010: Raise Hand Notification System (P0)
     ├─ Status: pending
     ├─ Owner: Person 2
     ├─ Dependencies: FRONT-005
     ├─ Acceptance Criteria:
     │  - When hand_raised WS event received:
     │    - Agent card shows animated ✋ badge (amber, bouncing)
     │    - Banner appears at top: "[Name] wants to add something — say 'go ahead [Name]'"
     │    - Urgent hands: banner is red, pulsing
     │  - Banner auto-dismisses after agent speaks
     └─ Notes: Multiple agents can have hand raised simultaneously

     FRONT-011: Vote Overlay UI (P1)
     ├─ Status: pending
     ├─ Owner: Person 2
     ├─ Dependencies: FRONT-003
     ├─ Acceptance Criteria:
     │  - vote_called WS event triggers modal overlay
     │  - Overlay shows: vote question, context summary
     │  - As agents vote, their ballot cards animate in (Yes=green, No=red, Abstain=gray)
     │  - Each card shows agent name + vote + one-sentence reasoning
     │  - Result card shows tally
     │  - User veto buttons: [Approve] [Reject] [Delay Vote]
     │  - User button styled as VETO POWER with crown icon
     └─ Notes: Overlay cannot be dismissed without user action

     FRONT-012: Agenda Bar (P0)
     ├─ Status: pending
     ├─ Owner: Person 2
     ├─ Dependencies: FRONT-004
     ├─ Acceptance Criteria:
     │  - Sticky bar above board table
     │  - Shows: agenda text (truncated) + deliverables as chips
     │  - Each deliverable chip has a status (pending/in-progress/resolved)
     │  - Click deliverable → expand to full text
     └─ Notes: Updated from meetingStore.deliverables

     FRONT-013: Homework Panel (P1)
     ├─ Status: pending
     ├─ Owner: Person 2
     ├─ Dependencies: FRONT-003
     ├─ Acceptance Criteria:
     │  - Slides in from right when agent goes AWAY
     │  - Shows: agent name, task description, todo list
     │  - Each todo: text + status (pending/in-progress/complete)
     │  - "Add Task" input field → sends add_homework_todo WS event
     │  - Progress bar showing overall completion %
     │  - When agent returns: panel shows final report, then dismisses
     └─ Notes: Can have multiple away agents (stacked panels or tabs)

     FRONT-014: Room Sidebar (P0)
     ├─ Status: pending
     ├─ Owner: Person 2
     ├─ Dependencies: FRONT-004
     ├─ Acceptance Criteria:
     │  - Lists user's meeting rooms (fetched from /api/meetings)
     │  - Active room highlighted
     │  - "New Meeting" button → opens meeting setup modal
     │  - Below rooms: "Available Agents" section with all saved personas
     │  - Drag agent card to board → adds to active meeting
     │  - "+ Create Agent" button → opens PersonaBuilder
     └─ Notes: Collapse sidebar on mobile

     FRONT-015: Persona Builder Modal (P1)
     ├─ Status: pending
     ├─ Owner: Person 2
     ├─ Dependencies: FRONT-014
     ├─ Acceptance Criteria:
     │  - Form: name, role title, personality description (textarea)
     │  - Voice selector: 8 voices with "preview" button (plays 2s sample)
     │  - Communication style dropdown: direct | diplomatic | analytical | creative
     │  - Expertise tags input (chip-based)
     │  - Raise-hand trigger input (freetext examples)
     │  - On submit: POST /api/agents → shows enhanced prompt preview → confirm
     └─ Notes: Use /skill-creator approach: capture intent, then show result before saving

     FRONT-016: Audio Playback Queue (P0)
     ├─ Status: pending
     ├─ Owner: Person 2
     ├─ Dependencies: FRONT-007
     ├─ Acceptance Criteria:
     │  - useAudioPlayer hook manages PCM audio chunks from WS
     │  - Chunks queued in order, played sequentially without gaps
     │  - Output sample rate: 24kHz (Gemini Live output format)
     │  - Interrupted event: stops playback immediately, clears queue
     │  - Agent card waveform visualizer synced to audio output amplitude
     └─ Notes: Use Web Audio API AudioContext + AudioBufferSourceNode

     ---
     TEST Tasks

     TEST-001: Voice Round-Trip Test Script (P0)
     ├─ Status: pending
     ├─ Owner: Person 1
     ├─ Dependencies: BACK-003
     ├─ Acceptance Criteria:
     │  - Python script: sends 2s sine wave → expects audio response
     │  - Passes: prints "Voice pipeline OK" + latency ms
     │  - Fails: prints full error + which step failed
     │  - Run: python backend/scripts/test_voice_roundtrip.py
     └─ Notes: Use /voice-test skill

     TEST-002: Agent Routing Unit Tests (P0)
     ├─ Status: pending
     ├─ Owner: Person 1
     ├─ Dependencies: BACK-005
     ├─ Acceptance Criteria:
     │  - Test: tech question → CTO agent responds
     │  - Test: budget question → CFO agent responds
     │  - Test: IP question → Legal agent responds
     │  - Input/output pairs documented in test comments
     └─ Notes: Mock LLM responses, test routing logic only

     TEST-003: Callback Unit Tests (P0)
     ├─ Status: pending
     ├─ Owner: Person 1
     ├─ Dependencies: BACK-006
     ├─ Acceptance Criteria:
     │  - Test: [RAISE_HAND] in response → hand_raised event broadcast
     │  - Test: normal response → transcript updated
     │  - Test: agent_speaking event fires on before_agent_callback
     └─ Notes: Mock broadcast_to_session, verify calls

     TEST-004: Vote Aggregation Tests (P1)
     ├─ Status: pending
     ├─ Owner: Person 1
     ├─ Dependencies: BACK-008
     ├─ Acceptance Criteria:
     │  - Test: 2 yes + 1 no → majority yes result
     │  - Test: tie → result = "TIE, user decides"
     │  - Test: agent votes twice → second vote rejected
     └─ Notes: Document input/output pairs in test comments

     TEST-005: Frontend Component Tests (P1)
     ├─ Status: pending
     ├─ Owner: Person 2
     ├─ Dependencies: FRONT-005
     ├─ Acceptance Criteria:
     │  - AgentCard renders speaking state with waveform
     │  - AgentCard renders away state with correct text
     │  - RaiseHandBadge appears on hand_raised event
     │  - VoteOverlay renders all vote options
     └─ Notes: Use /webapp-testing skill

     TEST-006: End-to-End Demo Scenario (P0)
     ├─ Status: pending
     ├─ Owner: Both
     ├─ Dependencies: all P0 tasks complete
     ├─ Acceptance Criteria:
     │  - Run full demo scenario (manual test):
     │    1. Create meeting with agenda
     │    2. Start voice → CTO responds to tech question
     │    3. CFO raises hand → grant turn → CFO speaks
     │    4. Drop PDF → agent comments
     │    5. End meeting → transcript saved
     │  - Each step works without errors
     │  - Deployed URL works (not just localhost)
     └─ Notes: Rehearse demo 2x before submission

     ---
     PART 5 — Decision Docs

     DEC-001: Agent Communication Pattern

     Options:
     - A) LLM routing via transfer_to_agent() — orchestrator LLM decides who speaks
     - B) Explicit AgentTool invocation — orchestrator calls agent like a function

     Decision: Option A — LLM routing. More natural for voice; orchestrator can decide based on conversation context. AgentTool reserved for structured tasks
     (voting, homework assignment).

     Trade-off: Less deterministic, but more natural conversation flow.

     ---
     DEC-002: "Raise Hand" Detection Method

     Options:
     - A) Confidence score threshold from model
     - B) Explicit [RAISE_HAND] marker in agent instruction output

     Decision: Option B — explicit marker. Gemini Live doesn't expose confidence scores. Instruct agents to include [RAISE_HAND: reason] in their internal
     reasoning when they want to speak. after_model_callback parses this.

     Trade-off: Relies on instruction-following. Mitigation: test with all 3 agents pre-launch.

     ---
     DEC-003: Audio Transport from Browser

     Options:
     - A) MediaRecorder → WebM chunks → server decodes
     - B) AudioWorklet → raw PCM → base64 JSON → server

     Decision: Option B for MVP. Use a single deterministic PCM pipeline end-to-end to avoid codec mismatch and reduce debug risk under hackathon time limits.

     Trade-off: Option B requires slightly more frontend work but avoids transcoding errors and provides lower end-to-end latency.

     ---
     DEC-004: Multi-Agent Voice — One Session or Multiple

     Options:
     - A) One Gemini Live session, orchestrator routes
     - B) Separate Live session per agent, mix audio streams

     Decision: Option A — one session. ADK routes between sub-agents within a single runner. Multiple sessions would require audio mixing which is out of
     scope.

     Trade-off: One voice at a time (natural for meeting). Agents don't literally talk over each other.

     ---
     DEC-005: ADK Built-In Tool Compatibility Strategy

     Context:
     Some ADK Gemini built-in tool combinations may be constrained depending on SDK/runtime versions.

     Decision:
     Use tool-specialist delegation for reliability:
     - `search_specialist_agent` owns `google_search`
     - `compute_specialist_agent` owns `code_executor`
     - board-member agents call specialists through orchestrator/tool routing

     Trade-off:
     Slightly more orchestration complexity, but avoids runtime failures from unsupported tool combinations.

     ---
     DEC-006: Cloud Run WebSocket Session Robustness

     Context:
     In-memory session/event buses can break on reconnect if traffic lands on a different Cloud Run instance.

     Decision:
     - Enable Cloud Run session affinity for demo stability
     - Keep session metadata minimal and persisted in Firestore
     - Treat in-memory queues as ephemeral transport only

     Trade-off:
     Session affinity improves demo reliability but is not a complete distributed-state solution for production scale.

     ---
     PART 6 — Progress Tracking

     Create progress.txt in project root (append-only):

     === Session Template ===
     ### Session N — YYYY-MM-DD HH:MM
     Completed: [task IDs]
     Tech notes: [decisions made, surprises found]
     Tests passing: [count]
     Next: [task IDs]
     ========================

     ---
     PART 7 — 12-Hour Timeline

     ┌───────────┬───────────────────────────────────────────────────────────┬──────────────────────────────────────────────┐
     │   Hour    │                    Person 1 (Backend)                     │             Person 2 (Frontend)              │
     ├───────────┼───────────────────────────────────────────────────────────┼──────────────────────────────────────────────┤
     │ Pre-clock │ INFRA-001 + GCP init + install skills                     │ Install skills + React scaffold FRONT-001    │
     ├───────────┼───────────────────────────────────────────────────────────┼──────────────────────────────────────────────┤
     │ H1-2      │ BACK-001, BACK-002, BACK-003                              │ FRONT-002, FRONT-003, FRONT-004              │
     ├───────────┼───────────────────────────────────────────────────────────┼──────────────────────────────────────────────┤
     │ H3-4      │ BACK-004, BACK-005 (3 agents)                             │ FRONT-005, FRONT-006 (agent cards + avatars) │
     ├───────────┼───────────────────────────────────────────────────────────┼──────────────────────────────────────────────┤
     │ H4-5      │ BACK-006, BACK-007 (callbacks)                            │ FRONT-007, FRONT-016 (voice + audio player)  │
     ├───────────┼───────────────────────────────────────────────────────────┼──────────────────────────────────────────────┤
     │ H5-6      │ BACK-008 (raise hand + vote tools), BACK-009 (doc upload) │ FRONT-008, FRONT-009, FRONT-010              │
     ├───────────┼───────────────────────────────────────────────────────────┼──────────────────────────────────────────────┤
     │ H6-7      │ BACK-010, BACK-011, BACK-012 (meetings CRUD + session)    │ FRONT-012, FRONT-014 (agenda bar + sidebar)  │
     ├───────────┼───────────────────────────────────────────────────────────┼──────────────────────────────────────────────┤
     │ H7-8      │ Integration: end-to-end voice test (TEST-001, TEST-002)   │ FRONT-011 (vote overlay), TEST-005           │
     ├───────────┼───────────────────────────────────────────────────────────┼──────────────────────────────────────────────┤
     │ H8-9      │ BACK-013, BACK-014 (homework loop) if ahead               │ FRONT-013 (homework panel) if ahead          │
     ├───────────┼───────────────────────────────────────────────────────────┼──────────────────────────────────────────────┤
     │ H9-10     │ BACK-016 (Docker + Cloud Run deploy)                      │ Polish: animations, fonts, responsive        │
     ├───────────┼───────────────────────────────────────────────────────────┼──────────────────────────────────────────────┤
     │ H10-11    │ TEST-006: full demo rehearsal                             │ TEST-006: full demo rehearsal                │
     ├───────────┼───────────────────────────────────────────────────────────┼──────────────────────────────────────────────┤
     │ H11-12    │ README.md + demo video                                    │ Demo video recording + submission            │
     └───────────┴───────────────────────────────────────────────────────────┴──────────────────────────────────────────────┘

     ---
     MVP Checklist (Must all be green before submission)

     - Voice: speak → correct board member responds (distinct voice)
     - Barge-in: interrupt mid-response naturally
     - Raise hand: agent shows ✋ visually + user can grant turn by voice
     - PDF drop: agent comments on document content
     - Group chat: real-time transcript visible in right panel
     - Deployed: working Cloud Run URL (not localhost)
     - Beautiful: dark war room UI, animated agent cards

     Stretch Goals (in priority order)

     - Voting UI (BACK-008 + FRONT-011)
     - Homework loop (BACK-013 + FRONT-013)
     - Custom persona builder (BACK-015 + FRONT-015)
     - Persistent meeting rooms (Firestore)
     - Maya Patel (4th board member)

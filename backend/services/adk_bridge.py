"""
ADK-based bridge to Gemini Live API — MULTI-VOICE architecture.

Architecture:
  - Each agent gets its OWN Gemini Live session with a UNIQUE voice.
  - User audio goes to the "primary listener" (Director/moderator by default).
  - After the primary responds, other agents are prompted via TEXT to contribute.
  - Each agent responds with audio in their own distinct voice.
  - STRICT turn-taking: only ONE agent speaks at a time.
  - When the user speaks, ALL agents immediately stop and listen.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import re
import time
import traceback
import uuid
from typing import Any, Callable, Awaitable

from google.adk.agents import Agent
from google.adk.agents.live_request_queue import LiveRequestQueue
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import google_search
from google.genai import types

from backend.core.config import settings
from backend.models.agents import AgentDefinition, get_agent
from backend.models.events import (
    AgentInfo,
    AgentStateMsg,
    AudioOutMsg,
    SessionErrorMsg,
    SessionReadyMsg,
    TranscriptAddMsg,
    TranscriptEntry,
    VoteItem,
    VoteProposedMsg,
)

logger = logging.getLogger(__name__)

# ── Singleton ADK infra ─────────────────────────────────────────────────────

_session_service = InMemorySessionService()
_APP_NAME = "quorum"

SendFn = Callable[[dict[str, Any]], Awaitable[None]]


# ── Per-agent live session ──────────────────────────────────────────────────

class AgentLiveSession:
    """A single agent's persistent Gemini Live session with its own voice."""

    def __init__(
        self,
        agent_def: AgentDefinition,
        agenda: str,
        other_agent_names: list[str],
        parent_session_id: str,
    ):
        self.agent_def = agent_def
        self.agent_id = agent_def.id
        self.agent_name = agent_def.name
        self.voice = agent_def.voice
        self.info = AgentInfo(
            id=agent_def.id,
            name=agent_def.name,
            role=agent_def.role,  # type: ignore[arg-type]
            avatar=agent_def.avatar_url,
        )
        self._parent_id = parent_session_id
        self._user_id = f"user-{parent_session_id}-{agent_def.id}"

        # Build this agent's individual system prompt
        system_prompt = agent_def.build_system_prompt(
            agenda=agenda,
            other_agent_names=other_agent_names,
        )

        # ADK components
        self._adk_agent = Agent(
            name=f"quorum_{agent_def.name.lower().replace(' ', '_')}",
            model=settings.live_model_id,
            instruction=system_prompt,
            tools=[google_search],
        )
        self._runner = Runner(
            app_name=_APP_NAME,
            agent=self._adk_agent,
            session_service=_session_service,
        )
        self._queue: LiveRequestQueue | None = None
        self._task: asyncio.Task | None = None
        self._active = False
        self._adk_session_id: str | None = None

        # Transcript accumulation
        self._accumulated_transcript = ""

        # Gate: is this agent allowed to send audio to the client right now?
        self.audio_gate_open = False

    def _make_run_config(self) -> RunConfig:
        """Create RunConfig with this agent's unique voice."""
        return RunConfig(
            streaming_mode=StreamingMode.BIDI,
            response_modalities=["AUDIO"],
            output_audio_transcription=types.AudioTranscriptionConfig(),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=self.voice
                    )
                )
            ),
        )

    async def start(self, on_audio: Callable, on_transcript: Callable, on_turn_complete: Callable, on_error: Callable, on_input_transcript: Callable) -> None:
        """Initialize the ADK session and start the event loop."""
        self._on_audio = on_audio
        self._on_transcript = on_transcript
        self._on_turn_complete = on_turn_complete
        self._on_error = on_error
        self._on_input_transcript = on_input_transcript

        session = await _session_service.create_session(
            app_name=_APP_NAME,
            user_id=self._user_id,
        )
        self._adk_session_id = session.id
        self._queue = LiveRequestQueue()
        self._active = True

        self._task = asyncio.create_task(
            self._event_loop(session.id, self._make_run_config()),
            name=f"agent-{self.agent_name}-{self._parent_id}",
        )
        logger.info(
            "[AGENT:%s] Session started (voice=%s, adk_session=%s)",
            self.agent_name, self.voice, session.id,
        )

    async def _event_loop(self, adk_session_id: str, run_config: RunConfig) -> None:
        """Process events from this agent's run_live() stream."""
        try:
            async for event in self._runner.run_live(
                user_id=self._user_id,
                session_id=adk_session_id,
                live_request_queue=self._queue,
                run_config=run_config,
            ):
                if not self._active:
                    break

                # ── Audio output ─────────────────────────────────────
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.inline_data and part.inline_data.data:
                            if self.audio_gate_open:
                                audio_b64 = base64.b64encode(
                                    part.inline_data.data
                                ).decode("ascii")
                                await self._on_audio(self.agent_id, audio_b64)
                            # else: audio dropped — not this agent's turn

                        if part.text and not event.partial:
                            if self.audio_gate_open:
                                await self._on_transcript(
                                    self.agent_id, self.agent_name, self.info.role, part.text
                                )

                # ── Output transcription ─────────────────────────────
                if event.output_transcription and event.output_transcription.text:
                    text = event.output_transcription.text
                    if event.output_transcription.finished:
                        final_text = text if text else self._accumulated_transcript
                        if final_text.strip() and self.audio_gate_open:
                            await self._on_transcript(
                                self.agent_id, self.agent_name, self.info.role,
                                final_text,
                            )
                        self._accumulated_transcript = ""
                    else:
                        self._accumulated_transcript = text

                # ── Input transcription ──────────────────────────────
                if event.input_transcription and event.input_transcription.text:
                    if event.input_transcription.finished:
                        await self._on_input_transcript(event.input_transcription.text)

                # ── Turn complete ────────────────────────────────────
                if event.turn_complete:
                    logger.info("[AGENT:%s] turn_complete event", self.agent_name)
                    await self._on_turn_complete(self.agent_id)

                # ── Interrupted ──────────────────────────────────────
                if event.interrupted:
                    logger.info("[AGENT:%s] interrupted event", self.agent_name)
                    await self._on_turn_complete(self.agent_id)

                # ── Error ────────────────────────────────────────────
                if event.error_message:
                    logger.error("[AGENT:%s] ADK error: %s", self.agent_name, event.error_message)
                    await self._on_error(self.agent_id, event.error_message)

        except asyncio.CancelledError:
            logger.info("[AGENT:%s] event loop cancelled", self.agent_name)
        except Exception as e:
            tb = traceback.format_exc()
            logger.error("[AGENT:%s] event loop error: %s\n%s", self.agent_name, e, tb)
            await self._on_error(self.agent_id, str(e))
        finally:
            self._active = False

    def send_audio(self, audio_bytes: bytes) -> None:
        """Send raw PCM16 audio bytes to this agent."""
        if self._queue and self._active:
            blob = types.Blob(data=audio_bytes, mime_type="audio/pcm;rate=16000")
            self._queue.send_realtime(blob)

    def send_text(self, text: str) -> None:
        """Send a text message to this agent."""
        if self._queue and self._active:
            logger.debug("[AGENT:%s] Sending text (%d chars)", self.agent_name, len(text))
            content = types.Content(
                parts=[types.Part(text=text)],
                role="user",
            )
            self._queue.send_content(content)

    def send_activity_start(self) -> None:
        if self._queue and self._active:
            self._queue.send_activity_start()

    def send_activity_end(self) -> None:
        if self._queue and self._active:
            self._queue.send_activity_end()

    async def stop(self) -> None:
        """Shut down this agent's session."""
        self._active = False
        self.audio_gate_open = False
        if self._queue:
            self._queue.close()
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[AGENT:%s] session stopped", self.agent_name)


# ── Multi-agent orchestrator ────────────────────────────────────────────────

class MultiAgentSession:
    """Manages multiple agent Live sessions with STRICT sequential turn-taking.

    Key behaviors:
      1. Only ONE agent speaks at a time (audio gate system).
      2. When the user speaks, ALL agents immediately stop and listen.
      3. After user finishes → primary agent responds → then each other agent
         gets a turn in sequence, with FULL conversation context.
      4. Everything is heavily logged for debugging.
    """

    def __init__(
        self,
        session_id: str,
        agent_ids: list[str],
        agenda: str,
        send_fn: SendFn,
    ):
        self.session_id = session_id
        self.agenda = agenda
        self._send = send_fn
        self._agent_ids = agent_ids

        # Agent sessions (ordered)
        self._agent_sessions: dict[str, AgentLiveSession] = {}
        self._agent_order: list[str] = []  # agent IDs in speaking order
        self._primary_agent_id: str | None = None  # receives user audio

        # Turn management — STRICT: only one speaker at a time
        self._current_speaker: str | None = None
        self._turn_complete_event = asyncio.Event()
        self._orchestration_lock = asyncio.Lock()  # prevents overlapping orchestration rounds
        self._user_is_speaking = False  # when True, cancel all agent output
        self._orchestration_task: asyncio.Task | None = None  # current followup task

        # Shared conversation transcript for context
        self._conversation_history: list[str] = []  # "Name: text" lines
        self._last_user_text: str = ""  # last transcribed user speech
        self._transcript_counter = 0
        self._vote_counter = 0
        self._active = False
        self._audio_chunk_count = 0  # for logging

    async def start(self) -> None:
        """Initialize all agent sessions and notify frontend."""
        logger.info(
            "═══════════════════════════════════════════════════════════════\n"
            "  [SESSION:%s] STARTING with agents %s\n"
            "═══════════════════════════════════════════════════════════════",
            self.session_id, self._agent_ids,
        )

        # Resolve agent definitions
        agent_defs: list[AgentDefinition] = []
        for aid in self._agent_ids:
            agent_def = get_agent(aid)
            if agent_def:
                agent_defs.append(agent_def)
                logger.info("[SESSION:%s] Agent resolved: %s (%s, voice=%s)",
                            self.session_id, agent_def.name, agent_def.role, agent_def.voice)
            else:
                logger.warning("[SESSION:%s] Agent %s NOT FOUND, skipping", self.session_id, aid)

        if not agent_defs:
            await self._send(
                SessionErrorMsg(message="No valid agents selected").model_dump()
            )
            return

        # Determine speaking order: chairperson first, then others
        chairpersons = [a for a in agent_defs if a.role == "chairperson"]
        non_chairpersons = [a for a in agent_defs if a.role != "chairperson"]
        ordered = chairpersons + non_chairpersons

        all_names = [a.name for a in ordered]
        logger.info("[SESSION:%s] Speaking order: %s", self.session_id, [a.name for a in ordered])

        # Create individual agent sessions
        for agent_def in ordered:
            other_names = [n for n in all_names if n != agent_def.name]
            agent_session = AgentLiveSession(
                agent_def=agent_def,
                agenda=self.agenda,
                other_agent_names=other_names,
                parent_session_id=self.session_id,
            )
            self._agent_sessions[agent_def.id] = agent_session
            self._agent_order.append(agent_def.id)

        # Primary listener = first agent (usually Director/chairperson)
        self._primary_agent_id = self._agent_order[0]
        self._active = True
        logger.info("[SESSION:%s] Primary listener: %s",
                    self.session_id, self._agent_sessions[self._primary_agent_id].agent_name)

        # Build agents list for frontend
        agents_info = [s.info for s in self._agent_sessions.values()]

        # Send session.ready
        await self._send(SessionReadyMsg(agents=agents_info).model_dump())
        logger.info("[SESSION:%s] Sent session.ready to frontend", self.session_id)

        # Start ALL agent live sessions concurrently
        start_tasks = []
        for agent_session in self._agent_sessions.values():
            start_tasks.append(
                agent_session.start(
                    on_audio=self._handle_agent_audio,
                    on_transcript=self._handle_agent_transcript,
                    on_turn_complete=self._handle_turn_complete,
                    on_error=self._handle_agent_error,
                    on_input_transcript=self._handle_input_transcript,
                )
            )
        await asyncio.gather(*start_tasks)
        logger.info("[SESSION:%s] ✓ All %d agent Gemini sessions connected",
                    self.session_id, len(self._agent_sessions))

    # ── User interruption: STOP ALL AGENTS ──────────────────────────────────

    async def _interrupt_all_agents(self) -> None:
        """When user starts speaking, immediately stop all agent output."""
        logger.info("[SESSION:%s] ▶▶▶ USER INTERRUPTION — stopping all agents", self.session_id)
        self._user_is_speaking = True

        # Cancel any ongoing orchestration
        if self._orchestration_task and not self._orchestration_task.done():
            logger.info("[SESSION:%s] Cancelling ongoing orchestration", self.session_id)
            self._orchestration_task.cancel()
            try:
                await self._orchestration_task
            except (asyncio.CancelledError, Exception):
                pass
            self._orchestration_task = None

        # Close all audio gates — no agent can send audio to client
        for aid, session in self._agent_sessions.items():
            if session.audio_gate_open:
                session.audio_gate_open = False
                logger.info("[SESSION:%s] Closed audio gate for %s", self.session_id, session.agent_name)

        # Mark all as idle on frontend
        if self._current_speaker:
            await self._send(
                AgentStateMsg(agentId=self._current_speaker, speakingState="idle").model_dump()
            )
            self._current_speaker = None

        # Signal turn complete so any waiting code unblocks
        self._turn_complete_event.set()

    async def _user_done_speaking(self) -> None:
        """User stopped speaking — agents can resume."""
        logger.info("[SESSION:%s] ◀◀◀ USER DONE SPEAKING", self.session_id)
        self._user_is_speaking = False

    # ── Callbacks from individual agent sessions ────────────────────────────

    async def _handle_agent_audio(self, agent_id: str, audio_b64: str) -> None:
        """Forward audio from an agent to the client — ONLY if it's their turn."""
        session = self._agent_sessions.get(agent_id)
        if not session or not session.audio_gate_open:
            return  # not this agent's turn (gate system handles everything)

        # Update speaking state if needed
        if self._current_speaker != agent_id:
            await self._set_speaker(agent_id)

        self._audio_chunk_count += 1
        if self._audio_chunk_count % 20 == 1:
            logger.debug("[SESSION:%s] Audio chunk #%d from %s",
                        self.session_id, self._audio_chunk_count, session.agent_name)

        await self._send(AudioOutMsg(data=audio_b64).model_dump())

    async def _handle_agent_transcript(
        self, agent_id: str, agent_name: str, role: str, text: str
    ) -> None:
        """Handle transcript text from an agent."""
        if not text.strip():
            return

        # Clean up: remove self-prefixing that some agents do
        clean_text = re.sub(
            rf"^\s*{re.escape(agent_name)}\s*:\s*",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()
        if not clean_text:
            clean_text = text.strip()

        logger.info("[SESSION:%s] 💬 %s: %s", self.session_id, agent_name, clean_text[:120])

        # Detect vote proposals
        vote_match = re.search(
            r"(?:call a vote|propose a vote|vote on)[:\s]*(.+?)(?:\.|$)",
            clean_text,
            re.IGNORECASE,
        )
        if vote_match:
            self._vote_counter += 1
            vote = VoteItem(
                id=f"vote-{self._vote_counter}",
                motion=vote_match.group(1).strip(),
            )
            await self._send(VoteProposedMsg(vote=vote).model_dump())
            logger.info("[SESSION:%s] Vote proposed: %s", self.session_id, vote.motion)

        # Add to conversation history for cross-agent context
        self._conversation_history.append(f"{agent_name}: {clean_text}")

        # Emit transcript entry
        await self._add_transcript(agent_id, agent_name, role, clean_text)

    async def _handle_turn_complete(self, agent_id: str) -> None:
        """Called when an agent finishes speaking."""
        session = self._agent_sessions.get(agent_id)
        name = session.agent_name if session else agent_id
        logger.info("[SESSION:%s] ✓ Turn complete: %s", self.session_id, name)

        # Close this agent's audio gate
        if session:
            session.audio_gate_open = False

        if self._current_speaker == agent_id:
            await self._send(
                AgentStateMsg(agentId=agent_id, speakingState="idle").model_dump()
            )
            self._current_speaker = None

        # Signal that turn is done — allows orchestration to proceed
        self._turn_complete_event.set()

    async def _handle_agent_error(self, agent_id: str, error: str) -> None:
        """Handle error from an agent session."""
        session = self._agent_sessions.get(agent_id)
        name = session.agent_name if session else agent_id
        logger.error("[SESSION:%s] ❌ Agent %s error: %s", self.session_id, name, error)

        # Don't send "Internal streaming error" to frontend as session.error
        # — it's usually transient and the agent can still work
        if "internal" in error.lower() and "streaming" in error.lower():
            logger.warning("[SESSION:%s] Transient Gemini error for %s, not killing session", self.session_id, name)
            # Signal turn complete so orchestration can continue
            self._turn_complete_event.set()
            return

        await self._send(
            SessionErrorMsg(message=f"Agent error ({name}): {error}").model_dump()
        )

    async def _handle_input_transcript(self, text: str) -> None:
        """Handle user's speech transcription (from primary listener).
        
        NOTE: We do NOT start orchestration here because the user is still
        talking (audio chunks still flowing). Orchestration starts in
        send_activity_end() when the user actually releases the mic.
        """
        logger.info("[SESSION:%s] 🎤 USER SAID: %s", self.session_id, text)
        self._last_user_text = text
        self._conversation_history.append(f"User: {text}")
        await self._add_transcript("user", "You", "chairperson", text)

    # ── Turn orchestration ──────────────────────────────────────────────────

    async def _start_orchestration(self, user_text: str) -> None:
        """Cancel any existing orchestration and start a new round."""
        if self._orchestration_task and not self._orchestration_task.done():
            logger.info("[SESSION:%s] Cancelling previous orchestration", self.session_id)
            self._orchestration_task.cancel()
            try:
                await self._orchestration_task
            except (asyncio.CancelledError, Exception):
                pass

        self._orchestration_task = asyncio.create_task(
            self._orchestrate_round(user_text),
            name=f"orchestrate-{self.session_id}",
        )

    async def _orchestrate_round(self, user_text: str) -> None:
        """Full orchestration round: primary responds, then each other agent gets a turn.

        STRICT rules:
          - Only one agent speaks at a time (audio gate)
          - If user interrupts, everything cancels
          - Each agent gets FULL conversation context
        """
        async with self._orchestration_lock:
            if not self._active:
                return

            logger.info(
                "[SESSION:%s] ═══ ORCHESTRATION ROUND START ═══\n"
                "  User said: %s\n"
                "  Conversation history: %d lines",
                self.session_id, user_text[:100], len(self._conversation_history),
            )

            # ── Phase 1: Wait for primary agent to respond ──────────────

            primary = self._agent_sessions.get(self._primary_agent_id)
            if not primary:
                logger.error("[SESSION:%s] Primary agent not found!", self.session_id)
                return

            # Open ONLY primary's audio gate
            self._close_all_gates()
            primary.audio_gate_open = True
            logger.info("[SESSION:%s] 🔊 Opened gate for PRIMARY: %s", self.session_id, primary.agent_name)

            # Wait for primary to finish speaking
            self._turn_complete_event.clear()
            try:
                await asyncio.wait_for(self._turn_complete_event.wait(), timeout=45.0)
                logger.info("[SESSION:%s] Primary %s finished speaking", self.session_id, primary.agent_name)
            except asyncio.TimeoutError:
                logger.warning("[SESSION:%s] ⏰ Primary %s turn TIMEOUT (45s)", self.session_id, primary.agent_name)
            except asyncio.CancelledError:
                logger.info("[SESSION:%s] Orchestration cancelled during primary turn", self.session_id)
                self._close_all_gates()
                return

            if not self._active:
                logger.info("[SESSION:%s] Aborting orchestration (inactive)", self.session_id)
                self._close_all_gates()
                return

            # ── Phase 2: Other agents respond in sequence ───────────────

            for i, agent_id in enumerate(self._agent_order):
                if agent_id == self._primary_agent_id:
                    continue  # skip primary, already spoke

                if not self._active:
                    logger.info("[SESSION:%s] Aborting followup (inactive)", self.session_id)
                    break

                agent_session = self._agent_sessions.get(agent_id)
                if not agent_session:
                    continue

                logger.info("[SESSION:%s] ── Agent %d/%d: %s's turn ──",
                           self.session_id, i + 1, len(self._agent_order) - 1, agent_session.agent_name)

                # Build FULL conversation context
                full_context = "\n".join(self._conversation_history)

                prompt = (
                    f"[FULL CONVERSATION SO FAR]\n{full_context}\n\n"
                    f"───────────────────────────────\n"
                    f"It's now YOUR turn to speak, {agent_session.agent_name}. "
                    f"Respond to the discussion above in character. "
                    f"Keep it concise (2-4 sentences). "
                    f"If you have nothing meaningful to add, just say 'Nothing to add' very briefly."
                )

                # Close all gates, open ONLY this agent's gate
                self._close_all_gates()
                agent_session.audio_gate_open = True
                logger.info("[SESSION:%s] 🔊 Opened gate for %s", self.session_id, agent_session.agent_name)

                # Send the prompt
                agent_session.send_text(prompt)

                # Wait for this agent to finish
                self._turn_complete_event.clear()
                try:
                    await asyncio.wait_for(self._turn_complete_event.wait(), timeout=30.0)
                    logger.info("[SESSION:%s] ✓ %s finished speaking", self.session_id, agent_session.agent_name)
                except asyncio.TimeoutError:
                    logger.warning("[SESSION:%s] ⏰ %s turn TIMEOUT (30s)", self.session_id, agent_session.agent_name)
                except asyncio.CancelledError:
                    logger.info("[SESSION:%s] Orchestration cancelled during %s's turn",
                               self.session_id, agent_session.agent_name)
                    self._close_all_gates()
                    return

                # Small pause between agents so audio doesn't run together
                await asyncio.sleep(0.3)

            self._close_all_gates()
            logger.info("[SESSION:%s] ═══ ORCHESTRATION ROUND COMPLETE ═══", self.session_id)

    def _close_all_gates(self) -> None:
        """Close all agent audio gates so nobody can send audio."""
        for session in self._agent_sessions.values():
            session.audio_gate_open = False

    # ── Speaker state management ────────────────────────────────────────────

    async def _set_speaker(self, agent_id: str) -> None:
        """Update which agent is currently speaking."""
        if self._current_speaker and self._current_speaker != agent_id:
            await self._send(
                AgentStateMsg(
                    agentId=self._current_speaker, speakingState="idle"
                ).model_dump()
            )
        self._current_speaker = agent_id
        session = self._agent_sessions.get(agent_id)
        name = session.agent_name if session else agent_id
        logger.info("[SESSION:%s] 🔈 Now speaking: %s", self.session_id, name)
        await self._send(
            AgentStateMsg(agentId=agent_id, speakingState="speaking").model_dump()
        )

    async def _add_transcript(
        self, agent_id: str, agent_name: str, role: str, text: str
    ) -> None:
        """Send a transcript entry to the frontend."""
        self._transcript_counter += 1
        entry = TranscriptEntry(
            id=str(self._transcript_counter),
            agentId=agent_id,
            agentName=agent_name,
            role=role,  # type: ignore[arg-type]
            text=text,
            timestamp=time.time() * 1000,
        )
        await self._send(TranscriptAddMsg(entry=entry).model_dump())

    # ── Public methods for upstream data ─────────────────────────────────────

    async def send_audio(self, audio_b64: str) -> None:
        """Send audio from user mic to the primary listener agent.

        When user starts sending audio, we INTERRUPT all agents.
        """
        if not self._active or not self._primary_agent_id:
            return

        # If user just started speaking, interrupt everything
        if not self._user_is_speaking:
            await self._interrupt_all_agents()

        audio_bytes = base64.b64decode(audio_b64)

        # Send ONLY to primary listener
        primary = self._agent_sessions.get(self._primary_agent_id)
        if primary:
            primary.send_audio(audio_bytes)

    async def send_text(self, text: str) -> None:
        """Send user text to primary agent + add to transcript."""
        if not self._active:
            return

        logger.info("[SESSION:%s] 📝 User text: %s", self.session_id, text[:100])

        # Interrupt any current agent speech
        await self._interrupt_all_agents()
        self._user_is_speaking = False  # text is instant, not ongoing

        # Add to transcript
        self._conversation_history.append(f"User: {text}")
        await self._add_transcript("user", "You", "chairperson", text)

        # Open primary's gate and send to primary agent
        primary = self._agent_sessions.get(self._primary_agent_id)
        if primary:
            primary.audio_gate_open = True
            primary.send_text(text)

        # Schedule full orchestration round
        await self._start_orchestration(text)

    def send_activity_start(self) -> None:
        """Signal that user started speaking — need to interrupt agents."""
        logger.info("[SESSION:%s] 🎙️ User mic ACTIVATED", self.session_id)
        # The actual interruption happens in send_audio() on first chunk
        # send_activity_start to primary so it knows to listen
        primary = self._agent_sessions.get(self._primary_agent_id)
        if primary:
            primary.send_activity_start()

    def send_activity_end(self) -> None:
        """Signal that user stopped speaking — NOW start orchestration."""
        logger.info("[SESSION:%s] 🎙️ User mic DEACTIVATED", self.session_id)
        self._user_is_speaking = False

        # Signal activity end to primary
        primary = self._agent_sessions.get(self._primary_agent_id)
        if primary:
            primary.send_activity_end()
            # Open primary's gate so it can respond
            primary.audio_gate_open = True
            logger.info("[SESSION:%s] 🔊 Opened gate for primary %s after user stopped",
                       self.session_id, primary.agent_name)

        # NOW start orchestration — user is done talking
        user_text = getattr(self, '_last_user_text', '') or 'User finished speaking'
        asyncio.create_task(self._start_orchestration(user_text))

    async def send_text_to_agent(self, agent_id: str, text: str) -> None:
        """Send text directly to a specific agent."""
        agent_session = self._agent_sessions.get(agent_id)
        if agent_session:
            logger.info("[SESSION:%s] Direct text to %s: %s", self.session_id, agent_session.agent_name, text[:80])
            agent_session.send_text(text)

    async def stop(self) -> None:
        """Shut down all agent sessions."""
        logger.info("[SESSION:%s] ═══ STOPPING SESSION ═══", self.session_id)
        self._active = False
        self._close_all_gates()

        if self._orchestration_task and not self._orchestration_task.done():
            self._orchestration_task.cancel()

        stop_tasks = [s.stop() for s in self._agent_sessions.values()]
        await asyncio.gather(*stop_tasks, return_exceptions=True)
        logger.info("[SESSION:%s] ═══ SESSION STOPPED ═══", self.session_id)

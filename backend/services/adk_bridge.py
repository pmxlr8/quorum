"""
ADK-based bridge to Gemini Live API — MULTI-VOICE architecture.

Architecture:
  - Each agent gets its OWN Gemini Live session with a UNIQUE voice.
  - User audio goes to the "primary listener" (Director/moderator by default).
  - After the primary responds, other agents are prompted via TEXT to contribute.
  - Each agent responds with audio in their own distinct voice.
  - Turn-taking is managed via an asyncio queue.
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
            "AgentLiveSession started: %s (voice=%s, adk_session=%s)",
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
                            audio_b64 = base64.b64encode(
                                part.inline_data.data
                            ).decode("ascii")
                            await self._on_audio(self.agent_id, audio_b64)

                        if part.text and not event.partial:
                            await self._on_transcript(
                                self.agent_id, self.agent_name, self.info.role, part.text
                            )

                # ── Output transcription ─────────────────────────────
                if event.output_transcription and event.output_transcription.text:
                    text = event.output_transcription.text
                    if event.output_transcription.finished:
                        final_text = text if text else self._accumulated_transcript
                        if final_text.strip():
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
                    await self._on_turn_complete(self.agent_id)

                # ── Interrupted ──────────────────────────────────────
                if event.interrupted:
                    await self._on_turn_complete(self.agent_id)

                # ── Error ────────────────────────────────────────────
                if event.error_message:
                    logger.error("Agent %s ADK error: %s", self.agent_name, event.error_message)
                    await self._on_error(self.agent_id, event.error_message)

        except asyncio.CancelledError:
            logger.info("Agent %s event loop cancelled", self.agent_name)
        except Exception as e:
            tb = traceback.format_exc()
            logger.error("Agent %s event loop error: %s\n%s", self.agent_name, e, tb)
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
        if self._queue:
            self._queue.close()
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Agent %s session stopped", self.agent_name)


# ── Multi-agent orchestrator ────────────────────────────────────────────────

class MultiAgentSession:
    """Manages multiple agent Live sessions with turn-taking.

    Architecture:
      - Each agent has its own Gemini Live session with a unique voice.
      - User audio goes to the "primary listener" (first agent / Director).
      - After primary responds, other agents are prompted to contribute.
      - Audio is queued so only one agent plays at a time.
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

        # Turn management
        self._current_speaker: str | None = None
        self._turn_complete_event = asyncio.Event()
        self._speaking_lock = asyncio.Lock()

        # Shared conversation transcript for context
        self._conversation_history: list[str] = []  # "Name: text" lines
        self._transcript_counter = 0
        self._vote_counter = 0
        self._active = False
        self._input_transcript_sent = False  # avoid duplicate user transcript

    async def start(self) -> None:
        """Initialize all agent sessions and notify frontend."""
        logger.info(
            "Starting MultiAgentSession %s with agents %s",
            self.session_id, self._agent_ids,
        )

        # Resolve agent definitions
        agent_defs: list[AgentDefinition] = []
        for aid in self._agent_ids:
            agent_def = get_agent(aid)
            if agent_def:
                agent_defs.append(agent_def)
            else:
                logger.warning("Agent %s not found, skipping", aid)

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

        # Build agents list for frontend
        agents_info = [s.info for s in self._agent_sessions.values()]

        # Send session.ready
        await self._send(SessionReadyMsg(agents=agents_info).model_dump())

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
        logger.info("All %d agent sessions started", len(self._agent_sessions))

    # ── Callbacks from individual agent sessions ────────────────────────────

    async def _handle_agent_audio(self, agent_id: str, audio_b64: str) -> None:
        """Forward audio from an agent to the client."""
        # Update speaking state if needed
        if self._current_speaker != agent_id:
            await self._set_speaker(agent_id)

        await self._send(AudioOutMsg(data=audio_b64).model_dump())

    async def _handle_agent_transcript(
        self, agent_id: str, agent_name: str, role: str, text: str
    ) -> None:
        """Handle transcript text from an agent."""
        if not text.strip():
            return

        # Clean up: remove self-prefixing that some agents do despite instructions
        clean_text = re.sub(
            rf"^\s*{re.escape(agent_name)}\s*:\s*",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()
        if not clean_text:
            clean_text = text.strip()

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

        # Add to conversation history for cross-agent context
        self._conversation_history.append(f"{agent_name}: {clean_text}")

        # Emit transcript entry
        await self._add_transcript(agent_id, agent_name, role, clean_text)

    async def _handle_turn_complete(self, agent_id: str) -> None:
        """Called when an agent finishes speaking."""
        logger.info("Turn complete for agent %s", agent_id)
        if self._current_speaker == agent_id:
            await self._send(
                AgentStateMsg(agentId=agent_id, speakingState="idle").model_dump()
            )
            self._current_speaker = None

        # Signal that turn is done — allows orchestration to proceed
        self._turn_complete_event.set()

    async def _handle_agent_error(self, agent_id: str, error: str) -> None:
        """Handle error from an agent session."""
        logger.error("Agent %s error: %s", agent_id, error)
        await self._send(
            SessionErrorMsg(message=f"Agent error ({agent_id}): {error}").model_dump()
        )

    async def _handle_input_transcript(self, text: str) -> None:
        """Handle user's speech transcription (from primary listener)."""
        if not self._input_transcript_sent:
            self._input_transcript_sent = True
            # Reset after a short delay to allow next input
            asyncio.get_event_loop().call_later(2.0, self._reset_input_flag)

            self._conversation_history.append(f"User: {text}")
            await self._add_transcript("user", "You", "chairperson", text)

            # After primary agent responds, prompt other agents
            # Give primary a moment to start responding, then schedule follow-ups
            asyncio.create_task(self._orchestrate_followup(text))

    def _reset_input_flag(self):
        self._input_transcript_sent = False

    # ── Turn orchestration ──────────────────────────────────────────────────

    async def _orchestrate_followup(self, user_text: str) -> None:
        """After the primary agent responds, prompt other agents to contribute."""
        if not self._active:
            return

        # Wait for primary agent to finish their turn
        self._turn_complete_event.clear()
        try:
            await asyncio.wait_for(self._turn_complete_event.wait(), timeout=30.0)
        except asyncio.TimeoutError:
            logger.warning("Primary agent turn timeout, proceeding with follow-ups")

        if not self._active:
            return

        # Build conversation context for other agents
        context = "\n".join(self._conversation_history[-10:])

        # Prompt each non-primary agent in order
        for agent_id in self._agent_order[1:]:
            if not self._active:
                break

            agent_session = self._agent_sessions.get(agent_id)
            if not agent_session:
                continue

            # Send conversation context + prompt to contribute
            prompt = (
                f"[Conversation update]\n{context}\n\n"
                f"It's your turn to contribute to the discussion. "
                f"Respond in character. If you have nothing to add, just say 'I'll pass on this one' very briefly."
            )
            agent_session.send_text(prompt)

            # Wait for this agent to finish
            self._turn_complete_event.clear()
            try:
                await asyncio.wait_for(self._turn_complete_event.wait(), timeout=20.0)
            except asyncio.TimeoutError:
                logger.warning("Agent %s turn timeout", agent_id)

        logger.info("All agents have had their turn")

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
        """Send audio from user mic to the primary listener agent."""
        if not self._active or not self._primary_agent_id:
            return
        audio_bytes = base64.b64decode(audio_b64)

        # Send to primary listener
        primary = self._agent_sessions.get(self._primary_agent_id)
        if primary:
            primary.send_audio(audio_bytes)

    async def send_text(self, text: str) -> None:
        """Send user text to primary agent + add to transcript."""
        if not self._active:
            return

        # Add to transcript
        self._conversation_history.append(f"User: {text}")
        await self._add_transcript("user", "You", "chairperson", text)

        # Send to primary agent
        primary = self._agent_sessions.get(self._primary_agent_id)
        if primary:
            primary.send_text(text)

        # Schedule follow-ups from other agents
        asyncio.create_task(self._orchestrate_followup(text))

    def send_activity_start(self) -> None:
        """Signal all agents that user started speaking."""
        for agent_session in self._agent_sessions.values():
            agent_session.send_activity_start()

    def send_activity_end(self) -> None:
        """Signal all agents that user stopped speaking."""
        for agent_session in self._agent_sessions.values():
            agent_session.send_activity_end()

    async def send_text_to_agent(self, agent_id: str, text: str) -> None:
        """Send text directly to a specific agent."""
        agent_session = self._agent_sessions.get(agent_id)
        if agent_session:
            agent_session.send_text(text)

    async def stop(self) -> None:
        """Shut down all agent sessions."""
        logger.info("Stopping MultiAgentSession %s", self.session_id)
        self._active = False
        stop_tasks = [s.stop() for s in self._agent_sessions.values()]
        await asyncio.gather(*stop_tasks, return_exceptions=True)
        logger.info("MultiAgentSession %s stopped", self.session_id)

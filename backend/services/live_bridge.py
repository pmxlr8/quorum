from __future__ import annotations

import asyncio
import base64
import logging
import re
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from google import genai
from google.genai import types

from backend.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class LiveSessionRuntime:
    stack: AsyncExitStack
    session: Any
    broadcast: Callable[[dict], Awaitable[None]] | None = None
    reader_task: asyncio.Task[None] | None = None
    transcript_buffer: str = ""


class LiveBridge:
    """Gemini Live bridge with per-websocket session lifecycle.

    Uses a background reader loop per session so audio/text sends are fire-and-forget.
    Responses stream back via the broadcast callback.

    Fallback behavior:
    - If no client auth mode is configured, emits local stub events so tests and local UI wiring keep working.
    """

    def __init__(self) -> None:
        self.model_id = settings.live_model_id
        self.client = self._build_client()
        self._sessions: dict[str, LiveSessionRuntime] = {}
        self._lock = asyncio.Lock()

    def _build_client(self) -> genai.Client | None:
        if settings.google_genai_use_vertexai:
            project = settings.google_cloud_project or settings.gcp_project_id
            location = settings.google_cloud_location or settings.gcp_region
            if not project:
                return None
            return genai.Client(vertexai=True, project=project, location=location)

        if settings.google_api_key:
            return genai.Client(api_key=settings.google_api_key)

        return None

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    async def start_session(
        self,
        session_id: str,
        broadcast: Callable[[dict], Awaitable[None]] | None = None,
    ) -> None:
        if self.client is None:
            return

        async with self._lock:
            if session_id in self._sessions:
                return

            stack = AsyncExitStack()
            session = await stack.enter_async_context(
                self.client.aio.live.connect(
                    model=self.model_id,
                    config={
                        'response_modalities': ['AUDIO'],
                        'output_audio_transcription': {},
                    },
                )
            )
            runtime = LiveSessionRuntime(stack=stack, session=session, broadcast=broadcast)
            if broadcast is not None:
                runtime.reader_task = asyncio.create_task(
                    self._read_loop(session_id, runtime)
                )
            self._sessions[session_id] = runtime

    async def close_session(self, session_id: str) -> None:
        async with self._lock:
            runtime = self._sessions.pop(session_id, None)
        if runtime is not None:
            if runtime.reader_task is not None:
                runtime.reader_task.cancel()
                try:
                    await runtime.reader_task
                except (asyncio.CancelledError, Exception):
                    pass
            await runtime.stack.aclose()

    # ------------------------------------------------------------------
    # Background reader — continuously reads Live session stream
    # ------------------------------------------------------------------

    async def _read_loop(self, session_id: str, runtime: LiveSessionRuntime) -> None:
        """Continuously read server events and broadcast them.

        Transcript fragments from output_transcription are buffered and flushed
        as a single consolidated message when turn_complete arrives.
        """
        try:
            async for response in runtime.session.receive():
                if session_id not in self._sessions:
                    break
                events = self._parse_response(response)
                for event in events:
                    if runtime.broadcast is None:
                        continue

                    if event.get('type') == 'transcript_update' and event.get('_buffered'):
                        # Accumulate transcript fragments instead of broadcasting
                        runtime.transcript_buffer += event['payload']['text']
                        continue

                    if event.get('type') == 'turn_complete':
                        # Flush buffered transcript as one message, then send turn_complete
                        if runtime.transcript_buffer.strip():
                            await runtime.broadcast({
                                'type': 'transcript_update',
                                'payload': {
                                    'speaker': 'assistant',
                                    'text': runtime.transcript_buffer.strip(),
                                    'partial': False,
                                },
                            })
                        runtime.transcript_buffer = ""
                        await runtime.broadcast(event)
                        continue

                    await runtime.broadcast(event)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.exception('read_loop error session=%s', session_id)
            if runtime.broadcast is not None:
                # Flush any buffered transcript before error
                if runtime.transcript_buffer.strip():
                    try:
                        await runtime.broadcast({
                            'type': 'transcript_update',
                            'payload': {
                                'speaker': 'assistant',
                                'text': runtime.transcript_buffer.strip(),
                                'partial': False,
                            },
                        })
                        runtime.transcript_buffer = ""
                    except Exception:
                        pass
                try:
                    await runtime.broadcast(
                        {'type': 'error', 'payload': {'message': f'Live stream error: {exc}'}}
                    )
                except Exception:
                    pass

    def _parse_response(self, response: Any) -> list[dict]:
        """Parse a single Live API server response into WS event dicts."""
        events: list[dict] = []
        server_content = getattr(response, 'server_content', None)
        if server_content is None:
            return events

        # Output transcription (speech-to-text of model audio) — buffered
        output_transcription = getattr(server_content, 'output_transcription', None)
        if output_transcription is not None:
            text = getattr(output_transcription, 'text', None)
            if text:
                events.append(
                    {
                        'type': 'transcript_update',
                        '_buffered': True,
                        'payload': {'speaker': 'assistant', 'text': text, 'partial': False},
                    }
                )

        # Model turn parts (text + audio chunks)
        model_turn = getattr(server_content, 'model_turn', None)
        parts = getattr(model_turn, 'parts', None) if model_turn else None
        if parts:
            for part in parts:
                text = getattr(part, 'text', None)
                if text:
                    events.append(
                        {
                            'type': 'transcript_update',
                            'payload': {'speaker': 'assistant', 'text': text, 'partial': False},
                        }
                    )

                inline_data = getattr(part, 'inline_data', None)
                data = getattr(inline_data, 'data', None) if inline_data else None
                mime = (
                    getattr(inline_data, 'mime_type', 'audio/pcm;rate=24000')
                    if inline_data
                    else None
                )
                if data:
                    events.append(
                        {
                            'type': 'audio_chunk',
                            'payload': {
                                'data': base64.b64encode(data).decode('utf-8'),
                                'mime': mime,
                            },
                        }
                    )

        if getattr(server_content, 'interrupted', False):
            events.append({'type': 'interrupted', 'payload': {}})

        if getattr(server_content, 'turn_complete', False):
            events.append({'type': 'turn_complete', 'payload': {}})

        return events

    # ------------------------------------------------------------------
    # Send helpers — fire-and-forget (responses come via _read_loop)
    # ------------------------------------------------------------------

    async def handle_audio(self, session_id: str, b64_audio: str) -> list[dict]:
        runtime = self._sessions.get(session_id)
        if runtime is None:
            return []  # No spam in stub mode

        try:
            audio_bytes = base64.b64decode(b64_audio)
            await runtime.session.send_realtime_input(
                audio=types.Blob(data=audio_bytes, mime_type='audio/pcm;rate=16000')
            )
            return []  # Response arrives via background reader
        except Exception as exc:
            return [{'type': 'error', 'payload': {'message': f'Live audio error: {exc}'}}]

    async def handle_text(self, session_id: str, text: str) -> list[dict]:
        runtime = self._sessions.get(session_id)
        if runtime is None:
            return self._stub_text_response(text)

        try:
            await runtime.session.send_client_content(
                turns={'role': 'user', 'parts': [{'text': text}]},
                turn_complete=True,
            )
            return []  # Response arrives via background reader
        except Exception as exc:
            return [{'type': 'error', 'payload': {'message': f'Live text error: {exc}'}}]

    # ------------------------------------------------------------------
    # Stub / demo fallback (no Live client configured)
    # ------------------------------------------------------------------

    def _stub_text_response(self, prompt: str) -> list[dict]:
        role_match = re.search(r'You are the (.+?) board member', prompt)
        role = role_match.group(1) if role_match else 'Orchestrator'

        user_match = re.search(r'User request:\s*(.+)$', prompt)
        request = user_match.group(1).strip() if user_match else prompt.strip()

        response = (
            f'{role} demo response.\n'
            f'Decision: Proceed with a scoped pilot tied to "{request}".\n'
            f'Risks: timeline slip, unclear ownership, and integration surprises.\n'
            f'Owner: {role} with weekly checkpoint updates.'
        )
        return [
            {
                'type': 'transcript_update',
                'payload': {'speaker': 'orchestrator', 'text': response, 'partial': False},
            }
        ]


live_bridge = LiveBridge()

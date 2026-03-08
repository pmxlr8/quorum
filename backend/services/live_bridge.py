from __future__ import annotations

import asyncio
import base64
import re
from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import Any

from google import genai
from google.genai import types

from backend.core.config import settings


@dataclass
class LiveSessionRuntime:
    stack: AsyncExitStack
    session: Any


class LiveBridge:
    """Gemini Live bridge with per-websocket session lifecycle.

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

    async def start_session(self, session_id: str) -> None:
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
            self._sessions[session_id] = LiveSessionRuntime(stack=stack, session=session)

    async def close_session(self, session_id: str) -> None:
        async with self._lock:
            runtime = self._sessions.pop(session_id, None)
        if runtime is not None:
            await runtime.stack.aclose()

    async def handle_audio(self, session_id: str, b64_audio: str) -> list[dict]:
        runtime = self._sessions.get(session_id)
        if runtime is None:
            return self._stub_audio_response()

        try:
            audio_bytes = base64.b64decode(b64_audio)
            await runtime.session.send_realtime_input(
                audio=types.Blob(data=audio_bytes, mime_type='audio/pcm;rate=16000')
            )
            return await self._collect_session_events(runtime.session)
        except Exception as exc:
            return [{'type': 'error', 'payload': {'message': f'Live audio error: {exc}'}}]

    async def handle_text(self, session_id: str, text: str) -> list[dict]:
        runtime = self._sessions.get(session_id)
        if runtime is None:
            return self._stub_text_response(text)

        try:
            await runtime.session.send_client_content(turns={'role': 'user', 'parts': [{'text': text}]}, turn_complete=True)
            return await self._collect_session_events(runtime.session)
        except Exception as exc:
            return [{'type': 'error', 'payload': {'message': f'Live text error: {exc}'}}]

    async def _collect_session_events(self, session: Any) -> list[dict]:
        events: list[dict] = []
        turn = session.receive()

        while len(events) < 30:
            try:
                response = await asyncio.wait_for(anext(turn), timeout=0.2)
            except TimeoutError:
                break
            except StopAsyncIteration:
                break

            server_content = getattr(response, 'server_content', None)
            if server_content is None:
                continue

            output_transcription = getattr(server_content, 'output_transcription', None)
            if output_transcription is not None:
                text = getattr(output_transcription, 'text', None)
                if text:
                    events.append(
                        {
                            'type': 'transcript_update',
                            'payload': {'speaker': 'assistant', 'text': text, 'partial': False},
                        }
                    )

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
                    mime = getattr(inline_data, 'mime_type', 'audio/pcm;rate=24000') if inline_data else None
                    if data:
                        events.append(
                            {
                                'type': 'audio_chunk',
                                'payload': {'data': base64.b64encode(data).decode('utf-8'), 'mime': mime},
                            }
                        )

            if getattr(server_content, 'interrupted', False):
                events.append({'type': 'interrupted', 'payload': {}})

            if getattr(server_content, 'turn_complete', False):
                events.append({'type': 'turn_complete', 'payload': {}})
                break

        if not events:
            return [{'type': 'transcript_update', 'payload': {'speaker': 'system', 'text': 'Live session active.', 'partial': False}}]
        return events

    def _stub_audio_response(self) -> list[dict]:
        # In local fallback mode, the browser streams many audio chunks per second.
        # Emitting transcript lines per chunk floods the UI and obscures real events.
        return []

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

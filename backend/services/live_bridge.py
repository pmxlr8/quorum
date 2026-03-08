import asyncio
import base64

from backend.core.config import settings


class LiveBridge:
    """Minimal bridge for BACK-003.

    Current behavior:
    - validates inbound PCM payload (base64)
    - emits transcript placeholder and audio echo event for UI wiring
    - prepared for swap-in with ADK live runner implementation
    """

    def __init__(self) -> None:
        self.model_id = settings.live_model_id

    async def handle_audio(self, b64_audio: str) -> list[dict]:
        _ = base64.b64decode(b64_audio)
        await asyncio.sleep(0)
        return [
            {
                'type': 'transcript_update',
                'payload': {
                    'speaker': 'orchestrator',
                    'text': 'Audio received. Live bridge connected.',
                    'partial': False,
                },
            },
            {
                'type': 'audio_chunk',
                'payload': {
                    'data': b64_audio,
                    'mime': 'audio/pcm;rate=16000',
                },
            },
        ]

    async def handle_text(self, text: str) -> list[dict]:
        await asyncio.sleep(0)
        return [
            {
                'type': 'transcript_update',
                'payload': {
                    'speaker': 'orchestrator',
                    'text': f'Heard: {text}',
                    'partial': False,
                },
            }
        ]


live_bridge = LiveBridge()

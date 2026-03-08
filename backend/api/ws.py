from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.models.events import (
    AudioInEvent,
    GrantSpeakingTurnInEvent,
    TextInEvent,
    TurnCompleteInEvent,
    VoteInEvent,
)
from backend.services.live_bridge import live_bridge
from backend.services.session_manager import session_manager

router = APIRouter()


@router.websocket('/ws/{session_id}')
async def websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    await session_manager.connect(session_id, websocket)
    await session_manager.broadcast(
        session_id,
        {'type': 'meeting_status', 'payload': {'status': 'active'}},
    )
    try:
        while True:
            raw = await websocket.receive_json()
            event_type = raw.get('type')

            if event_type == 'audio':
                event = AudioInEvent.model_validate(raw)
                for out in await live_bridge.handle_audio(event.data):
                    await session_manager.broadcast(session_id, out)
            elif event_type == 'text':
                event = TextInEvent.model_validate(raw)
                for out in await live_bridge.handle_text(event.text):
                    await session_manager.broadcast(session_id, out)
            elif event_type == 'grant_speaking_turn':
                event = GrantSpeakingTurnInEvent.model_validate(raw)
                await session_manager.broadcast(
                    session_id,
                    {
                        'type': 'agent_speaking',
                        'payload': {'agent': event.agent},
                    },
                )
            elif event_type == 'cast_vote':
                event = VoteInEvent.model_validate(raw)
                await session_manager.broadcast(
                    session_id,
                    {
                        'type': 'vote_result',
                        'payload': {'votes': {'user': {'vote': event.vote}}, 'result': 'pending'},
                    },
                )
            elif event_type == 'turn_complete':
                _ = TurnCompleteInEvent.model_validate(raw)
                await session_manager.broadcast(session_id, {'type': 'turn_complete', 'payload': {}})
            else:
                await session_manager.broadcast(
                    session_id,
                    {'type': 'error', 'payload': {'message': f'Unsupported event: {event_type}'}},
                )
    except WebSocketDisconnect:
        await session_manager.disconnect(session_id, websocket)
        await session_manager.broadcast(
            session_id,
            {'type': 'meeting_status', 'payload': {'status': 'ended'}},
        )

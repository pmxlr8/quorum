import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.models.events import (
    AudioInEvent,
    GrantSpeakingTurnInEvent,
    TextInEvent,
    TurnCompleteInEvent,
    VoteInEvent,
)
from backend.services.live_bridge import live_bridge
from backend.services.orchestrator import orchestrator
from backend.services.session_manager import session_manager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket('/ws/{session_id}')
async def websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    logger.info('ws connect session=%s', session_id)
    await session_manager.connect(session_id, websocket)
    orchestrator.start_session(session_id)
    live_session_ready = True
    try:
        await live_bridge.start_session(session_id)
    except Exception as exc:
        live_session_ready = False
        logger.exception('live start failed session=%s err=%s', session_id, exc)
    await session_manager.broadcast(
        session_id,
        {'type': 'meeting_status', 'payload': {'status': 'active'}},
    )
    if live_bridge.client is None or not live_session_ready:
        message = 'Demo mode: Live model auth is not configured. Text replies use local fallback; microphone will not produce real model speech.'
        if live_bridge.client is not None and not live_session_ready:
            message = (
                f'Demo mode: Live session failed to start for model "{live_bridge.model_id}". '
                'Check LIVE_MODEL_ID/project permissions. Text replies use local fallback.'
            )
        await session_manager.broadcast(
            session_id,
            {
                'type': 'transcript_update',
                'payload': {
                    'speaker': 'system',
                    'text': message,
                    'partial': False,
                },
            },
        )
    try:
        while True:
            raw = await websocket.receive_json()
            event_type = raw.get('type')
            logger.info('ws in session=%s type=%s', session_id, event_type)

            if event_type == 'audio':
                event = AudioInEvent.model_validate(raw)
                for out in await live_bridge.handle_audio(session_id, event.data):
                    logger.info('ws out session=%s type=%s', session_id, out.get('type'))
                    await session_manager.broadcast(session_id, out)
            elif event_type == 'text':
                event = TextInEvent.model_validate(raw)
                agent_id, role = orchestrator.route(event.text)
                logger.info('ws route session=%s agent=%s role=%s', session_id, agent_id, role)
                await session_manager.broadcast(
                    session_id,
                    {'type': 'agent_speaking', 'payload': {'agent': agent_id}},
                )
                routed_prompt = orchestrator.build_prompt(session_id, role, event.text)
                for out in await live_bridge.handle_text(session_id, routed_prompt):
                    logger.info('ws out session=%s type=%s', session_id, out.get('type'))
                    await session_manager.broadcast(session_id, out)
            elif event_type == 'grant_speaking_turn':
                event = GrantSpeakingTurnInEvent.model_validate(raw)
                logger.info('ws grant session=%s agent=%s', session_id, event.agent)
                await session_manager.broadcast(
                    session_id,
                    {
                        'type': 'agent_speaking',
                        'payload': {'agent': event.agent},
                    },
                )
            elif event_type == 'cast_vote':
                event = VoteInEvent.model_validate(raw)
                logger.info('ws vote session=%s vote=%s', session_id, event.vote)
                await session_manager.broadcast(
                    session_id,
                    {
                        'type': 'vote_result',
                        'payload': {'votes': {'user': {'vote': event.vote}}, 'result': 'pending'},
                    },
                )
            elif event_type == 'turn_complete':
                _ = TurnCompleteInEvent.model_validate(raw)
                logger.info('ws turn_complete session=%s', session_id)
                await session_manager.broadcast(session_id, {'type': 'turn_complete', 'payload': {}})
            else:
                logger.warning('ws unsupported session=%s type=%s', session_id, event_type)
                await session_manager.broadcast(
                    session_id,
                    {'type': 'error', 'payload': {'message': f'Unsupported event: {event_type}'}},
                )
    except WebSocketDisconnect:
        logger.info('ws disconnect session=%s', session_id)
        await session_manager.disconnect(session_id, websocket)
        orchestrator.end_session(session_id)
        await live_bridge.close_session(session_id)
        await session_manager.broadcast(
            session_id,
            {'type': 'meeting_status', 'payload': {'status': 'ended'}},
        )

"""
WebSocket endpoint for the Quorum war room.

Protocol:
  Client → Server: JSON messages with { type, ... }
  Server → Client: JSON messages with { type, ... }

See backend/models/events.py for all message schemas.
"""

import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.models.events import (
    AudioChunkMsg,
    AudioStopMsg,
    DocumentUploadMsg,
    HandRaiseMsg,
    SessionCreateMsg,
    SessionEndedMsg,
    SessionErrorMsg,
    TextSendMsg,
    VoteCastMsg,
    parse_client_message,
)
from backend.services.session_manager import session_manager
from backend.services.adk_bridge import MultiAgentSession

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Single WebSocket connection per user session."""
    await websocket.accept()
    logger.info("WebSocket connected")

    live_session: MultiAgentSession | None = None

    async def send_json(msg: dict[str, Any]) -> None:
        """Send a JSON message to the client, silently ignoring broken pipes."""
        try:
            await websocket.send_json(msg)
        except Exception:
            logger.warning("Failed to send WS message")

    try:
        while True:
            raw = await websocket.receive_json()
            msg_type = raw.get("type", "")

            # ── Session Create ───────────────────────────────────────
            if msg_type == "session.create":
                msg = SessionCreateMsg.model_validate(raw)
                logger.info(
                    "Creating session: agenda=%s agents=%s",
                    msg.config.agenda,
                    msg.config.selectedAgentIds,
                )
                try:
                    live_session = await session_manager.create_session(
                        agent_ids=msg.config.selectedAgentIds,
                        agenda=msg.config.agenda,
                        send_fn=send_json,
                    )
                except Exception:
                    logger.exception("Failed to create session")
                    await send_json(
                        SessionErrorMsg(
                            message="Failed to create session — check server logs"
                        ).model_dump()
                    )

            # ── Audio Chunk ──────────────────────────────────────────
            elif msg_type == "audio.chunk":
                if live_session:
                    msg = AudioChunkMsg.model_validate(raw)
                    await live_session.send_audio(msg.data)

            # ── Audio Stop (mic off) ─────────────────────────────────
            elif msg_type == "audio.stop":
                if live_session:
                    live_session.send_activity_end()

            # ── Text Send ────────────────────────────────────────────
            elif msg_type == "text.send":
                if live_session:
                    msg = TextSendMsg.model_validate(raw)
                    await live_session.send_text(msg.text)

            # ── Vote Cast ────────────────────────────────────────────
            elif msg_type == "vote.cast":
                if live_session:
                    msg = VoteCastMsg.model_validate(raw)
                    await session_manager.cast_vote(
                        session_id=live_session.session_id,
                        vote_id=msg.voteId,
                        voter="user",
                        value=msg.value,
                        send_fn=send_json,
                    )

            # ── Hand Raise ───────────────────────────────────────────
            elif msg_type == "hand.raise":
                if live_session:
                    await live_session.send_text(
                        "[User raises hand — they want to speak or ask a question]"
                    )

            # ── Document Upload ──────────────────────────────────────
            elif msg_type == "document.upload":
                if live_session:
                    msg = DocumentUploadMsg.model_validate(raw)
                    from backend.models.events import DocumentStatusMsg

                    doc_id = f"doc-{msg.name}"
                    await send_json(
                        DocumentStatusMsg(
                            docId=doc_id, status="processing"
                        ).model_dump()
                    )
                    await live_session.send_text(
                        f"[Document uploaded: {msg.name}. Reference it in discussion.]"
                    )
                    await send_json(
                        DocumentStatusMsg(
                            docId=doc_id,
                            status="analyzed",
                            summary=f"Document '{msg.name}' shared with the board.",
                        ).model_dump()
                    )

            else:
                logger.warning("Unknown message type: %s", msg_type)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception:
        logger.exception("WebSocket error")
    finally:
        if live_session:
            await session_manager.destroy_session(live_session.session_id)
            await send_json(SessionEndedMsg().model_dump())

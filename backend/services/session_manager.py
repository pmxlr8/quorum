"""
Session manager: tracks active MultiAgentSessions and handles vote state.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from backend.models.events import VoteItem, VoteUpdateMsg, VoteValue
from backend.services.adk_bridge import MultiAgentSession, SendFn

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages all active war room sessions."""

    def __init__(self) -> None:
        self._sessions: dict[str, MultiAgentSession] = {}
        self._votes: dict[str, dict[str, VoteItem]] = {}

    async def create_session(
        self,
        agent_ids: list[str],
        agenda: str,
        send_fn: SendFn,
    ) -> MultiAgentSession:
        """Create and start a new multi-agent live session."""
        session_id = str(uuid.uuid4())[:8]
        session = MultiAgentSession(
            session_id=session_id,
            agent_ids=agent_ids,
            agenda=agenda,
            send_fn=send_fn,
        )
        self._sessions[session_id] = session
        self._votes[session_id] = {}
        await session.start()
        return session

    async def destroy_session(self, session_id: str) -> None:
        """Stop and remove a session."""
        session = self._sessions.pop(session_id, None)
        self._votes.pop(session_id, None)
        if session:
            await session.stop()

    def get_session(self, session_id: str) -> MultiAgentSession | None:
        return self._sessions.get(session_id)

    # ── Vote management ──────────────────────────────────────────────────────

    def register_vote(self, session_id: str, vote: VoteItem) -> None:
        if session_id in self._votes:
            self._votes[session_id][vote.id] = vote

    async def cast_vote(
        self,
        session_id: str,
        vote_id: str,
        voter: str,
        value: VoteValue,
        send_fn: SendFn,
    ) -> None:
        votes = self._votes.get(session_id, {})
        vote = votes.get(vote_id)
        if vote and vote.status == "open":
            vote.votes[voter] = value
            await send_fn(VoteUpdateMsg(vote=vote).model_dump())


# Singleton
session_manager = SessionManager()

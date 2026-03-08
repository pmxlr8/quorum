"""Pydantic models for WebSocket messages between frontend and backend."""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


# ── Shared types (mirror frontend/src/types/warroom.ts) ──────────────────────

AgentRole = Literal["chairperson", "analyst", "advocate", "critic", "secretary"]
VoteValue = Literal["yes", "no", "abstain"]
SessionStatus = Literal["idle", "connecting", "active", "error", "ended"]
SpeakingState = Literal["idle", "listening", "speaking", "thinking"]


class AgentInfo(BaseModel):
    id: str
    name: str
    role: AgentRole
    avatar: str = ""
    speakingState: SpeakingState = "idle"
    isHandRaised: bool = False


class TranscriptEntry(BaseModel):
    id: str
    agentId: str
    agentName: str
    role: AgentRole
    text: str
    timestamp: float  # epoch ms


class VoteItem(BaseModel):
    id: str
    motion: str
    votes: dict[str, VoteValue] = Field(default_factory=dict)
    status: Literal["open", "closed"] = "open"


class DocumentInfo(BaseModel):
    id: str
    name: str
    status: Literal["uploading", "processing", "analyzed", "error"]
    summary: str | None = None


# ── Client → Server messages ─────────────────────────────────────────────────

class SessionCreateMsg(BaseModel):
    type: Literal["session.create"] = "session.create"
    config: SessionConfig


class SessionConfig(BaseModel):
    agenda: str
    selectedAgentIds: list[str]


class AudioChunkMsg(BaseModel):
    type: Literal["audio.chunk"] = "audio.chunk"
    data: str  # base64-encoded PCM16 16kHz mono


class AudioStopMsg(BaseModel):
    type: Literal["audio.stop"] = "audio.stop"


class TextSendMsg(BaseModel):
    type: Literal["text.send"] = "text.send"
    text: str


class VoteCastMsg(BaseModel):
    type: Literal["vote.cast"] = "vote.cast"
    voteId: str
    value: VoteValue


class HandRaiseMsg(BaseModel):
    type: Literal["hand.raise"] = "hand.raise"


class DocumentUploadMsg(BaseModel):
    type: Literal["document.upload"] = "document.upload"
    name: str
    data: str  # base64 file content
    mimeType: str = "application/pdf"


# ── Server → Client messages ─────────────────────────────────────────────────

class SessionReadyMsg(BaseModel):
    type: Literal["session.ready"] = "session.ready"
    agents: list[AgentInfo]


class AgentStateMsg(BaseModel):
    type: Literal["agent.state"] = "agent.state"
    agentId: str
    speakingState: SpeakingState


class TranscriptAddMsg(BaseModel):
    type: Literal["transcript.add"] = "transcript.add"
    entry: TranscriptEntry


class AudioOutMsg(BaseModel):
    type: Literal["audio.chunk"] = "audio.chunk"
    data: str  # base64-encoded PCM16 24kHz mono


class VoteProposedMsg(BaseModel):
    type: Literal["vote.proposed"] = "vote.proposed"
    vote: VoteItem


class VoteUpdateMsg(BaseModel):
    type: Literal["vote.update"] = "vote.update"
    vote: VoteItem


class DocumentStatusMsg(BaseModel):
    type: Literal["document.status"] = "document.status"
    docId: str
    status: str
    summary: str | None = None


class SessionErrorMsg(BaseModel):
    type: Literal["session.error"] = "session.error"
    message: str


class SessionEndedMsg(BaseModel):
    type: Literal["session.ended"] = "session.ended"


# ── Helper to parse incoming messages ────────────────────────────────────────

CLIENT_MSG_TYPES: dict[str, type[BaseModel]] = {
    "session.create": SessionCreateMsg,
    "audio.chunk": AudioChunkMsg,
    "audio.stop": AudioStopMsg,
    "text.send": TextSendMsg,
    "vote.cast": VoteCastMsg,
    "hand.raise": HandRaiseMsg,
    "document.upload": DocumentUploadMsg,
}


def parse_client_message(raw: dict[str, Any]) -> BaseModel:
    """Parse a raw JSON dict from the client into the appropriate message model."""
    msg_type = raw.get("type", "")
    model_cls = CLIENT_MSG_TYPES.get(msg_type)
    if model_cls is None:
        raise ValueError(f"Unknown message type: {msg_type}")
    return model_cls.model_validate(raw)

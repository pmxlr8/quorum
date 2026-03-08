import asyncio
from collections import defaultdict
from dataclasses import dataclass, field

from fastapi import WebSocket


@dataclass
class SessionRuntime:
    queue: asyncio.Queue[dict] = field(default_factory=asyncio.Queue)
    sockets: set[WebSocket] = field(default_factory=set)


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionRuntime] = defaultdict(SessionRuntime)
        self._lock = asyncio.Lock()

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._sessions[session_id].sockets.add(websocket)

    async def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            runtime = self._sessions.get(session_id)
            if runtime is None:
                return
            runtime.sockets.discard(websocket)
            if not runtime.sockets:
                self._sessions.pop(session_id, None)

    async def broadcast(self, session_id: str, event: dict) -> None:
        runtime = self._sessions.get(session_id)
        if runtime is None:
            return
        dead: list[WebSocket] = []
        for socket in runtime.sockets:
            try:
                await socket.send_json(event)
            except Exception:
                dead.append(socket)
        for socket in dead:
            runtime.sockets.discard(socket)


session_manager = SessionManager()

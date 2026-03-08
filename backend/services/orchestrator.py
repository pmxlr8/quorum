from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MeetingState:
    agenda: str = 'Decide next product milestone.'
    deliverables: list[str] = field(default_factory=lambda: ['Decision', 'Risks', 'Owner'])


class Orchestrator:
    """Baseline routing orchestrator for BACK-004.

    This provides deterministic keyword routing while the full ADK multi-agent
    behavior is integrated in subsequent tasks.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, MeetingState] = {}

    def start_session(self, session_id: str) -> None:
        self._sessions.setdefault(session_id, MeetingState())

    def end_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def route(self, text: str) -> tuple[str, str]:
        msg = text.lower()
        if any(k in msg for k in ['budget', 'cost', 'pricing', 'runway', 'roi']):
            return ('sarah_kim', 'CFO')
        if any(k in msg for k in ['legal', 'contract', 'ip', 'compliance', 'gdpr', 'liability']):
            return ('marcus_webb', 'Legal')
        if any(k in msg for k in ['architecture', 'latency', 'scalability', 'security', 'tech']):
            return ('alex_chen', 'CTO')
        return ('charon_orchestrator', 'Orchestrator')

    def build_prompt(self, session_id: str, role: str, user_text: str) -> str:
        state = self._sessions.get(session_id, MeetingState())
        return (
            f'You are the {role} board member in a decision meeting. '\
            f'Agenda: {state.agenda}. '\
            f'Deliverables: {", ".join(state.deliverables)}. '\
            f'User request: {user_text}'
        )


orchestrator = Orchestrator()

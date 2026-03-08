from __future__ import annotations

from dataclasses import dataclass, field

AGENT_PERSONAS = {
    'CTO': {
        'name': 'Alex Chen',
        'voice': 'Orus',
        'style': 'Direct, structured, evidence-driven. Uses engineering analogies. Numbers-focused.',
        'expertise': 'architecture, scalability, security, tech debt, timeline feasibility',
    },
    'CFO': {
        'name': 'Sarah Kim',
        'voice': 'Fenrir',
        'style': 'Precise, margin-focused, risk-aware. Frames everything in ROI and runway terms.',
        'expertise': 'budget, margins, runway, pricing strategy, unit economics, fundraising',
    },
    'Legal': {
        'name': 'Marcus Webb',
        'voice': 'Kore',
        'style': 'Cautious, thorough, worst-case thinker. Flags liability before opportunity.',
        'expertise': 'contracts, IP, compliance, GDPR, liability, regulatory risk',
    },
    'Orchestrator': {
        'name': 'Charon',
        'voice': 'Charon',
        'style': 'Authoritative facilitator. Synthesizes perspectives, drives toward decisions.',
        'expertise': 'meeting facilitation, decision synthesis, conflict resolution, agenda management',
    },
}


@dataclass
class MeetingState:
    agenda: str = 'Decide next product milestone.'
    deliverables: list[str] = field(default_factory=lambda: ['Decision', 'Risks', 'Owner'])
    transcript: list[dict[str, str]] = field(default_factory=list)


class Orchestrator:
    """Routing orchestrator that directs user messages to the right board agent.

    Maintains per-session meeting state and builds rich persona-aware prompts.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, MeetingState] = {}

    def start_session(self, session_id: str) -> None:
        self._sessions.setdefault(session_id, MeetingState())

    def end_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def route(self, text: str) -> tuple[str, str]:
        msg = text.lower()
        if any(k in msg for k in ['budget', 'cost', 'pricing', 'runway', 'roi', 'revenue', 'margin', 'financial', 'money', 'funding']):
            return ('sarah_kim', 'CFO')
        if any(k in msg for k in ['legal', 'contract', 'ip', 'compliance', 'gdpr', 'liability', 'regulation', 'patent', 'lawsuit']):
            return ('marcus_webb', 'Legal')
        if any(k in msg for k in ['architecture', 'latency', 'scalability', 'security', 'tech', 'code', 'api', 'infrastructure', 'database', 'deploy', 'engineering', 'build']):
            return ('alex_chen', 'CTO')
        return ('charon_orchestrator', 'Orchestrator')

    def build_prompt(self, session_id: str, role: str, user_text: str) -> str:
        state = self._sessions.get(session_id, MeetingState())
        persona = AGENT_PERSONAS.get(role, AGENT_PERSONAS['Orchestrator'])

        # Track conversation turns
        state.transcript.append({'speaker': 'user', 'text': user_text})

        # Build recent context (last 6 turns)
        recent = state.transcript[-6:]
        context_lines = '\n'.join(f"  {t['speaker']}: {t['text']}" for t in recent)

        prompt = (
            f'You are {persona["name"]}, the {role} on an executive board of directors in a live voice meeting.\n'
            f'Personality: {persona["style"]}\n'
            f'Expertise: {persona["expertise"]}\n\n'
            f'Meeting agenda: {state.agenda}\n'
            f'Required deliverables: {", ".join(state.deliverables)}\n\n'
            f'Recent conversation:\n{context_lines}\n\n'
            f'Respond naturally as {persona["name"]} in 2-4 sentences. Be specific, opinionated, and in-character. '
            f'Address the user directly. If you strongly disagree or see a risk, say so clearly.'
        )
        return prompt


orchestrator = Orchestrator()

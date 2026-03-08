"""
Agent definitions with full customization support for the Quorum war room.

Each agent has:
  - Deep personality, tone, speaking style
  - Unique Gemini Live voice
  - AI-generated avatar (via Imagen)
  - Individual system prompts (no more single-session role-playing)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional

# ── Available Gemini Live voices (each sounds distinct) ──────────────────────

AVAILABLE_VOICES = [
    {"id": "Puck", "label": "Puck", "description": "Bright, energetic, youthful"},
    {"id": "Charon", "label": "Charon", "description": "Deep, authoritative, commanding"},
    {"id": "Fenrir", "label": "Fenrir", "description": "Sharp, intense, dynamic"},
    {"id": "Kore", "label": "Kore", "description": "Warm, measured, empathetic"},
    {"id": "Aoede", "label": "Aoede", "description": "Clear, elegant, professional"},
    {"id": "Leda", "label": "Leda", "description": "Calm, thoughtful, diplomatic"},
    {"id": "Orus", "label": "Orus", "description": "Firm, decisive, no-nonsense"},
    {"id": "Zephyr", "label": "Zephyr", "description": "Light, creative, inspiring"},
]

AVAILABLE_VOICE_IDS = [v["id"] for v in AVAILABLE_VOICES]

AVAILABLE_TONES = [
    "formal", "casual", "aggressive", "diplomatic", "skeptical",
    "optimistic", "measured", "passionate", "dry", "authoritative",
]

AVAILABLE_ROLES = [
    {"id": "chairperson", "label": "Chairperson / Moderator"},
    {"id": "analyst", "label": "Analyst / Strategist"},
    {"id": "critic", "label": "Critic / Devil's Advocate"},
    {"id": "advocate", "label": "Compliance / Advocate"},
    {"id": "secretary", "label": "Secretary / Researcher"},
    {"id": "creative", "label": "Creative / Visionary"},
    {"id": "technical", "label": "Technical / Engineer"},
    {"id": "financial", "label": "Financial / CFO"},
    {"id": "custom", "label": "Custom Role"},
]


# ── Agent definition dataclass ───────────────────────────────────────────────

@dataclass
class AgentDefinition:
    """Full agent definition with rich customization."""

    id: str
    name: str
    role: str
    label: str
    description: str
    personality: str
    speaking_style: str
    tone: str
    expertise: list[str]
    voice: str
    avatar_url: str = ""
    background_theme: str = ""
    is_builtin: bool = True

    def build_system_prompt(
        self,
        agenda: str,
        other_agent_names: list[str],
        conversation_so_far: str = "",
        documents_context: str = "",
    ) -> str:
        """Build individual system prompt for this agent's own Gemini Live session."""
        others = ", ".join(other_agent_names) if other_agent_names else "no one else"

        doc_block = ""
        if documents_context:
            doc_block = f"""

UPLOADED DOCUMENTS (reference these when relevant):
{documents_context}
"""

        convo_block = ""
        if conversation_so_far:
            convo_block = f"""

CONVERSATION SO FAR (for context — continue naturally from here):
{conversation_so_far}
"""

        return f"""You are {self.name}, a member of a virtual board of directors called "Quorum".

YOUR IDENTITY:
- Name: {self.name}
- Role: {self.label} ({self.role})
- Description: {self.description}
- Personality: {self.personality}
- Speaking Style: {self.speaking_style}
- Tone: {self.tone}
- Areas of Expertise: {', '.join(self.expertise)}

SESSION AGENDA:
{agenda}

OTHER BOARD MEMBERS IN THIS SESSION: {others}
{doc_block}{convo_block}
CRITICAL RULES:
1. You ARE {self.name}. Stay in character at ALL times.
2. Speak naturally as {self.name} would — your voice, tone, and personality must be consistent.
3. Do NOT prefix your speech with your name. Just speak directly.
4. Keep responses concise (2-4 sentences) to maintain a dynamic discussion.
5. Reference what other board members have said when relevant.
6. If asked who you are, describe yourself in character.
7. Be opinionated and have a distinct voice. Don't be generic.
8. If you have nothing substantive to add, say so briefly and yield the floor.
9. You may use Google Search to look up real facts, data, or news when relevant.
"""

    def to_dict(self) -> dict:
        """Serialize for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "label": self.label,
            "description": self.description,
            "personality": self.personality,
            "speaking_style": self.speaking_style,
            "tone": self.tone,
            "expertise": self.expertise,
            "voice": self.voice,
            "avatar_url": self.avatar_url,
            "background_theme": self.background_theme,
            "is_builtin": self.is_builtin,
        }


# ── Built-in agents (rich defaults) ─────────────────────────────────────────

DEFAULT_AGENTS: dict[str, AgentDefinition] = {
    "pa1": AgentDefinition(
        id="pa1",
        name="Cipher",
        role="analyst",
        label="Strategist",
        description="Deep market & data analysis. Uses quantitative reasoning.",
        personality=(
            "Analytical, methodical, data-obsessed. You see the world in numbers "
            "and probabilities. You get visibly excited when you spot a pattern in data. "
            "You sometimes forget that not everything can be quantified. You respect "
            "hard evidence over gut feelings. You have a competitive streak."
        ),
        speaking_style=(
            "Precise and measured. You use numbers, percentages, and statistics naturally. "
            "You speak with quiet confidence. You occasionally drop jargon then explain it. "
            "You start many sentences with 'The data shows...' or 'If we look at the numbers...'"
        ),
        tone="measured",
        expertise=["data analysis", "market research", "financial modeling", "statistics"],
        voice="Puck",
    ),
    "pa2": AgentDefinition(
        id="pa2",
        name="Probe",
        role="critic",
        label="Devil's Advocate",
        description="Challenges assumptions and pokes holes in arguments.",
        personality=(
            "Sharp, contrarian, intellectually fierce. You love finding weaknesses "
            "in arguments because you believe stress-testing ideas makes them stronger. "
            "You have a dry wit and occasionally make sardonic observations. You're "
            "secretly proud when someone's idea survives your scrutiny."
        ),
        speaking_style=(
            "Direct, sometimes blunt. You use rhetorical questions frequently. "
            "You speak with an intellectual edge. You often say 'But have you considered...' "
            "or 'That's assuming...' You speed up when you find a flaw."
        ),
        tone="skeptical",
        expertise=["risk assessment", "critical analysis", "strategy stress-testing", "scenario planning"],
        voice="Fenrir",
    ),
    "pa3": AgentDefinition(
        id="pa3",
        name="Shield",
        role="advocate",
        label="Compliance Officer",
        description="Legal & regulatory review. Ensures compliance and ethics.",
        personality=(
            "Careful, principled, detail-oriented. You take rules seriously but you're "
            "not a bureaucrat — you genuinely care about doing things right. You see "
            "regulations as guardrails, not roadblocks. You occasionally add a dry legal joke."
        ),
        speaking_style=(
            "Formal but accessible. You reference regulations and frameworks by name. "
            "You speak carefully and deliberately. You often say 'From a compliance standpoint...' "
            "or 'The regulatory framework requires...' You slow down for important legal points."
        ),
        tone="authoritative",
        expertise=["legal compliance", "regulatory frameworks", "ethics", "governance"],
        voice="Kore",
    ),
    "pa4": AgentDefinition(
        id="pa4",
        name="Scribe",
        role="secretary",
        label="Researcher",
        description="Document & fact retrieval. Summarizes and finds information.",
        personality=(
            "Curious, thorough, organized. You're the knowledge keeper — you love "
            "connecting disparate pieces of information. You sometimes go down rabbit "
            "holes. You get excited when you find the perfect supporting evidence."
        ),
        speaking_style=(
            "Clear and structured. You reference sources methodically. "
            "You lay out information in logical order. You often say 'According to...' "
            "or 'The research indicates...' You speak at a moderate pace."
        ),
        tone="neutral",
        expertise=["research", "document analysis", "fact-checking", "summarization"],
        voice="Aoede",
    ),
    "pa5": AgentDefinition(
        id="pa5",
        name="Director",
        role="chairperson",
        label="Mediator",
        description="Moderates discussion and drives toward actionable outcomes.",
        personality=(
            "Diplomatic, decisive, big-picture thinker. You're a natural leader who "
            "knows when to let debate run and when to cut it off. You balance all "
            "perspectives fairly but express your own view. You care deeply about "
            "reaching consensus and moving to action."
        ),
        speaking_style=(
            "Warm but commanding. You summarize others' points fairly. You use inclusive "
            "language: 'we', 'our', 'let's'. You speak with gravitas. You often say "
            "'Let me bring us back to...' or 'What I'm hearing is...'"
        ),
        tone="diplomatic",
        expertise=["leadership", "conflict resolution", "consensus building", "strategic planning"],
        voice="Charon",
    ),
}


# ── Custom agent store (in-memory) ──────────────────────────────────────────

_custom_agents: dict[str, AgentDefinition] = {}


def get_all_agents() -> dict[str, AgentDefinition]:
    """Get all available agents (built-in + custom)."""
    return {**DEFAULT_AGENTS, **_custom_agents}


def get_agent(agent_id: str) -> AgentDefinition | None:
    """Get an agent by ID."""
    return DEFAULT_AGENTS.get(agent_id) or _custom_agents.get(agent_id)


def create_custom_agent(
    name: str,
    role: str,
    label: str,
    description: str,
    personality: str,
    speaking_style: str,
    tone: str,
    expertise: list[str],
    voice: str,
    avatar_url: str = "",
    background_theme: str = "",
) -> AgentDefinition:
    """Create a new custom agent."""
    agent_id = f"custom-{uuid.uuid4().hex[:8]}"
    agent = AgentDefinition(
        id=agent_id,
        name=name,
        role=role,
        label=label,
        description=description,
        personality=personality,
        speaking_style=speaking_style,
        tone=tone,
        expertise=expertise,
        voice=voice if voice in AVAILABLE_VOICE_IDS else "Aoede",
        avatar_url=avatar_url,
        background_theme=background_theme,
        is_builtin=False,
    )
    _custom_agents[agent_id] = agent
    return agent


def delete_custom_agent(agent_id: str) -> bool:
    """Delete a custom agent. Cannot delete built-in agents."""
    return _custom_agents.pop(agent_id, None) is not None


def list_agents_for_api() -> list[dict]:
    """Return all agents serialized for API response."""
    all_agents = get_all_agents()
    return [a.to_dict() for a in all_agents.values()]
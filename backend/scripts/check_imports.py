"""Quick backend import check."""
from backend.core.config import settings
print("Config OK")

from backend.models.agents import (
    DEFAULT_AGENTS, AVAILABLE_VOICES, get_all_agents,
    create_custom_agent, list_agents_for_api
)
print(f"Agents OK, defaults: {len(DEFAULT_AGENTS)}, voices: {len(AVAILABLE_VOICES)}")

from backend.models.events import parse_client_message, SessionCreateMsg
print("Events OK")

from backend.services.adk_bridge import MultiAgentSession, AgentLiveSession
print("ADK Bridge OK")

from backend.services.session_manager import session_manager
print("Session Manager OK")

# Test custom agent creation
agent = create_custom_agent(
    name="TestBot", role="custom", label="Tester", description="A test agent",
    personality="Curious and helpful", speaking_style="Clear and direct",
    tone="casual", expertise=["testing"], voice="Puck",
)
print(f"Custom agent: {agent.id} ({agent.name})")
print(f"All agents: {len(list_agents_for_api())}")

# Test system prompt
prompt = DEFAULT_AGENTS["pa1"].build_system_prompt(
    agenda="Test agenda", other_agent_names=["Probe", "Director"]
)
print(f"System prompt length: {len(prompt)}")
print("ALL IMPORTS OK")

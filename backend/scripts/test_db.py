"""Quick test for agent DB persistence."""
from backend.models.agents import create_custom_agent, get_all_agents, delete_custom_agent
from backend.models.agent_db import load_all_agents
import os

a = create_custom_agent(
    name="TestBot", role="creative", label="Test", description="test",
    personality="test", speaking_style="test", tone="casual",
    expertise=["x"], voice="Zephyr",
)
print(f"Created: {a.id}")
print(f"Total agents: {len(get_all_agents())}")
print(f"DB exists: {os.path.exists('backend/quorum_agents.db')}")
print(f"In DB: {len(load_all_agents())}")

delete_custom_agent(a.id)
print(f"After delete: {len(get_all_agents())}")
print(f"In DB after delete: {len(load_all_agents())}")
print("ALL OK")

"""
Quorum — Virtual War Room Backend

FastAPI application with WebSocket endpoint for live voice + text sessions
powered by Google ADK + Gemini Live API.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import settings

# ── CRITICAL: Export env vars for google-genai / ADK ─────────────────────────
# The ADK reads these from os.environ, not from pydantic-settings.
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", str(settings.google_genai_use_vertexai).lower())
if settings.google_cloud_project:
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", settings.google_cloud_project)
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", settings.google_cloud_location)

from backend.api.ws import router as ws_router  # noqa: E402 (import after env setup)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logging.getLogger(__name__).info(
        "Quorum backend starting — model=%s project=%s",
        settings.live_model_id,
        settings.google_cloud_project,
    )
    yield
    logging.getLogger(__name__).info("Quorum backend shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ws_router)


# ── REST API for agents ──────────────────────────────────────────────────────

from backend.models.agents import (
    AVAILABLE_VOICES,
    AVAILABLE_TONES,
    AVAILABLE_ROLES,
    list_agents_for_api,
    get_agent,
    create_custom_agent,
    delete_custom_agent,
)


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "version": settings.app_version,
        "model": settings.live_model_id,
        "project": settings.google_cloud_project,
        "location": settings.google_cloud_location,
        "vertexai": settings.google_genai_use_vertexai,
    }


@app.get("/api/agents")
async def get_agents():
    """List all available agents (built-in + custom)."""
    return {"agents": list_agents_for_api()}


@app.get("/api/agents/{agent_id}")
async def get_agent_detail(agent_id: str):
    """Get a single agent's details."""
    agent = get_agent(agent_id)
    if not agent:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent.to_dict()


@app.post("/api/agents")
async def create_agent(body: dict):
    """Create a new custom agent."""
    required = ["name", "role", "label", "description", "personality", "speaking_style", "tone", "voice"]
    for field in required:
        if field not in body:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

    agent = create_custom_agent(
        name=body["name"],
        role=body["role"],
        label=body["label"],
        description=body["description"],
        personality=body["personality"],
        speaking_style=body["speaking_style"],
        tone=body["tone"],
        expertise=body.get("expertise", []),
        voice=body["voice"],
        avatar_url=body.get("avatar_url", ""),
        background_theme=body.get("background_theme", ""),
    )
    return agent.to_dict()


@app.delete("/api/agents/{agent_id}")
async def remove_agent(agent_id: str):
    """Delete a custom agent."""
    success = delete_custom_agent(agent_id)
    if not success:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Agent not found or is built-in")
    return {"deleted": True}


@app.get("/api/voices")
async def get_voices():
    """List available Gemini Live voices."""
    return {"voices": AVAILABLE_VOICES}


@app.get("/api/roles")
async def get_roles():
    """List available agent roles."""
    return {"roles": AVAILABLE_ROLES}


@app.get("/api/tones")
async def get_tones():
    """List available tone presets."""
    return {"tones": AVAILABLE_TONES}


@app.post("/api/generate-avatar")
async def generate_avatar(body: dict):
    """Generate an AI avatar for an agent using Imagen."""
    agent_name = body.get("name", "Character")
    agent_role = body.get("role", "advisor")
    agent_personality = body.get("personality", "professional")
    style = body.get("style", "digital art portrait")

    prompt = (
        f"Professional avatar portrait of a character named '{agent_name}', "
        f"who is a {agent_role}. Personality: {agent_personality}. "
        f"Style: {style}, dark moody background, suitable for a boardroom AI assistant. "
        f"Clean, modern, high quality digital illustration. No text."
    )

    try:
        from google import genai as genai_client

        client = genai_client.Client()
        response = client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=prompt,
            config=genai_client.types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="1:1",
            ),
        )

        if response.generated_images and len(response.generated_images) > 0:
            import base64
            image_bytes = response.generated_images[0].image.image_bytes
            b64 = base64.b64encode(image_bytes).decode("ascii")
            data_uri = f"data:image/png;base64,{b64}"
            return {"avatar_url": data_uri}
        else:
            return {"avatar_url": "", "error": "No image generated"}

    except Exception as e:
        logging.getLogger(__name__).error("Avatar generation failed: %s", e)
        return {"avatar_url": "", "error": str(e)}

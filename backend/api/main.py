from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.ws import router as ws_router
from backend.core.config import settings
from backend.services.live_bridge import live_bridge


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Reserved for runner/session initialization and cleanup.
    yield


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.allowed_origins.split(',')],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.include_router(ws_router)


@app.get('/health')
async def health() -> dict:
    auth_mode = 'vertex' if settings.google_genai_use_vertexai else ('api_key' if settings.google_api_key else 'none')
    return {
        'status': 'ok',
        'version': settings.app_version,
        'live_model_id': settings.live_model_id,
        'live_client_ready': live_bridge.client is not None,
        'auth_mode': auth_mode,
        'project': settings.google_cloud_project or settings.gcp_project_id,
        'location': settings.google_cloud_location or settings.gcp_region,
    }

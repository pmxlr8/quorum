from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.ws import router as ws_router
from backend.core.config import settings


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
    return {'status': 'ok', 'version': settings.app_version, 'live_model_id': settings.live_model_id}

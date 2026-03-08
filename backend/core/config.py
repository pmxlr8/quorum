from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=('backend/.env', '.env'), extra='ignore')

    app_name: str = 'quorum-backend'
    app_version: str = '2.0.0'

    # Gemini Live model for voice streaming (ADK)
    live_model_id: str = Field(
        default='gemini-live-2.5-flash-native-audio',
        alias='LIVE_MODEL_ID',
    )
    # Text model for doc analysis, summaries, etc.
    text_model_id: str = Field(
        default='gemini-2.5-flash',
        alias='TEXT_MODEL_ID',
    )

    # GCP / Vertex AI
    google_cloud_project: str | None = Field(default=None, alias='GOOGLE_CLOUD_PROJECT')
    google_cloud_location: str = Field(default='us-central1', alias='GOOGLE_CLOUD_LOCATION')
    google_genai_use_vertexai: bool = Field(default=True, alias='GOOGLE_GENAI_USE_VERTEXAI')

    # CORS
    allowed_origins: str = Field(
        default='http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080',
        alias='ALLOWED_ORIGINS',
    )

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(',') if o.strip()]


settings = Settings()

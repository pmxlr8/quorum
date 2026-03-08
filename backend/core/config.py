from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=('backend/.env', '.env'), extra='ignore')

    app_name: str = 'virtual-war-room-backend'
    app_version: str = '0.1.0'
    live_model_id: str = Field(default='gemini-live-2.5-flash-native-audio', alias='LIVE_MODEL_ID')
    text_model_id: str = Field(default='gemini-2.5-flash', alias='TEXT_MODEL_ID')
    google_api_key: str | None = Field(default=None, alias='GOOGLE_API_KEY')
    gcp_project_id: str | None = Field(default=None, alias='GCP_PROJECT_ID')
    gcp_region: str = Field(default='us-central1', alias='GCP_REGION')
    google_cloud_project: str | None = Field(default=None, alias='GOOGLE_CLOUD_PROJECT')
    google_cloud_location: str = Field(default='us-central1', alias='GOOGLE_CLOUD_LOCATION')
    google_genai_use_vertexai: bool = Field(default=False, alias='GOOGLE_GENAI_USE_VERTEXAI')
    allowed_origins: str = Field(default='http://localhost:5173', alias='ALLOWED_ORIGINS')


settings = Settings()

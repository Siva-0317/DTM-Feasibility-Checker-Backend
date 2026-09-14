from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    lmstudio_model_url: str = "http://127.0.0.1:1234/v1/chat/completions"
    upload_dir: str = "uploads"
    output_dir: str = "outputs"
    max_file_size_mb: int = 10000
    cors_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    hf_api_token: str = "your_token_here"
    hf_model_url: str = "https://api-inference.huggingface.co/models/meta-llama/Llama-3.2-11B-Instruct"
    upload_dir: str = "uploads"
    output_dir: str = "outputs"
    max_file_size_mb: int = 200
    cors_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()

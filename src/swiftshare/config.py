from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    shared_dir: Path = Path.cwd() / "shared"
    port: int = 8000
    host: str = "0.0.0.0"
    max_upload_size: int = 2 * 1024 * 1024 * 1024
    enable_auth: bool = False
    share_expiry_hours: int = 24

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

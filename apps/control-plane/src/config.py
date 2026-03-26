from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    app_env: str
    log_level: str
    openai_api_key: str
    anthropic_api_key: str


def _required(name: str) -> str:
    value = os.getenv(name, "")
    if not value.strip():
        raise ValueError(f"Missing required environment variable: {name}")
    return value


settings = Settings(
    app_env=os.getenv("APP_ENV", "local"),
    log_level=os.getenv("LOG_LEVEL", "info"),
    openai_api_key=_required("OPENAI_API_KEY"),
    anthropic_api_key=_required("ANTHROPIC_API_KEY"),
)

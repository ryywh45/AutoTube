from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProviderConfig(BaseModel):
    """Configuration for a single LLM provider."""

    model: str
    temperature: float = 0.7
    max_tokens: int = 4096


class TTSConfig(BaseModel):
    """TTS service configuration."""

    provider: str = "edge-tts"
    voice: str = "zh-TW-HsiaoChenNeural"
    language: str = "zh-TW"


class VideoConfig(BaseModel):
    """Video output settings."""

    default_format: str = "medium"
    resolution: str = "1920x1080"
    fps: int = 30


class Settings(BaseSettings):
    """Application settings. Secrets from .env, everything else from config.yaml."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API keys (loaded from .env)
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""

    # Non-secret settings (populated from config.yaml via load_settings)
    llm: LLMProviderConfig = LLMProviderConfig(model="tbd")
    tts: TTSConfig = TTSConfig()
    video: VideoConfig = VideoConfig()
    output_dir: Path = Path("output")


def load_settings(config_path: Path = Path("config.yaml")) -> Settings:
    """Load settings by merging .env secrets with config.yaml values."""
    overrides: dict[str, Any] = {}
    if config_path.exists():
        with open(config_path) as f:
            overrides = yaml.safe_load(f) or {}
    return Settings(**overrides)

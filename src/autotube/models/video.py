from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel

from autotube.models.audio import AudioSegment
from autotube.models.storyboard import StoryboardScene


class VideoFormat(StrEnum):
    SHORT = "short"  # < 1 min (shorts)
    MEDIUM = "medium"  # 3-5 min
    LONG = "long"  # 8+ min


class VideoProject(BaseModel):
    """Aggregates all artifacts for a single video production."""

    concept: str
    format: VideoFormat
    scenes: list[StoryboardScene] = []
    audio_segments: list[AudioSegment] = []
    output_path: Path | None = None

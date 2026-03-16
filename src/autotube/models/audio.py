from pathlib import Path

from pydantic import BaseModel


class AudioSegment(BaseModel):
    """A segment of TTS audio corresponding to a scene."""

    scene_index: int
    text: str
    audio_path: Path | None = None
    duration_seconds: float | None = None

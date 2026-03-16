from pathlib import Path

from pydantic import BaseModel


class VideoMetadata(BaseModel):
    """YouTube metadata generated for a video."""

    title: str
    description: str
    tags: list[str]
    thumbnail_path: Path | None = None

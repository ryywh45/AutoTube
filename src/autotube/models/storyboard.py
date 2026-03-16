from pathlib import Path

from pydantic import BaseModel


class StoryboardScene(BaseModel):
    """A single scene in the storyboard, linking narration to a visual."""

    scene_index: int
    narration: str
    visual_description: str
    image_path: Path | None = None

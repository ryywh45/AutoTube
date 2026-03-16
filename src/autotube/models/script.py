from pydantic import BaseModel


class ScriptSection(BaseModel):
    """A section of the script with its narration text."""

    heading: str
    narration: str


class Script(BaseModel):
    """Complete script for a video, composed of ordered sections."""

    title: str
    concept: str
    sections: list[ScriptSection]

    @property
    def full_narration(self) -> str:
        return "\n\n".join(s.narration for s in self.sections)

    @property
    def estimated_duration_seconds(self) -> float:
        """Rough estimate based on Chinese speech rate (~4 chars/sec)."""
        char_count = sum(len(s.narration) for s in self.sections)
        return char_count / 4.0

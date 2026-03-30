import re
from datetime import datetime
from pathlib import Path


class PipelineRun:
    """Manages run identity and artifact output directory."""

    def __init__(self, concept: str, output_root: Path = Path("output")):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = _slugify(concept)
        self._run_id = f"{timestamp}_{slug}"
        self._run_dir = output_root / self._run_id
        self._run_dir.mkdir(parents=True, exist_ok=True)

    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def run_dir(self) -> Path:
        return self._run_dir

    def stage_dir(self, stage_name: str) -> Path:
        d = self._run_dir / stage_name
        d.mkdir(parents=True, exist_ok=True)
        return d


def _slugify(text: str, max_len: int = 20) -> str:
    """Keep Chinese/alphanumeric chars, replace rest with underscores."""
    slug = re.sub(r"[^\w\u4e00-\u9fff]", "_", text)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug[:max_len]

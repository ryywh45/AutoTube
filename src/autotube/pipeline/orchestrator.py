import json
import logging
from pathlib import Path
from typing import Any

from autotube.pipeline.stage import Stage, StageResult, StageStatus

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Executes pipeline stages sequentially with pause/resume support.

    State is persisted to a JSON file so the pipeline can be interrupted
    and resumed from the last completed stage.
    """

    def __init__(self, stages: list[Stage], state_path: Path = Path("pipeline_state.json")):
        self._stages = stages
        self._state_path = state_path

    async def run(self, initial_input: Any = None) -> dict[str, StageResult]:
        """Run all stages sequentially, skipping already-completed stages.

        Args:
            initial_input: Input for the first stage.

        Returns:
            Dict mapping stage name to its result.
        """
        completed = self._load_state()
        results: dict[str, StageResult] = {}
        current_input = initial_input

        for stage in self._stages:
            if stage.name in completed:
                logger.info("Skipping completed stage: %s", stage.name)
                results[stage.name] = StageResult(status=StageStatus.SKIPPED)
                continue

            logger.info("Running stage: %s", stage.name)
            try:
                result = await stage.run(current_input)
                results[stage.name] = result

                if result.status == StageStatus.COMPLETED:
                    completed.add(stage.name)
                    self._save_state(completed)
                    current_input = result.output
                else:
                    logger.error("Stage %s finished with status: %s", stage.name, result.status)
                    break
            except Exception as e:
                logger.exception("Stage %s failed with exception", stage.name)
                results[stage.name] = StageResult(status=StageStatus.FAILED, error=str(e))
                break

        return results

    def reset(self) -> None:
        """Clear all saved state, allowing the pipeline to run from scratch."""
        if self._state_path.exists():
            self._state_path.unlink()

    def _load_state(self) -> set[str]:
        if self._state_path.exists():
            data = json.loads(self._state_path.read_text())
            return set(data.get("completed_stages", []))
        return set()

    def _save_state(self, completed: set[str]) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(json.dumps({"completed_stages": sorted(completed)}, indent=2))

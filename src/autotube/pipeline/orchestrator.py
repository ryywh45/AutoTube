import json
import logging
from typing import Any

from autotube.pipeline.run import PipelineRun
from autotube.pipeline.stage import Stage, StageResult, StageStatus

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Executes pipeline stages sequentially with pause/resume support.

    State is persisted to a JSON file so the pipeline can be interrupted
    and resumed from the last completed stage.
    """

    def __init__(self, stages: list[Stage]):
        self._stages = stages

    async def run(self, pipeline_run: PipelineRun, initial_input: Any = None) -> dict[str, StageResult]:
        """Run all stages sequentially, skipping already-completed stages.

        Args:
            pipeline_run: The run context (ID, output directory).
            initial_input: Input for the first stage.

        Returns:
            Dict mapping stage name to its result.
        """
        state_path = pipeline_run.run_dir / "pipeline_state.json"
        completed = self._load_state(state_path)
        results: dict[str, StageResult] = {}
        current_input = initial_input

        for stage in self._stages:
            if stage.name in completed:
                logger.info("Skipping completed stage: %s", stage.name)
                results[stage.name] = StageResult(status=StageStatus.SKIPPED)
                continue

            logger.info("Running stage: %s", stage.name)
            try:
                result = await stage.run(current_input, pipeline_run)
                results[stage.name] = result

                if result.status == StageStatus.COMPLETED:
                    completed.add(stage.name)
                    self._save_state(state_path, completed)
                    current_input = result.output
                else:
                    logger.error("Stage %s finished with status: %s", stage.name, result.status)
                    break
            except Exception as e:
                logger.exception("Stage %s failed with exception", stage.name)
                results[stage.name] = StageResult(status=StageStatus.FAILED, error=str(e))
                break

        return results

    @staticmethod
    def _load_state(state_path) -> set[str]:
        if state_path.exists():
            data = json.loads(state_path.read_text())
            return set(data.get("completed_stages", []))
        return set()

    @staticmethod
    def _save_state(state_path, completed: set[str]) -> None:
        state_path.write_text(json.dumps({"completed_stages": sorted(completed)}, indent=2))

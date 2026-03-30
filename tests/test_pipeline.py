import pytest
from pathlib import Path

from autotube.pipeline import Stage, StageResult, StageStatus, PipelineOrchestrator, PipelineRun


class AddOneStage(Stage):
    @property
    def name(self) -> str:
        return "add_one"

    async def run(self, input_data, pipeline_run):
        return StageResult(status=StageStatus.COMPLETED, output=input_data + 1)


class DoubleStage(Stage):
    @property
    def name(self) -> str:
        return "double"

    async def run(self, input_data, pipeline_run):
        return StageResult(status=StageStatus.COMPLETED, output=input_data * 2)


class FailingStage(Stage):
    @property
    def name(self) -> str:
        return "fail"

    async def run(self, input_data, pipeline_run):
        raise RuntimeError("boom")


class TestPipelineOrchestrator:
    @pytest.mark.asyncio
    async def test_sequential_execution(self, tmp_path: Path):
        run = PipelineRun("test", output_root=tmp_path)
        orchestrator = PipelineOrchestrator(stages=[AddOneStage(), DoubleStage()])
        results = await orchestrator.run(run, initial_input=5)
        assert results["add_one"].output == 6
        assert results["double"].output == 12

    @pytest.mark.asyncio
    async def test_resume_skips_completed(self, tmp_path: Path):
        run = PipelineRun("test", output_root=tmp_path)
        orchestrator = PipelineOrchestrator(stages=[AddOneStage(), DoubleStage()])
        # First run
        await orchestrator.run(run, initial_input=5)

        # Second run should skip both
        results = await orchestrator.run(run, initial_input=5)
        assert results["add_one"].status == StageStatus.SKIPPED
        assert results["double"].status == StageStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_stops_on_failure(self, tmp_path: Path):
        run = PipelineRun("test", output_root=tmp_path)
        orchestrator = PipelineOrchestrator(
            stages=[AddOneStage(), FailingStage(), DoubleStage()],
        )
        results = await orchestrator.run(run, initial_input=5)
        assert results["add_one"].status == StageStatus.COMPLETED
        assert results["fail"].status == StageStatus.FAILED
        assert "double" not in results

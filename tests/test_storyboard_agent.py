import json
from pathlib import Path

import pytest

from autotube.agents.storyboard_agent import StoryboardAgent
from autotube.llm.stub import StubLLMProvider
from autotube.models.script import Script
from autotube.models.storyboard import Storyboard
from autotube.pipeline.run import PipelineRun
from autotube.pipeline.stage import StageStatus


class _StoryboardStubProvider(StubLLMProvider):
    async def generate_structured(self, prompt, *, system="", response_model=None, **kwargs):
        # Return the internal _LLMStoryboardOutput structure
        return response_model.model_validate(
            {
                "scenes": [
                    {
                        "narration": "歡迎收看本期影片。",
                        "visual_description": "A warm sunrise over a calm ocean, cinematic wide shot",
                    },
                    {
                        "narration": "今天要介紹的是測試概念。",
                        "visual_description": "Close-up of a scientist examining data on a screen",
                    },
                ]
            }
        )


def _make_script() -> Script:
    return Script(
        title="測試影片",
        concept="測試概念",
        sections=[
            {"heading": "開場", "narration": "歡迎收看本期影片。"},
            {"heading": "主題", "narration": "今天要介紹的是測試概念。"},
        ],
    )


class TestStoryboardAgent:
    @pytest.mark.asyncio
    async def test_generates_storyboard(self, tmp_path: Path):
        run = PipelineRun("test", output_root=tmp_path)
        agent = StoryboardAgent(llm=_StoryboardStubProvider())
        result = await agent.run(_make_script(), run)
        assert result.status == StageStatus.COMPLETED
        assert isinstance(result.output, Storyboard)
        assert len(result.output.scenes) == 2
        assert result.output.scenes[0].scene_index == 1

    @pytest.mark.asyncio
    async def test_saves_storyboard_json(self, tmp_path: Path):
        run = PipelineRun("test", output_root=tmp_path)
        agent = StoryboardAgent(llm=_StoryboardStubProvider())
        await agent.run(_make_script(), run)
        sb_file = run.stage_dir("storyboard_agent") / "storyboard.json"
        assert sb_file.exists()
        data = json.loads(sb_file.read_text(encoding="utf-8"))
        assert len(data["scenes"]) == 2

    @pytest.mark.asyncio
    async def test_generates_placeholder_images(self, tmp_path: Path):
        run = PipelineRun("test", output_root=tmp_path)
        agent = StoryboardAgent(llm=_StoryboardStubProvider())
        result = await agent.run(_make_script(), run)
        for scene in result.output.scenes:
            assert scene.image_path is not None
            assert Path(scene.image_path).exists()

    @pytest.mark.asyncio
    async def test_rejects_non_script_input(self, tmp_path: Path):
        run = PipelineRun("test", output_root=tmp_path)
        agent = StoryboardAgent(llm=_StoryboardStubProvider())
        result = await agent.run("not a script", run)
        assert result.status == StageStatus.FAILED

    @pytest.mark.asyncio
    async def test_stage_name(self):
        agent = StoryboardAgent(llm=_StoryboardStubProvider())
        assert agent.name == "storyboard_agent"

import json
from pathlib import Path

import pytest

from autotube.agents.script_agent import ScriptAgent
from autotube.llm.stub import StubLLMProvider
from autotube.models.script import Script
from autotube.pipeline.run import PipelineRun
from autotube.pipeline.stage import StageStatus


class _ScriptStubProvider(StubLLMProvider):
    """Stub that returns a valid Script JSON for structured generation."""

    async def generate_structured(self, prompt, *, system="", response_model=None, **kwargs):
        return Script(
            title="測試影片",
            concept="測試概念",
            sections=[
                {"heading": "開場", "narration": "歡迎收看本期影片。"},
                {"heading": "主題", "narration": "今天要介紹的是測試概念。"},
                {"heading": "結尾", "narration": "感謝收看，我們下次見。"},
            ],
        )


class TestScriptAgent:
    @pytest.mark.asyncio
    async def test_generates_script(self, tmp_path: Path):
        run = PipelineRun("test", output_root=tmp_path)
        agent = ScriptAgent(llm=_ScriptStubProvider())
        result = await agent.run("測試概念", run)
        assert result.status == StageStatus.COMPLETED
        assert isinstance(result.output, Script)
        assert result.output.title == "測試影片"
        assert len(result.output.sections) == 3

    @pytest.mark.asyncio
    async def test_saves_script_json(self, tmp_path: Path):
        run = PipelineRun("test", output_root=tmp_path)
        agent = ScriptAgent(llm=_ScriptStubProvider())
        await agent.run("測試概念", run)
        script_file = run.stage_dir("script_agent") / "script.json"
        assert script_file.exists()
        data = json.loads(script_file.read_text(encoding="utf-8"))
        assert data["title"] == "測試影片"

    @pytest.mark.asyncio
    async def test_rejects_empty_input(self, tmp_path: Path):
        run = PipelineRun("test", output_root=tmp_path)
        agent = ScriptAgent(llm=_ScriptStubProvider())
        result = await agent.run("", run)
        assert result.status == StageStatus.FAILED

    @pytest.mark.asyncio
    async def test_rejects_non_string_input(self, tmp_path: Path):
        run = PipelineRun("test", output_root=tmp_path)
        agent = ScriptAgent(llm=_ScriptStubProvider())
        result = await agent.run(123, run)
        assert result.status == StageStatus.FAILED

    @pytest.mark.asyncio
    async def test_stage_name(self):
        agent = ScriptAgent(llm=_ScriptStubProvider())
        assert agent.name == "script_agent"

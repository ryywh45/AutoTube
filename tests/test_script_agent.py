import json
from pathlib import Path

import pytest

from autotube.agents.script_agent import ScriptAgent
from autotube.llm.stub import StubLLMProvider
from autotube.models.script import Script
from autotube.pipeline.run import PipelineRun
from autotube.pipeline.stage import StageStatus


class _ScriptStubProvider(StubLLMProvider):
    """Stub that dispatches on response_model to feed each sub-stage."""

    async def generate_structured(self, prompt, *, system="", response_model=None, **kwargs):
        name = response_model.__name__
        if name == "_ResearchNotes":
            return response_model.model_validate(
                {
                    "real_scenes": ["場景 1", "場景 2", "場景 3", "場景 4"],
                    "inner_voices": ["心聲 1", "心聲 2", "心聲 3", "心聲 4"],
                    "counterintuitive_points": ["反直覺 1", "反直覺 2"],
                    "interesting_angles": ["角度 1", "角度 2", "角度 3"],
                    "takeaway": "看完之後想一下自己的選擇。",
                }
            )
        if name == "_Outline":
            return response_model.model_validate(
                {
                    "title": "測試影片",
                    "sections": [
                        {
                            "heading": "開場",
                            "core_argument": "引起興趣",
                            "target_char_count": 200,
                            "role": "拋出觀眾共鳴的場景",
                        },
                        {
                            "heading": "主題",
                            "core_argument": "核心內容",
                            "target_char_count": 600,
                            "role": "翻轉常見的誤解",
                        },
                        {
                            "heading": "結尾",
                            "core_argument": "呼籲行動",
                            "target_char_count": 200,
                            "role": "給一個讓人重新思考的結尾",
                        },
                    ],
                }
            )
        if name == "_SectionDraft":
            return response_model.model_validate({"narration": "這是這一段的旁白文字。"})
        if name == "_PolishedScript":
            return response_model.model_validate(
                {
                    "sections": [
                        {"heading": "開場", "narration": "歡迎收看本期影片。"},
                        {"heading": "主題", "narration": "今天要介紹的是測試概念。"},
                        {"heading": "結尾", "narration": "感謝收看，我們下次見。"},
                    ],
                }
            )
        return response_model.model_validate({})


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

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from autotube.agents.tts_agent import TTSAgent
from autotube.models.audio import AudioSegment
from autotube.models.storyboard import Storyboard, StoryboardScene
from autotube.pipeline.run import PipelineRun
from autotube.pipeline.stage import StageStatus


def _make_storyboard() -> Storyboard:
    return Storyboard(
        title="測試影片",
        scenes=[
            StoryboardScene(
                scene_index=1,
                narration="歡迎收看本期影片。",
                visual_description="A warm sunrise over a calm ocean",
                image_path=None,
            ),
            StoryboardScene(
                scene_index=2,
                narration="今天要介紹的是測試概念。",
                visual_description="Close-up of a scientist examining data",
                image_path=None,
            ),
        ],
    )


def _mock_edge_tts_communicate(text, voice):
    """Return a mock Communicate object with an async save method."""
    mock = AsyncMock()

    async def fake_save(path):
        # Write a small dummy file so the path exists
        Path(path).write_bytes(b"\x00" * 100)

    mock.save = fake_save
    return mock


class TestTTSAgent:
    @pytest.mark.asyncio
    async def test_generates_audio_segments(self, tmp_path: Path):
        run = PipelineRun("test", output_root=tmp_path)
        agent = TTSAgent(voice="zh-TW-HsiaoChenNeural")

        with (
            patch("autotube.agents.tts_agent.edge_tts") as mock_tts,
            patch("autotube.agents.tts_agent._get_audio_duration", return_value=3.5),
        ):
            mock_tts.Communicate = _mock_edge_tts_communicate

            result = await agent.run(_make_storyboard(), run)

        assert result.status == StageStatus.COMPLETED
        storyboard, segments = result.output
        assert isinstance(storyboard, Storyboard)
        assert len(segments) == 2
        assert all(isinstance(s, AudioSegment) for s in segments)
        assert segments[0].scene_index == 1
        assert segments[1].scene_index == 2
        assert segments[0].duration_seconds == 3.5

    @pytest.mark.asyncio
    async def test_saves_audio_files(self, tmp_path: Path):
        run = PipelineRun("test", output_root=tmp_path)
        agent = TTSAgent()

        with (
            patch("autotube.agents.tts_agent.edge_tts") as mock_tts,
            patch("autotube.agents.tts_agent._get_audio_duration", return_value=2.0),
        ):
            mock_tts.Communicate = _mock_edge_tts_communicate

            result = await agent.run(_make_storyboard(), run)

        _, segments = result.output
        for seg in segments:
            assert seg.audio_path is not None
            assert Path(seg.audio_path).exists()

    @pytest.mark.asyncio
    async def test_saves_metadata_json(self, tmp_path: Path):
        run = PipelineRun("test", output_root=tmp_path)
        agent = TTSAgent()

        with (
            patch("autotube.agents.tts_agent.edge_tts") as mock_tts,
            patch("autotube.agents.tts_agent._get_audio_duration", return_value=2.0),
        ):
            mock_tts.Communicate = _mock_edge_tts_communicate

            await agent.run(_make_storyboard(), run)

        meta = run.stage_dir("tts_agent") / "audio_segments.json"
        assert meta.exists()
        data = json.loads(meta.read_text(encoding="utf-8"))
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_rejects_non_storyboard_input(self, tmp_path: Path):
        run = PipelineRun("test", output_root=tmp_path)
        agent = TTSAgent()
        result = await agent.run("not a storyboard", run)
        assert result.status == StageStatus.FAILED

    @pytest.mark.asyncio
    async def test_stage_name(self):
        agent = TTSAgent()
        assert agent.name == "tts_agent"

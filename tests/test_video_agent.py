import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from autotube.agents.video_agent import VideoSynthesisAgent
from autotube.models.audio import AudioSegment
from autotube.models.storyboard import Storyboard, StoryboardScene
from autotube.models.video import VideoProject
from autotube.pipeline.run import PipelineRun
from autotube.pipeline.stage import StageStatus


def _make_input(tmp_path: Path) -> tuple[Storyboard, list[AudioSegment]]:
    """Create a valid (Storyboard, AudioSegments) input with real files."""
    # Create dummy image files
    img1 = tmp_path / "img1.png"
    img2 = tmp_path / "img2.png"
    img1.write_bytes(b"\x89PNG" + b"\x00" * 100)
    img2.write_bytes(b"\x89PNG" + b"\x00" * 100)

    # Create dummy audio files
    aud1 = tmp_path / "aud1.mp3"
    aud2 = tmp_path / "aud2.mp3"
    aud1.write_bytes(b"\x00" * 100)
    aud2.write_bytes(b"\x00" * 100)

    storyboard = Storyboard(
        title="測試影片",
        scenes=[
            StoryboardScene(
                scene_index=1,
                narration="歡迎收看本期影片。",
                visual_description="A warm sunrise",
                image_path=img1,
            ),
            StoryboardScene(
                scene_index=2,
                narration="今天要介紹的是測試概念。",
                visual_description="A scientist",
                image_path=img2,
            ),
        ],
    )
    segments = [
        AudioSegment(scene_index=1, text="歡迎收看本期影片。", audio_path=aud1, duration_seconds=3.0),
        AudioSegment(scene_index=2, text="今天要介紹的是測試概念。", audio_path=aud2, duration_seconds=4.0),
    ]
    return storyboard, segments


def _make_fake_subprocess(output_dir: Path):
    """Create a mock subprocess that writes dummy mp4 files."""

    async def fake_exec(*args, **kwargs):
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))

        # If ffmpeg is creating a scene video or final video, create the output file
        args_list = list(args)
        if "ffmpeg" in str(args_list[0]):
            # The output path is the last argument
            out_path = Path(args_list[-1])
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(b"\x00" * 100)

        return mock_proc

    return fake_exec


class TestVideoSynthesisAgent:
    @pytest.mark.asyncio
    async def test_synthesizes_video(self, tmp_path: Path):
        run = PipelineRun("test", output_root=tmp_path)
        agent = VideoSynthesisAgent(fps=30)
        input_data = _make_input(tmp_path)

        with patch("asyncio.create_subprocess_exec", side_effect=_make_fake_subprocess(tmp_path)):
            result = await agent.run(input_data, run)

        assert result.status == StageStatus.COMPLETED
        assert isinstance(result.output, VideoProject)
        assert result.output.output_path is not None

    @pytest.mark.asyncio
    async def test_creates_final_video_file(self, tmp_path: Path):
        run = PipelineRun("test", output_root=tmp_path)
        agent = VideoSynthesisAgent()
        input_data = _make_input(tmp_path)

        with patch("asyncio.create_subprocess_exec", side_effect=_make_fake_subprocess(tmp_path)):
            result = await agent.run(input_data, run)

        assert Path(result.output.output_path).exists()

    @pytest.mark.asyncio
    async def test_saves_project_metadata(self, tmp_path: Path):
        run = PipelineRun("test", output_root=tmp_path)
        agent = VideoSynthesisAgent()
        input_data = _make_input(tmp_path)

        with patch("asyncio.create_subprocess_exec", side_effect=_make_fake_subprocess(tmp_path)):
            await agent.run(input_data, run)

        meta = run.stage_dir("video_synthesis") / "video_project.json"
        assert meta.exists()
        data = json.loads(meta.read_text(encoding="utf-8"))
        assert data["concept"] == "測試影片"
        assert len(data["scenes"]) == 2

    @pytest.mark.asyncio
    async def test_rejects_invalid_input(self, tmp_path: Path):
        run = PipelineRun("test", output_root=tmp_path)
        agent = VideoSynthesisAgent()
        result = await agent.run("not valid", run)
        assert result.status == StageStatus.FAILED

    @pytest.mark.asyncio
    async def test_rejects_missing_image(self, tmp_path: Path):
        run = PipelineRun("test", output_root=tmp_path)
        agent = VideoSynthesisAgent()

        storyboard = Storyboard(
            title="test",
            scenes=[
                StoryboardScene(
                    scene_index=1,
                    narration="test",
                    visual_description="test",
                    image_path=None,
                ),
            ],
        )
        segments = [AudioSegment(scene_index=1, text="test", audio_path=tmp_path / "a.mp3", duration_seconds=1.0)]

        result = await agent.run((storyboard, segments), run)
        assert result.status == StageStatus.FAILED
        assert "no image_path" in result.error

    @pytest.mark.asyncio
    async def test_stage_name(self):
        agent = VideoSynthesisAgent()
        assert agent.name == "video_synthesis"

    @pytest.mark.asyncio
    async def test_estimates_format(self, tmp_path: Path):
        run = PipelineRun("test", output_root=tmp_path)
        agent = VideoSynthesisAgent()
        input_data = _make_input(tmp_path)

        with patch("asyncio.create_subprocess_exec", side_effect=_make_fake_subprocess(tmp_path)):
            result = await agent.run(input_data, run)

        # 3.0 + 4.0 = 7.0s < 60s → SHORT
        assert result.output.format == "short"

    @pytest.mark.asyncio
    async def test_concat_list_uses_absolute_paths(self, tmp_path: Path):
        """Ensure concat_list.txt uses absolute paths so ffmpeg resolves them correctly."""
        run = PipelineRun("test", output_root=tmp_path)
        agent = VideoSynthesisAgent()
        input_data = _make_input(tmp_path)

        concat_contents: list[str] = []

        original_make_fake = _make_fake_subprocess(tmp_path)

        async def capturing_exec(*args, **kwargs):
            args_list = list(args)
            # Intercept the concat step to capture the list file
            if "concat" in args_list and "-i" in args_list:
                idx = args_list.index("-i") + 1
                list_path = Path(args_list[idx])
                if list_path.exists():
                    concat_contents.append(list_path.read_text(encoding="utf-8"))
            return await original_make_fake(*args, **kwargs)

        with patch("asyncio.create_subprocess_exec", side_effect=capturing_exec):
            result = await agent.run(input_data, run)

        assert result.status == StageStatus.COMPLETED
        assert len(concat_contents) == 1
        for line in concat_contents[0].strip().splitlines():
            # Each line should be: file '/absolute/path/to/scene_XX.mp4'
            path_str = line.split("'")[1]
            assert Path(path_str).is_absolute(), f"Path in concat list is not absolute: {path_str}"

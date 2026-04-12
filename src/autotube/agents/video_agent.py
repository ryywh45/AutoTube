import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from autotube.models.audio import AudioSegment
from autotube.models.storyboard import Storyboard
from autotube.models.video import VideoProject, VideoFormat
from autotube.pipeline.run import PipelineRun
from autotube.pipeline.stage import Stage, StageResult, StageStatus

logger = logging.getLogger(__name__)


async def _make_scene_video(
    image_path: Path,
    audio_path: Path,
    output_path: Path,
    fps: int = 30,
) -> Path:
    """Create a video clip from a single image + audio using ffmpeg.

    Applies a slow zoom-in (Ken Burns) effect for visual interest.
    """
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(image_path),
        "-i", str(audio_path),
        "-vf", (
            # Slow zoom from 100% to 110% over the clip duration
            "scale=8000:-1,"
            "zoompan=z='min(zoom+0.0005,1.1)'"
            ":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d=1:s=1920x1080:fps={fps},"
            f"fps={fps}"
        ),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-pix_fmt", "yuv420p",
        str(output_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed for {image_path.name}: {stderr.decode()[-500:]}"
        )
    return output_path


async def _concat_videos(
    scene_videos: list[Path],
    output_path: Path,
) -> Path:
    """Concatenate scene videos into a single video using ffmpeg concat demuxer."""
    concat_list = output_path.parent / "concat_list.txt"
    concat_list.write_text(
        "\n".join(f"file '{v}'" for v in scene_videos),
        encoding="utf-8",
    )

    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(output_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg concat failed: {stderr.decode()[-500:]}")

    concat_list.unlink()
    return output_path


class VideoSynthesisAgent(Stage):
    """Pipeline stage that combines scene images and audio into a final video."""

    def __init__(self, fps: int = 30):
        self._fps = fps

    @property
    def name(self) -> str:
        return "video_synthesis"

    async def run(self, input_data: Any, pipeline_run: PipelineRun) -> StageResult:
        if not (
            isinstance(input_data, tuple)
            and len(input_data) == 2
            and isinstance(input_data[0], Storyboard)
            and isinstance(input_data[1], list)
        ):
            return StageResult(
                status=StageStatus.FAILED,
                error="Input must be a (Storyboard, list[AudioSegment]) tuple.",
            )

        storyboard: Storyboard = input_data[0]
        segments: list[AudioSegment] = input_data[1]

        logger.info("Synthesizing video for %d scenes", len(storyboard.scenes))

        try:
            output_dir = pipeline_run.stage_dir(self.name)

            # Build scene videos
            scene_videos: list[Path] = []
            for scene, segment in zip(storyboard.scenes, segments):
                if scene.image_path is None:
                    return StageResult(
                        status=StageStatus.FAILED,
                        error=f"Scene {scene.scene_index} has no image_path.",
                    )
                if segment.audio_path is None:
                    return StageResult(
                        status=StageStatus.FAILED,
                        error=f"Scene {segment.scene_index} has no audio_path.",
                    )

                clip_path = output_dir / f"scene_{scene.scene_index:02d}.mp4"
                await _make_scene_video(
                    image_path=Path(scene.image_path),
                    audio_path=Path(segment.audio_path),
                    output_path=clip_path,
                    fps=self._fps,
                )
                scene_videos.append(clip_path)
                logger.info("Scene %d video created", scene.scene_index)

            # Concatenate all scenes
            final_path = output_dir / "final.mp4"
            await _concat_videos(scene_videos, final_path)

            total_duration = sum(s.duration_seconds or 0 for s in segments)
            logger.info("Final video: %s (%.1fs)", final_path, total_duration)

            video_project = VideoProject(
                concept=storyboard.title,
                format=_estimate_format(total_duration),
                scenes=storyboard.scenes,
                audio_segments=segments,
                output_path=final_path,
            )

            # Save project metadata
            meta_path = output_dir / "video_project.json"
            serializable = video_project.model_dump()
            for key in ("output_path",):
                if serializable.get(key):
                    serializable[key] = str(serializable[key])
            for s in serializable.get("scenes", []):
                if s.get("image_path"):
                    s["image_path"] = str(s["image_path"])
            for s in serializable.get("audio_segments", []):
                if s.get("audio_path"):
                    s["audio_path"] = str(s["audio_path"])
            meta_path.write_text(
                json.dumps(serializable, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            return StageResult(status=StageStatus.COMPLETED, output=video_project)
        except Exception as e:
            logger.exception("Video synthesis failed")
            return StageResult(status=StageStatus.FAILED, error=str(e))


def _estimate_format(duration_seconds: float) -> VideoFormat:
    if duration_seconds < 60:
        return VideoFormat.SHORT
    elif duration_seconds < 360:
        return VideoFormat.MEDIUM
    else:
        return VideoFormat.LONG

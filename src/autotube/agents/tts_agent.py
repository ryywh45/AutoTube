import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import edge_tts

from autotube.models.audio import AudioSegment
from autotube.models.storyboard import Storyboard
from autotube.pipeline.run import PipelineRun
from autotube.pipeline.stage import Stage, StageResult, StageStatus

logger = logging.getLogger(__name__)

# Microsoft Edge TTS voices for Chinese
DEFAULT_VOICE = "zh-TW-HsiaoChenNeural"  # Female, Traditional Chinese


async def _get_audio_duration(audio_path: Path) -> float:
    """Get audio duration in seconds using ffprobe."""
    proc = await asyncio.create_subprocess_exec(
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        str(audio_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    info = json.loads(stdout)
    return float(info["format"]["duration"])


async def _synthesize_scene(
    scene_index: int,
    text: str,
    output_dir: Path,
    voice: str,
) -> AudioSegment:
    """Generate TTS audio for a single scene."""
    audio_path = output_dir / f"scene_{scene_index:02d}.mp3"

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(audio_path))

    duration = await _get_audio_duration(audio_path)

    logger.info("Scene %d TTS: %.1fs -> %s", scene_index, duration, audio_path)
    return AudioSegment(
        scene_index=scene_index,
        text=text,
        audio_path=audio_path,
        duration_seconds=duration,
    )


class TTSAgent(Stage):
    """Pipeline stage that generates per-scene TTS audio using edge-tts."""

    def __init__(self, voice: str = DEFAULT_VOICE):
        self._voice = voice

    @property
    def name(self) -> str:
        return "tts_agent"

    async def run(self, input_data: Any, pipeline_run: PipelineRun) -> StageResult:
        if not isinstance(input_data, Storyboard):
            return StageResult(
                status=StageStatus.FAILED,
                error="Input must be a Storyboard instance.",
            )

        storyboard: Storyboard = input_data
        logger.info(
            "Generating TTS for %d scenes (voice: %s)",
            len(storyboard.scenes),
            self._voice,
        )

        try:
            output_dir = pipeline_run.stage_dir(self.name)

            segments: list[AudioSegment] = []
            for scene in storyboard.scenes:
                segment = await _synthesize_scene(
                    scene.scene_index,
                    scene.narration,
                    output_dir,
                    self._voice,
                )
                segments.append(segment)

            total_duration = sum(s.duration_seconds for s in segments)
            logger.info(
                "TTS complete: %d segments, total %.1fs",
                len(segments),
                total_duration,
            )

            # Save segments metadata
            meta_path = output_dir / "audio_segments.json"
            serializable = [s.model_dump() for s in segments]
            for s in serializable:
                if s.get("audio_path"):
                    s["audio_path"] = str(s["audio_path"])
            meta_path.write_text(
                json.dumps(serializable, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            return StageResult(
                status=StageStatus.COMPLETED,
                output=(storyboard, segments),
            )
        except Exception as e:
            logger.exception("TTS generation failed")
            return StageResult(status=StageStatus.FAILED, error=str(e))

import asyncio
import logging
import sys

from autotube.agents.script_agent import ScriptAgent
from autotube.agents.storyboard_agent import StoryboardAgent
from autotube.agents.tts_agent import TTSAgent
from autotube.agents.video_agent import VideoSynthesisAgent
from autotube.config import load_settings
from autotube.llm.gemini import GeminiProvider
from autotube.pipeline.orchestrator import PipelineOrchestrator
from autotube.pipeline.run import PipelineRun
from autotube.pipeline.stage import StageStatus

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")


async def main():
    concept = sys.argv[1] if len(sys.argv) > 1 else "為什麼天空是藍色的"

    settings = load_settings()
    llm = GeminiProvider(api_key=settings.gemini_api_key)
    run = PipelineRun(concept, output_root=settings.output_dir)

    pipeline = PipelineOrchestrator(
        stages=[
            ScriptAgent(llm=llm),
            StoryboardAgent(llm=llm),
            TTSAgent(voice=settings.tts.voice),
            VideoSynthesisAgent(fps=settings.video.fps),
        ],
    )
    results = await pipeline.run(run, initial_input=concept)

    print(f"\nRun ID: {run.run_id}")
    print(f"Output: {run.run_dir}")

    # Print script
    script_result = results.get("script_agent")
    if script_result and script_result.status == StageStatus.COMPLETED:
        script = script_result.output
        print(f"\n{'='*60}")
        print(f"Title: {script.title}")
        print(f"Sections: {len(script.sections)}")
        print(f"Est. duration: {script.estimated_duration_seconds:.0f}s")
        print(f"{'='*60}")
        for section in script.sections:
            print(f"\n## {section.heading}\n")
            print(section.narration)

    # Print storyboard
    sb_result = results.get("storyboard_agent")
    if sb_result and sb_result.status == StageStatus.COMPLETED:
        storyboard = sb_result.output
        print(f"\n{'='*60}")
        print(f"Storyboard: {len(storyboard.scenes)} scenes")
        print(f"{'='*60}")
        for scene in storyboard.scenes:
            print(f"\n[Scene {scene.scene_index}] {scene.visual_description}")
            print(f"  Narration: {scene.narration[:60]}...")
            if scene.image_path:
                print(f"  Image: {scene.image_path}")

    # Print TTS results
    tts_result = results.get("tts_agent")
    if tts_result and tts_result.status == StageStatus.COMPLETED:
        _, segments = tts_result.output
        total = sum(s.duration_seconds for s in segments)
        print(f"\n{'='*60}")
        print(f"TTS: {len(segments)} segments, total {total:.1f}s")
        print(f"{'='*60}")
        for seg in segments:
            print(f"  Scene {seg.scene_index}: {seg.duration_seconds:.1f}s -> {seg.audio_path}")

    # Print video results
    video_result = results.get("video_synthesis")
    if video_result and video_result.status == StageStatus.COMPLETED:
        vp = video_result.output
        print(f"\n{'='*60}")
        print(f"Video: {vp.output_path}")
        print(f"Format: {vp.format}")
        print(f"{'='*60}")

    # Check for failures
    for name, result in results.items():
        if result.status == StageStatus.FAILED:
            print(f"\nFAILED at {name}: {result.error}")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

import json
import logging
from typing import Any

from pydantic import BaseModel

from autotube.llm.base import LLMProvider
from autotube.models.script import Script
from autotube.models.storyboard import Storyboard, StoryboardScene
from autotube.pipeline.run import PipelineRun
from autotube.pipeline.stage import Stage, StageResult, StageStatus

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
你是一位專業的影片分鏡師。你的任務是將影片講稿拆分成分鏡場景。

要求：
- 每個場景大約對應 15-25 秒的旁白
- 在語義自然斷點處切割（場景轉換、新概念、情緒轉折）
- 為每個場景撰寫具體的畫面描述，描述要能直接用於文生圖
- 畫面描述使用英文（適合圖片生成模型）
- 旁白文字保持繁體中文原文，不要修改或摘要
- 3-5 分鐘的影片通常拆成 8-15 個場景
"""

USER_PROMPT_TEMPLATE = """\
請將以下影片講稿拆分成分鏡場景。

影片標題：{title}

完整講稿：
{narration}

請以 JSON 格式回覆，結構如下：
{{
  "scenes": [
    {{
      "narration": "該場景對應的旁白原文（繁體中文）",
      "visual_description": "Scene visual description in English, detailed enough for image generation"
    }}
  ]
}}

重要：
1. 旁白必須是原文的完整切割，所有旁白文字都必須被涵蓋，不可遺漏或修改
2. 畫面描述要具體、視覺化，包含場景、物件、色調、構圖等細節
"""


class _LLMSceneOutput(BaseModel):
    """Schema for LLM structured output — no scene_index or image_path."""

    narration: str
    visual_description: str


class _LLMStoryboardOutput(BaseModel):
    scenes: list[_LLMSceneOutput]


def _generate_placeholder(scene: StoryboardScene, output_dir: PipelineRun, stage_name: str) -> StoryboardScene:
    """Generate a placeholder image with the visual description as text."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        logger.warning("Pillow not installed, skipping placeholder image generation")
        return scene

    img = Image.new("RGB", (1920, 1080), color=(30, 30, 30))
    draw = ImageDraw.Draw(img)

    # Scene number
    draw.text((60, 40), f"Scene {scene.scene_index}", fill=(255, 255, 255))

    # Visual description (wrap text manually)
    y = 120
    line = ""
    for char in scene.visual_description:
        line += char
        if len(line) >= 60 or char == "\n":
            draw.text((60, y), line.strip(), fill=(200, 200, 200))
            y += 30
            line = ""
    if line:
        draw.text((60, y), line.strip(), fill=(200, 200, 200))

    img_dir = output_dir.stage_dir(stage_name)
    img_path = img_dir / f"scene_{scene.scene_index:02d}.png"
    img.save(img_path)
    return scene.model_copy(update={"image_path": img_path})


class StoryboardAgent(Stage):
    """Pipeline stage that splits a script into storyboard scenes using LLM."""

    def __init__(self, llm: LLMProvider):
        self._llm = llm

    @property
    def name(self) -> str:
        return "storyboard_agent"

    async def run(self, input_data: Any, pipeline_run: PipelineRun) -> StageResult:
        if not isinstance(input_data, Script):
            return StageResult(
                status=StageStatus.FAILED,
                error="Input must be a Script instance.",
            )
        script: Script = input_data

        logger.info("Generating storyboard for: %s", script.title)
        try:
            llm_output = await self._llm.generate_structured(
                prompt=USER_PROMPT_TEMPLATE.format(
                    title=script.title,
                    narration=script.full_narration,
                ),
                system=SYSTEM_PROMPT,
                response_model=_LLMStoryboardOutput,
            )

            scenes = [
                StoryboardScene(
                    scene_index=i + 1,
                    narration=s.narration,
                    visual_description=s.visual_description,
                )
                for i, s in enumerate(llm_output.scenes)
            ]

            # Generate placeholder images
            scenes = [_generate_placeholder(s, pipeline_run, self.name) for s in scenes]

            storyboard = Storyboard(title=script.title, scenes=scenes)

            logger.info("Storyboard generated: %d scenes", len(scenes))

            # Save storyboard JSON
            out_path = pipeline_run.stage_dir(self.name) / "storyboard.json"
            serializable = storyboard.model_dump()
            # Convert Path to string for JSON
            for s in serializable["scenes"]:
                if s.get("image_path"):
                    s["image_path"] = str(s["image_path"])
            out_path.write_text(
                json.dumps(serializable, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info("Storyboard saved to %s", out_path)

            return StageResult(status=StageStatus.COMPLETED, output=storyboard)
        except Exception as e:
            logger.exception("Storyboard generation failed")
            return StageResult(status=StageStatus.FAILED, error=str(e))

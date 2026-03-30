import json
import logging
from typing import Any

from autotube.llm.base import LLMProvider
from autotube.models.script import Script
from autotube.pipeline.run import PipelineRun
from autotube.pipeline.stage import Stage, StageResult, StageStatus

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
你是一位專業的 YouTube 影片腳本撰寫者。你的任務是根據給定的概念，撰寫一份結構完整的中文影片講稿。

要求：
- 講稿需要有清楚的段落結構（開場、主要內容段落、結尾）
- 語氣自然、口語化，適合旁白朗讀
- 使用繁體中文
- 目標長度：3-5 分鐘的影片（約 720-1200 字的旁白文字）
"""

USER_PROMPT_TEMPLATE = """\
請為以下概念撰寫一份 YouTube 影片講稿：

概念：{concept}

請以 JSON 格式回覆，結構如下：
{{
  "title": "影片標題",
  "concept": "{concept}",
  "sections": [
    {{
      "heading": "段落標題",
      "narration": "該段落的旁白文字"
    }}
  ]
}}

請確保：
1. 包含至少 3 個段落（開場、主要內容、結尾）
2. 總旁白字數在 720-1200 字之間
3. 內容準確、有趣且適合一般觀眾
"""


class ScriptAgent(Stage):
    """Pipeline stage that generates a video script from a concept using LLM."""

    def __init__(self, llm: LLMProvider):
        self._llm = llm

    @property
    def name(self) -> str:
        return "script_agent"

    async def run(self, input_data: Any, pipeline_run: PipelineRun) -> StageResult:
        concept: str = input_data
        if not concept or not isinstance(concept, str):
            return StageResult(
                status=StageStatus.FAILED,
                error="Input must be a non-empty string concept.",
            )

        logger.info("Generating script for concept: %s", concept)
        try:
            script = await self._llm.generate_structured(
                prompt=USER_PROMPT_TEMPLATE.format(concept=concept),
                system=SYSTEM_PROMPT,
                response_model=Script,
            )
            logger.info(
                "Script generated: %s (%d sections, ~%.0fs)",
                script.title,
                len(script.sections),
                script.estimated_duration_seconds,
            )

            out_path = pipeline_run.stage_dir(self.name) / "script.json"
            out_path.write_text(
                json.dumps(script.model_dump(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info("Script saved to %s", out_path)

            return StageResult(status=StageStatus.COMPLETED, output=script)
        except Exception as e:
            logger.exception("Script generation failed")
            return StageResult(status=StageStatus.FAILED, error=str(e))

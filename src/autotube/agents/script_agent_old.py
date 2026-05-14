import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from autotube.llm.base import LLMProvider
from autotube.models.script import Script, ScriptSection
from autotube.pipeline.run import PipelineRun
from autotube.pipeline.stage import Stage, StageResult, StageStatus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Stage A: Concept Expansion — 主題研究筆記
# ---------------------------------------------------------------------------

RESEARCH_SYSTEM_PROMPT = """\
你是一位資深的中文 YouTuber 的內容企劃夥伴。當給定一個主題時，你的工作
不是做學術分析，而是幫忙蒐集「能讓觀眾有共鳴的素材」。

你要找的是：
- 真實生活中會發生的場景（不是抽象的概念）
- 觀眾私下會跟朋友抱怨的事（不是新聞標題式的爭議）
- 能讓觀眾「對對對我也是這樣」的具體經驗
- 反直覺、有趣、或讓人意外的觀點

避免：
- 教科書式的分析框架（例如「從 A、B、C 三個維度切入」）
- 過於正式的詞彙（例如「機會成本」「資產配置」「總擁有成本」）
- 空泛的大道理

語言：繁體中文，思考時就用一般人講話的方式，不要用「分析報告」的語氣。
"""

RESEARCH_USER_PROMPT = """\
幫我針對「{concept}」這個主題蒐集影片素材。最終影片是 3-5 分鐘的中文 YouTube 影片。

請整理：

1. **真實場景（real_scenes）**：觀眾在日常生活中，什麼時候會想到這個主題？
   想出 4-6 個具體的生活場景，越具體越好。
   範例（不同主題）：「滑手機看到同學買房 PO 文」「過年被親戚問什麼時候買房」。

2. **內心 OS（inner_voices）**：觀眾私下會在心裡冒出來的真實想法或抱怨。
   想出 4-6 句，用第一人稱、口語化的方式寫。
   範例：「每次匯房租都覺得這錢好像在燒」「明明薪水也不低為什麼還是買不起」。

3. **反直覺觀點（counterintuitive_points）**：關於這個主題，有什麼是大多數人
   沒想過、或想錯了的？想出 2-4 個。

4. **可講的有趣切入點（interesting_angles）**：能讓觀眾覺得「這個角度沒看過」
   的切入方式。想出 3-5 個，每個用一句話描述。

5. **這支影片想讓觀眾帶走什麼（takeaway）**：用一兩句話描述。不是教條，
   而是觀眾看完之後，心裡會浮現的那個感受或想法。

請以 JSON 格式回覆：
{{
  "real_scenes": ["...", "..."],
  "inner_voices": ["...", "..."],
  "counterintuitive_points": ["...", "..."],
  "interesting_angles": ["...", "..."],
  "takeaway": "..."
}}
"""


class _ResearchNotes(BaseModel):
    real_scenes: list[str]
    inner_voices: list[str]
    counterintuitive_points: list[str]
    interesting_angles: list[str]
    takeaway: str


# ---------------------------------------------------------------------------
# Stage B: Outline Generation — 只有結構、沒有內容的大綱
# ---------------------------------------------------------------------------

OUTLINE_SYSTEM_PROMPT = """\
你是一位資深的中文 YouTube 影片結構規劃者。根據素材筆記，規劃影片的段落結構。

你的工作不是寫旁白，而是決定：
- 影片要分成幾段
- 每段要講什麼（一兩句話講清楚）
- 每段大概多長
- 每段在影片中扮演什麼角色

關於「段落角色」，請用以下方式思考（不要用敘事學術語）：
- 第一段：要在 15 秒內讓觀眾不想滑走（用問題、反差、或一個具體場景）
- 中間段落：每一段都應該推進論述、或翻轉觀眾的想法，避免變成「再來一個論點」
- 最後一段：給觀眾一個帶得走的東西（不一定是行動呼籲，可以是一個讓人安靜下來的觀點）

中文 3-5 分鐘影片總字數約 720-1200 字。

語言：繁體中文。
"""

OUTLINE_USER_PROMPT = """\
以下是針對「{concept}」蒐集的素材。請規劃影片的段落結構。

素材筆記：
{research_notes}

請規劃 4-6 個段落，每個段落寫出：
- heading：段落標題（給內部用，可以寫得直白一點，不必是最終影片用的標題）
- core_argument：這段要傳達的一個重點（一兩句話，用講人話的方式寫，不要用分析腔）
- target_char_count：預期字數
- role：這段在影片裡扮演什麼角色（用一句話描述，例如「拋出觀眾共鳴的場景，把人留下來」、
  「翻轉一個常見的誤解」、「給一個讓人重新思考的結尾」）

請以 JSON 格式回覆：
{{
  "title": "影片標題（這個會給觀眾看，要吸引人但不要標題黨）",
  "sections": [
    {{
      "heading": "...",
      "core_argument": "...",
      "target_char_count": 200,
      "role": "..."
    }}
  ]
}}

要求：
1. 段落數 4-6 段
2. 所有段落 target_char_count 加總在 720-1200 字之間
3. 第一段必須是抓注意力的段落，最後一段必須有收束感
4. 每段的 role 必須不一樣，避免「再講一個論點」式的平鋪直敘
"""


class _OutlineSection(BaseModel):
    heading: str
    core_argument: str
    target_char_count: int
    role: str


class _Outline(BaseModel):
    title: str
    sections: list[_OutlineSection]


# ---------------------------------------------------------------------------
# Stage C: Section-by-Section Writing — 逐段擴寫
# ---------------------------------------------------------------------------

SECTION_SYSTEM_PROMPT = """\
你是一位中文 YouTube 影片旁白撰稿者。你一次只負責寫一段。

# 你要寫出的東西

像一個朋友在跟你聊天的旁白。不是演講、不是教科書、不是新聞稿。
讀出來要像「人在講話」，不是「字在朗讀」。

# 必須避免的東西（重要）

**避免的詞彙**（這些詞會讓觀眾立刻感覺到 AI 感）：
- 「沉沒成本」「機會成本」「總擁有成本」「資產配置」「現金流」「對沖」
  「淨值」「複利」「指數型基金」等金融術語 → 改用「白花的錢」「能拿去做別的事的錢」
  「全部加起來的花費」這類說法
- 「核心」「本質」「關鍵在於」「值得思考的是」 → 直接講重點，不要鋪陳
- 「層面」「維度」「框架」「模型」「策略」 → 換成「角度」「方法」「想法」或乾脆刪掉

**避免的句式**：
- 「我們不談 X，而是 Y」這種對偶句（一段最多用一次）
- 「並非 A，而是 B」「不在於 X，而在於 Y」（一段最多用一次）
- 「想像一下...」「讓我們...」「準備好了嗎？」這類主持人引導語
- 「接下來」「總結來說」「綜上所述」這類連接詞
- 「值得我們深思」「令人驚訝的是」這類書面評論

**避免的結構**：
- 不要在段落結尾預告下一段（「接下來我們要看...」）
- 不要每段都用「總分總」收尾
- 不要每句都工工整整、長度差不多——口語有長有短，有時甚至會有不完整的句子

# 應該做的事

- **用具體取代抽象**：說「房貸」不要說「居住成本」；說「兩百萬」不要說「一筆資金」；
  說「你媽問你」不要說「來自家人的壓力」
- **用畫面取代論述**：每段至少要有一兩個具體的場景、人物、或物件，
  讓 storyboard 等下能轉成畫面。例如「打開 591 看到台北房價」「下班路上經過建案廣告」
- **保留口語的雜訊**：適當使用「其實」「就是」「對啊」「你看」「老實說」這類口語助詞，
  但不要每句都用
- **節奏要有變化**：可以一句很長、下一句很短。可以拋個問題、然後自己回答

# 不同段落的差異

- 抓注意力的段落：開頭一句就要有畫面或反差，不要先解釋背景
- 中間段落：聚焦一個重點，不要塞兩個
- 收尾段落：留個讓人想一下的東西，不要急著呼籲訂閱

語言：繁體中文。
"""

SECTION_USER_PROMPT = """\
請寫這一段的旁白。

影片標題：{title}
影片概念：{concept}

==== 這一段要寫什麼 ====
段落標題：{heading}
這段要講的重點：{core_argument}
目標字數：{target_char_count}（誤差 ±15%）
這段的角色：{role}

==== 前面已經寫好的段落（保持連貫，但不要重複） ====
{previous_sections}

==== 後面還沒寫的段落（不要劇透細節，但可以鋪陳） ====
{upcoming_sections}

==== 寫之前先想一下 ====
1. 這段的第一句話有畫面感嗎？會讓人想繼續看嗎？
2. 這段有沒有一兩個具體的場景或物件可以對應到畫面？
3. 我有沒有不小心用了金融術語或書面腔？
4. 這段結尾會不會太像「總結」或「預告」？

請以 JSON 格式回覆：
{{
  "narration": "這一段的旁白（繁體中文）"
}}
"""


class _SectionDraft(BaseModel):
    narration: str


# ---------------------------------------------------------------------------
# Stage D: Polish Pass — 全文潤稿，只做小幅修飾
# ---------------------------------------------------------------------------

POLISH_SYSTEM_PROMPT = """\
你是一位中文影片旁白的潤稿者。你會看到所有段落的初稿，做一次全文檢視。

# 重要原則

**只做小幅修飾，不重寫內容。** 不可改變每段的核心論點、不可改變段落順序、
不可改變段落標題、整體字數變動 ±10% 以內。

# 你要做的事

1. **去 AI 感**：找出讀起來像「AI 寫的」的句子，改成更像人講話的版本
   - 改掉金融術語、書面詞彙
   - 拆掉過多的對偶句（同段最多保留一個）
   - 移除「準備好了嗎？」「想像一下」這類主持人引導語
   - 拆掉太工整的句子，讓長短有變化

2. **去重複**：如果有兩段在講類似的事，把後面那段往別的方向修一下，
   不要全段重寫

3. **改銜接**：段落間如果有突兀的跳躍，加個轉折句；如果太多連接詞
   （「接著」「然後」「另外」），刪掉一些

4. **節奏微調**：如果某段全部都是長句子，拆一兩句變短；
   如果某段全部都是短句，合併一兩句

# 不要做的事

- 不要把口語助詞（「其實」「就是」「對啊」）全部刪掉，那會讓文字變硬
- 不要把所有句子改得「更精煉」，旁白需要呼吸感
- 不要為了「結構清晰」加上「首先、其次、最後」

語言：繁體中文。
"""

POLISH_USER_PROMPT = """\
以下是影片各段的初稿，請做潤稿。

影片標題：{title}
影片概念：{concept}

各段落初稿：
{sections}

請依序檢查：
- 哪些句子讀起來像 AI 寫的？怎麼改更像人講話？
- 段落之間銜接順嗎？
- 有沒有重複的論點？
- 每段的節奏有變化嗎？

請以 JSON 格式回覆，順序與輸入相同：
{{
  "sections": [
    {{
      "heading": "段落標題（保持不變）",
      "narration": "潤稿後的旁白"
    }}
  ]
}}
"""


class _PolishedSection(BaseModel):
    heading: str
    narration: str


class _PolishedScript(BaseModel):
    sections: list[_PolishedSection]


# ---------------------------------------------------------------------------
# ScriptAgent
# ---------------------------------------------------------------------------


class ScriptAgent(Stage):
    """Pipeline stage that generates a video script via four sub-stages:

    A. Concept Expansion — research notes about the topic
    B. Outline Generation — structure-only outline
    C. Section-by-Section Writing — iterative per-section drafting
    D. Polish Pass — full-text smoothing without rewriting
    """

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

        stage_dir = pipeline_run.stage_dir(self.name)
        try:
            research = await self._stage_a_research(concept, stage_dir)
            outline = await self._stage_b_outline(concept, research, stage_dir)
            drafts = await self._stage_c_write_sections(concept, outline, stage_dir)
            script = await self._stage_d_polish(concept, outline, drafts, stage_dir)
            return StageResult(status=StageStatus.COMPLETED, output=script)
        except Exception as e:
            logger.exception("Script generation failed")
            return StageResult(status=StageStatus.FAILED, error=str(e))

    async def _stage_a_research(self, concept: str, stage_dir: Path) -> _ResearchNotes:
        logger.info("[Stage A] Researching concept: %s", concept)
        notes = await self._llm.generate_structured(
            prompt=RESEARCH_USER_PROMPT.format(concept=concept),
            system=RESEARCH_SYSTEM_PROMPT,
            response_model=_ResearchNotes,
        )
        (stage_dir / "research_notes.json").write_text(
            json.dumps(notes.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(
            "[Stage A] Done — %d scenes, %d inner voices, %d counterintuitive, %d angles",
            len(notes.real_scenes),
            len(notes.inner_voices),
            len(notes.counterintuitive_points),
            len(notes.interesting_angles),
        )
        return notes

    async def _stage_b_outline(
        self, concept: str, research: _ResearchNotes, stage_dir: Path
    ) -> _Outline:
        logger.info("[Stage B] Generating outline")
        outline = await self._llm.generate_structured(
            prompt=OUTLINE_USER_PROMPT.format(
                concept=concept,
                research_notes=json.dumps(
                    research.model_dump(), ensure_ascii=False, indent=2
                ),
            ),
            system=OUTLINE_SYSTEM_PROMPT,
            response_model=_Outline,
        )
        (stage_dir / "outline.json").write_text(
            json.dumps(outline.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        target_total = sum(s.target_char_count for s in outline.sections)
        logger.info(
            "[Stage B] Done — title=%s, %d sections, target ~%d chars",
            outline.title,
            len(outline.sections),
            target_total,
        )
        return outline

    async def _stage_c_write_sections(
        self, concept: str, outline: _Outline, stage_dir: Path
    ) -> list[ScriptSection]:
        sections_dir = stage_dir / "sections"
        sections_dir.mkdir(parents=True, exist_ok=True)

        drafts: list[ScriptSection] = []
        total = len(outline.sections)
        for i, section in enumerate(outline.sections):
            logger.info(
                "[Stage C] Writing section %d/%d: %s (%s)",
                i + 1,
                total,
                section.heading,
                section.role,
            )
            draft = await self._llm.generate_structured(
                prompt=SECTION_USER_PROMPT.format(
                    title=outline.title,
                    concept=concept,
                    heading=section.heading,
                    core_argument=section.core_argument,
                    target_char_count=section.target_char_count,
                    role=section.role,
                    previous_sections=_format_previous(drafts),
                    upcoming_sections=_format_upcoming(outline.sections[i + 1 :]),
                ),
                system=SECTION_SYSTEM_PROMPT,
                response_model=_SectionDraft,
            )
            written = ScriptSection(heading=section.heading, narration=draft.narration)
            drafts.append(written)
            (sections_dir / f"section_{i + 1:02d}.json").write_text(
                json.dumps(written.model_dump(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        logger.info("[Stage C] Done — %d sections written", len(drafts))
        return drafts

    async def _stage_d_polish(
        self,
        concept: str,
        outline: _Outline,
        drafts: list[ScriptSection],
        stage_dir: Path,
    ) -> Script:
        logger.info("[Stage D] Polishing full script")
        polished = await self._llm.generate_structured(
            prompt=POLISH_USER_PROMPT.format(
                title=outline.title,
                concept=concept,
                sections=_format_sections_for_polish(drafts),
            ),
            system=POLISH_SYSTEM_PROMPT,
            response_model=_PolishedScript,
        )

        if len(polished.sections) == len(drafts):
            final_sections = [
                ScriptSection(heading=p.heading, narration=p.narration)
                for p in polished.sections
            ]
        else:
            # Polish should not change section count; fall back to drafts to preserve structure.
            logger.warning(
                "[Stage D] Polished section count mismatch (%d vs %d); using drafts",
                len(polished.sections),
                len(drafts),
            )
            final_sections = drafts

        script = Script(title=outline.title, concept=concept, sections=final_sections)

        (stage_dir / "script.json").write_text(
            json.dumps(script.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(
            "[Stage D] Done — %s, %d sections, ~%.0fs",
            script.title,
            len(script.sections),
            script.estimated_duration_seconds,
        )
        return script


def _format_previous(drafts: list[ScriptSection]) -> str:
    if not drafts:
        return "（這是第一段，沒有前文）"
    return "\n\n".join(f"【{s.heading}】\n{s.narration}" for s in drafts)


def _format_upcoming(upcoming: list[_OutlineSection]) -> str:
    if not upcoming:
        return "（這是最後一段，沒有後文）"
    return "\n".join(
        f"- {s.heading}（{s.role}）：{s.core_argument}" for s in upcoming
    )


def _format_sections_for_polish(drafts: list[ScriptSection]) -> str:
    return "\n\n".join(
        f"段落 {i + 1}【{s.heading}】\n{s.narration}" for i, s in enumerate(drafts)
    )

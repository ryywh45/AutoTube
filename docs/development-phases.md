# AutoTube 開發 Phase 切分

## Context

AutoTube 是一個自動化 YouTube 影片製作 pipeline，使用 multi-agent 架構。採用 **Vertical Slice** 策略：先用最簡方式打通整條 pipeline，再逐階段提升品質。MVP 目標為 **3-5 分鐘的中等長度影片**，Shorts 定位為中等長度影片的精華摘要（列入未來 phase）。LLM 選擇尚未決定，需設計為 LLM-agnostic。

---

## Phase 1: Project Foundation

建立專案骨架與跨 stage 的基礎設施。

- Python 專案結構（`pyproject.toml`、套件管理）
- LLM-agnostic 抽象層（統一介面，日後可換 Claude / Gemini / OpenAI）
- 定義各 stage 之間的 data model（Script、StoryboardScene、AudioSegment 等）
- Pipeline orchestrator 骨架（依序執行各 stage，支援中斷/繼續）
- 基本 config 系統（API keys、模型選擇、影片長度設定）

## Phase 2: Vertical Slice — Minimal E2E Pipeline

用最簡單的方式讓每個 stage 都能跑，目標：**輸入一個概念 → 產出一部可觀看的粗略 3-5 分鐘影片**。

- **Script Agent**：單次 LLM 呼叫產出講稿（先不做迭代擴充）
- **Storyboard Agent**：基本分鏡切割 + placeholder 圖片（或簡單文生圖）
- **TTS**：基本中文 TTS（選定一個可用服務先串接）
- **Video Synthesis**：FFmpeg 將圖片 + 音訊拼接成影片（無特效）
- 人工審核以 CLI prompt 或簡單確認機制實現

**Phase 2 完成標準**：能從 key concept 到產出一部完整影片（品質不要求高）。

## Phase 3: Script & Storyboard 品質提升

提升內容生成的品質與可控性。

- Script Agent 迭代擴充流程（從少量內容逐步擴充，使用 Skill 指導）
- 人工審核 gate（講稿審核後才進入分鏡）
- Storyboard 分鏡切割邏輯改進（研究最佳拆分策略）
- 接入實際文生圖模型（Nano Banana / 其他）
- 可產出多張圖供人工選擇

## Phase 4: 視覺一致性 & 圖片品質

鎖定風格後提升圖片產出品質，為日後 RAG 打基礎。

- 建立虛擬角色設定（風格、樣式）
- 固定所有圖片的 style prompt / style reference
- 調整文生圖模型參數，提升圖片品質與人物一致性
- 建立圖片品質審核標準（只有通過審核的圖片才有資格日後進入 vector DB）

## Phase 5: 影片製作品質提升

讓最終產出達到可發布水準。

- TTS 分段產生（per-scene segmentation）
- 影片動態效果（zoom in/out、pan）
- 自動產生 SRT 字幕 + 關鍵字高亮
- BGM 自動選配（免費可商用音樂庫）+ Auto-ducking
- SFX 研究與整合

## Phase 6: Metadata & Pipeline 穩健性

完善發布流程與系統穩定度。

- Metadata Agent（標題、說明欄、Tags、封面圖 + 文字）
- Pipeline 錯誤處理與重試機制
- Human-in-the-loop 工作流程優化
- 支援從中斷點恢復 pipeline

**Phase 6 完成標準**：pipeline 穩定運作，開始實際上線發布影片。

## Phase 7: RAG 圖片資產複用

**前提：已上線數部影片，累積一批經品質審核的風格一致圖片。**

- Gemini Embedding API 整合
- Vector store 建立（選定方案並實作）
- 語義檢索已有圖片，避免重複生成
- 人工從 RAG 結果中選圖
- 新產出圖片經審核後入庫

## Phase 8（Future）: Shorts 精華提取

從中等長度影片衍生 Shorts。

- 從完整講稿中提取 key points
- 重用主影片的分鏡圖、TTS 音檔等素材
- 產出 < 1 分鐘的 Shorts 版本
- 具體策略（AI 自動摘要 vs 人工標記）待定

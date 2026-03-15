### 自動化影片系統

1. 講稿 (Script)

- 來源
  - 提供 Key Concept 給 AI 生成
    - 獨立 Agent 進行
    - 不要一步到位，從少量內容一步一步擴充
    - 使用 Skill 指導 Agent 進行擴充
  - 參考網路文章/影片
    - (備註：還沒想好怎麼進行)
- 長度分類
  - Shorts (1分鐘內)
    - 備註：Shorts 定位為中等長度影片的精華 key points 衍生產物，不獨立製作
  - 短影片 (3~5分鐘)
  - 長影片 (8分鐘+)
- 人工審核最終講稿


2. 分鏡圖 (Storyboard)

- 講稿內容拆成文字分鏡
  - 獨立 Agent 進行
  - 設計 Prompt
  - 研究拆分邏輯
  - 確認是否需 Skill 來指導 Agent
  - 人工審核結果
- 由文字分鏡產出圖片
  - RAG 語義檢索，重用分鏡圖
    - 檢索出多張圖，人工選擇
    - 串 Gemini Embedding API
  - 無相似，則產圖
    - 模型選擇
      - Nano Banana (或是其他文生圖模型)
      - Kling AI (影片生成模型)
      - 其他 (待了解)
    - 可產多張圖，人工審核加入資料庫
    - 風格需一致


3. 文字轉聲音 TTS (Text-to-Speech)

- 需要中文聲音
  - 是否需要分段產生？
  - 前期文字直出聲音
  - 後期研究語氣變化


4. 影片合成 (Video Synthesis)

- 實作方法(待研究)
  - Python 套件？
  - FFmpeg？
- 讓靜態圖片產生動態感
  - zoom in
  - zoom out
  - pan
- 字幕
  - 自動生成srt字幕檔
  - 關鍵字高亮(Highlight Keywords)
- 背景音樂 BGM
  - 免費可商用BGM音樂庫 / yt內建音效清單
  - 自動檢索情緒選配樂
  - 人聲講話時自動調整音量 (Auto-ducking)
- 音效(SFX)
  - 待研究


5. 標題與封面(Metadata)
  - 根據講稿生成
    - 標題(Title)
    - 說明欄(Description)
    - Tag
    - 封面圖與搭配的文字


6. 圖片風格一致性(Style Consistency)

- 建立一個虛擬角色(風格與樣式待決定)
- 由虛擬角色產生所有分鏡
- 固定所有圖片的風格描述



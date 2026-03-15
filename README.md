# AutoTube

An automated YouTube video production system powered by multi-agent workflows. Each stage of video creation — from script writing to final rendering — is handled by specialized AI agents with human-in-the-loop review at critical checkpoints.

> **Status:** Architecture design phase — pipeline structure and agent roles defined, implementation not yet started.

## Pipeline Stages

1. **Script Agent** — Iteratively expands a key concept into a full script
2. **Storyboard Agent** — Splits script into scenes, generates or retrieves images
3. **TTS** — Chinese text-to-speech, per-scene segmented
4. **Video Synthesis** — Combines images (with motion effects) + audio + subtitles + BGM
5. **Metadata Agent** — Generates title, description, tags, and thumbnail

## Design Principles

- **Modular agents** — Each stage is an independent agent with a defined input/output contract
- **Human-in-the-loop** — Critical checkpoints (script approval, storyboard review, image selection) require human sign-off
- **LLM-agnostic** — Abstraction layer allows swapping between Claude / Gemini / OpenAI
- **Iterative refinement** — Scripts and storyboards are built incrementally, not in a single prompt
- **RAG for asset reuse** — Semantic retrieval to reuse existing images (introduced only after visual quality is established)

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python |
| LLM | TBD (LLM-agnostic design) |
| Embedding | Gemini Embedding API |
| TTS | TBD (Chinese language support required) |
| Image Generation | TBD (evaluating options) |
| Video Synthesis | TBD (FFmpeg / Python libraries) |
| Vector Store | TBD |

## Development Roadmap

Strategy: **Vertical Slice** — build a minimal end-to-end pipeline first, then improve each stage iteratively. MVP targets **3–5 minute videos**.

| Phase | Focus | Goal |
|-------|-------|------|
| 1 | Project Foundation | Project structure, data models, LLM abstraction, pipeline orchestrator |
| 2 | Minimal E2E Pipeline | Input a concept → output a rough but complete video |
| 3 | Script & Storyboard Quality | Iterative script expansion, improved scene splitting, real image generation |
| 4 | Visual Consistency | Lock down art style, virtual character, image quality standards |
| 5 | Video Production Quality | TTS segmentation, motion effects, subtitles, BGM, SFX |
| 6 | Metadata & Robustness | Metadata agent, error handling, pipeline resume — **go live** |
| 7 | RAG Asset Reuse | Vector DB for image retrieval (after accumulating quality assets) |
| 8 | Shorts (Future) | Derive shorts from medium-length video key points |

> Detailed phase descriptions (in Chinese): [`docs/development-phases.md`](docs/development-phases.md)

## License

MIT

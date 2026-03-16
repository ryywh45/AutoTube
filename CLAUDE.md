# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AutoTube is an automated YouTube video production system using multi-agent AI workflows. The pipeline covers: script writing, storyboarding, image generation (with RAG-based reuse), TTS (Chinese language), video synthesis, and metadata generation. Human-in-the-loop review gates exist at critical stages.

**Status:** Phase 1 — implementing project foundation.

## Pipeline Stages

1. **Script Agent** — Iteratively expands a key concept into a full script (not one-shot). Supports shorts (<1min), short (3–5min), and long (8min+) formats.
2. **Storyboard Agent** — Splits script into scene descriptions, then generates or retrieves images via RAG (Gemini Embedding API). Human selects from retrieved candidates or approves new generations.
3. **TTS** — Chinese text-to-speech, potentially per-scene segmented.
4. **Video Synthesis** — Combines images (with motion: zoom, pan) + TTS audio + subtitles (SRT with keyword highlighting) + BGM (auto-ducking) + SFX.
5. **Metadata Agent** — Generates title, description, tags, and thumbnail from the script.

## Tech Stack

- **Language:** Python (>=3.12)
- **Package management:** uv — all dependency management (add, remove, lock, sync) must go through `uv`. Do not edit `pyproject.toml` dependencies by hand; use `uv add` / `uv remove` instead.
- **Embeddings:** Gemini Embedding API
- Chinese language support is a hard requirement for TTS.
- LLM, TTS provider, image generation model, video tooling, and vector store are all TBD.

## Key Design Decisions

- Each pipeline stage is an independent agent with defined input/output contracts.
- LLM integration must be agnostic — design a unified abstraction layer so the provider (Claude / Gemini / OpenAI) can be swapped.
- RAG for image reuse comes **after** visual style and quality are established (not early-stage).
- A virtual character/consistent art style is planned for all generated imagery.
- Shorts are derived from medium-length (3–5min) videos by extracting key points — not produced independently.
- The concept note (`docs/concept-note.md`) is written in Traditional Chinese and contains the detailed design thinking.

## Conventions

- `README.md` must be written entirely in English.
- `docs/concept-note.md` is in Traditional Chinese.

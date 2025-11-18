# v30 Summary: Ollama Integration and Prompt Strategy

Date: 2025-08-17 01:15:16 EDT

## Overview

This codebase runs a Flask + Socket.IO chat app that integrates with Ollama’s `/api/generate` endpoint. It supports two operational modes: a full megaprompt strategy (persona + history + ephemeral system each turn) and a KV-efficient tail mode (baseline persona once, then minimal ephemeral system tails). Vector retrieval (PostgreSQL + sentence-transformers) can be enabled to inject relevant memories into the ephemeral system prompt.

## Core Components

- `config.py`
  - `OLLAMA_API_URL`: `http://windows-host:11434/api/generate`
  - `MODEL_NAME`: `llama3.2:3b-instruct-q4_K_M`
  - `LLM_CONTEXT_SIZE`: 8000
  - `USE_FULL_MEGA_PROMPT`: controls full vs tail mode
  - `RETRIEVAL_ENABLED`: toggles vector retrieval
  - `OLLAMA_SESSION_ID`: fixed session for residency/KV reuse

- `llm.py`
  - Persona and ephemeral system builders (Llama 3.2 header format)
  - `build_megaprompt(...)`: persona + prior pairs + ephemeral (time + memories) + latest user + assistant header
  - `build_baseline_prompt(...)`: persona + latest user (for tail mode first turn)
  - `build_tail_prompt(...)`: minimal ephemeral + latest user (small, KV-friendly)
  - `generate_api_call(...)`: streams tokens from `/api/generate`, returns text, context (often empty), and timing counters (e.g., `prompt_eval_count`)
  - Local metadata/summary helpers for memory pipeline (GLiClass + T5-small fast paths)

- `app.py`
  - WebSocket handler for chat UI; webhook `/api/webhook` for programmatic tests
  - Maintains per-session KV context (`SESSION_CONTEXTS`) and tail-mode flag
  - Emits token estimates and KV stats (`prompt_eval_count`, durations) to UI
  - Retrieval inspector endpoints: `/api/retrieve_inspect`, `/api/memory`

- `memory.py`
  - Parent-document storage: summary + chunks into Postgres with embeddings
  - Hybrid retrieval: semantic + keywords + recency + tag scoring
  - Deduplication against recent conversation to reduce noise

- `utils.py`
  - Conversation history store, token estimates, NLTK setup

## Operational Modes

1) Full Megaprompt (USE_FULL_MEGA_PROMPT=True)
   - Persona + prior conversation pairs are sent every turn
   - Ephemeral system (time + retrieved memories) injected before latest user
   - Pros: Strong multi-turn recall, clear instruction adherence
   - Cons: Token hungry; prompt_eval_count rises with history; relies on session residency but not on returned context

2) Tail Mode (USE_FULL_MEGA_PROMPT=False)
   - Turn 1 baseline: persona + latest user
   - Subsequent turns: tiny ephemeral system + latest user (no history resend)
   - Pros: Clear KV reuse; prompt_eval_count drops sharply on turn 2; very low latency after warm-up
   - Cons: Weak recall beyond the last turn unless a small rolling recap or retrieval is used

## Retrieval and Memories

- When `RETRIEVAL_ENABLED=True`, relevant chunks are fetched and formatted as concise bullets in the ephemeral system prompt.
- Retrieved memories are not appended to chat history; they are ephemeral context for the current turn.
- Storage threshold and classification control what gets embedded; consider forcing storage of personal/biographical patterns to improve recall.

## KV Behavior

- With tail mode: observed `prompt_eval_count` drop (e.g., baseline ~220 → tail ~77) and total duration reductions after warm-up.
- With full megaprompt: `prompt_eval_count` tends to increase as history grows; latency remains acceptable on the 3B Q4 model.
- Returned `context` from the server is typically empty; the app relies on session residency and prompt structure rather than explicit context chaining.

## Known Trade-offs

- Full megaprompt: excellent recall and instruction adherence, but higher tokens/compute.
- Tail mode: excellent efficiency and latency, but limited multi-turn recall unless augmented by recap or retrieval.
- Classifier and embedding models add a one-time cold-start cost; can be preloaded at startup to avoid first-turn delay.

## Recommended Practices

- Keep `OLLAMA_SESSION_ID` stable during a session for residency benefits.
- Place ephemeral system immediately before the latest user block.
- If using tail mode, include a small rolling recap (last 1–2 pairs) when you need short-range recall without heavy token cost.
- For personal facts, consider lowering the storage threshold or pattern-matching to force-store important biographical data.



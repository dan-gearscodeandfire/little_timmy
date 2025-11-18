## System Prompt and KV Cache Strategy (2025-08-15)

### Goal
Maximize KV cache reuse and response quality with Llama 3.2 Instruct via Ollama `/api/generate`, while keeping prompts compact and consistent.

### Key facts
- The deprecated `context` array was token IDs, not the KV itself. KV stays on the server.
- The recommended approach is stable `session_id` + `keep_alive` so the server retains KV across turns.
- When the prefix + current turn exceeds `num_ctx` (`LLM_CONTEXT_SIZE`), Ollama truncates oldest tokens to fit. You’ll see “truncating input prompt … new=8000”.
- The most recent `system` block is authoritative; older system tokens remain in KV but are effectively overridden.

### Prompt structure strategy
- Turn 1 (prime):
  - Send a full, static persona as a `system` block once so it lands in the cached prefix.
  - Include any essential global rules that should not change.
- Turn ≥2 (tail mode):
  - Send a short “turn context” `system` block immediately before the user message.
  - Keep this block minimal and changing: only the most relevant memories/time markers.
  - Optionally include a 1–2 line “micro‑persona” reminder if needed, not the entire persona.
  - Then send the user message and the assistant header.

### Ephemeral system block (turn context) guidelines
- Keep to 3–5 bullets; newest first; 1 sentence each.
- Label style (consistent, compact): `[fact] [identity] [project] [plan] [constraint] [urgent] [test] [preference]`.
- Example template (placed right before user message):
  - “Turn context (use only if directly relevant; prefer newest on conflict; do not contradict static persona):
    - (22m) [identity][fact] Cat is Winston; breed: Cornish Rex.
    - (3h) [project][plan] WSL→Win port proxy; avoid 8888/11434 forwarding.”
- Do not restate the full persona here; avoid conflicting rules.

### KV/window management
- Use tail‑only prompting after Turn 1 to avoid re‑evaluating the full history.
- Keep `num_ctx` within the model’s window; if truncation appears in logs, reduce:
  - conversation history length (trim aggressively),
  - number/length of memory bullets,
  - frequency/size of persona refresh.
- Periodic re‑priming: if behavior drifts or truncation has likely evicted the persona, send one turn with the full persona again, then return to micro‑persona + short turn context.

### Retrieval integration (what feeds the turn context)
- Two‑stage retrieval (already in code):
  - Select relevant parent documents by summary embedding.
  - Select best chunks within those parents via hybrid scoring (semantic + keyword + recency + tag weights).
- From the final chunks, compress into atomic claims with recency tags; dedupe; cap to 3–5 bullets.

### Session handling
- Keep a stable `session_id` and set `keep_alive` (e.g., "1h") on `/api/generate` to preserve KV.
- Reset session only when you need to clear context or switch persona/rules decisively.

### Monitoring signals
- Healthy KV reuse: second and later turns show sharply lower `prompt_eval_count` and prompt eval duration.
- Warning signs: truncation logs, prompt_eval spikes, growing prompt sizes, inconsistent behavior (persona likely evicted).

### Failure modes and responses
- Persona drift after long chats:
  - Re‑prime with full persona once; then go back to micro‑persona + short turn context.
- Latency spikes or truncation:
  - Reduce memory bullets, trim history, ensure tail‑only prompting.
- Conflicting rules across system blocks:
  - Reserve static persona for timeless rules; keep turn context factual and non‑directive.

### Quick checklist
- Use one‑time full persona on Turn 1.
- Subsequent turns: short turn‑context `system` block, then user message.
- Keep bullets 3–5, labeled, newest first, one sentence each.
- Tail‑only prompting to maximize KV reuse.
- Stable `session_id` + `keep_alive`.
- Trim history and cap memory bullets to avoid truncation.
- Periodically re‑prime when needed.



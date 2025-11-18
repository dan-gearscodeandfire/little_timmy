## Context Estimation Improvements (To‑Do)

Goal: Make the UI’s “context used” reflect what the model actually evaluates and how much of the window is occupied, especially in tail mode with KV cache.

### What to display
- Server truth (primary)
  - Evaluated tokens (this turn): Ollama `prompt_eval_count`
  - Generated tokens: Ollama `eval_count`

- Prompt sizes (secondary)
  - Logical full prompt tokens: tokenized full megaprompt (for visibility only)
  - Sent prompt tokens (tail): tokenized actual prompt sent in tail mode

- Window utilization
  - Context window: `LLM_CONTEXT_SIZE` (num_ctx)
  - Utilization (est.): `min(num_ctx, cached_prefix + tail) / num_ctx`
  - Truncation alert: show banner if Ollama logs “truncating input prompt … new=…”

- KV reuse signal (approx.)
  - `KV_reuse ≈ 1 − (prompt_eval_count / sent_prompt_tokens)`
  - Sudden drops indicate truncation or cache breakage

### Tokenization guidance
- Replace word×1.3 heuristic with real tokenizer counts for Llama 3.2.
- Options (pick one):
  - Use a local Llama tokenizer (e.g., Hugging Face `transformers` tokenizer for Llama)
  - Use `llama.cpp` compatible tokenizer if already present
- Compute both counts when building prompts:
  - `logical_full_tokens = tokenize(full_megaprompt)`
  - `sent_tail_tokens = tokenize(tail_prompt)`

### Instrumentation and wiring
- Capture from Ollama responses (already parsed in code):
  - `prompt_eval_count`, `eval_count`, `prompt_eval_duration`, `total_duration`
- Emit via SocketIO:
  - `evaluated_tokens`, `generated_tokens`, `sent_tail_tokens`, `logical_full_tokens`, `num_ctx`, `kv_reuse_est`, `truncation_detected`
- UI updates:
  - Primary row: Evaluated tokens, Generated tokens
  - Secondary row: Sent tail tokens, Logical full tokens, Utilization
  - Status chip: KV reuse good/poor; Truncation alert when detected

### Detection of truncation
- Watch Ollama logs or response metadata (when available): if server logs “truncating input prompt … limit=… new=…”, set `truncation_detected = true` for that turn.
- Also infer from spikes in `prompt_eval_count` vs `sent_tail_tokens`.

### UX notes
- Keep the primary numbers minimal and truthful: server counts first.
- Use tooltips to explain “Evaluated” (prompt tokens re‑evaluated this turn) vs “Generated”.
- Avoid surfacing raw “context” arrays; they’re deprecated and not KV.

### Future enhancements
- Show moving averages (p50/p95) of evaluated tokens and latencies.
- Track per‑session trends to flag when re‑priming persona may be needed.
- Add a small legend explaining KV reuse and truncation behavior.



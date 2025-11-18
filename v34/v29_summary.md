# v29 Session Summary

## Major changes implemented
- KV testing utility (`kv_cache_test.py`): session/context/raw modes; CLI flags; PASS/FAIL via prompt_eval_count; results: session PASS, context FAIL, raw PASS (~0.37 ratio).
- Prompt pipeline (`llm.py`): added `build_baseline_prompt`, `build_tail_prompt`, compact identity anchor, optional session recap; enabled internal streaming to capture stats/context; added explicit `context` chaining; metadata fast-path to avoid storing test prompts.
- App (`app.py`): baseline on first turn, tail thereafter; persists returned context per session; optional tiny session recap; KV telemetry buffer + `/api/kv_stats` and Socket.IO `kv_stats` event.
- Web UI (`templates/chat.html`): KV stats panel (tail_mode, prompt_eval_count, durations) alongside token panel.
- Config (`config.py`): `RETRIEVAL_ENABLED` flag (can disable memory injection for KV/session-only tests).

## What worked (successes)
- KV reuse validated via test script (session/raw modes show reduced prompt_eval_count on second turn).
- KV stats endpoint and live UI updates working.
- Compact identity anchor often improves tone without resending the full persona.
- Retrieval can be disabled quickly for clean tests.

## What didn’t (failures/partial)
- Same-session recall (e.g., “purple toaster”) failed repeatedly in the app path:
  - Logs show Returned context length: 0, so explicit chaining had nothing to pass forward.
  - Tail excludes prior turns (by design for KV efficiency); with empty context and retrieval disabled, prior turns weren’t available → recall failed.
- Personality drift still appears at times despite anchor.
- Using payload `context` with this server setup did not yield non-empty returned context in app logs.

## Known behaviors/tradeoffs
- KV reuse vs persona: resending persona each turn costs tokens; compact anchor is a small-cost compromise.
- Retrieval pollution: injecting memories can skew answers; disable during session-only tests.
- Session-only recall: reliable in test script raw mode; unreliable in app when returned context is empty and old turns aren’t re-sent.

## Recommendations/next steps
- For reliable chat history without returned context:
  - Use `/api/chat` with `messages` history + `session_id`, or
  - Include a small rolling recap (last 1–2 turns) in the tail.
- For explicit context chaining with `/api/generate`:
  - Try to obtain a non-empty `context` on turn 1 (e.g., first call without `raw`), then pass it forward; avoid resending old text when using `context`.
- Keep `RETRIEVAL_ENABLED=False` for session-only validation.

## For future assistants: limitations, failed fixes, known good features
- Limitations
  - `/api/generate` returned context was consistently empty in the app path; explicit chaining ineffective.
  - Tone can drift without a per-turn identity nudge; compact anchor helps but isn’t flawless.
  - TTS requires a single final string; internal streaming must be buffered.
- Failed/partial fixes
  - `session_id` alone didn’t ensure recall without prior turns or non-empty returned context.
  - Supplying `context` didn’t help when server returned none.
  - Relying solely on KV + minimal tail (no recap, retrieval off) caused recall failures.
- Known good features
  - `kv_cache_test.py` validates KV reuse (prompt_eval reductions).
  - `/api/kv_stats` + UI KV panel are useful for visibility.
  - `RETRIEVAL_ENABLED` flag simplifies clean KV/session tests.
  - Compact per-turn identity anchor reduces drift with low token cost.

"""Quick test program to verify KV cache reuse with Ollama /api/generate.

Two reuse strategies are supported:
- context: send the returned "context" array on subsequent turns, do not resend system
- session: send a fixed session_id (from config) and do not use the deprecated context field

We consider the KV cache reused successfully if second-turn prompt_eval_count
is significantly smaller than the first-turn. Threshold is configurable.
"""

import json
import time
import argparse
import requests
import config

# Use shared config to ensure correct host/model from WSL
OLLAMA_URL = config.OLLAMA_API_URL
MODEL = config.MODEL_NAME  # keep in sync with app config

session = requests.Session()  # keep-alive


def ollama_generate(prompt, context=None, system=None, use_session=False, stream=True, print_tokens=True, raw=False):
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": stream,
        "keep_alive": "1h",
        "options": {"num_ctx": getattr(config, "LLM_CONTEXT_SIZE", 8192)},
    }
    if context is not None:
        payload["context"] = context
    if system is not None:
        payload["system"] = system  # send once (first turn), then stop sending
    if use_session and getattr(config, "OLLAMA_SESSION_ID", None):
        payload["session_id"] = config.OLLAMA_SESSION_ID
    if raw:
        payload["raw"] = True

    final_context = context
    stats = {}

    with session.post(OLLAMA_URL, json=payload, stream=stream) as r:
        r.raise_for_status()
        if not stream:
            msg = r.json()
            final_context = msg.get("context", final_context)
            stats = {
                "prompt_eval_count": msg.get("prompt_eval_count"),
                "prompt_eval_duration": msg.get("prompt_eval_duration"),
                "eval_count": msg.get("eval_count"),
                "eval_duration": msg.get("eval_duration"),
                "total_duration": msg.get("total_duration"),
            }
            return final_context, stats

        for line in r.iter_lines():
            if not line:
                continue
            msg = json.loads(line.decode("utf-8"))

            token = msg.get("response")
            if token and print_tokens:
                print(token, end="", flush=True)

            if msg.get("done"):
                final_context = msg.get("context", final_context)
                stats = {
                    "prompt_eval_count": msg.get("prompt_eval_count"),
                    "prompt_eval_duration": msg.get("prompt_eval_duration"),
                    "eval_count": msg.get("eval_count"),
                    "eval_duration": msg.get("eval_duration"),
                    "total_duration": msg.get("total_duration"),
                }
                if print_tokens:
                    print()
                break

    return final_context, stats


def run_scenario(mode: str, threshold: float, quiet: bool) -> bool:
    assert mode in {"context", "session", "raw"}

    persona = (
        "You are Little Timmy, a witty but concise co-host. "
        "Stay under 2 sentences unless asked; be playful, not corny."
    )

    if mode == "raw":
        # Turn 1: put persona + user into the raw prompt (no system field)
        first_prompt = (
            f"{persona}\n\n"
            "User: Hey Timmy, give me one fun fact about LEDs."
        )
        ctx = None
        t0 = time.time()
        ctx, st1 = ollama_generate(
            prompt=first_prompt,
            system=None,
            use_session=False,
            stream=True,
            print_tokens=not quiet,
            raw=True,
        )
        t1 = time.time()

        # Turn 2: send only the new user tail; include returned context; keep raw=True
        ctx2, st2 = ollama_generate(
            prompt="User: Nice. Now make it about PWM dimming, super short.",
            context=ctx,
            use_session=False,
            stream=True,
            print_tokens=not quiet,
            raw=True,
        )
        t2 = time.time()
    else:
        # Original modes
        # Turn 1: send persona via system exactly once
        ctx = None
        t0 = time.time()
        ctx, st1 = ollama_generate(
            prompt="User: Hey Timmy, give me one fun fact about LEDs.",
            system=persona,
            context=None if mode == "session" else None,
            use_session=(mode == "session"),
            stream=True,
            print_tokens=not quiet,
        )
        t1 = time.time()

        # Turn 2: do NOT resend system; reuse context or session
        ctx2, st2 = ollama_generate(
            prompt="User: Nice. Now make it about PWM dimming, super short.",
            context=ctx if mode == "context" else None,
            use_session=(mode == "session"),
            stream=True,
            print_tokens=not quiet,
        )
        t2 = time.time()

    # Basic reporting
    print(f"\n[{mode}] First-turn stats: {st1}")
    print(f"[{mode}] Second-turn stats: {st2}")
    if st1.get("prompt_eval_count") is None or st2.get("prompt_eval_count") is None:
        print(f"[{mode}] Unable to read prompt_eval_count; cannot assert KV reuse.")
        return False

    c1 = st1["prompt_eval_count"] or 0
    c2 = st2["prompt_eval_count"] or 0
    ratio = (c2 / c1) if c1 > 0 else 1.0
    print(f"[{mode}] prompt_eval_count ratio second/first = {ratio:.3f}")
    print(f"[{mode}] durations (s) first={t1-t0:.2f}, second={t2-t1:.2f}")

    success = ratio <= threshold
    print(f"[{mode}] KV reuse {'PASS' if success else 'FAIL'} (threshold {threshold:.2f})")
    return success


def main():
    parser = argparse.ArgumentParser(description="Verify KV cache reuse on Ollama /api/generate")
    parser.add_argument("--mode", choices=["context", "session", "raw", "both"], default="both")
    parser.add_argument("--threshold", type=float, default=0.70, help="Max allowed second/first prompt_eval_count ratio")
    parser.add_argument("--quiet", action="store_true", help="Suppress token streaming output")
    args = parser.parse_args()

    modes = ["context", "session"] if args.mode == "both" else [args.mode]
    results = []
    for m in modes:
        print(f"\n=== Running KV test mode: {m} ===")
        ok = run_scenario(m, args.threshold, args.quiet)
        results.append((m, ok))

    # Final exit code summary
    all_ok = all(ok for _, ok in results)
    print("\n=== Summary ===")
    for m, ok in results:
        print(f"{m}: {'PASS' if ok else 'FAIL'}")

    if not all_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

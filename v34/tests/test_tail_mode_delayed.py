#!/usr/bin/env python3
import json
import time
import requests

import config
import llm


def main():
    print("WARMUP: sending 'hi' without session_id to load model...")
    payload = {
        "model": config.MODEL_NAME,
        "prompt": "hi",
        "stream": False,
        "keep_alive": "1h",
        "options": {"num_ctx": config.LLM_CONTEXT_SIZE},
    }
    r = requests.post(config.OLLAMA_API_URL, json=payload, timeout=90)
    print("Warmup status:", r.status_code)
    try:
        print("Warmup preview:", r.json().get("response", "")[:80])
    except Exception:
        print("Warmup preview: <unavailable>")

    print("Waiting 5 seconds before Turn 1...")
    time.sleep(5)

    config.DEBUG_MODE = True

    # Turn 1: baseline
    p1 = llm.build_baseline_prompt("Say 'OK'.")
    r1, c1, s1 = llm.generate_api_call(p1, context=None, raw=True)
    print("T1 prompt_eval_count:", (s1 or {}).get("prompt_eval_count"), "total:", (s1 or {}).get("total_duration"))

    print("Waiting 1 second before Turn 2...")
    time.sleep(1)

    # Turn 2: tail
    p2 = llm.build_tail_prompt(user_message="Say 'OK' again.", retrieved_memories=[], session_recap="")
    r2, c2, s2 = llm.generate_api_call(p2, context=c1, raw=True)
    print("T2 prompt_eval_count:", (s2 or {}).get("prompt_eval_count"), "total:", (s2 or {}).get("total_duration"))


if __name__ == "__main__":
    main()



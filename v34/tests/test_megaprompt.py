#!/usr/bin/env python3
import json
import time

import config
import llm


def print_stats(label: str, stats: dict):
    print(f"\n--- {label} ---")
    if not stats:
        print("No stats returned")
        return
    print("prompt_eval_count:", stats.get("prompt_eval_count"))
    print("eval_count:", stats.get("eval_count"))
    print("durations (ns): load=", stats.get("load_duration"),
          " prompt_eval=", stats.get("prompt_eval_duration"),
          " eval=", stats.get("eval_duration"),
          " total=", stats.get("total_duration"))


def main():
    # Be noisy for this test
    config.DEBUG_MODE = True

    # Simple 2-turn chat using the megaprompt builder
    history = []

    # Turn 1
    user1 = "Sanity check: answer in one witty sentence about magnets."
    mp1 = llm.build_megaprompt(history, user1, retrieved_memories=[])
    resp1, ctx1, stats1 = llm.generate_api_call(mp1, context=None, raw=True)
    print("\nResponse 1:", resp1)
    print("Returned context len:", 0 if ctx1 is None else len(ctx1))
    print_stats("Turn 1 stats", stats1)

    # Add assistant reply to history
    history.append({"role": "user", "content": user1})
    history.append({"role": "assistant", "content": resp1})

    # Small delay to avoid overlapping timing noise
    time.sleep(0.5)

    # Turn 2
    user2 = "Follow-up: do you remember what you just said? Keep it short."
    mp2 = llm.build_megaprompt(history, user2, retrieved_memories=[])
    resp2, ctx2, stats2 = llm.generate_api_call(mp2, context=ctx1, raw=True)
    print("\nResponse 2:", resp2)
    print("Returned context len:", 0 if ctx2 is None else len(ctx2))
    print_stats("Turn 2 stats", stats2)

    # Basic success condition
    ok1 = isinstance(resp1, str) and len(resp1.strip()) > 0
    ok2 = isinstance(resp2, str) and len(resp2.strip()) > 0
    print("\nSUCCESS:", ok1 and ok2)


if __name__ == "__main__":
    main()



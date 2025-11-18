#!/usr/bin/env python3
import json
import time

import config
import llm


def run_tail_test():
    config.DEBUG_MODE = True
    print("USE_FULL_MEGA_PROMPT:", getattr(config, 'USE_FULL_MEGA_PROMPT', None))

    # Turn 1: baseline (persona only)
    t1_prompt = llm.build_baseline_prompt("Say 'OK'.")
    resp1, ctx1, stats1 = llm.generate_api_call(t1_prompt, context=None, raw=True)
    print("Turn1 response:", resp1)
    print("Turn1 stats:", json.dumps(stats1))

    # Short delay
    time.sleep(0.5)

    # Turn 2: tail (minimal ephemeral + latest user)
    tail_prompt = llm.build_tail_prompt(user_message="Say 'OK' again.", retrieved_memories=[], session_recap="")
    resp2, ctx2, stats2 = llm.generate_api_call(tail_prompt, context=ctx1, raw=True)
    print("Turn2 response:", resp2)
    print("Turn2 stats:", json.dumps(stats2))

    pe1 = stats1.get('prompt_eval_count') if stats1 else None
    pe2 = stats2.get('prompt_eval_count') if stats2 else None
    print("\nPrompt eval counts: turn1=", pe1, " turn2=", pe2)


if __name__ == "__main__":
    run_tail_test()



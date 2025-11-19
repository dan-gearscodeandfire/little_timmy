#!/usr/bin/env python3
import llm

test_cases = [
    "The cat that I tested your memory with was named Winston and he was a Cornish Rex",
    "My cat Winston was a Cornish Rex",
    "I tested the motor yesterday"
]

print("="*70)
print("TESTING 'testing' KEYWORD FIX")
print("="*70)

for text in test_cases:
    result = llm.fast_generate_metadata(text)
    print(f"\nInput: {text}")
    print(f"  Topic: {result['topic']}")
    print(f"  Importance: {result['importance']}")
    print(f"  Tags: {result['tags']}")
    print(f"  Would store: {'YES (embedded)' if result['importance'] >= 2 else 'NO (too low)'}")


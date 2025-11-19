#!/usr/bin/env python3
import difflib

messages = [
    "My cat is named Winston",
    "My cat's name is Winston",
    "Winston is my cat's name"
]

print("Similarity Matrix:")
print("="*60)

for i, msg1 in enumerate(messages):
    for j, msg2 in enumerate(messages):
        if i < j:
            ratio = difflib.SequenceMatcher(None, msg1, msg2).ratio()
            print(f"{i+1} vs {j+1}: {ratio:.3f}")
            print(f"  '{msg1}'")
            print(f"  '{msg2}'")
            print()


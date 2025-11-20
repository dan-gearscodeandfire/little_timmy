#!/usr/bin/env python3
"""Test the fine-tuning capture system."""

import fine_tuning_capture

print("="*70)
print("TESTING FINE-TUNING CAPTURE SYSTEM")
print("="*70)

# Test praise detection
test_phrases = [
    ("Good one, Timmy", True),
    ("That was a great response", True),
    ("Excellent", True),
    ("What's my cat's name?", False),
    ("I like that", True),
    ("Perfect response", True),
    ("Tell me more", False),
]

print("\n📝 PRAISE DETECTION TESTS:")
passed = 0
for phrase, expected in test_phrases:
    result = fine_tuning_capture.is_praise(phrase)
    status = "✅" if result == expected else "❌"
    print(f"  {status} '{phrase}' → {result} (expected {expected})")
    if result == expected:
        passed += 1

print(f"\nPassed: {passed}/{len(test_phrases)}")

# Test capture function
print("\n" + "="*70)
print("TESTING CAPTURE FUNCTION")
print("="*70)

try:
    fine_tuning_capture.capture_fine_tuning_example(
        user_message_n3="What's my cat's name?",
        system_prompt_n2="You are Little Timmy...\n\nMemories:\n• [Personal Data, Importance: 5] User (1h ago) - My cat is Winston",
        assistant_response_n1="Winston, of course - the feline overlord who demands treats.",
        praise_message_n0="Good one, Timmy!",
        metadata={"test": True, "session": "test"}
    )
    print("✅ Capture function executed successfully")
    print("✅ Check fine_tuning_best_case_interchanges.md for output")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "="*70)
print("DONE")
print("="*70)


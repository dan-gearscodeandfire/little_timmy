#!/usr/bin/env python3
import llm

print("="*70)
print("TESTING PERSONA FIXES")
print("="*70)

# Test 1: Winston statement (should be high importance)
result1 = llm.fast_generate_metadata('My first cat was Winston and he was a Cornish Rex')
print('\nTest 1: Winston statement')
print(f'  Topic: {result1["topic"]}')
print(f'  Importance: {result1["importance"]} (should be 5)')
print(f'  Tags: {result1["tags"]}')

# Test 2: Do you remember question (should not be heavily penalized)
result2 = llm.fast_generate_metadata('Do you remember the names of my new cats?')
print('\nTest 2: Do you remember question')
print(f'  Topic: {result2["topic"]}')
print(f'  Importance: {result2["importance"]} (should be 0-1, not heavily penalized)')
print(f'  Tags: {result2["tags"]}')

# Test 3: Check persona text
print('\n' + '='*70)
print('PERSONA TEXT CHECK')
print('='*70)
persona = llm.get_persona_text()
print('\nKey rules present:')
print('  ✅ YOU are Little Timmy' if 'YOU are Little Timmy' in persona else '  ❌ Missing identity clarification')
print('  ✅ DAN is the user' if 'DAN is the user' in persona else '  ❌ Missing Dan identification')
print('  ✅ Do NOT narrate' if 'Do NOT narrate' in persona else '  ❌ Missing anti-narration rule')
print('  ✅ Do NOT be overly helpful' if 'Do NOT be overly helpful' in persona else '  ❌ Missing tone guidance')


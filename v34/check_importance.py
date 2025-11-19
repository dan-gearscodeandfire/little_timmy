#!/usr/bin/env python3
import json

data = json.load(open('memory_test_results.json'))
imp = data['test_categories']['importance']

print('='*60)
print('IMPORTANCE SCORING FAILURES')
print('='*60)

for t in imp['test_results']:
    if not t['passed']:
        print(f"\nTest {t['test_number']}:")
        print(f"  Input: {t.get('input', 'N/A')}")
        print(f"  Expected: {t.get('expected_range', 'N/A')}")
        print(f"  Actual: {t.get('actual_importance', 'N/A')}")
        print(f"  Reason: {t.get('reason', 'N/A')}")
        print(f"  Topic: {t.get('actual_topic', 'N/A')}")
        print(f"  Tags: {t.get('actual_tags', [])}")


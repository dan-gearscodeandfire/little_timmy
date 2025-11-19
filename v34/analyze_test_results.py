#!/usr/bin/env python3
import json

with open('memory_test_results.json') as f:
    data = json.load(f)

print("="*60)
print("CLASSIFICATION TEST ANALYSIS")
print("="*60)

classification = data['test_categories']['classification']
print(f"\nPass Rate: {classification['pass_rate']}%")
print(f"Passed: {classification['passed']}/{classification['total_tests']}\n")

for t in classification['test_results']:
    status = "✅ PASS" if t['passed'] else "❌ FAIL"
    print(f"\n{status} Test {t['test_number']}: {t['description']}")
    print(f"  Input: {t['input']}")
    print(f"  Expected topic: {t['expected']['topic']}")
    print(f"  Actual topic: {t['actual']['topic']}")
    print(f"  Expected importance: {t['expected']['importance']}")
    print(f"  Actual importance: {t['actual']['importance']}")
    print(f"  Tags: {t['actual']['tags']}")


#!/usr/bin/env python3
import json

with open('memory_test_results.json') as f:
    data = json.load(f)

print('='*60)
print('REMAINING FAILURES ANALYSIS')
print('='*60)

for cat_name, cat_data in data['test_categories'].items():
    print(f"\n{cat_data['category']}: {cat_data['passed']}/{cat_data['total_tests']} passed ({cat_data['pass_rate']}%)")
    
    failures = [t for t in cat_data['test_results'] if not t['passed']]
    if failures:
        for test in failures:
            print(f"  ❌ Test {test['test_number']}: {test['description']}")
            if 'input' in test:
                print(f"     Input: {test['input'][:60]}")
            if 'expected' in test and 'actual' in test:
                print(f"     Expected: {test['expected']}")
                print(f"     Actual: {test['actual']}")
    else:
        print("  ✅ All tests passed!")

print('\n' + '='*60)
print('SUMMARY')
print('='*60)
summary = data['overall_summary']
print(f"Total: {summary['total_passed']}/{summary['total_tests']} passed ({summary['overall_pass_rate']}%)")
print(f"Status: {summary['status']}")


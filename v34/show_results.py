#!/usr/bin/env python3
import json

with open('memory_test_results.json') as f:
    data = json.load(f)

print('='*70)
print('MEMORY SYSTEM TEST RESULTS')
print('='*70)

for cat_name, cat_data in data['test_categories'].items():
    status_icon = "✅" if cat_data['failed'] == 0 else "⚠️"
    print(f"\n{status_icon} {cat_data['category']}: {cat_data['passed']}/{cat_data['total_tests']} ({cat_data['pass_rate']}%)")
    
    for test in cat_data['test_results']:
        icon = "✅" if test['passed'] else "❌"
        desc = test.get('description', 'No description')
        print(f"  {icon} Test {test['test_number']}: {desc}")

print('\n' + '='*70)
print('OVERALL SUMMARY')
print('='*70)
summary = data['overall_summary']
print(f"Total Tests: {summary['total_tests']}")
print(f"Passed: {summary['total_passed']}")
print(f"Failed: {summary['total_failed']}")
print(f"Pass Rate: {summary['overall_pass_rate']}%")
print(f"Status: {summary['status']}")
print(f"Duration: {data['total_duration_seconds']}s")


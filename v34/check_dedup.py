#!/usr/bin/env python3
import json

data = json.load(open('memory_test_results.json'))
dedup = data['test_categories']['deduplication']

print('='*70)
print('DEDUPLICATION TEST DETAILS')
print('='*70)

for t in dedup['test_results']:
    print(f"\nTest {t['test_number']}: {t['description']}")
    print(f"  Stored messages: {t['stored_messages']}")
    print(f"  Query: {t['query']}")
    print(f"  Expected max results: {t['max_expected']}")
    print(f"  Actually retrieved: {t['actual_retrieved']}")
    print(f"  Total chunks found: {t['total_chunks']}")
    print(f"  Passed: {'✅' if t['passed'] else '❌'}")
    if 'retrieved_texts' in t:
        print(f"  Retrieved texts:")
        for i, text in enumerate(t['retrieved_texts'], 1):
            print(f"    {i}. {text}")


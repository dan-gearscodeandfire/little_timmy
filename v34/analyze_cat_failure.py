#!/usr/bin/env python3
"""Analyze why the cat breed question failed."""

import re

with open('session5_extract.txt') as f:
    data = f.read()

# Find the cat question conversation
convos = data.split('=== Megaprompt at')

cat_question_convo = None
for convo in convos:
    if 'what was the name of my cat and what breed was he' in convo.lower():
        cat_question_convo = convo
        break

if not cat_question_convo:
    print("❌ Cat question not found")
    exit(1)

print("="*70)
print("CAT BREED QUESTION FAILURE ANALYSIS")
print("="*70)

# Extract memories that were shown
if 'Relevant memories for this turn:' in cat_question_convo:
    mem_section = cat_question_convo.split('Relevant memories for this turn:')[1].split('<|eot_id|>')[0]
    print("\n💾 MEMORIES RETRIEVED:")
    print(mem_section)
    
    # Check if Winston was in the memories
    if 'Winston' in mem_section:
        print("\n✅ Winston memory WAS retrieved")
    else:
        print("\n❌ Winston memory was NOT retrieved")
    
    if 'Cornish Rex' in mem_section:
        print("✅ Cornish Rex was in memories")
    else:
        print("❌ Cornish Rex was NOT in memories")
else:
    print("\n❌ NO MEMORIES RETRIEVED (retrieval might be disabled or failed)")

# Check response
if 'Mr. Whiskers' in cat_question_convo:
    print("\n🚨 HALLUCINATION CONFIRMED: Mr. Whiskers (completely made up)")
if 'Maine Coon' in cat_question_convo:
    print("🚨 HALLUCINATION CONFIRMED: Maine Coon (wrong breed)")

print("\n" + "="*70)
print("DIAGNOSIS")
print("="*70)

if 'Relevant memories' not in cat_question_convo:
    print("\n❌ RETRIEVAL FAILURE: No memories were retrieved")
    print("   Possible causes:")
    print("   - Database query failed")
    print("   - Winston memory not yet embedded")
    print("   - Query didn't match stored text")
elif 'Winston' not in mem_section:
    print("\n❌ RETRIEVAL PRECISION FAILURE: Wrong memories retrieved")
    print("   Winston memory exists but wasn't retrieved")
    print("   Possible causes:")
    print("   - Semantic mismatch between query and stored text")
    print("   - Recency/importance scoring issues")
    print("   - Other memories ranked higher")
else:
    print("\n❌ LLM HALLUCINATION: Memory was retrieved but LLM ignored it")
    print("   This is the WORST case - memory system working but LLM not using it")
    print("   Possible causes:")
    print("   - LLM didn't understand memory format")
    print("   - LLM preferred its training data")
    print("   - Prompt structure issues")


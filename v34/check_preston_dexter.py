#!/usr/bin/env python3
"""Check if Preston and Dexter are in the database and test retrieval."""

import memory
import utils

memory.init_db_pool()

# Check database
conn = memory.db_pool.getconn()
with conn.cursor() as cur:
    cur.execute("""
        SELECT content, importance, topic, timestamp
        FROM memory_chunks
        WHERE content ILIKE '%Preston%' OR content ILIKE '%Dexter%'
        ORDER BY timestamp DESC;
    """)
    results = cur.fetchall()

memory.db_pool.putconn(conn)

print("="*70)
print("PRESTON/DEXTER IN DATABASE")
print("="*70)

if results:
    print(f"Found {len(results)} memories mentioning Preston or Dexter:\n")
    for content, imp, topic, ts in results:
        print(f"[{topic}, Imp: {imp}] {ts}")
        print(f"  {content[:150]}...")
        print()
else:
    print("❌ NO memories found mentioning Preston or Dexter!")
    print("   They were never stored or were cleaned up")

# Test retrieval
print("="*70)
print("RETRIEVAL TEST")
print("="*70)

queries = [
    "What are my new cats' names?",
    "Tell me about Preston and Dexter",
    "What are my cats named?"
]

for query in queries:
    print(f"\nQuery: {query}")
    chunks = memory.retrieve_unique_relevant_chunks(query, k=5)
    print(f"Retrieved {len(chunks)} chunks:")
    
    found_preston = False
    found_dexter = False
    
    for i, chunk in enumerate(chunks, 1):
        text = chunk.get('text', '')
        if 'Preston' in text or 'Dexter' in text:
            if 'Preston' in text:
                found_preston = True
            if 'Dexter' in text:
                found_dexter = True
            print(f"  {i}. ✅ [{chunk.get('topic')}, Imp: {chunk.get('importance')}] {text[:80]}...")
        else:
            print(f"  {i}. [{chunk.get('topic')}, Imp: {chunk.get('importance')}] {text[:80]}...")
    
    if found_preston and found_dexter:
        print("  ✅ Both cats found!")
    elif found_preston or found_dexter:
        print("  ⚠️  Only one cat found")
    else:
        print("  ❌ Neither cat found")

memory.close_db_pool()


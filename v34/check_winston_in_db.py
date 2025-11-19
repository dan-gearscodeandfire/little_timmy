#!/usr/bin/env python3
import memory
import utils

memory.init_db_pool()

# Search for Winston
query = "what was the name of my cat and what breed"
chunks = memory.retrieve_unique_relevant_chunks(query, k=10)

print("="*70)
print("WINSTON RETRIEVAL TEST")
print("="*70)
print(f"Query: {query}")
print(f"Chunks retrieved: {len(chunks)}")
print()

for i, chunk in enumerate(chunks, 1):
    print(f"{i}. [{chunk.get('topic', 'N/A')}, Imp: {chunk.get('importance', 0)}] "
          f"{chunk.get('role', 'N/A')} ({utils.time_ago(chunk['timestamp'])})")
    print(f"   {chunk['text'][:120]}...")
    print(f"   Distance: {chunk.get('distance', 'N/A'):.4f}, "
          f"Hybrid score: {chunk.get('hybrid_score', 'N/A'):.4f}")
    print()

# Check if Winston is in database at all
conn = memory.db_pool.getconn()
with conn.cursor() as cur:
    cur.execute("""
        SELECT content, importance, topic, timestamp
        FROM memory_chunks
        WHERE content ILIKE '%Winston%' AND content ILIKE '%Cornish%'
        ORDER BY timestamp DESC
        LIMIT 5;
    """)
    winston_memories = cur.fetchall()

memory.db_pool.putconn(conn)
memory.close_db_pool()

print("="*70)
print("WINSTON MEMORIES IN DATABASE")
print("="*70)
if winston_memories:
    for content, imp, topic, ts in winston_memories:
        print(f"[{topic}, Imp: {imp}] {ts}")
        print(f"  {content[:150]}...")
        print()
else:
    print("❌ NO Winston+Cornish memories found in database!")


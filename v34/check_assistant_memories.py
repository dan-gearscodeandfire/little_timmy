#!/usr/bin/env python3
import memory

memory.init_db_pool()

conn = memory.db_pool.getconn()
with conn.cursor() as cur:
    # Count assistant memories
    cur.execute("""
        SELECT COUNT(*), AVG(importance)
        FROM memory_chunks
        WHERE speaker = 'assistant';
    """)
    count, avg_imp = cur.fetchone()
    
    # Get some examples
    cur.execute("""
        SELECT content, importance, topic, timestamp
        FROM memory_chunks
        WHERE speaker = 'assistant'
        ORDER BY timestamp DESC
        LIMIT 10;
    """)
    examples = cur.fetchall()

memory.db_pool.putconn(conn)
memory.close_db_pool()

print('='*70)
print('ASSISTANT MEMORIES IN DATABASE (SHOULD BE NONE!)')
print('='*70)
print(f"Total assistant memories: {count}")
print(f"Average importance: {avg_imp:.2f}" if avg_imp else "N/A")
print()

if examples:
    print("Recent examples:")
    for i, (content, imp, topic, ts) in enumerate(examples, 1):
        print(f"{i}. [{topic}, Imp: {imp}] {ts}")
        print(f"   {content[:100]}...")
        print()
else:
    print("✅ No assistant memories found (correct!)")


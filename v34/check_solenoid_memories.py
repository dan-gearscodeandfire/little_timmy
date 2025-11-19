#!/usr/bin/env python3
import memory

memory.init_db_pool()

conn = memory.db_pool.getconn()
with conn.cursor() as cur:
    # Check for solenoid memories
    cur.execute("""
        SELECT content, importance, topic, timestamp, speaker
        FROM memory_chunks
        WHERE content ILIKE '%solenoid%'
        ORDER BY timestamp DESC
        LIMIT 10;
    """)
    solenoid_results = cur.fetchall()
    
    # Check for wire memories
    cur.execute("""
        SELECT content, importance, topic, timestamp, speaker
        FROM memory_chunks
        WHERE content ILIKE '%wire%'
        ORDER BY timestamp DESC
        LIMIT 10;
    """)
    wire_results = cur.fetchall()

memory.db_pool.putconn(conn)
memory.close_db_pool()

print('='*70)
print('SOLENOID MEMORIES IN DATABASE')
print('='*70)
if solenoid_results:
    for i, (content, imp, topic, ts, speaker) in enumerate(solenoid_results, 1):
        print(f"{i}. [{topic}, Imp: {imp}] {speaker} @ {ts}")
        print(f"   {content[:120]}...")
        print()
else:
    print("No solenoid memories found")

print('='*70)
print('WIRE MEMORIES IN DATABASE')
print('='*70)
if wire_results:
    for i, (content, imp, topic, ts, speaker) in enumerate(wire_results, 1):
        print(f"{i}. [{topic}, Imp: {imp}] {speaker} @ {ts}")
        print(f"   {content[:120]}...")
        print()
else:
    print("No wire memories found")


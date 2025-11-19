#!/usr/bin/env python3
"""Clean ALL test data from database before running tests."""

import memory

# Initialize database
memory.init_db_pool()

try:
    conn = memory.db_pool.getconn()
    with conn.cursor() as cur:
        # Delete all chunks with test-related content
        cur.execute("""
            DELETE FROM memory_chunks 
            WHERE content ILIKE '%Winston%'
               OR content ILIKE '%pizza%'
               OR content ILIKE '%chassis%'
               OR content ILIKE '%weld%'
               OR content ILIKE '%Erin%'
               OR session_id LIKE 'test_session_%';
        """)
        chunks_deleted = cur.rowcount
        
        # Delete orphaned parent documents
        cur.execute("""
            DELETE FROM parent_documents 
            WHERE id NOT IN (SELECT DISTINCT parent_id FROM memory_chunks WHERE parent_id IS NOT NULL)
               OR session_id LIKE 'test_session_%';
        """)
        parents_deleted = cur.rowcount
    
    conn.commit()
    memory.db_pool.putconn(conn)
    
    print(f"✅ Cleaned up {chunks_deleted} test chunks and {parents_deleted} parent documents")
    
except Exception as e:
    print(f"❌ Error: {e}")
finally:
    memory.close_db_pool()


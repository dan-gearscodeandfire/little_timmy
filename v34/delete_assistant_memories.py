#!/usr/bin/env python3
"""Delete all assistant memories from the database."""

import memory

memory.init_db_pool()

try:
    conn = memory.db_pool.getconn()
    with conn.cursor() as cur:
        # Delete assistant chunks
        cur.execute("""
            DELETE FROM memory_chunks 
            WHERE speaker = 'assistant';
        """)
        chunks_deleted = cur.rowcount
        
        # Delete orphaned parent documents
        cur.execute("""
            DELETE FROM parent_documents 
            WHERE speaker = 'assistant'
               OR id NOT IN (SELECT DISTINCT parent_id FROM memory_chunks WHERE parent_id IS NOT NULL);
        """)
        parents_deleted = cur.rowcount
    
    conn.commit()
    memory.db_pool.putconn(conn)
    
    print(f"✅ Deleted {chunks_deleted} assistant chunks and {parents_deleted} parent documents")
    print("✅ Database cleaned - only user messages remain")
    
except Exception as e:
    print(f"❌ Error: {e}")
finally:
    memory.close_db_pool()


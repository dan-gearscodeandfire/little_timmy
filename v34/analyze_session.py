#!/usr/bin/env python3
"""Analyze a session log for memory system performance."""

import re
from collections import Counter, defaultdict

with open('app_session.log', 'r', encoding='utf-8') as f:
    log = f.read()

# Split into conversations
conversations = log.split('*********************************************BEGIN*********************************************')

print("="*70)
print("SESSION ANALYSIS")
print("="*70)
print(f"\nTotal conversations: {len(conversations) - 1}")  # First split is header

# Extract metrics
stored_count = 0
skipped_count = 0
retrieved_counts = []
importance_scores = []
topics = []
retrieval_times = []

for conv in conversations[1:]:  # Skip first empty split
    # Check if message was stored
    if "chunk_and_store_text" in conv or "Stored" in conv:
        stored_count += 1
    if "Skipped storing" in conv:
        skipped_count += 1
    
    # Extract importance scores
    importance_match = re.search(r'Final importance: (\d+)', conv)
    if importance_match:
        importance_scores.append(int(importance_match.group(1)))
    
    # Extract topics
    topic_match = re.search(r'Topic: ([^,]+),', conv)
    if topic_match:
        topics.append(topic_match.group(1).strip())
    
    # Extract retrieval counts
    retrieved_match = re.search(r'Retrieved (\d+) memory chunks for context', conv)
    if retrieved_match:
        retrieved_counts.append(int(retrieved_match.group(1)))
    
    # Extract retrieval times
    time_match = re.search(r'Step 4 \(Context Retrieval\) took: ([\d.]+)s', conv)
    if time_match:
        retrieval_times.append(float(time_match.group(1)))

print(f"\n📊 STORAGE METRICS:")
print(f"  Messages stored: {stored_count}")
print(f"  Messages skipped: {skipped_count}")
print(f"  Storage rate: {stored_count/(stored_count+skipped_count)*100:.1f}%")

print(f"\n📈 IMPORTANCE DISTRIBUTION:")
importance_dist = Counter(importance_scores)
for score in sorted(importance_dist.keys(), reverse=True):
    count = importance_dist[score]
    bar = "█" * (count * 2)
    print(f"  Importance {score}: {count:2d} {bar}")

print(f"\n🏷️  TOPIC DISTRIBUTION:")
topic_dist = Counter(topics)
for topic, count in topic_dist.most_common(10):
    print(f"  {topic:25s}: {count}")

print(f"\n🔍 RETRIEVAL METRICS:")
if retrieved_counts:
    print(f"  Avg chunks retrieved: {sum(retrieved_counts)/len(retrieved_counts):.1f}")
    print(f"  Max chunks retrieved: {max(retrieved_counts)}")
    print(f"  Min chunks retrieved: {min(retrieved_counts)}")

if retrieval_times:
    print(f"\n⏱️  RETRIEVAL PERFORMANCE:")
    print(f"  Avg retrieval time: {sum(retrieval_times)/len(retrieval_times):.3f}s")
    print(f"  Max retrieval time: {max(retrieval_times):.3f}s")
    print(f"  Min retrieval time: {min(retrieval_times):.3f}s")

# Look for errors
errors = re.findall(r'Error|Exception|WARNING', log, re.IGNORECASE)
print(f"\n⚠️  ERRORS/WARNINGS: {len(errors)}")

# Check for wife's name queries
wife_queries = [conv for conv in conversations if "wife" in conv.lower() and "name" in conv.lower()]
if wife_queries:
    print(f"\n👰 WIFE'S NAME QUERIES: {len(wife_queries)} found")
    print("  (Check if Erin was correctly recalled)")

print("\n" + "="*70)
print("RECOMMENDATIONS")
print("="*70)

# Analyze importance distribution
if importance_scores:
    avg_importance = sum(importance_scores) / len(importance_scores)
    high_importance = sum(1 for s in importance_scores if s >= 4)
    low_importance = sum(1 for s in importance_scores if s <= 1)
    
    print(f"\nAverage importance: {avg_importance:.2f}")
    print(f"High importance (4-5): {high_importance} ({high_importance/len(importance_scores)*100:.1f}%)")
    print(f"Low importance (0-1): {low_importance} ({low_importance/len(importance_scores)*100:.1f}%)")
    
    if avg_importance < 2:
        print("⚠️  Low average importance - most messages being filtered")
    elif avg_importance > 3:
        print("⚠️  High average importance - may be storing too much")
    else:
        print("✅ Good balance of important vs casual messages")


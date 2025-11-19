#!/usr/bin/env python3
"""Analyze Session 4 from payloads.txt"""

import re

with open('session4_data.txt', 'r', encoding='utf-8') as f:
    data = f.read()

# Split by conversation
convos = data.split('=== Megaprompt at')

print("="*70)
print(f"SESSION 4 ANALYSIS - {len(convos)-1} Conversations")
print("="*70)

user_messages = []
assistant_responses = []
memories_shown = []

for i, convo in enumerate(convos[1:], 1):  # Skip first empty split
    # Extract user message
    user_match = re.search(r'<\|start_header_id\|>user<\|end_header_id\|>\n(.+?)\n<\|eot_id\|>', convo, re.DOTALL)
    if user_match:
        user_msg = user_match.group(1).strip()
        # Get last user message (most recent)
        user_parts = user_msg.split('<|start_header_id|>user<|end_header_id|>')
        if user_parts:
            last_user = user_parts[-1].split('<|eot_id|>')[0].strip()
            if last_user and len(last_user) > 5:
                user_messages.append(last_user)
    
    # Extract assistant response (if present in history)
    asst_matches = re.findall(r'<\|start_header_id\|>assistant<\|end_header_id\|>\n(.+?)\n<\|eot_id\|>', convo, re.DOTALL)
    if asst_matches:
        assistant_responses.append(asst_matches[-1].strip())
    
    # Check for retrieved memories
    if 'Relevant memories for this turn:' in convo:
        mem_section = convo.split('Relevant memories for this turn:')[1].split('<|eot_id|>')[0]
        memories_shown.append(mem_section.strip())

print(f"\n📊 CONVERSATION FLOW:")
print(f"  User messages: {len(user_messages)}")
print(f"  Assistant responses: {len(assistant_responses)}")
print(f"  Turns with memories: {len(memories_shown)}")

print(f"\n👤 USER MESSAGES (last 10):")
for i, msg in enumerate(user_messages[-10:], 1):
    print(f"  {i}. {msg[:80]}...")

print(f"\n🤖 ASSISTANT RESPONSES (last 10):")
for i, resp in enumerate(assistant_responses[-10:], 1):
    print(f"  {i}. {resp[:80]}...")

# Check for persona issues
print(f"\n🎭 PERSONA CHECK:")
identity_issues = sum(1 for r in assistant_responses if 'Little Timmy' in r and 'you' in r.lower())
narration_issues = sum(1 for r in assistant_responses if "I've stored" in r or "I'll remember" in r or "I'll make sure" in r)
helpful_tone = sum(1 for r in assistant_responses if "I'll do my best" in r or "great to hear" in r.lower())

print(f"  Identity confusion (calling you Little Timmy): {identity_issues}")
print(f"  Narration issues (I've stored...): {narration_issues}")
print(f"  Overly helpful tone: {helpful_tone}")

# Check for memory format
print(f"\n💾 MEMORY FORMAT CHECK:")
if memories_shown:
    sample = memories_shown[-1] if memories_shown else ""
    has_metadata = '[' in sample and 'Importance:' in sample
    print(f"  Enhanced format with metadata: {'✅ YES' if has_metadata else '❌ NO (old format)'}")
    if has_metadata:
        print(f"  Sample: {sample[:150]}...")

print("\n" + "="*70)


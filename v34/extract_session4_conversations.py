#!/usr/bin/env python3
import re

with open('session4_data.txt', 'r', encoding='utf-8') as f:
    data = f.read()

convos = data.split('=== Megaprompt at')

print("="*70)
print("SESSION 4 - CONVERSATION EXTRACTION")
print("="*70)

for i, convo in enumerate(convos[1:], 1):
    # Extract timestamp
    ts_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', convo)
    timestamp = ts_match.group(1) if ts_match else "Unknown"
    
    # Extract last user message
    user_parts = convo.split('<|start_header_id|>user<|end_header_id|>')
    if len(user_parts) > 1:
        last_user = user_parts[-1].split('<|eot_id|>')[0].strip()
    else:
        last_user = "N/A"
    
    # Extract last assistant response (from history, not current)
    asst_parts = convo.split('<|start_header_id|>assistant<|end_header_id|>')
    if len(asst_parts) > 1:
        # Get second-to-last (last is empty header for current turn)
        last_asst = asst_parts[-2].split('<|eot_id|>')[0].strip() if len(asst_parts) > 2 else asst_parts[-1].split('<|eot_id|>')[0].strip()
    else:
        last_asst = "N/A"
    
    print(f"\n{'='*70}")
    print(f"Conversation {i} @ {timestamp}")
    print(f"{'='*70}")
    print(f"👤 USER: {last_user[:200]}")
    if last_asst and last_asst != "N/A" and len(last_asst) > 3:
        print(f"🤖 TIMMY: {last_asst[:200]}")


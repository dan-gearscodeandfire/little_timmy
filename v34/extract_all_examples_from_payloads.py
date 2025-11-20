#!/usr/bin/env python3
"""Extract ALL fine-tuning examples from payloads.txt"""

import re
import fine_tuning_capture

print("="*70)
print("EXTRACTING ALL EXAMPLES FROM PAYLOADS.TXT")
print("="*70)

with open('payloads.txt', 'r', encoding='utf-8') as f:
    data = f.read()

# Split by megaprompt
convos = data.split('=== Megaprompt at')

examples_captured = 0
skipped = 0

for i in range(1, len(convos)):
    convo = convos[i]
    
    # Extract timestamp
    ts_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', convo)
    timestamp = ts_match.group(1) if ts_match else "Unknown"
    
    # Get current user message (the last one in this conversation)
    user_parts = convo.split('<|start_header_id|>user<|end_header_id|>')
    if len(user_parts) < 2:
        continue
    
    current_user = user_parts[-1].split('<|eot_id|>')[0].strip()
    
    # Check if current user message is praise
    if not fine_tuning_capture.is_praise(current_user):
        continue
    
    # This is praise! Now get the previous user message and assistant response
    # Previous user message is second-to-last user block
    if len(user_parts) >= 3:
        previous_user = user_parts[-2].split('<|eot_id|>')[0].strip()
    else:
        skipped += 1
        continue
    
    # Get assistant response (last complete one before current user)
    asst_parts = convo.split('<|start_header_id|>assistant<|end_header_id|>')
    if len(asst_parts) >= 2:
        # Get the last complete assistant response
        previous_asst = asst_parts[-2].split('<|eot_id|>')[0].strip()
    else:
        skipped += 1
        continue
    
    # Skip if assistant response is too short or empty
    if not previous_asst or len(previous_asst) < 10:
        skipped += 1
        continue
    
    # Get system prompt (everything from start to first user message)
    system_parts = convo.split('<|start_header_id|>system<|end_header_id|>')
    if len(system_parts) >= 2:
        # Get last system prompt
        system_prompt = system_parts[-1].split('<|eot_id|>')[0].strip()
    else:
        system_prompt = "System prompt not found"
    
    # Capture it
    try:
        fine_tuning_capture.capture_fine_tuning_example(
            user_message_n3=previous_user,
            system_prompt_n2=system_prompt,
            assistant_response_n1=previous_asst,
            praise_message_n0=current_user,
            metadata={
                "source": "payloads.txt",
                "timestamp": timestamp,
                "conversation_number": i
            }
        )
        examples_captured += 1
        if examples_captured <= 10:  # Show first 10
            print(f'  ✅ {examples_captured}. {timestamp} - {current_user[:50]}...')
        elif examples_captured % 10 == 0:  # Show every 10th
            print(f'  ✅ {examples_captured}. {timestamp} - {current_user[:50]}...')
    except Exception as e:
        print(f'  ❌ Error at {timestamp}: {e}')
        skipped += 1

print(f'\\n{"="*70}')
print(f'RESULTS')
print(f'{"="*70}')
print(f'Examples captured: {examples_captured}')
print(f'Skipped (incomplete): {skipped}')
print(f'\\n✅ All examples saved to: fine_tuning_best_case_interchanges.md')


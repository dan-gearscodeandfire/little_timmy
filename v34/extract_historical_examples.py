#!/usr/bin/env python3
"""Extract fine-tuning examples from historical session data."""

import re
import fine_tuning_capture

# Load all session data
session_files = [
    'session4_data.txt',
    'session5_extract.txt', 
    'session6_data.txt',
    'session7_data.txt'
]

print("="*70)
print("EXTRACTING HISTORICAL FINE-TUNING EXAMPLES")
print("="*70)

examples_found = 0

for session_file in session_files:
    try:
        with open(session_file, 'r', encoding='utf-8') as f:
            data = f.read()
    except FileNotFoundError:
        print(f"⚠️  {session_file} not found, skipping")
        continue
    
    print(f"\n📄 Processing {session_file}...")
    
    # Split into conversations
    convos = data.split('=== Megaprompt at')
    
    for i in range(1, len(convos)):
        convo = convos[i]
        
        # Extract timestamp
        ts_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', convo)
        timestamp = ts_match.group(1) if ts_match else "Unknown"
        
        # Extract all user messages in this conversation
        user_parts = convo.split('<|start_header_id|>user<|end_header_id|>')
        user_messages = []
        for part in user_parts[1:]:
            msg = part.split('<|eot_id|>')[0].strip()
            if msg:
                user_messages.append(msg)
        
        # Extract all assistant responses
        asst_parts = convo.split('<|start_header_id|>assistant<|end_header_id|>')
        asst_responses = []
        for part in asst_parts[1:]:
            resp = part.split('<|eot_id|>')[0].strip()
            if resp and len(resp) > 5:
                asst_responses.append(resp)
        
        # Check if last user message is praise
        if user_messages and len(user_messages) >= 2:
            last_user = user_messages[-1]
            
            if fine_tuning_capture.is_praise(last_user):
                # This is praise! Capture the previous exchange
                if len(user_messages) >= 2 and len(asst_responses) >= 1:
                    user_n3 = user_messages[-2]  # Previous user message
                    asst_n1 = asst_responses[-1]  # Previous assistant response
                    praise_n0 = last_user
                    
                    # Extract system prompt (everything before last user message)
                    system_parts = convo.split('<|start_header_id|>system<|end_header_id|>')
                    if len(system_parts) > 1:
                        # Get last system prompt
                        system_prompt = system_parts[-1].split('<|eot_id|>')[0].strip()
                    else:
                        system_prompt = "System prompt not found"
                    
                    # Capture it
                    try:
                        fine_tuning_capture.capture_fine_tuning_example(
                            user_message_n3=user_n3,
                            system_prompt_n2=system_prompt,
                            assistant_response_n1=asst_n1,
                            praise_message_n0=praise_n0,
                            metadata={
                                "source": session_file,
                                "timestamp": timestamp,
                                "extracted_from_history": True
                            }
                        )
                        examples_found += 1
                        print(f"  ✅ Captured example from {timestamp}")
                        print(f"     Praise: {praise_n0[:50]}...")
                    except Exception as e:
                        print(f"  ❌ Error capturing: {e}")

print(f"\n" + "="*70)
print(f"TOTAL EXAMPLES CAPTURED: {examples_found}")
print("="*70)
print(f"\n✅ Examples saved to: fine_tuning_best_case_interchanges.md")


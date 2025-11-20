#!/usr/bin/env python3
import re

with open('session7_data.txt') as f:
    data = f.read()

convos = data.split('=== Megaprompt at')[1:]

print('='*70)
print('SESSION 7 - KEY Q&A PAIRS')
print('='*70)

for i, convo in enumerate(convos[-12:], 1):
    user_parts = convo.split('<|start_header_id|>user<|end_header_id|>')
    if len(user_parts) > 1:
        user_msg = user_parts[-1].split('<|eot_id|>')[0].strip()
    else:
        continue
    
    asst_parts = convo.split('<|start_header_id|>assistant<|end_header_id|>')
    if len(asst_parts) > 2:
        asst = asst_parts[-2].split('<|eot_id|>')[0].strip()
    else:
        asst = "N/A"
    
    # Only show key questions
    if any(keyword in user_msg.lower() for keyword in ['wife', 'cat', 'name', 'breed', 'preston', 'dexter', 'winston']):
        print(f'\n{"="*70}')
        print(f'Q{i}: {user_msg[:150]}')
        print(f'{"="*70}')
        if asst and asst != "N/A":
            print(f'A: {asst[:200]}')
            
            # Check for correctness
            if 'wife' in user_msg.lower() and 'name' in user_msg.lower():
                if 'Erin' in asst:
                    print('✅ CORRECT: Erin')
                else:
                    print('❌ WRONG or MISSING')
            
            if 'winston' in user_msg.lower() and 'breed' in user_msg.lower():
                if 'Winston' in asst and 'Cornish Rex' in asst:
                    print('✅ CORRECT: Winston, Cornish Rex')
                elif 'Winston' in asst:
                    print('⚠️  PARTIAL: Winston but missing breed')
                else:
                    print('❌ WRONG or MISSING')
            
            if 'new cats' in user_msg.lower() or 'preston' in user_msg.lower() or 'dexter' in user_msg.lower():
                if 'Preston' in asst and 'Dexter' in asst:
                    print('✅ CORRECT: Preston and Dexter')
                elif 'Preston' in asst or 'Dexter' in asst:
                    print('⚠️  PARTIAL: Only one name')
                elif "don't recall" in asst.lower() or "don't know" in asst.lower():
                    print('✅ HONEST: Admitted not knowing')
                else:
                    print('❌ WRONG or HALLUCINATION')


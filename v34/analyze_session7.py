#!/usr/bin/env python3
import re

with open('session7_data.txt') as f:
    data = f.read()

convos = data.split('=== Megaprompt at')[1:]
recent = convos[-12:]  # Last 12

print('='*70)
print('SESSION 7 ANALYSIS - Anti-Hallucination Test')
print('='*70)

enhanced_format_count = 0
cat_questions = []
wife_questions = []
responses = []

for i, convo in enumerate(recent, 1):
    if '[' in convo and 'Importance:' in convo:
        enhanced_format_count += 1
    
    user_parts = convo.split('<|start_header_id|>user<|end_header_id|>')
    if len(user_parts) > 1:
        user_msg = user_parts[-1].split('<|eot_id|>')[0].strip()
        
        if 'cat' in user_msg.lower() and ('name' in user_msg.lower() or 'breed' in user_msg.lower()):
            cat_questions.append((i, user_msg[:100]))
        if 'wife' in user_msg.lower() and 'name' in user_msg.lower():
            wife_questions.append((i, user_msg[:100]))
    
    asst_parts = convo.split('<|start_header_id|>assistant<|end_header_id|>')
    if len(asst_parts) > 2:
        asst = asst_parts[-2].split('<|eot_id|>')[0].strip()
        if asst and len(asst) > 5:
            responses.append(asst)

print(f'\nConversations: {len(recent)}')
print(f'Enhanced format: {enhanced_format_count}/{len(recent)} ({enhanced_format_count/len(recent)*100:.0f}%)')

# Hallucinations
hallucination_phrases = ['Mr. Whiskers', 'Luna', 'Leo', 'Maine Coon']
hallucinations = []
for r in responses:
    for phrase in hallucination_phrases:
        if phrase in r:
            hallucinations.append(phrase)

print(f'\n🚨 Hallucinations: {len(hallucinations)}')
if hallucinations:
    print(f'   Types: {set(hallucinations)}')
else:
    print('   ✅ None detected!')

# Narration
narration = [r for r in responses if "I've stored" in r or "I'll remember" in r or "I'll make sure" in r]
print(f'\n📝 Narration issues: {len(narration)}')

# Identity
identity = [r for r in responses if 'Little Timmy' in r and 'you' in r.lower()]
print(f'🎭 Identity confusion: {len(identity)}')

# Honesty (saying I don't know)
honest = [r for r in responses if "don't recall" in r.lower() or "don't know" in r.lower() or "don't have" in r.lower()]
print(f'\n✅ Honest responses: {len(honest)}')
if honest:
    print('   (Admitting lack of information)')

print(f'\n🐱 Cat questions: {len(cat_questions)}')
print(f'👰 Wife questions: {len(wife_questions)}')

print('\n' + '='*70)
print('SAMPLE RESPONSES')
print('='*70)
for i, r in enumerate(responses[-5:], 1):
    print(f'\n{i}. {r[:120]}...')


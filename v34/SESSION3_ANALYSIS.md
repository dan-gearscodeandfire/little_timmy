# Session 3 Behavioral Analysis

**Date:** November 19, 2025  
**Conversations:** 6  
**Focus:** Memory testing and persona evaluation

---

## 🚨 **Behavioral Deviations Identified:**

### **Deviation #1: Identity Confusion - Calling User "Little Timmy"**

**Occurrences:**
- "I'll make sure to remember this for future conversations about you, Little Timmy!"
- "I've stored the names of your new cats as Preston and Dexter, Little Timmy."
- "It's great to hear that you're enjoying our conversations, Little Timmy!"

**Expected:** Timmy should know HE is Little Timmy, and YOU are Dan.

**Actual:** Timmy is calling Dan "Little Timmy" ❌

---

### **Deviation #2: Overly Helpful/Nice Tone**

**Occurrences:**
- "I'll make sure to remember..."
- "I'll do my best to recall..."
- "It's great to hear..."
- "I'll keep working on my responses..."

**Expected:** Witty, sarcastic, slightly arrogant

**Actual:** Polite, eager to please, apologetic ❌

---

### **Deviation #3: Meta-Commentary About Storage**

**Occurrences:**
- "I've stored 'Winston' as the name..."
- "I've stored the names of your new cats..."

**Expected:** Natural conversation, no narration of internal processes

**Actual:** Explaining what he's storing in memory ❌

---

### **Deviation #4: Failed Memory Recall**

**Query:** "I earlier mentioned the names of two new cats... Do you remember those names?"

**Timmy's Response:** "No, actually... no, wait! You did mention adopting some new cats, but I don't recall their specific names."

**Classification:**
- Topic: `asking questions`
- Importance: **1** (testing question penalty)

**Problem:** This was a legitimate memory test, but got classified as a testing question and scored low.

---

## 🔍 **Root Cause Analysis:**

### **Cause #1: Persona Not Being Enforced**

**Current Setup:**
- Persona sent in FIRST turn only (baseline prompt)
- Subsequent turns use "tail mode" with minimal reinforcement

**Tail reinforcement (llm.py:739):**
```python
reinforcement = (
    "Identity: Little Timmy — witty, sarcastic; 1 sentence answer + short quip after an em dash; no apologies; never say 'as an AI'; talk to Dan."
)
```

**Issue:** This brief reinforcement isn't strong enough to maintain personality.

---

### **Cause #2: USE_FULL_MEGA_PROMPT = True**

**Config setting (config.py:15):**
```python
USE_FULL_MEGA_PROMPT = True
```

**What this means:**
- Full persona + history sent EVERY turn
- Should maintain personality better
- But clearly not working as expected

**Let me check what's actually being sent...**

Looking at the code flow:
```python
# app.py:180-181
if getattr(config, "USE_FULL_MEGA_PROMPT", False):
    prompt_to_send = full_megaprompt_for_estimate
```

**Wait - the config says `True` but the code checks for `False`!**

Let me verify:

<function_calls>
<invoke name="grep">
<parameter name="pattern">USE_FULL_MEGA_PROMPT

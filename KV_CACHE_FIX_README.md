# KV Cache Fix - Implementation & Restore Guide

**Date:** November 27, 2025  
**Restore Point Tag:** `before-kv-cache-fix`

## 🔖 How to Restore if Something Breaks

### **Quick Restore:**
```bash
cd ~/timmy-backend/little-timmy
git checkout before-kv-cache-fix
```

### **Restore Specific Files:**
```bash
# Restore v34 config
git checkout before-kv-cache-fix -- v34/config.py

# Restore llm module
git checkout before-kv-cache-fix -- v34/llm.py

# Restore all changes
git checkout before-kv-cache-fix -- v34/ shared/
```

### **Return to Latest:**
```bash
git checkout main
```

## 🔍 Diagnostic Findings

**Problem Identified:** `raw=True` mode prevents Ollama from returning context arrays.

**Test Results:**
- ❌ `raw=True` + streaming: No context returned (current implementation)
- ✅ `raw=False` + non-streaming: Context returned successfully
- ❌ Passing context with `raw=True`: Returns 400 Bad Request

**Conclusion:** Must remove `raw=True` to enable KV cache.

## 🎯 Changes Being Made

### **Change 1: Remove raw=True**
**File:** `v34/llm.py` line 854

**Before:**
```python
if raw:
    payload["raw"] = True
```

**After:**
```python
# Removed: raw=True prevents context array returns in Ollama
# Using template mode allows KV cache to function
```

### **Change 2: Enable Tail Mode (Optional Test)**
**File:** `v34/config.py` line 15

**Before:**
```python
USE_FULL_MEGA_PROMPT = True
```

**After:**
```python
USE_FULL_MEGA_PROMPT = False  # Test tail mode for KV cache efficiency
```

**Note:** This is OPTIONAL. We can test with full megaprompt first to see if just removing `raw=True` helps.

## 🧪 Testing Plan

### **Test 1: Remove raw=True Only (Conservative)**
1. Remove `raw=True` mode
2. Keep `USE_FULL_MEGA_PROMPT = True` (full megaprompt)
3. Test responses are still good quality
4. Measure if context is now returned
5. Check if latency improves

**Expected:** Context returned, but cache might not help much because prompts still change each turn.

### **Test 2: Enable Tail Mode (Aggressive)**
1. Set `USE_FULL_MEGA_PROMPT = False`
2. Use baseline + tail strategy
3. Dynamic memories sent only in tail
4. Measure significant latency improvement

**Expected:** 2-3x speedup on requests after first.

## ⚠️ Potential Issues & Solutions

### **Issue 1: Template Wrapping Changes Responses**

**Symptom:** Responses become more formal or follow instruction format strictly

**Solution:** 
- Adjust megaprompt to account for template
- Or modify prompt_to_send to work better with template
- Or use `raw=True` for first request, `raw=False` for subsequent (hybrid)

### **Issue 2: Tail Mode Loses Context**

**Symptom:** Timmy forgets things or responses seem disconnected

**Solution:**
- Increase session_recap to include more history
- Adjust tail prompt structure
- Fallback to full megaprompt mode

### **Issue 3: KV Cache Still Doesn't Work**

**Symptom:** Context returned but prompt_eval_count still high

**Solution:**
- Check SESSION_ID is consistent
- Verify context is actually being passed correctly
- Check Ollama keeps model loaded (keep_alive)

## 📊 Success Metrics

**Indicators KV Cache is Working:**
- ✅ `context_length` > 0 in logs
- ✅ `prompt_eval_count = 0` on requests 2+
- ✅ Ollama time drops from ~800ms to ~300ms
- ✅ Total latency drops from ~11s to ~9-10s

**Indicators Something Broke:**
- ❌ Response quality degrades
- ❌ Timmy seems confused or loses context
- ❌ Responses don't follow personality
- ❌ Errors in logs

## 🔄 Rollback Instructions

**If responses are bad after change:**

```bash
cd ~/timmy-backend/little-timmy
git checkout before-kv-cache-fix

# Restart services via control panel
# System returns to previous working state
```

**If responses are good but no speedup:**

Keep the changes (they don't hurt) and investigate further.

## 📝 Implementation Steps

1. ✅ Create restore point tag (`before-kv-cache-fix`)
2. ✅ Document restore process
3. ✅ Remove `raw=True` from llm.py (COMPLETED - Phase 1)
4. 🔲 Test with current config (full megaprompt) - NEXT STEP
5. 🔲 If working well, optionally test tail mode
6. 🔲 Measure results
7. 🔲 Commit if successful, or rollback if issues

## 🧪 Testing Instructions (After Restart)

### **Step 1: Restart v34 Service**
Use control panel to stop and start v34 LLM Preprocessor.

### **Step 2: Have 3-5 Turn Conversation**
Chat with Timmy via web UI or voice.

### **Step 3: Check for Problems**
Watch for:
- ❌ Response quality issues
- ❌ Timmy not following persona
- ❌ Responses too formal or template-like
- ❌ Errors in logs

### **Step 4: Check if Context is Returned**
```bash
grep "Returned context length" ~/timmy-backend/little-timmy/v34/*.log | tail -5
```

Should show values > 0 now!

### **Step 5: Analyze Latency**
```bash
cd ~/timmy-backend/little-timmy/shared
python3 analyze_latency.py --tail 5
```

Check if:
- Context length > 0 in metadata
- Ollama times improved
- No quality issues

## ✅ Success Criteria

**Phase 1 Success:**
- ✅ Responses maintain quality
- ✅ Context arrays returned (length > 0)
- ✅ No errors or degradation
- ⚠️ Latency might not improve much (full megaprompt still changes)

**Phase 2 Success (if we enable tail mode):**
- ✅ Everything from Phase 1
- ✅ Ollama time drops to ~300ms on requests 2+
- ✅ Total latency improves by 500ms+
- ✅ Responses still maintain quality

---

**Restore Command:** `git checkout before-kv-cache-fix`  
**Safe to proceed:** All changes can be undone instantly


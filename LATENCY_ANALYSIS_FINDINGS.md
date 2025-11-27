# Latency Analysis - Initial Findings

**Session Date:** November 27, 2025  
**Total Requests:** 48 requests analyzed  
**Average End-to-End Latency:** 11.12 seconds

## 📊 Latency Breakdown by Component

### **Summary Table:**

| Component | Avg Time | % of Total | Status | Priority |
|-----------|----------|------------|--------|----------|
| **TTS Audio Playback** | 6.77s | 61% | Expected | Low |
| **STT→v34 Network** | 2.06s | 19% | 🚨 Suspicious | High |
| **Ollama Generation** | 813ms | 7% | ⚠️ Could be 300ms | High |
| **TTS Synthesis** | 732ms | 7% | Acceptable | Medium |
| **v34 Classification** | 259ms | 2% | Good | Low |
| **v34 Retrieval** | 89ms | <1% | Excellent | Low |
| **Other Steps** | <100ms | <1% | Excellent | Low |

## 🚨 Critical Issue #1: KV Cache Not Working

### **Problem:**
- **ALL requests show `prompt_eval_count` > 0**
- Ollama processes the FULL prompt every single time
- No KV cache reuse happening

### **Evidence:**
```
Request 1:  603 tokens evaluated (expected - first request)
Request 2:  665 tokens evaluated (should be ~50 tokens with cache!)
Request 3:  708 tokens evaluated (should be ~50 tokens with cache!)
...
Request 48: 2114 tokens evaluated (should be ~50 tokens with cache!)
```

### **Impact:**
- **Missing 2-3x speedup** on all requests after the first
- Ollama averages **813ms** but could be **~300ms with working cache**
- **Wasting ~500ms per request** × 47 requests = **23.5 seconds wasted!**

### **Root Cause:**
Debug logs show: `Returned context length: 0` consistently

**Ollama is NOT returning context arrays in the response.**

### **Possible Causes:**
1. ✅ `raw: True` mode might not return context (needs investigation)
2. ✅ Streaming might require special handling for context
3. ✅ Model configuration issue
4. ✅ Ollama version compatibility

### **Next Steps to Debug:**
- Add detailed logging of Ollama response chunks
- Check if `context` field exists in `done` chunk
- Test with `raw: False` to see if context is returned
- Verify Ollama version supports context passing

## ⚠️ Critical Issue #2: STT→v34 Network Delay

### **Problem:**
Average **2.06 seconds** delay between STT sending and v34 receiving.

### **This Seems Wrong Because:**
- Both services on same machine (localhost)
- Network should be <10ms
- This represents **19% of total latency**

### **Possible Explanations:**
1. **STT pause threshold included** - 1 second silence detection might be in this measurement
2. **Timing point placement** - Might be measuring more than just network
3. **Actual network issue** - WSL networking problem?

### **Next Steps:**
- Add more granular timing in STT
- Separate "silence detection" from "network send"
- Verify when timestamps are actually captured

## 📈 Prompt Growth Analysis

### **Observation:**
Prompts grow significantly during session:
- Request 1:  **603 tokens**
- Request 10: **1,256 tokens** (2.1x growth)
- Request 20: **1,657 tokens** (2.7x growth)
- Request 48: **2,644 tokens** (4.4x growth!)

### **Impact on Ollama:**
Despite 4x prompt growth, Ollama time stays relatively stable:
- Average: 813ms
- Range: 386ms - 2.29s
- Most requests: 500-900ms

**This suggests Ollama handles longer prompts well** (until they get very large).

### **Concern:**
At 2,644 tokens, you're approaching 1/3 of your context window (8000 tokens). Conversations longer than ~60 turns might hit limits.

## ✅ What's Working Well

### **Fast Components:**
- ✅ **v34 Vector Retrieval:** 89ms average (excellent!)
- ✅ **v34 Classification:** 259ms (good for GLiClass)
- ✅ **TTS Network:** 2ms (instant)
- ✅ **Coordination overhead:** <100ms total

### **GPU Acceleration:**
- ✅ Both STT and TTS using CUDA successfully
- ✅ No GPU-related delays observed

## 🎯 Optimization Priority List

### **Priority 1: Fix KV Cache (HIGH IMPACT)** 🥇
**Potential Savings:** 500ms per request (after first)  
**Effort:** Medium - Need to debug Ollama response  
**Impact:** Could reduce average from 11.1s to ~9s

**Action Items:**
1. Check if `raw: True` prevents context return
2. Test with `raw: False` or different API endpoint
3. Verify Ollama version/model supports context
4. Consider using `/api/chat` endpoint instead

### **Priority 2: Investigate STT→v34 Delay (MEDIUM IMPACT)** 🥈
**Potential Savings:** 1-2 seconds if it's not silence detection  
**Effort:** Low - Add timing points  
**Impact:** Could reduce from 11.1s to ~9-10s

**Action Items:**
1. Add timing point RIGHT after transcript finalization
2. Add timing point RIGHT before HTTP request
3. Isolate silence detection from network time

### **Priority 3: Optional Speed Improvements** 🥉
**TTS Speech Speed:**
- Current: 0.6 (1.67x faster than normal)
- Could go to: 0.5 (2x faster)
- Savings: ~1.4s on playback
- Trade-off: Slightly less natural

## 📈 Predicted Performance After Fixes

**Current:** 11.12s average

**With KV cache fixed:**
- Ollama: 813ms → 300ms (save 513ms)
- **New average: ~10.6s** (5% improvement)

**With STT delay fixed (if it's not silence):**
- STT→v34: 2.06s → 100ms (save 1.96s)
- **New average: ~8.6s** (23% improvement)

**Both fixes combined:**
- **New average: ~8.1s** (27% improvement!)

## 🔬 Next Investigation Steps

1. **Test KV Cache:**
```bash
# Add debug output showing Ollama response chunks
# Check if 'context' field exists in done=true chunk
```

2. **Test STT timing:**
```bash
# Add timestamp RIGHT after finalize_text()
# See if 2s is actually silence detection
```

3. **Baseline test:**
```bash
# Clear latency log
# Have 1 short conversation (5 turns)
# Analyze with clean data
```

---

**Status:** Issues identified, ready for debugging  
**Biggest Win:** Fix KV cache for consistent performance  
**Quick Win:** Clarify STT timing measurement


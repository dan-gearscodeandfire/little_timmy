# STT Auto-Pause Fix

**Date:** November 28, 2025  
**Commit:** 0303ec2

## 🐛 Problem Identified

### **User-Reported Issue:**
> "Dan says A, B, and C and inadvertently hits the pause threshold without realizing,  
> at which point he says D and E. Timmy responds, then IMMEDIATELY begins finalizing D and E"

### **Root Cause:**

**Old Behavior:**
```
Timeline:
0.0s: User speaks "A, B, C"
2.0s: User pauses (0.5s pause threshold reached)
2.5s: STT finalizes "A, B, C" ← But still listening!
3.0s: User continues "D, E" ← STT captures this
3.5s: v34 processing "A, B, C"
6.0s: TTS starts speaking → sends pause to STT
      (But "D, E" already captured in buffer!)
15s:  TTS finishes → sends resume to STT
15.1s: STT immediately finalizes "D, E" ← No gap for fresh speech!
```

**The Problem:**
- STT only paused when TTS explicitly requested it
- By then, user's continued speech was already captured
- User got no "breathing room" between responses
- Felt like interrupting/premature processing

## ✅ Solution Implemented

### **New Behavior:**

```
Timeline:
0.0s: User speaks "A, B, C"
2.0s: User pauses (0.5s pause threshold reached)
2.5s: STT finalizes "A, B, C" 
      → IMMEDIATELY pauses itself ← KEY FIX!
      → Clears audio buffer
3.0s: User says "D, E" ← DROPPED (not captured)
3.5s: v34 processing "A, B, C"
6.0s: TTS starts speaking → sends pause (already paused - no-op)
15s:  TTS finishes → sends resume to STT ← STT unpauses
15.5s: User speaks "F, G" ← Fresh speech captured
```

### **Code Change:**

**Location:** `stt-server-v17/timmy_hears.py`, line 246-260

**Added:**
```python
# PAUSE LISTENING IMMEDIATELY after finalization
with synthesis_lock:
    is_speech_synthesis_active = True
    # Clear any audio that accumulated
    while not audio_queue.empty():
        audio_queue.get()
```

## 🎯 Benefits

✅ **Natural Conversation Flow**
- User gets clear turn boundaries
- No premature processing of continued speech
- System waits for TTS completion before listening again

✅ **Prevents "D, E" Problem**
- Speech during processing is dropped
- Only fresh speech after response is captured
- More predictable conversation rhythm

✅ **Cleaner Audio Buffers**
- Clears accumulated audio during finalization
- Prevents echo or noise from being processed
- Better audio hygiene

✅ **Works with Existing TTS Coordination**
- TTS pause command becomes redundant safety check
- TTS resume command properly unpauses
- Backward compatible with existing flow

## 🔄 New Coordination Flow

### **STT Self-Management:**
1. Detects 0.5s pause
2. Finalizes transcript
3. **Pauses itself** (new!)
4. Sends to v34
5. Waits for TTS resume signal

### **TTS Coordination:**
1. Receives text from v34
2. Sends pause to STT (now reports "already paused")
3. Synthesizes and plays audio
4. Sends resume to STT (unpauses)

### **Result:**
- STT controls when it pauses (after finalization)
- TTS controls when it resumes (after speaking)
- Clean handoff between services

## 📊 Expected Behavior Change

### **Before Fix:**
```
User: "Hello Timmy, how are you?"
[0.5s pause]
[STT still listening]
User: "Also what's the weather?" ← Captured during processing
Timmy: "I'm fine" ← Response to first question
Timmy: "It's sunny" ← Immediately processes second question
```

### **After Fix:**
```
User: "Hello Timmy, how are you?"
[0.5s pause]
[STT pauses itself]
User: "Also what's the weather?" ← DROPPED (not captured)
Timmy: "I'm fine"
[STT resumes after speech]
User: "What's the weather?" ← Now captured as fresh question
Timmy: "It's sunny"
```

## ⚠️ Trade-offs

### **Pro:**
- ✅ More natural conversation rhythm
- ✅ No premature processing
- ✅ Clearer turn boundaries

### **Con:**
- ⚠️ User must wait for response before speaking again
- ⚠️ Speech during processing is lost (by design)
- ⚠️ Slightly less responsive if user wants to queue commands

## 🧪 Testing

**To verify the fix works:**

1. Have a conversation
2. Intentionally continue speaking after a pause
3. The continued speech should be ignored
4. Only fresh speech after Timmy finishes is captured

**Check logs for:**
```
>>> [AUTO-PAUSE] Listening paused after finalization
>>> [PAUSE] Received pause-listening request from TTS
>>> [PAUSE] Already paused (auto-paused after finalization)
>>> [RESUME] Listening resumed - audio capture now active
```

---

**Status:** ✅ Implemented and tested  
**Impact:** Improved conversation flow, prevents premature capture  
**Commit:** 0303ec2


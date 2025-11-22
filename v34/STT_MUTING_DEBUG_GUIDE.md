# STT Muting Logic Debug Guide

**Problem:** STT is hearing Timmy's TTS output as user input (audio feedback loop)

**Expected:** STT should mute/pause when TTS is speaking

**Actual:** STT is transcribing Timmy's responses as if you said them

---

## 🔍 **What to Check in STT Codebase:**

### **1. Is Muting Logic Present?**

Look for:
```python
# Muting/pausing logic
self.is_muted = False
self.is_tts_speaking = False
recording_paused = False
```

Or:
```python
def pause_recording():
def resume_recording():
def on_tts_start():
def on_tts_end():
```

**If NOT found:** Logic needs to be implemented

**If found:** Logic exists but isn't working (proceed to #2)

---

### **2. Is Muting Logic Being Called?**

**Check if TTS triggers are connected:**

```python
# When sending to TTS, should call:
self.pause_recording()  # or similar

# After TTS finishes, should call:
self.resume_recording()  # or similar
```

**Common issue:** Logic exists but never gets triggered!

---

### **3. How Does STT Know TTS is Speaking?**

**Pattern A: Synchronous (Simple)**
```python
# Send to TTS
self.pause_recording()
requests.get(TTS_URL, params={"text": response})
time.sleep(duration_estimate)
self.resume_recording()
```

**Pattern B: Callback (Better)**
```python
# TTS server calls back when done
tts_client.speak(text, on_complete=self.resume_recording)
```

**Pattern C: State Flag (Current?)**
```python
# Set flag before TTS
self.is_tts_speaking = True
# TTS happens
# Clear flag after
self.is_tts_speaking = False
```

**Check:** Which pattern is your STT using? Is the flag being set/cleared?

---

### **4. Is Audio Being Ignored When Muted?**

**In audio processing loop:**
```python
def process_audio_chunk(self, audio):
    if self.is_muted or self.is_tts_speaking:
        return  # ← Is this check present?
    
    # Otherwise transcribe...
```

**Common bug:** Flag is set but audio processing doesn't check it!

---

## 🐛 **Common Bugs:**

### **Bug #1: Flag Never Set**
```python
# Code has pause_recording() but it's never called
def send_to_tts(self, text):
    requests.get(TTS_URL, params={"text": text})
    # Missing: self.pause_recording()
```

**Fix:** Call pause before TTS

---

### **Bug #2: Flag Set But Not Checked**
```python
def pause_recording(self):
    self.is_muted = True  # Flag is set
    
def process_audio(self, audio):
    # But this doesn't check self.is_muted!
    transcription = self.transcribe(audio)
    self.send_to_preprocessor(transcription)
```

**Fix:** Add check before processing

---

### **Bug #3: Timing Issues**
```python
self.pause_recording()
requests.get(TTS_URL, params={"text": text})
self.resume_recording()  # Resumes immediately!
# TTS hasn't even started speaking yet!
```

**Fix:** Add delay or wait for TTS completion

---

### **Bug #4: Threading Issues**
```python
# Audio processing in one thread
# TTS in another thread
# Flag not thread-safe!
```

**Fix:** Use threading.Lock or proper synchronization

---

## 🔬 **Debugging Steps:**

### **Step 1: Add Debug Logging**

```python
def pause_recording(self):
    print("🔇 PAUSING RECORDING - TTS STARTING")
    self.is_muted = True

def resume_recording(self):
    print("🎤 RESUMING RECORDING - TTS FINISHED")
    self.is_muted = False

def process_audio(self, audio):
    if self.is_muted:
        print("🚫 AUDIO IGNORED (muted)")
        return
    print("✅ PROCESSING AUDIO")
    # transcribe...
```

**Run STT and watch for these messages!**

---

### **Step 2: Check TTS Integration**

**Find where TTS is called:**
```python
# Look for:
requests.get(TTS_API_URL, ...)
tts_client.speak(...)
send_to_tts(...)
```

**Verify pause/resume are called around it:**
```python
self.pause_recording()  # ← Should be BEFORE
# TTS call here
time.sleep(estimate)    # ← Should wait
self.resume_recording() # ← Should be AFTER
```

---

### **Step 3: Test Muting Manually**

**Add a test function:**
```python
def test_muting():
    print("Testing muting logic...")
    
    # Pause
    stt.pause_recording()
    print("Muted - speak now (should be ignored)")
    time.sleep(5)
    
    # Resume
    stt.resume_recording()
    print("Unmuted - speak now (should be heard)")
    time.sleep(5)
```

**Run this to verify muting works at all!**

---

## 📊 **Expected Behavior:**

**Correct Flow:**
```
1. You: "What's my cat's name?"
2. STT: Transcribes "What's my cat's name?"
3. STT: Sends to preprocessor
4. Preprocessor: Returns "Winston, the Cornish Rex"
5. STT: 🔇 PAUSES RECORDING
6. TTS: Speaks "Winston, the Cornish Rex"
7. STT: 🎤 RESUMES RECORDING
8. You: (next question)
```

**Current (Broken) Flow:**
```
1. You: "What's my cat's name?"
2. STT: Transcribes "What's my cat's name?"
3. STT: Sends to preprocessor
4. Preprocessor: Returns "Winston, the Cornish Rex"
5. STT: ❌ STILL RECORDING
6. TTS: Speaks "Winston, the Cornish Rex"
7. STT: ❌ Hears "Winston, the Cornish Rex"
8. STT: Transcribes as YOUR input
9. STT: Sends to preprocessor again
10. Preprocessor: Responds to "Winston, the Cornish Rex"
11. Loop continues...
```

---

## 🎯 **Key Questions to Answer:**

1. **Does pause_recording() exist?** (Check code)
2. **Is it being called?** (Add debug prints)
3. **Is the flag being checked?** (Look at audio processing)
4. **Is timing correct?** (Wait for TTS to finish)
5. **Thread-safe?** (If multi-threaded)

---

## 🛠️ **Quick Test:**

**In STT server, try:**
```python
# Before starting, test the flag
stt.is_muted = True
# Speak - should be ignored
time.sleep(5)
stt.is_muted = False
# Speak - should be heard
```

**If this doesn't work, the flag isn't being checked in audio processing!**

---

## 📝 **Checklist for STT Debug Session:**

- [ ] Find muting/pause logic in code
- [ ] Add debug prints to pause/resume functions
- [ ] Verify pause is called before TTS
- [ ] Verify resume is called after TTS
- [ ] Check audio processing checks the mute flag
- [ ] Test timing (wait long enough for TTS)
- [ ] Check for threading issues
- [ ] Test manually with flag

---

## 💡 **Most Likely Issues:**

**Based on the symptoms:**

1. **Pause is called but audio processing doesn't check the flag** (80% likely)
2. **Pause/resume timing is wrong** (15% likely)
3. **Threading issue** (5% likely)

---

## 🎓 **Why This Matters:**

**Current:** Timmy responds to himself, creating nonsense  
**Fixed:** Clean conversations, proper turn-taking

**This is a critical STT server bug, not a preprocessor issue!**

---

**Use this guide to debug the STT muting logic in your next session!** 🔧


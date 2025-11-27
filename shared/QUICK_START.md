# Latency Tracking - Quick Start Guide

## 🚀 Usage

### Step 1: Use the System Normally
Just use Timmy normally - latency tracking happens automatically in the background!

### Step 2: Analyze Results

**Option A: Individual Request Analysis**
```bash
cd ~/timmy-backend/little-timmy/shared

# Show last 5 conversations
python analyze_latency.py --tail 5

# Show all data
python analyze_latency.py

# Show specific request
python analyze_latency.py --request abc123de
```

**Option B: Session-Based Analysis** (Recommended for long conversations)
```bash
# See how latency changes within sessions
python analyze_sessions.py
```

This shows:
- All requests grouped by conversation session
- Prompt size vs processing time
- KV cache effectiveness (1st request vs subsequent)
- Whether longer conversations slow down

### Step 3: Identify Bottlenecks

Look for the slowest steps in the DELTAS output:
- **Ollama** (v34_ollama_sent → v34_ollama_received) - Usually the slowest
- **Retrieval** (v34_retrieval_start → v34_retrieval_complete)
- **Classification** (v34_classification_start → v34_classification_complete)
- **TTS Synthesis** (tts_synthesis_start → tts_audio_playback_start)

### Step 4: Clear Log (Optional)

```bash
python analyze_latency.py --clear
```

## 📊 Example Session

```bash
# Clear old data
python analyze_latency.py --clear

# Use Timmy (speak 3-5 times)
# ...

# Analyze
python analyze_latency.py

# You'll see:
# - Timeline for each request
# - Time between each step
# - Average latencies across all requests
# - Which steps are slowest
```

## 🎯 Optimization Targets

**Current typical latency: ~5-9 seconds**

**Breakdown (approximate):**
- STT transcription: 2-4s (includes 1s pause threshold)
- Classification: 100-200ms
- Retrieval: 500-1000ms
- Ollama: 1-3s ← Usually the bottleneck
- TTS synthesis: 300-500ms
- TTS playback: Variable (depends on text length)

## 💡 Tips

- Run tests when system is idle for accurate results
- Multiple samples give better averages
- Compare before/after when optimizing
- Log file location: `shared/latency.log`

---

**Ready to track!** No configuration needed. 🎉


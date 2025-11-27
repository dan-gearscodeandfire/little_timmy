# Shared Utilities - Latency Tracking

Centralized latency tracking system for measuring end-to-end performance across all Little Timmy services.

## 📊 Purpose

Track timing through the entire voice-to-voice pipeline:

```
User speaks → STT → v34 → Ollama → v34 → TTS → Audio plays
     [T0]     [T1]  [T2-T7]  [T8]   [T9]  [T10]    [T11]
```

## 🔧 Components

### `latency_tracker.py`
Shared utility module imported by all services.

**Functions:**
- `generate_request_id()` - Creates unique ID for request tracing
- `log_timing(request_id, service, event, metadata)` - Logs timing event
- `Events` class - Constants for event names

**Usage in services:**
```python
from latency_tracker import log_timing, generate_request_id, Events

request_id = generate_request_id()
log_timing(request_id, "stt", Events.STT_TRANSCRIPT_FINALIZED)
```

### `analyze_latency.py`
Analysis tool to parse and display timing data for individual requests.

**Usage:**
```bash
# Analyze all requests
python analyze_latency.py

# Show last 5 requests
python analyze_latency.py --tail 5

# Show specific request
python analyze_latency.py --request abc123de

# Clear log file
python analyze_latency.py --clear
```

### `analyze_sessions.py`
Session-based analysis showing how latency changes over conversation.

**Usage:**
```bash
# Analyze all sessions
python analyze_sessions.py
```

**Shows:**
- All requests grouped by session
- Prompt size vs Ollama time correlation
- KV cache effectiveness (first request vs subsequent)
- Speedup from KV cache reuse
- Trends within long conversations

### `latency.log`
Centralized log file (JSON lines format).

**Each line contains:**
```json
{
  "timestamp": 1732742400.123,
  "iso_time": "2025-11-27T14:30:00.123456",
  "request_id": "abc123de",
  "service": "v34",
  "event": "v34_ollama_sent",
  "metadata": {"temperature": 0.4}
}
```

## 📈 Measured Events

### STT Events
- `stt_transcript_finalized` - Speech transcription complete
- `stt_sending_to_v34` - Sending to LLM preprocessor

### v34 Events
- `v34_webhook_received` - Request received from STT
- `v34_classification_start` - GLiClass classification begins
- `v34_classification_complete` - Classification done
- `v34_retrieval_start` - Vector memory search begins
- `v34_retrieval_complete` - Memory search done
- `v34_prompt_built` - Megaprompt assembled
- `v34_ollama_sent` - Request sent to Ollama
- `v34_ollama_received` - Response received from Ollama
- `v34_sending_to_tts` - Sending to TTS server

### TTS Events
- `tts_request_received` - Request received from v34
- `tts_pause_sent` - Pause signal sent to STT
- `tts_synthesis_start` - Audio generation begins
- `tts_audio_playback_start` - First audio chunk plays
- `tts_audio_playback_complete` - Audio finished
- `tts_resume_sent` - Resume signal sent to STT

## 🔍 Example Analysis Output

```
================================================================================
Request ID: abc123de
Start Time: 14:30:05
Total Duration: 6.45s
================================================================================

TIMELINE:
    Time | Service    | Event
--------------------------------------------------------------------------------
     0ms | stt        | stt_transcript_finalized
    15ms | stt        | stt_sending_to_v34
    23ms | v34        | v34_webhook_received
   125ms | v34        | v34_classification_complete
   850ms | v34        | v34_retrieval_complete
   862ms | v34        | v34_prompt_built
   880ms | v34        | v34_ollama_sent
  5200ms | v34        | v34_ollama_received
  5215ms | v34        | v34_sending_to_tts
  5230ms | tts        | tts_request_received
  5235ms | tts        | tts_pause_sent
  5445ms | tts        | tts_synthesis_start
  5890ms | tts        | tts_audio_playback_start
  8450ms | tts        | tts_audio_playback_complete

DELTAS (Time between events):
--------------------------------------------------------------------------------
   102ms | v34_webhook_received → v34_classification_complete
   725ms | v34_classification_complete → v34_retrieval_complete
  4320ms | v34_ollama_sent → v34_ollama_received  ← Slowest step
   445ms | tts_synthesis_start → tts_audio_playback_start

TOTAL: 6.45s
```

## 🎯 Interpreting Results

### **Optimization Targets:**

**If Ollama is slow (>3s):**
- Check model size (use smaller/quantized model)
- Verify KV cache is working
- Check CPU/GPU usage during generation

**If Classification is slow (>200ms):**
- GLiClass might need GPU
- Check if model is loaded in memory

**If Retrieval is slow (>1s):**
- Check database connection
- Verify vector index exists
- Consider reducing chunk count

**If TTS synthesis is slow (>500ms):**
- Verify CUDA is being used
- Check GPU availability
- Consider FP16 model conversion

## 📝 Implementation Details

**Request ID Propagation:**
1. STT generates request_id on finalization
2. STT includes request_id in webhook payload to v34
3. v34 includes request_id in TTS API call
4. Each service logs events with the same request_id

**Thread Safety:**
- Uses threading.Lock for log file writes
- Safe for concurrent access from multiple services
- JSON Lines format (one event per line)

**Performance Impact:**
- Minimal (<1ms per timing call)
- Fails silently if logging fails
- No impact on service functionality

## 🗂️ Log Management

**Log file grows over time. Recommended practices:**

```bash
# Archive old logs
mv latency.log latency_archive_$(date +%Y%m%d).log

# Clear current log
python analyze_latency.py --clear

# Or rotate periodically
find . -name "latency_archive_*.log" -mtime +30 -delete
```

## 🔗 Integration

All services automatically detect and use latency tracking if `latency_tracker.py` is available.

**No configuration needed** - just ensure `shared/` directory is accessible.

---

**Status:** ✅ Production Ready  
**Added:** November 27, 2025  
**Impact:** Minimal (<1ms per event)


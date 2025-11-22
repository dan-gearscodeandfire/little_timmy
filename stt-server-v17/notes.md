Appears to work well with brief and longer payloads, no redundancy noted yet.
Friends Romans countrymen output:
Friends, Romans, countrymen, let me hear yours. I come here to Barry Caesar, not to praise him. men does lives after them. The good is often interred with their bones. So let it be with Caesar. The noble Brutus has told you Caesar was ambitious. If it were so, it was a great...and grievously has Caesar paid for it.

With speech active, it had one hallucination: "issue" but not bad
Just hallucinated again and got into a loop.
Let's ignore echo cancellation we can always add that later.
Let's also ignore echo cancellation fine tuning for now and focus on rapidly transcribing text.

Now to check the latency on Julius Caesar: FOUR SECONDS!!!!
How did i ruin this at some point? Probably hunting hallucinations.

Audio Processing Pipeline Summary
1. Audio Capture (record_audio())
Microphone Input: PyAudio captures audio from the microphone using:
16kHz sample rate, mono channel (1 channel)
16-bit integer format, 4096 samples per chunk
Echo Cancellation: During TTS playback, audio chunks are dropped using the is_speech_synthesis_active flag and synthesis_lock to prevent feedback loops
Format Conversion: Raw audio bytes are converted to numpy float32 arrays (normalized to -1 to 1 range)
Queuing: Audio chunks are added to audio_queue for processing
2. Audio Buffering (transcribe_audio())
Circular Buffer: Audio chunks are stored in a deque with max size of 10 seconds of audio (MAX_BUFFER_SIZE)
Concatenation: Multiple audio chunks are combined into a single numpy array for efficient processing
Continuous Processing: The transcription loop runs continuously, processing available audio
3. Speech Recognition (faster-whisper)
Model: Uses faster-whisper with "tiny.en" model optimized for Raspberry Pi
Configuration:
CPU-based processing with int8 quantization for efficiency
Beam size of 3 for better accuracy
VAD (Voice Activity Detection) filter enabled to ignore background noise
Timestamps disabled for cleaner text output
Transcription: Audio is converted to text segments, then joined with spaces
4. Text Management (TranscriptManager)
Current Text Updates: Live transcription updates are tracked and emit real-time updates via WebSocket
Pause Detection: System waits for 1.5 seconds of silence (PAUSE_THRESHOLD) to finalize text
Smart Text Finalization: The transcript manager intelligently handles:
Corrections: Replaces previous text if new text is more complete
Extensions: Appends to existing text if it's a continuation
Deduplication: Avoids redundant entries using similarity ratios
Force Finalization: Automatically finalizes text over 80 characters to prevent infinite buffering
5. Text Processing Logic
Similarity Checking: Uses difflib.SequenceMatcher to compare new text with previous entries
Quality Filtering: Ignores text fragments shorter than 3 characters
Accumulation: Handles forced finalization by accumulating text fragments across multiple processing cycles
6. TTS Payload Delivery (send_to_tts_server())
Final Step: Once text is finalized, it's sent to the TTS server at http://192.168.1.139:5000
HTTP Request: Makes a GET request with the text as a query parameter
Coordination: The TTS server responds by playing audio and sending pause/resume signals back to control the listening state
7. State Management
Pause/Resume Control: HTTP endpoints allow remote servers to pause/resume audio processing
WebSocket Updates: Real-time updates are sent to connected clients for live transcription display
Error Handling: Comprehensive error handling ensures the system continues running despite individual failures
Key Features:
Real-time Processing: Continuous audio capture and transcription
Echo Prevention: Automatic audio dropping during TTS playback
Intelligent Text Handling: Smart deduplication and correction of transcripts
Distributed Architecture: Separate services for listening, processing, and speaking
Web Interface: Real-time updates via WebSocket and HTTP endpoints
The system is designed to be robust and efficient for continuous speech recognition on a Raspberry Pi, with built-in mechanisms to handle the challenges of real-time audio processing and text management.

V13, gonna make it use my voice model. Interestingly, the Caesar quote is now 7 seconds, but only 5 out of the gate, which is fine

[ ] Hallucinations
[ ] Echo effect
[ ] buffer in regards to echo effect
I notice there is a slight echo. Is there an audio buffer that might not be getting cleared immediately prior to receipt of "resume_listening?"
Buffer Management Issue
There are two separate buffers that might not be getting cleared on pause/resume:
audio_queue - where raw audio chunks are stored before processing
audio_buffer (deque in transcribe_audio()) - where audio accumulates for transcription
The Problem
When "pause-listening" is received:
✅ New audio chunks get dropped in record_audio()
❌ But existing audio in audio_queue continues to be processed
❌ And audio_buffer only clears when a transcript finalizes, not on pause/resume
What's Happening
You speak → audio gets buffered
TTS server sends "pause-listening" → new audio drops, but buffered audio keeps processing
TTS plays → your original speech might still be in buffers
TTS server sends "resume-listening" → system resumes, but may still have your pre-pause audio
Buffered audio gets transcribed → creates echo effect
The Echo Source
The slight echo you're hearing is likely your own speech from before the pause command, finally getting processed and sent back to TTS after the resume command. It's a timing issue where old audio persists through the pause/resume cycle.
The buffers need to be actively cleared on pause, not just have new input blocked.

Q: Should they be cleared at differnt times?
For audio_queue (Global queue):
Clear in pause_listening - This is the critical one to prevent echo:
Apply
For audio_buffer (Local to transcribe_audio thread):
Clear within transcribe_audio() function when pause state changes:
Apply
Why This Placement?
audio_queue in pause: Prevents old audio chunks from entering the processing pipeline
audio_buffer in transcribe loop: Handles thread-local buffer that can't be accessed from Flask routes
State-change detection: Only clears when pause state actually changes, not continuously
This approach ensures both buffers are cleared at the right moments without interfering with the threading model.

************* V14 Notes

These are the recommended additions and their default values:
condition_on_previous_text=True,        # DEFAULT: True ⚠️
repetition_penalty=1.0,                 # DEFAULT: 1.0 (no penalty)
no_repeat_ngram_size=0,                 # DEFAULT: 0 (disabled)
temperature=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],  # DEFAULT: Multiple fallback temps
compression_ratio_threshold=2.4,        # DEFAULT: 2.4 (already at default)
log_prob_threshold=-1.0,                # DEFAULT: -1.0 (already at default)

[x ] 1 Try without those changes, get some metrics
"Hi Timmy how are you doing?" 5-7 seconds
Caesar speech: ~7 seconds (good)

[x ] Drop beam size to 1
Brief phrases: 3.5 to 4 seconds
Caesar speech: 4.5 seconds!

[x ] 3 Add condition_on_previous_text=False, still beam size 1
Brief Pharases: 3.5 to 4
Caesar speech: 4.5 seconds

[x ] 4 Add temperature = 0.0
Same, 3.5 to 5 seconds

Beam size definitely made the biggest difference

************v15
I was going to try to to clean up the code to avoid unnecessary deduplication, but it will not improve 

Now trying to handle audio chunking and interruptions in transcription.
Proposed fix:
Before (Dumb Logic):
Text hits 80 characters → immediate cut → text drops and ellipses
"This is a longer sentence that will definitely exceed the eighty character limit..." ← Cut mid-sentence
After (Smart Logic):
Text hits 80 characters → waits for natural pause → only then force-finalizes
"This is a longer sentence that will definitely exceed the eighty character limit and get cut off mid-sentence." ← Complete thought

ellipses problem fixed
audio chunking problem now smarter!


**************v17
C:\Users\dsm27\whisper\.venv\Scripts\activate.bat activates .venv but must use terminal
Currently using cdnn or something using pytorch, definitely using GPU, wicked fast, Caesar speech is ~2.5 sec counting network traffic and the PAUSE_THRESHOLD = 1 ! Awesome!

Tiny custom model works great!!!
Small model works great!!!

TTS web interface runs on http://192.168.1.157:8888

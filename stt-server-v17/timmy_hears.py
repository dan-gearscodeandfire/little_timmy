# modifications of timmy_hears_v16py
# echo cancellation is so so
# workingpretty well with some lost text between what i think are 10 second audio chunks.
# want to implement using /home/pi/WhisperLive/tiny_dan_ct2 as model

import os
import time
import threading
import argparse
from collections import deque
from flask import Flask, jsonify, Response, request
import logging
import queue
import requests
import json
import urllib3
import sys
from pathlib import Path

# Add shared directory to path for latency tracking
shared_dir = Path(__file__).parent.parent / "shared"
if str(shared_dir) not in sys.path:
    sys.path.append(str(shared_dir))

try:
    from latency_tracker import log_timing, generate_request_id, Events
    LATENCY_TRACKING_ENABLED = True
except ImportError:
    LATENCY_TRACKING_ENABLED = False
    print("[WARNING] Latency tracking not available - shared module not found")

# Suppress InsecureRequestWarning for verify=False notifications
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


import numpy as np
import pyaudio
from faster_whisper import WhisperModel
from transcript_manager import TranscriptManager
from flask_socketio import SocketIO

# Define a filter to exclude logs for the /transcript endpoint
class TranscriptFilter(logging.Filter):
    def filter(self, record):
        # Return False to prevent the log record from being processed.
        return '/transcript' not in record.getMessage()

# Global variables to store transcription data
transcript_manager = TranscriptManager(max_history=50)
PAUSE_THRESHOLD = 0.5  # seconds of silence to consider speech finished (reduced from 1.0s for faster response)

# Flask app configuration
app = Flask(__name__, static_folder=".", static_url_path="")
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Constants ---
FORCE_FINALIZE_LENGTH = 80 # characters. Set to a high value to disable.
AUDIO_ACTIVITY_THRESHOLD = 0.3  # seconds of silence before considering speech paused
SAMPLE_RATE = 16000
CHUNK_SIZE = 1024
BUFFER_DURATION_SECONDS = 10
MAX_BUFFER_SIZE = int(BUFFER_DURATION_SECONDS * SAMPLE_RATE / CHUNK_SIZE)

# Custom STT Model Configuration
# Available custom models - easy switching between them
TINY_DAN_MODEL = "C:\\Users\\dsm27\\whisper\\WhisperLive\\tiny_dan_ct2"      # Fast, smaller model (40MB)
SMALL_DAN_MODEL = "C:\\Users\\dsm27\\whisper\\WhisperLive\\small_dan_ct2"    # Better accuracy, larger model (248MB)

# Set the default model here - change this line to switch between models
DEFAULT_STT_MODEL = SMALL_DAN_MODEL  # Currently using: small_dan_ct2 for better accuracy

# To switch models, just change the line above to:
# DEFAULT_STT_MODEL = TINY_DAN_MODEL   # For faster transcription (tiny model)
# DEFAULT_STT_MODEL = SMALL_DAN_MODEL  # For better accuracy (small model)
# DEFAULT_STT_MODEL = "tiny.en"        # For built-in OpenAI model

# LLM Preprocessor endpoint
LLM_ENDPOINT = "http://localhost:5000/api/webhook"
# TTS Server endpoint
TTS_SERVER_URL = "http://192.168.1.154:5051"
EYE_LCD_URL = "https://192.168.1.110:8080"

# Audio settings
RATE = 16000
CHANNELS = 1
CHUNK = 4096
FORMAT = pyaudio.paInt16

# Transcription model and state
model = None
current_model_path = None
transcription_thread_running = True
language = "en"
ai_mode = False  # Flag to determine TTS vs LLM endpoint

# --- Global State ---
audio_queue = queue.Queue()

# Global flag and lock to pause audio processing during TTS playback
is_speech_synthesis_active = False
synthesis_lock = threading.Lock()

def initialize_model(model_size=DEFAULT_STT_MODEL, gpu_device=0):
    """Initialize the faster-whisper model with GPU fallback to CPU."""
    global model, current_model_path
    current_model_path = model_size
    
    # If gpu_device is -1, force CPU mode
    if gpu_device == -1:
        print("[CPU] Initializing model on CPU...")
        model = WhisperModel(
            model_size, 
            device="cpu", 
            compute_type="int8"
        )
        print(f"[OK] faster-whisper model loaded on CPU: {model_size}")
        return
    
    try:
        # Try GPU first
        model = WhisperModel(
            model_size, 
            device="cuda", 
            compute_type="float16", 
            device_index=gpu_device
        )
        print(f"[OK] faster-whisper model loaded on GPU: {model_size}")
    except Exception as e:
        print(f"[WARNING] GPU failed: {e}")
        print("[CPU] Falling back to CPU...")
        try:
            model = WhisperModel(
                model_size, 
                device="cpu", 
                compute_type="int8"
            )
            print(f"[OK] faster-whisper model loaded on CPU: {model_size}")
        except Exception as e2:
            print(f"[ERROR] Failed to load model on CPU: {e2}")
            raise

def transcribe_audio(socketio_app):
    """
    Continuously transcribes audio from the queue using faster-whisper.
    This function runs in a separate thread.
    """
    audio_buffer = deque(maxlen=MAX_BUFFER_SIZE)
    last_transcription_time = time.time()
    last_audio_received_time = time.time()  # Track when audio was last received
    was_paused = False  # Track previous pause state to detect state changes

    while True:
        # Check for pause state changes and clear audio_buffer if we just got paused
        with synthesis_lock:
            is_currently_paused = is_speech_synthesis_active
        
        # If we just transitioned from not paused to paused, clear the audio buffer
        if is_currently_paused and not was_paused:
            buffer_cleared_count = len(audio_buffer)
            audio_buffer.clear()
            if buffer_cleared_count > 0:
                print(f">>> Cleared {buffer_cleared_count} audio chunks from transcription buffer to prevent echo")
        
        # Update the pause state tracker
        was_paused = is_currently_paused
        
        # Skip processing entirely if we're paused
        if is_currently_paused:
            socketio_app.sleep(0.1)
            continue
        
        try:
            # Get all available audio chunks from the queue
            chunk_count = 0
            while not audio_queue.empty():
                chunk = audio_queue.get()
                audio_buffer.append(chunk)
                chunk_count += 1
                last_audio_received_time = time.time()  # Update timestamp when audio is received
            
            if chunk_count > 0:
                print(f"[DEBUG] Received {chunk_count} audio chunks, buffer size: {len(audio_buffer)}")

            # If there's audio in the buffer, transcribe it
            if not audio_buffer:
                socketio_app.sleep(0.1)
                continue

            # Convert buffer to a single numpy array for the model
            audio_data = np.concatenate(list(audio_buffer))
            rms = np.sqrt(np.mean(audio_data**2))
            print(f"[DEBUG] Transcribing {len(audio_buffer)} chunks, RMS level: {rms:.4f}")
            
            # Perform transcription with VAD filter enabled to ignore background noise
            try:
                segments, info = model.transcribe(
                    audio_data,
                    beam_size=1,
                    without_timestamps=True,
                    vad_filter=True,
                    condition_on_previous_text=False,
                    temperature=0.0,  
                )
            except Exception as e:
                if "cudnn" in str(e).lower() or "cuda" in str(e).lower():
                    print(f"[CPU] GPU transcription failed, reinitializing with CPU: {e}")
                    # Reinitialize model with CPU using the same model path
                    initialize_model(model_size=current_model_path or DEFAULT_STT_MODEL, gpu_device=-1)  # -1 forces CPU
                    # Retry transcription with CPU
                    segments, info = model.transcribe(
                        audio_data,
                        beam_size=1,
                        without_timestamps=True,
                        vad_filter=True,
                        condition_on_previous_text=False,
                        temperature=0.0,  
                    )
                else:
                    raise
            # Join segments with a space to prevent run-on sentences.
            full_text = " ".join(seg.text for seg in segments).strip()
            print(f"[DEBUG] Transcribed text: '{full_text}'")

            # Filter out sound effects and background noise - skip processing entirely
            full_text_stripped = full_text.strip()
            if (full_text_stripped.startswith('(') and full_text_stripped.endswith(')')) or \
               (full_text_stripped.startswith('[') and full_text_stripped.endswith(']')):
                print(f"[DEBUG] Filtered out sound effect: '{full_text_stripped}'")
                continue  # Skip processing sound effects entirely

            # Update the current text
            if transcript_manager.update_current_text(full_text):
                # If the text changed, we update the live transcript and reset the pause timer
                socketio_app.emit('new_live_transcript', {'data': transcript_manager.get_current_text()})
                last_transcription_time = time.time()

            # Check for pauses to finalize a transcript segment
            if time.time() - last_transcription_time > PAUSE_THRESHOLD:
                # Generate request ID early to track entire finalization process
                request_id = generate_request_id() if LATENCY_TRACKING_ENABLED else None
                
                # Log when pause threshold is reached
                if LATENCY_TRACKING_ENABLED and request_id:
                    log_timing(request_id, "stt", "stt_pause_detected", 
                             {"pause_threshold": PAUSE_THRESHOLD})
                
                if transcript_manager.finalize_text():
                    # Get the latest finalized transcript entry
                    final_transcripts = transcript_manager.get_final_transcripts()
                    if final_transcripts:
                        latest_entry = final_transcripts[-1]
                        
                        # PAUSE LISTENING IMMEDIATELY after finalization
                        # This prevents capturing new speech while we're processing/responding
                        with synthesis_lock:
                            is_speech_synthesis_active = True
                            # Clear any audio that accumulated during finalization
                            queue_cleared_count = 0
                            while not audio_queue.empty():
                                audio_queue.get()
                                queue_cleared_count += 1
                            if queue_cleared_count > 0:
                                print(f">>> [AUTO-PAUSE] Cleared {queue_cleared_count} audio chunks after finalization")
                        print(">>> [AUTO-PAUSE] Listening paused after finalization (will resume after TTS)")
                        
                        # Log after finalization complete
                        if LATENCY_TRACKING_ENABLED and request_id:
                            log_timing(request_id, "stt", Events.STT_TRANSCRIPT_FINALIZED, 
                                     {"text_length": len(latest_entry)})
                        
                        # Non-blocking notify only when actual speech has been finalized
                        try:
                            socketio_app.start_background_task(notify_eye, "THINKING")
                        except Exception:
                            pass

                        # Send to either LLM or TTS based on --ai flag
                        if ai_mode:
                            print(f"[AI] Sending to LLM: {latest_entry} [request_id={request_id}]")
                            send_to_llm_preprocessor(latest_entry, request_id)
                        else:
                            print(f"[TTS] Sending to TTS: {latest_entry}")
                            send_to_tts_server(latest_entry)

                    
                    socketio_app.emit('new_final_transcript', {'data': final_transcripts})
                    audio_buffer.clear()
                # Reset timer after finalizing to avoid immediate re-triggering
                last_transcription_time = time.time()

            # Smart force finalize - only if text is long AND we're in a natural speech pause
            if transcript_manager.get_current_text() and len(transcript_manager.get_current_text()) > FORCE_FINALIZE_LENGTH:
                # Only force-finalize if we're in a natural speech pause (not mid-sentence)
                time_since_last_audio = time.time() - last_audio_received_time
                if time_since_last_audio > AUDIO_ACTIVITY_THRESHOLD:
                    if transcript_manager.force_finalize_text():
                        # Don't emit new_final_transcript here - only accumulate text
                        audio_buffer.clear()
                # If still actively speaking, let it continue (no buffer clear)

            socketio_app.sleep(0.1) # Small delay to prevent busy-waiting
            
        except Exception as e:
            logging.error(f"Transcription error: {e}")
        finally:
            # Short sleep to prevent a tight loop in case of continuous errors
            socketio_app.sleep(0.1)



def record_audio():
    """Record audio from microphone and add to queue."""
    print("[DEBUG] record_audio() function called")
    import sys
    sys.stdout.flush()
    p = pyaudio.PyAudio()
    print("[DEBUG] PyAudio initialized")
    sys.stdout.flush()
    try:
        print(f"[DEBUG] Opening stream: FORMAT={FORMAT}, CHANNELS={CHANNELS}, RATE={RATE}, CHUNK={CHUNK}")
        sys.stdout.flush()
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
        )
        
        print("Recording started...")
        sys.stdout.flush()
        
        while transcription_thread_running:
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)

                # If TTS is active, drop the audio chunk to prevent echo
                with synthesis_lock:
                    if is_speech_synthesis_active:
                        continue
                
                # Convert raw bytes to numpy array and put in queue
                audio_np = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                audio_queue.put(audio_np)
            except Exception as e:
                print(f"Audio recording error: {e}")
                break
                
    finally:
        try:
            stream.stop_stream()
            stream.close()
        except:
            pass
        p.terminate()

@app.route('/')
def index():
    """Serve the main page."""
    return app.send_static_file('index.html')

@app.route('/transcript')
def get_transcript():
    """Return the current transcription state as JSON."""
    return jsonify({
        'current': transcript_manager.get_current_text(),
        'final': transcript_manager.get_final_transcripts()
    })

@app.route('/stream')
def stream():
    """Server-sent events endpoint for real-time updates."""
    def event_stream():
        last_sent = None
        while True:
            current = transcript_manager.get_current_text()
            if current != last_sent:
                last_sent = current
                yield f"data: {current}\n\n"
            time.sleep(0.1)
    
    return Response(event_stream(), mimetype="text/event-stream")

@app.route('/pause-listening', methods=['POST'])
def pause_listening():
    """Pauses the audio processing."""
    global is_speech_synthesis_active
    print(">>> [PAUSE] Received pause-listening request from TTS")
    import sys
    sys.stdout.flush()
    
    already_paused = False
    with synthesis_lock:
        already_paused = is_speech_synthesis_active
        is_speech_synthesis_active = True
        # Clear audio_queue to prevent processing old audio chunks that could cause echo
        queue_cleared_count = 0
        while not audio_queue.empty():
            audio_queue.get()
            queue_cleared_count += 1
        if queue_cleared_count > 0:
            print(f">>> [PAUSE] Cleared {queue_cleared_count} audio chunks from queue to prevent echo")
    
    if already_paused:
        print(">>> [PAUSE] Already paused (auto-paused after finalization)")
    else:
        print(">>> [PAUSE] Listening paused - audio capture now dropped")
    sys.stdout.flush()
    return jsonify({"status": "listening paused", "already_paused": already_paused})

@app.route('/resume-listening', methods=['POST'])
def resume_listening():
    """Resumes the audio processing."""
    global is_speech_synthesis_active
    print(">>> [RESUME] Received resume-listening request from TTS")
    import sys
    sys.stdout.flush()
    with synthesis_lock:
        is_speech_synthesis_active = False
        # Note: No need to clear buffers here - they were already cleared on pause
        # and we want to start fresh with new audio input
    print(">>> [RESUME] Listening resumed - audio capture now active")
    sys.stdout.flush()
    return jsonify({"status": "listening resumed"})

def start_transcription_service(model_size, gpu_device=0):
    """Start all the transcription service threads."""
    import sys
    # Initialize the model
    initialize_model(model_size, gpu_device)
    
    # Start audio recording in a background thread
    print("[DEBUG] Starting audio recording thread...")
    sys.stdout.flush()
    audio_thread = threading.Thread(target=record_audio, daemon=True)
    audio_thread.start()
    print(f"[DEBUG] Audio thread started: {audio_thread.is_alive()}")
    sys.stdout.flush()
    
    # Start transcription in a background thread
    print("[DEBUG] Starting transcription thread...")
    sys.stdout.flush()
    transcription_thread = threading.Thread(target=transcribe_audio, args=(socketio,), daemon=True)
    transcription_thread.start()
    print(f"[DEBUG] Transcription thread started: {transcription_thread.is_alive()}")
    sys.stdout.flush()
    
    return audio_thread, transcription_thread

def clear_transcripts():
    transcript_manager.clear_all()
    # Emit empty data to clear the display on the client-side
    socketio.emit('new_live_transcript', {'data': ''})
    socketio.emit('new_final_transcript', {'data': []})

def send_to_tts_server(text):
    """Sends finalized transcript text to the TTS server to be spoken."""
    if not text:
        return
    try:
        # This request will cause the TTS server to play audio and send pause/resume signals
        response = requests.get(TTS_SERVER_URL, params={"text": text}, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error sending to TTS server: {e}")

def send_to_llm_preprocessor(text, request_id=None):
    """
    Send finalized transcript text to the LLM preprocessor endpoint.
    """
    try:
        payload = {"text": text}
        if request_id:
            payload["request_id"] = request_id
            
        if LATENCY_TRACKING_ENABLED and request_id:
            log_timing(request_id, "stt", Events.STT_SENDING_TO_V34, 
                     {"text_length": len(text)})
        
        # Log right before HTTP request
        if LATENCY_TRACKING_ENABLED and request_id:
            log_timing(request_id, "stt", "stt_http_request_start", 
                     {"endpoint": LLM_ENDPOINT})
        
        response = requests.post(
            LLM_ENDPOINT,
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=30  # Increased timeout for LLM preprocessing (classification + retrieval + generation)
        )
        response.raise_for_status()
        
        # Log right after HTTP response received
        if LATENCY_TRACKING_ENABLED and request_id:
            log_timing(request_id, "stt", "stt_http_response_received", 
                     {"status_code": response.status_code})
        
        result = response.json()
        print(f"[OK] LLM Response: {result.get('response', 'No response')}")
        return result
    except requests.exceptions.Timeout:
        print("[TIMEOUT] LLM preprocessor timeout (taking too long)")
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"[CONNECTION ERROR] Cannot connect to preprocessor: {e}")
        print(f"   Make sure preprocessor is running: Check localhost:5000")
        return None
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Error sending to LLM preprocessor: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"[ERROR] Error parsing LLM response: {e}")
        return None

def notify_eye(text: str):
    """Fire-and-forget notification to the eye LCD server (non-blocking caller).
    Mirrors: curl -k -X POST https://192.168.1.110:8080/esp32/write -H "Content-Type: application/json" -d '{"text":"AI_CONNECTED"}'
    """
    try:
        requests.post(
            f"{EYE_LCD_URL}/esp32/write",
            headers={"Content-Type": "application/json"},
            json={"text": text},
            timeout=1,
            verify=False,
        )
    except requests.exceptions.RequestException:
        # Intentionally ignore network errors for non-critical notification
        pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live transcription with web interface using faster-whisper")
    parser.add_argument("--flask-port", type=int, default=8888, 
                        help="Flask server port")
    parser.add_argument("--lang", type=str, default="en", 
                        help="Language code for transcription")
    parser.add_argument("--model", type=str, default=DEFAULT_STT_MODEL, 
                        help=f"faster-whisper model path or name (default: {DEFAULT_STT_MODEL})")
    parser.add_argument("--gpu-device", type=int, default=0, 
                        help="GPU device index to use (0 for first GPU, RTX 3060)")
    parser.add_argument("--ai", action="store_true", 
                        help="Send transcripts to LLM endpoint instead of TTS server")
    
    args = parser.parse_args()
    
    # Set global language and AI mode
    language = args.lang
    ai_mode = args.ai
    
    print(f"Starting faster-whisper transcription service with model: {args.model}")
    print("This may take a moment to initialize on GPU...")
    
    if ai_mode:
        print(f"[AI Mode] Transcripts will be sent to LLM endpoint: {LLM_ENDPOINT}")
    else:
        print(f"[TTS Mode] Transcripts will be sent to TTS server: {TTS_SERVER_URL}")
    
    # Start transcription in background
    threads = start_transcription_service(args.model, args.gpu_device)
    
    # Add a filter to the logger to hide the noisy /transcript polling
    log = logging.getLogger('werkzeug')
    log.addFilter(TranscriptFilter())
    
    try:
        # Start Flask server
        socketio.run(app, host="0.0.0.0", port=args.flask_port, debug=False)
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        # Clean shutdown
        transcription_thread_running = False
        for thread in threads:
            if thread.is_alive():
                thread.join(timeout=1.0)
        clear_transcripts() 
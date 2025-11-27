# timmy_speaks_cuda.py starting from v2

from __future__ import annotations

import argparse
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import numpy as np
import sounddevice as sd
from flask import Flask, jsonify, request

import requests
import warnings
import urllib3

# Suppress only HTTPS certificate warnings for verify=False calls
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    from piper.voice import PiperVoice
    from piper.config import SynthesisConfig
except Exception as exc:
    raise RuntimeError(
        "piper-tts is required. Install in your venv: pip install piper-tts"
    ) from exc

try:
    import onnxruntime as ort
except Exception:
    ort = None


LOGGER = logging.getLogger("timmy_hears_cuda")

# Default TTS speed configuration
DEFAULT_SPEECH_SPEED = 0.6  # Lower values = faster speech (1.0 = normal, 0.5 = 2x faster)

# Hearing server URL (hardcoded)
HEARING_SERVER_URL = "http://localhost:8888"

# External indicator (e.g., ESP32) endpoint for status signals
# Uses HTTPS with verify disabled (similar to curl -k).
SKULL_EYE_ENDPOINT = "https://192.168.1.110:8080/esp32/write"
INDICATOR_SPEAKING_TEXT = "SPEAKING"
INDICATOR_LISTENING_TEXT = "AI_CONNECTED"

# Playback lock ensures only one utterance plays at a time
playback_lock = threading.Lock()
_metrics_lock = threading.Lock()
_last_metrics: Dict[str, Any] = {
    "provider": None,
    "text_chars": 0,
    "duration_seconds": None,
    "started_at": None,
    "finished_at": None,
}

# Pre-compiled regex for quick text cleanup (preserves important punctuation)
TEXT_CLEANUP_REGEX = re.compile(r"[^\w\s.,!?;:\-'\"()]")
WHITESPACE_REGEX = re.compile(r"\s+")
DOTS_REGEX = re.compile(r"[.]{2,}")
EXCLAMATION_REGEX = re.compile(r"[!]{2,}")
QUESTION_REGEX = re.compile(r"[?]{2,}")


def optimize_text_for_speed(text: str) -> str:
    if len(text) <= 5:
        return text.strip()
    text = TEXT_CLEANUP_REGEX.sub(" ", text)
    # Remove parentheses explicitly for legacy payload normalization
    text = text.replace("(", " ").replace(")", " ")
    text = WHITESPACE_REGEX.sub(" ", text)
    text = DOTS_REGEX.sub(".", text)
    text = EXCLAMATION_REGEX.sub("!", text)
    text = QUESTION_REGEX.sub("?", text)
    return text.strip()


def post_hearing_action(action: str, wait: bool) -> None:
    if not HEARING_SERVER_URL:
        return
    def _send() -> None:
        try:
            timeout = 0.5 if wait else 0.1  # Increased timeout for pause
            resp = requests.post(f"{HEARING_SERVER_URL}/{action}", timeout=timeout)
            if resp.status_code == 200:
                LOGGER.debug(f"STT {action} successful")
            else:
                LOGGER.warning(f"STT {action} returned status {resp.status_code}")
        except requests.RequestException as e:
            LOGGER.warning(f"STT {action} failed: {e}")
    if wait:
        _send()
    else:
        threading.Thread(target=_send, daemon=True).start()


def post_indicator_text(text: str) -> None:
    if not SKULL_EYE_ENDPOINT:
        return
    def _send() -> None:
        try:
            # Non-blocking JSON POST to external indicator; disable TLS verify like curl -k
            requests.post(
                SKULL_EYE_ENDPOINT,
                json={"text": text},
                timeout=0.15,
                verify=False,
                headers={"Content-Type": "application/json"},
            )
        except requests.RequestException:
            pass
    threading.Thread(target=_send, daemon=True).start()


def _append_nvidia_dll_dirs_once() -> None:
    # Ensure NVIDIA cuBLAS/cuDNN DLLs from the venv are discoverable on Windows
    # Many NVIDIA wheels drop DLLs under site-packages\nvidia\** and onnxruntime expects them on PATH
    if os.name != "nt":
        return
    try:
        import site
        import sys
        site_paths = [Path(p) for p in (site.getsitepackages() + [site.getusersitepackages()]) if isinstance(p, str)]
        candidate_dirs = []
        for base in site_paths:
            # Typical locations for DLLs installed via pip (nvidia-*-cu12 wheels)
            for sub in [
                base / "nvidia",  # package root
                base / "nvidia" / "cublas" / "bin",
                base / "nvidia" / "cudnn" / "bin",
                base / "nvidia" / "cusolver" / "bin",
                base / "nvidia" / "cufft" / "bin",
                base / "nvidia" / "curand" / "bin",
                base / "nvidia" / "cusparse" / "bin",
                base / "nvidia" / "cuda_runtime" / "bin",
                base / "nvidia" / "cuda_nvrtc" / "bin",
                base / "nvidia" / "nvjitlink" / "bin",
                base / "onnxruntime",  # sometimes provider DLLs live here
                base / "onnxruntime" / "capi",
            ]:
                if sub.exists():
                    candidate_dirs.append(str(sub))

        # Append to PATH for current process so Windows loader can find DLLs
        if candidate_dirs:
            existing = os.environ.get("PATH", "")
            os.environ["PATH"] = os.pathsep.join(candidate_dirs + [existing])
    except Exception:
        pass


def _cuda_available() -> bool:
    if ort is None:
        return False
    try:
        providers = set(ort.get_available_providers())
        return "CUDAExecutionProvider" in providers
    except Exception:
        return False


class PiperEngine:
    def __init__(
        self,
        model_path: Path,
        config_path: Optional[Path],
    ) -> None:
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        # Make sure NVIDIA DLL folders are on PATH before initializing the session
        _append_nvidia_dll_dirs_once()
        if not _cuda_available():
            raise RuntimeError("CUDAExecutionProvider not available. Ensure onnxruntime-gpu and CUDA/cuDNN DLLs are installed in the venv and on PATH.")
        LOGGER.info("Loading Piper voice with CUDAExecutionProvider (cuDNN)")

        self.voice = PiperVoice.load(
            str(model_path),
            config_path=str(config_path) if config_path else None,
            use_cuda=True,
        )
        self.lock = threading.Lock()

    def _iterate_chunks(
        self, text: str, synth_args: Dict[str, Any]
    ) -> Iterable[bytes]:
        length_scale = synth_args.get("length_scale", DEFAULT_SPEECH_SPEED)
        noise_scale = synth_args.get("noise_scale", 0.667)
        noise_w = synth_args.get("noise_w", 0.8)
        speaker_id = synth_args.get("speaker_id")

        config_args: Dict[str, Any] = {
            "length_scale": length_scale,
            "noise_scale": noise_scale,
            "noise_w_scale": noise_w,
        }
        if speaker_id is not None:
            config_args["speaker_id"] = speaker_id

        synthesis_config = SynthesisConfig(**config_args)
        result = self.voice.synthesize(text, synthesis_config)
        for chunk in result:
            if chunk:
                yield chunk

    def speak(self, text: str, synth_args: Dict[str, Any]) -> None:
        if not text.strip():
            return
        optimized = optimize_text_for_speed(text)

        start_time = time.perf_counter()
        LOGGER.debug("SPEAK_START chars=%d", len(optimized))
        post_hearing_action("pause-listening", wait=True)
        # Give STT server time to fully pause and clear buffers
        time.sleep(0.2)  # Increased from 0.05 to 0.2 seconds
        # Fire-and-forget external indicator for speaking state
        post_indicator_text(INDICATOR_SPEAKING_TEXT)

        with self.lock:
            config = self.voice.config
            sample_rate = int(getattr(config, "sample_rate", 22050))
            
            LOGGER.info(f"Opening audio stream: sample_rate={sample_rate}, channels=1, dtype=int16")
            
            try:
                stream_obj = sd.OutputStream(
                    samplerate=sample_rate,
                    channels=1,
                    dtype="int16",
                    blocksize=max(128, sample_rate // 20),
                    device=None,
                )
            except Exception as e:
                LOGGER.error(f"Failed to open audio stream: {e}")
                raise

            with stream_obj as stream:
                chunks_written = 0
                for chunk in self._iterate_chunks(optimized, synth_args):
                    if not chunk:
                        continue
                    chunks_written += 1
                    raw: Optional[bytes] = None
                    if isinstance(chunk, (bytes, bytearray, memoryview)):
                        raw = bytes(chunk)
                    elif isinstance(chunk, np.ndarray):
                        arr = chunk
                        if np.issubdtype(arr.dtype, np.floating):
                            arr = np.clip(arr, -1.0, 1.0)
                            arr = (arr * 32767.0).astype(np.int16, copy=False)
                        if arr.size:
                            stream.write(arr)
                        continue
                    elif hasattr(chunk, "audio"):
                        val = getattr(chunk, "audio")
                        if isinstance(val, np.ndarray):
                            arr = val
                            if np.issubdtype(arr.dtype, np.floating):
                                arr = np.clip(arr, -1.0, 1.0)
                                arr = (arr * 32767.0).astype(np.int16, copy=False)
                            if arr.size:
                                stream.write(arr)
                            continue
                        elif isinstance(val, (bytes, bytearray, memoryview)):
                            raw = bytes(val)
                        else:
                            tobytes = getattr(val, "tobytes", None)
                            if callable(tobytes):
                                raw = tobytes()
                    elif str(type(chunk)) == "<class 'piper.voice.AudioChunk'>":
                        if hasattr(chunk, 'audio_int16_array') and chunk.audio_int16_array is not None:
                            stream.write(chunk.audio_int16_array)
                            continue
                        elif hasattr(chunk, 'audio_float_array') and chunk.audio_float_array is not None:
                            float_audio = chunk.audio_float_array
                            int16_audio = np.clip(float_audio, -1.0, 1.0)
                            int16_audio = (int16_audio * 32767.0).astype(np.int16, copy=False)
                            stream.write(int16_audio)
                            continue
                    else:
                        tobytes = getattr(chunk, "tobytes", None)
                        if callable(tobytes):
                            raw = tobytes()

                    if raw is not None and len(raw) > 0:
                        arr16 = np.frombuffer(raw, dtype=np.int16)
                        if arr16.size and np.any(arr16):
                            stream.write(arr16)
                        else:
                            if len(raw) % 4 == 0:
                                arrf = np.frombuffer(raw, dtype=np.float32)
                                if arrf.size:
                                    arrf = np.clip(arrf, -1.0, 1.0)
                                    arr16 = (arrf * 32767.0).astype(np.int16, copy=False)
                                    if arr16.size:
                                        stream.write(arr16)
            
            LOGGER.info(f"Audio playback complete: {chunks_written} chunks written to stream")

        duration = time.perf_counter() - start_time
        LOGGER.debug("SPEAK_END duration_s=%.3f", duration)
        with _metrics_lock:
            _last_metrics.update({
                "provider": "CUDA",
                "text_chars": len(optimized),
                "duration_seconds": duration,
                "started_at": None,
                "finished_at": None,
            })

        # Wait for audio to finish playing and speaker output to stop
        time.sleep(0.3)  # Increased from 0.05 to 0.3 seconds
        post_hearing_action("resume-listening", wait=False)
        # Fire-and-forget external indicator for listening state
        post_indicator_text(INDICATOR_LISTENING_TEXT)


def build_flask_app(engine: PiperEngine, synth_args: Dict[str, Any]) -> Flask:
    app = Flask(__name__)

    @app.route("/health", methods=["GET"])  # simple health check
    def health():
        return jsonify({"status": "ok", "provider": "CUDA"})

    # Accept legacy paths as well as root for synthesis
    @app.route("/", methods=["GET", "POST"])  # accept text and play
    @app.route("/tts", methods=["GET", "POST"])  # legacy compatibility
    @app.route("/speak", methods=["GET", "POST"])  # legacy compatibility
    def synth():
        # Support legacy payload shapes: query/form/json keys like text/message/q/utterance/content
        candidate_keys = ("text", "message", "q", "utterance", "content")
        text = ""
        if request.method == "POST":
            if request.data:
                try:
                    text = request.data.decode("utf-8", errors="ignore")
                except Exception:
                    text = str(request.data)
            if not text and request.is_json:
                body = request.get_json(silent=True) or {}
                for key in candidate_keys:
                    if key in body and body.get(key):
                        text = str(body.get(key))
                        break
            if not text and request.form:
                for key in candidate_keys:
                    val = request.form.get(key)
                    if val:
                        text = val
                        break
        else:
            for key in candidate_keys:
                val = request.args.get(key)
                if val:
                    text = val
                    break

        text = (text or "").strip()
        if not text:
            return jsonify({"error": "No text provided"}), 400

        LOGGER.info(f"TTS request received: {len(text)} chars")
        
        def _worker() -> None:
            try:
                LOGGER.info(f"Starting speech synthesis for: '{text[:50]}...'")
                engine.speak(text, synth_args)
                LOGGER.info("Speech synthesis completed successfully")
            except Exception as e:
                LOGGER.error(f"Playback error: {e}", exc_info=True)

        threading.Thread(target=_worker, daemon=True).start()
        return jsonify({"status": "playing", "text": text})

    @app.route("/metrics", methods=["GET"])  # last synthesis metrics
    def metrics():
        with _metrics_lock:
            return jsonify(dict(_last_metrics))

    return app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5051)
    parser.add_argument("-m", "--model", default=str(Path("models") / "skeletor_v1.onnx"))
    parser.add_argument("-c", "--config", default=str(Path("models") / "skeletor_v1.onnx.json"))
    parser.add_argument("--speaker", type=int)
    parser.add_argument("--length-scale", type=float, default=DEFAULT_SPEECH_SPEED, help="Speech speed scale (1.0=normal, 0.5=2x faster)")
    parser.add_argument("--noise-scale", type=float)
    parser.add_argument("--noise-w", type=float)
    parser.add_argument("--sentence-silence", type=float, default=0.0)
    # CUDA is required in this variant; no CPU fallback
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    if ort is not None:
        try:
            LOGGER.info("onnxruntime version: %s, providers: %s", ort.__version__, ort.get_available_providers())
        except Exception:
            pass

    model_path = Path(args.model).resolve()
    config_path = Path(args.config).resolve() if args.config else None

    engine = PiperEngine(model_path=model_path, config_path=config_path)

    synth_args: Dict[str, Any] = {
        "speaker_id": args.speaker,
        "length_scale": args.length_scale,
        "noise_scale": args.noise_scale if args.noise_scale is not None else 0.667,
        "noise_w": args.noise_w if args.noise_w is not None else 0.8,
        "sentence_silence": args.sentence_silence,
    }

    LOGGER.info(f"TTS Speed Configuration: length_scale={args.length_scale} (lower=faster, via SynthesisConfig)")

    app = build_flask_app(engine, synth_args)
    app.run(host=args.host, port=args.port, threaded=True)


if __name__ == "__main__":
    main()



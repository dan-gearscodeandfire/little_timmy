"""
Vision state management and compact observation generation for system prompt injection.

Design goals:
- Maintain a smoothed, recent view of camera observations (faces, names, caption)
- Apply EMA smoothing and hysteresis to reduce flicker from brief occlusions
- Expose a single compact line suitable for system prompts
"""

from __future__ import annotations

import threading
import time
from typing import Dict, List, Optional, Tuple
import re

try:
    import config  # type: ignore
except Exception:  # pragma: no cover
    class _Cfg:
        VISION_FRESHNESS_WINDOW_SEC = 60
        VISION_NAME_CONFIDENCE_THRESHOLD = 0.90
        VISION_ENTER_THRESHOLD = 0.90
        VISION_EXIT_THRESHOLD = 0.75
        VISION_COUNT_EMA_ALPHA = 0.70
        VISION_MAX_NAMES = 2
        VISION_MAX_CAPTION_WORDS = 12
        VISION_MAX_OBSERVATION_CHARS = 120
        VISION_OBSERVATION_MIN_CONFIDENCE = 0.50
        VISION_ENABLE = True
        VISION_SESSION_DEFAULT = None
        VISION_DEFAULT_KNOWN_CONFIDENCE = 0.92
        VISION_STOP_PHRASES = [
            "in a workshop",
            "in front of a computer",
            "full of tools",
        ]
        DEBUG_MODE = False
    config = _Cfg()  # type: ignore

try:
    import utils  # type: ignore
    debug_print = utils.debug_print
except Exception:  # pragma: no cover
    def debug_print(*args, **kwargs):
        if getattr(config, "DEBUG_MODE", False):
            print(*args, **kwargs)


def _now() -> float:
    return time.time()


def _truncate_words(text: str, max_words: int) -> str:
    parts = text.split()
    if len(parts) <= max_words:
        return text
    return " ".join(parts[:max_words])


def _get_stop_phrases() -> List[str]:
    try:
        phrases = getattr(config, "VISION_STOP_PHRASES", None)
        if isinstance(phrases, (list, tuple)):
            return [str(p).strip() for p in phrases if str(p).strip()]
    except Exception:
        pass
    return [
        "in a workshop",
        "in front of a computer",
        "full of tools",
    ]


def _filter_stop_phrases(text: str) -> str:
    """Remove boilerplate environment phrases from captions (case-insensitive).

    Cleans up extra spaces and dangling punctuation after removal.
    """
    if not text:
        return ""
    result = text
    for phrase in _get_stop_phrases():
        # Remove whole-phrase matches irrespective of case; allow surrounding spaces/punctuation
        pattern = re.compile(r"\b" + re.escape(phrase) + r"\b", flags=re.IGNORECASE)
        result = pattern.sub("", result)

    # Normalize whitespace and punctuation artifacts
    result = re.sub(r"\s+", " ", result)
    result = re.sub(r"\s*,\s*", ", ", result)
    result = re.sub(r"\s*[,;:.!?]\s*$/,", "", result) if result else result
    result = result.strip(" ,;:.!-?\t\n\r")
    return result.strip()


class TrackedFace:
    """State for a single tracked face with hysteresis on presence and EMA on confidence."""

    def __init__(self, stable_id: str):
        self.stable_id: str = stable_id
        self.name: Optional[str] = None
        self.is_known: bool = False
        self.confidence_ema: float = 0.0
        self.present: bool = False
        self.last_seen_ts: float = 0.0

    def update(self, name: Optional[str], is_known: Optional[bool], confidence: Optional[float], now: float):
        alpha = 0.5
        if confidence is not None:
            if self.confidence_ema == 0.0:
                self.confidence_ema = float(confidence)
            else:
                self.confidence_ema = alpha * float(confidence) + (1.0 - alpha) * self.confidence_ema
        if name:
            self.name = name
        if is_known is not None:
            self.is_known = bool(is_known)
        self.last_seen_ts = now

    def apply_hysteresis(self):
        enter = getattr(config, "VISION_ENTER_THRESHOLD", 0.90)
        exit_t = getattr(config, "VISION_EXIT_THRESHOLD", 0.75)
        # Enter when EMA rises above enter threshold
        if self.confidence_ema >= enter:
            self.present = True
        # Exit only when it falls below exit threshold
        elif self.confidence_ema <= exit_t:
            self.present = False


class VisionState:
    """Smoothed camera observation state for a single chat session."""

    def __init__(self):
        self.lock = threading.Lock()
        self.tracked: Dict[str, TrackedFace] = {}
        self.count_ema: float = 0.0
        self.last_caption: str = ""
        self.last_caption_ts: float = 0.0
        self.last_update_ts: float = 0.0

    def _ensure_face(self, stable_id: str) -> TrackedFace:
        face = self.tracked.get(stable_id)
        if not face:
            face = TrackedFace(stable_id)
            self.tracked[stable_id] = face
        return face

    def _derive_stable_id(self, face: dict, index: int) -> str:
        # Prefer payload-provided face_id; otherwise quantize bbox center
        if isinstance(face.get("face_id"), (int, str)):
            return f"face:{face['face_id']}"
        box = face.get("bounding_box") or {}
        try:
            cx = float(box.get("x", 0)) + float(box.get("width", 0)) / 2.0
            cy = float(box.get("y", 0)) + float(box.get("height", 0)) / 2.0
            qx = int(cx // 32)
            qy = int(cy // 32)
            return f"bbox:{qx}x{qy}#{index}"
        except Exception:
            return f"idx:{index}"

    def update_from_payload(self, payload: dict):
        """Update state from a single vision payload.

        Expected keys: caption, faces_detected (optional), faces: list[{name,is_known,confidence,bounding_box,face_id}]
        """
        if not getattr(config, "VISION_ENABLE", True):
            return
        now = _now()
        with self.lock:
            faces = payload.get("faces") or []
            if not isinstance(faces, list):
                faces = []

            # Update per-face
            present_count = 0
            for i, face in enumerate(faces):
                if not isinstance(face, dict):
                    continue
                stable_id = self._derive_stable_id(face, i)
                tf = self._ensure_face(stable_id)
                name = face.get("name") if isinstance(face.get("name"), str) else None
                # Accept booleans or string equivalents for is_known
                ik = face.get("is_known")
                if isinstance(ik, bool):
                    is_known = ik
                elif isinstance(ik, str):
                    is_known = ik.strip().lower() in ("true", "1", "yes")
                else:
                    is_known = None

                conf = face.get("confidence")
                try:
                    conf = float(conf) if conf is not None else None
                except Exception:
                    conf = None
                # If known named face lacks confidence, assume a default known confidence to stabilize
                if conf is None and name and is_known is True:
                    conf = getattr(config, "VISION_DEFAULT_KNOWN_CONFIDENCE", 0.92)
                tf.update(name=name, is_known=is_known, confidence=conf, now=now)
                tf.apply_hysteresis()
                if tf.present:
                    present_count += 1

            # Smooth face count with EMA, fallback to faces_detected when faces[] is empty
            alpha = getattr(config, "VISION_COUNT_EMA_ALPHA", 0.55)
            if self.count_ema == 0.0:
                self.count_ema = float(present_count)
            else:
                self.count_ema = alpha * float(present_count) + (1.0 - alpha) * self.count_ema

            if present_count == 0:
                try:
                    faces_detected = int(payload.get("faces_detected") or 0)
                    if faces_detected > 0:
                        self.count_ema = max(self.count_ema, float(faces_detected))
                except Exception:
                    pass

            # Caption update with simple change detection
            caption = payload.get("caption") or ""
            if isinstance(caption, str):
                caption = caption.strip()
                if caption and caption != self.last_caption:
                    self.last_caption = caption
                    self.last_caption_ts = now

            self.last_update_ts = now

            debug_print(f"*** VisionState updated: present_count={present_count} count_ema={self.count_ema:.2f}")

    def _collect_names(self) -> List[Tuple[str, float]]:
        """Return recognized names regardless of confidence, limited to fresh sightings.

        Includes any tracked face with a known name seen within the freshness window.
        Confidence is passed through if available (used only for ordering/format).
        """
        freshness = getattr(config, "VISION_FRESHNESS_WINDOW_SEC", 60)
        now_ts = _now()
        pairs: List[Tuple[str, float]] = []
        for tf in self.tracked.values():
            if not tf.name or not tf.is_known:
                continue
            if (now_ts - tf.last_seen_ts) > freshness:
                continue
            conf = tf.confidence_ema if tf.confidence_ema is not None else getattr(config, "VISION_DEFAULT_KNOWN_CONFIDENCE", 0.92)
            pairs.append((tf.name, float(conf)))
        # Sort by confidence desc for stable formatting
        pairs.sort(key=lambda p: p[1], reverse=True)
        return pairs

    def build_observation(self) -> Optional[str]:
        """Return a compact observation line, or None if stale/low-confidence.

        Example: "Vision 4s ago: approx 1 face; known: Dan 98%; summary: a man smiling at the camera"
        """
        freshness = getattr(config, "VISION_FRESHNESS_WINDOW_SEC", 60)
        max_names = getattr(config, "VISION_MAX_NAMES", 3)
        max_caption_words = getattr(config, "VISION_MAX_CAPTION_WORDS", 18)
        min_conf = getattr(config, "VISION_OBSERVATION_MIN_CONFIDENCE", 0.50)

        now = _now()
        age = now - max(self.last_update_ts, self.last_caption_ts)
        if age > freshness:
            return None

        # Round faces to nearest integer, but keep "approx"
        approx_count = int(round(self.count_ema))

        # If we have essentially no confidence in anything, skip
        has_confident_face = any(tf.present and tf.confidence_ema >= min_conf for tf in self.tracked.values())
        if not has_confident_face and approx_count == 0 and not self.last_caption:
            return None

        # Names
        names = self._collect_names()
        if names:
            shown = names[:max_names]
            names_text = ", ".join(f"{n} {int(round(c*100))}%" for n, c in shown)
            if len(names) > max_names:
                names_text += f", +{len(names) - max_names} more"
            names_section = f"; known: {names_text}"
        else:
            names_section = ""

        # Caption: remove boilerplate phrases, then truncate words. If empty, add a negative hint.
        filtered = _filter_stop_phrases(self.last_caption)
        caption = _truncate_words(filtered, max_caption_words) if filtered else ""
        if not caption:
            caption = "no specific object identified"

        # Age formatting: prefer seconds under a minute
        if age < 1:
            age_text = "just now"
        elif age < 60:
            age_text = f"{int(age)}s ago"
        elif age < 3600:
            age_text = f"{int(age//60)}m ago"
        else:
            age_text = f"{int(age//3600)}h ago"

        # Structured tag and consistent start token for salience
        parts = [f"[VISION] {age_text}: approx {approx_count} face(s)"]
        if names_section:
            parts.append(names_section)
        if caption:
            parts.append(f"; summary: {caption}")

        line = "".join(parts)
        # Hard cap total length to keep salience high
        try:
            max_chars = int(getattr(config, "VISION_MAX_OBSERVATION_CHARS", 120))
        except Exception:
            max_chars = 120
        if len(line) > max_chars:
            line = line[:max_chars]
        return line


class VisionStateManager:
    """Manages VisionState per session and provides safe accessors."""

    def __init__(self):
        self._lock = threading.Lock()
        self._session_to_state: Dict[str, VisionState] = {}
        self._current_session_id: Optional[str] = getattr(config, "VISION_SESSION_DEFAULT", None)

    def set_current_session(self, session_id: str):
        with self._lock:
            self._current_session_id = session_id

    def get_or_create(self, session_id: str) -> VisionState:
        with self._lock:
            vs = self._session_to_state.get(session_id)
            if not vs:
                vs = VisionState()
                self._session_to_state[session_id] = vs
            return vs

    def update_for_session(self, session_id: str, payload: dict):
        vs = self.get_or_create(session_id)
        vs.update_from_payload(payload)

    def build_observation_for_session(self, session_id: str) -> Optional[str]:
        vs = self.get_or_create(session_id)
        return vs.build_observation()

    def build_observation_for_current(self) -> Optional[str]:
        sid = self._current_session_id
        if not sid:
            return None
        return self.build_observation_for_session(sid)


_MANAGER = VisionStateManager()


def get_manager() -> VisionStateManager:
    return _MANAGER


def set_current_session(session_id: str):
    _MANAGER.set_current_session(session_id)



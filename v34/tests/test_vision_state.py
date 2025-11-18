import time

from vision_state import VisionState


def test_hysteresis_and_ema_basic():
    vs = VisionState()

    payload = {
        "caption": "a man smiling at the camera",
        "faces": [
            {"face_id": 1, "confidence": 0.99, "name": "Dan", "is_known": True},
            {"face_id": 2, "confidence": 0.60, "name": None, "is_known": False},
        ]
    }

    vs.update_from_payload(payload)
    # After first update, count_ema should reflect present faces (~2)
    assert vs.count_ema >= 1.0
    line = vs.build_observation()
    assert line is not None
    assert "approx" in line

    # Drop confidence for face 2 to test exit hysteresis
    payload2 = {
        "caption": "a man still smiling",
        "faces": [
            {"face_id": 1, "confidence": 0.98, "name": "Dan", "is_known": True},
            {"face_id": 2, "confidence": 0.40, "name": None, "is_known": False},
        ]
    }
    vs.update_from_payload(payload2)
    # Ensure we still produce a line and count doesn't instantly drop to 1
    line2 = vs.build_observation()
    assert line2 is not None

    # Simulate staleness
    vs.last_update_ts -= 60
    vs.last_caption_ts -= 60
    assert vs.build_observation() is None



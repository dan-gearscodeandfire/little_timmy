# TTS Server Configuration
# Modify these values for your setup

# Hearing server (STT) endpoint
HEARING_SERVER_URL = "http://localhost:8888"

# External status indicator (ESP32 LCD display)
SKULL_EYE_ENDPOINT = "https://192.168.1.110:8080/esp32/write"
INDICATOR_SPEAKING_TEXT = "SPEAKING"
INDICATOR_LISTENING_TEXT = "AI_CONNECTED"

# TTS Server Configuration
TTS_HOST = "0.0.0.0"
TTS_PORT = 5051

# Speech speed (lower = faster; 1.0 = normal, 0.6 = 1.67x faster)
DEFAULT_SPEECH_SPEED = 0.6

# Model paths (relative to tts-server directory)
DEFAULT_MODEL_PATH = "models/skeletor_v1.onnx"
DEFAULT_CONFIG_PATH = "models/skeletor_v1.onnx.json"


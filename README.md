# Little Timmy

My AI cohost and companion - an AI assistant with persistent vector memory, real-time chat capabilities, and personality.

## Repository Contents

### Python Environments
- **v34/** - Current stable version with vector memory system
  - Flask-based chat interface with WebSocket support
  - PostgreSQL + pgvector for semantic memory
  - GLiClass-based fast metadata classification
  - [See v34/README.md for details](v34/README.md)

### Hardware/ESP32
- **esp32_phoneme_to_jaw_openness/** - ESP32 Arduino sketches for physical robot control
  - Audio analysis and servo control
  - Phoneme-to-jaw-openness mapping

## Quick Start

**For v34 AI Assistant:**
\\ash
cd v34/
# See v34/README.md for installation instructions
\
**For ESP32 Hardware:**
\\ash
cd esp32_phoneme_to_jaw_openness/
# See Arduino IDE setup instructions
\
## License

MIT License - see v34/LICENSE

#!/bin/bash
# Monitor app_session.log in real-time with filtering

LOG_FILE="app_session.log"

if [ ! -f "$LOG_FILE" ]; then
    echo "❌ $LOG_FILE not found. Is the app running?"
    exit 1
fi

echo "📊 Monitoring Little Timmy Session Log"
echo "========================================"
echo "Press Ctrl+C to stop"
echo ""

# Follow log and highlight important lines
tail -f "$LOG_FILE" | grep --line-buffered -E "BEGIN|user_message|Retrieved|importance|Topic|LLM response|Error|WARNING" --color=always


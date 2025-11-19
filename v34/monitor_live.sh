#!/bin/bash
# Monitor payloads.txt for new conversations in real-time

PAYLOAD_FILE="payloads.txt"
START_LINE=$(wc -l < "$PAYLOAD_FILE")

echo "📊 Monitoring Little Timmy - Session 4"
echo "========================================"
echo "Starting from line: $START_LINE"
echo "Watching for new conversations..."
echo "Press Ctrl+C to stop and analyze"
echo ""

tail -f -n +$START_LINE "$PAYLOAD_FILE" | while read line; do
    if [[ $line == *"=== Megaprompt at"* ]]; then
        echo ""
        echo "🔔 NEW CONVERSATION: $line"
        echo "---"
    elif [[ $line == *"<|start_header_id|>user<|end_header_id|>"* ]]; then
        echo "👤 USER MESSAGE (next line)"
    fi
done


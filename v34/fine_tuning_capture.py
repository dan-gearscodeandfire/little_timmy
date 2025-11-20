# v34/fine_tuning_capture.py
"""Capture excellent response examples for future fine-tuning."""

import json
from datetime import datetime
from typing import List, Dict

# Praise phrases that indicate a good response
PRAISE_PHRASES = [
    "good one timmy",
    "good one, timmy",
    "great response",
    "excellent response",
    "amazing response",
    "that was great",
    "that was excellent",
    "that was amazing",
    "that was awesome",
    "that ruled",
    "that's awesome",
    "perfect response",
    "nice one",
    "well done",
    "good job",
    "that's good",
    "that's great",
    "i like that",
    "that's perfect",
    "wow timmy",
    "nice timmy",
    "good timmy",
    "love that",
    "love it",
]

def is_praise(user_message: str) -> bool:
    """Detect if user message is praising the previous response."""
    msg_lower = user_message.lower().strip()
    
    # Check for praise phrases
    for phrase in PRAISE_PHRASES:
        if phrase in msg_lower:
            return True
    
    # Check for short affirmative responses that are likely praise
    short_praise = ["good", "nice", "perfect", "excellent", "great", "amazing", "awesome", "wow", "love", "ruled"]
    words = msg_lower.split()
    if len(words) <= 3 and any(word in short_praise for word in words):
        return True
    
    # Check for enthusiastic responses with exclamation marks
    if "!" in user_message and len(words) <= 5:
        # Remove punctuation for checking
        words_clean = [w.strip('!.,?') for w in words]
        if any(word in short_praise for word in words_clean):
            return True
    
    # Check for "that [positive word]" pattern
    if msg_lower.startswith("that ") and any(word in msg_lower for word in ["ruled", "awesome", "great", "amazing", "perfect"]):
        return True
    
    return False

def capture_fine_tuning_example(
    user_message_n3: str,
    system_prompt_n2: str,
    assistant_response_n1: str,
    praise_message_n0: str,
    metadata: Dict = None
):
    """Save a fine-tuning example to the training data file.
    
    Args:
        user_message_n3: The user message that prompted the good response
        system_prompt_n2: The system prompt with injected memories
        assistant_response_n1: The excellent assistant response
        praise_message_n0: The praise message (for context, not training)
        metadata: Optional metadata (timestamp, importance scores, etc.)
    """
    
    example = {
        "captured_at": datetime.now().isoformat(),
        "praise_trigger": praise_message_n0,
        "training_example": {
            "user_message": user_message_n3,
            "system_prompt": system_prompt_n2,
            "assistant_response": assistant_response_n1
        },
        "metadata": metadata or {}
    }
    
    # Append to fine-tuning file
    with open("fine_tuning_best_case_interchanges.md", "a", encoding="utf-8") as f:
        f.write("\n" + "="*80 + "\n")
        f.write(f"## Example Captured: {example['captured_at']}\n")
        f.write(f"**Praise:** {praise_message_n0}\n")
        f.write("="*80 + "\n\n")
        
        f.write("### User Message (n-3):\n")
        f.write("```\n")
        f.write(user_message_n3)
        f.write("\n```\n\n")
        
        f.write("### System Prompt with Memories (n-2):\n")
        f.write("```\n")
        f.write(system_prompt_n2[:1000])  # Truncate if very long
        if len(system_prompt_n2) > 1000:
            f.write(f"\n... [truncated, full length: {len(system_prompt_n2)} chars]")
        f.write("\n```\n\n")
        
        f.write("### Assistant Response (n-1):\n")
        f.write("```\n")
        f.write(assistant_response_n1)
        f.write("\n```\n\n")
        
        if metadata:
            f.write("### Metadata:\n")
            f.write("```json\n")
            f.write(json.dumps(metadata, indent=2))
            f.write("\n```\n\n")
    
    return True

def get_conversation_context(conversation_history: List[Dict], n: int = 3) -> Dict:
    """Extract the last n messages from conversation history.
    
    Returns dict with user_n3, assistant_n1, etc.
    """
    if len(conversation_history) < 3:
        return None
    
    # Get last 4 entries (n-3, n-2 is system/memories, n-1, n-0)
    # conversation_history format: [{"role": "user/assistant", "content": "..."}]
    
    # Find last user message (n-0, the praise)
    # Find previous assistant (n-1, the good response)
    # Find previous user (n-3, the prompt that led to good response)
    
    result = {
        "user_n3": None,
        "assistant_n1": None,
        "user_n0": None
    }
    
    # Walk backwards through history
    user_messages = [e for e in conversation_history if e["role"] == "user"]
    assistant_messages = [e for e in conversation_history if e["role"] == "assistant"]
    
    if len(user_messages) >= 2 and len(assistant_messages) >= 1:
        result["user_n0"] = user_messages[-1]["content"]  # Current (praise)
        result["assistant_n1"] = assistant_messages[-1]["content"]  # Previous response
        result["user_n3"] = user_messages[-2]["content"]  # Previous user message
    
    return result


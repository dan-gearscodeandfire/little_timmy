#v_16.py


import difflib
from collections import deque

class TranscriptManager:
    """
    Manages transcription text by storing coherent snapshots of speech,
    while minimizing simple, progressive redundancy by replacing extensions
    of the previous transcript and appending new, distinct thoughts.
    """
    
    def __init__(self, max_history=50):
        """
        Initialize the transcript manager.
        """
        self.current_text = ""
        self.final_transcripts = deque(maxlen=max_history)
        self.accumulated_text = ""  # Buffer for text accumulated across force-finalize events
    
    def update_current_text(self, text):
        """
        Update the current (in-progress) transcription text.
        """
        if not text:
            return False
        if text != self.current_text:
            self.current_text = text
            return True
        return False
    
    def force_finalize_text(self):
        """
        Force finalize the current text and add it to accumulated buffer.
        This is called when text exceeds the force finalize length.
        """
        if not self.current_text or len(self.current_text.strip()) < 3:
            return False

        new_text = self.current_text.strip()
        # Clean up ellipses from force-finalized text
        new_text = new_text.replace("...", "").replace("…", "")  # Remove ellipses
        new_text = " ".join(new_text.split())  # Clean up extra whitespace
        
        # Add to accumulated buffer
        if self.accumulated_text:
            self.accumulated_text += " " + new_text
        else:
            self.accumulated_text = new_text
            
        self.current_text = ""
        return True
    
    def finalize_text(self):
        """
        Finalizes the current transcription on pause detection.
        It intelligently decides whether to append the new text as a new entry, merge it with the previous entry,
        or ignore it if it's redundant.
        """
        # Combine accumulated text with current text
        text_to_finalize = ""
        if self.accumulated_text:
            if self.current_text:
                text_to_finalize = self.accumulated_text + self.current_text.strip()
            else:
                text_to_finalize = self.accumulated_text
        elif self.current_text:
            text_to_finalize = self.current_text.strip()
        
        if not text_to_finalize or len(text_to_finalize) < 3:
            self.current_text = ""
            self.accumulated_text = ""
            return False

        # Clean up ellipses and extra spaces from transcription artifacts
        new_text = text_to_finalize.replace("...", "").replace("…", "")  # Remove ellipses
        new_text = " ".join(new_text.split())  # Clean up extra whitespace
        new_text_lower = new_text.lower()

        if not self.final_transcripts:
            self.final_transcripts.append(new_text)
            self.current_text = ""
            self.accumulated_text = ""
            return True

        last_text = self.final_transcripts[-1]
        last_text_lower = last_text.lower()

        # If new text is a less-complete subset of the last, ignore it
        if new_text_lower in last_text_lower and len(new_text) < len(last_text):
            self.current_text = ""
            self.accumulated_text = ""
            return False

        # Use similarity ratio to check for corrections/extensions
        matcher = difflib.SequenceMatcher(None, last_text_lower, new_text_lower)
        ratio = matcher.ratio()

        # If the texts are highly similar, treat as a correction/refinement
        if ratio > 0.7:
            # Replace the last text if the new one is more complete
            if len(new_text) >= len(last_text):
                self.final_transcripts[-1] = new_text
            # If the new one is shorter but highly similar, we keep the old one.
            self.current_text = ""
            self.accumulated_text = ""
            return True

        # If the last text is fully contained in the new one, it's a clear extension
        if last_text_lower in new_text_lower:
            self.final_transcripts[-1] = new_text
            self.current_text = ""
            self.accumulated_text = ""
            return True

        # Otherwise, it's a new thought
        self.final_transcripts.append(new_text)
        self.current_text = ""
        self.accumulated_text = ""
        return True

    def get_current_text(self):
        """Get the current in-progress transcription text."""
        return self.current_text
    
    def get_final_transcripts(self):
        """Get the list of finalized transcripts."""
        return list(self.final_transcripts)
    
    def clear_all(self):
        """Clear all transcripts."""
        self.current_text = ""
        self.accumulated_text = ""
        self.final_transcripts.clear() 
"""
Gemini Vision Service
Uses Google Gemini API to analyze webcam frames for behavioral assessment during interviews.
"""

import base64
import io
import time
from PIL import Image
from app.config import Config

# Initialize Gemini client lazily
_client = None


def _get_client():
    """Lazily initialize the Gemini client."""
    global _client
    if _client is None:
        if not Config.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not configured. Cannot perform behavioral analysis.")
        from google import genai
        _client = genai.Client(api_key=Config.GEMINI_API_KEY)
    return _client


BEHAVIORAL_ANALYSIS_PROMPT = """You are an expert behavioral analyst and interview coach. 
Analyze the following webcam frames captured during a mock interview session.

For each observable aspect, provide your assessment:

1. **Eye Contact & Gaze**: Is the candidate maintaining appropriate eye contact with the camera? 
   Are they looking away frequently, looking down, or maintaining steady focus?

2. **Facial Expressions**: What emotions are visible? (confidence, nervousness, anxiety, calm, 
   enthusiasm, boredom, frustration). How do expressions change across the frames?

3. **Posture & Body Language**: Is the candidate sitting upright? Slouching? Leaning too far 
   forward/backward? Are they fidgeting or appearing restless?

4. **Overall Confidence Level**: Based on all visual cues, rate the candidate's confidence 
   on a scale of 1-10.

5. **Professional Appearance**: Is the candidate presenting themselves professionally for 
   an interview setting?

6. **Behavioral Patterns**: Note any concerning patterns (excessive fidgeting, looking away 
   when answering, nervous tics, lack of engagement).

7. **Positive Observations**: Note positive behavioral traits (steady gaze, genuine smiles, 
   confident posture, engaged expressions).

Provide your analysis in the following format:

## Behavioral Analysis Summary

### Eye Contact & Gaze
[Your assessment]

### Facial Expressions & Emotions  
[Your assessment]

### Posture & Body Language
[Your assessment]

### Confidence Score: [X/10]

### Professional Presentation
[Your assessment]

### Key Observations
- [Positive points]
- [Areas of concern]

### Overall Behavioral Impression
[2-3 sentence summary of the candidate's non-verbal communication during the interview]

### Recommendations for Improvement
[Specific, actionable tips to improve interview body language and presence]
"""


def decode_base64_frame(frame_base64):
    """Decode a base64-encoded image frame to a PIL Image."""
    try:
        # Handle data URI prefix if present (e.g., "data:image/jpeg;base64,...")
        if ',' in frame_base64:
            frame_base64 = frame_base64.split(',', 1)[1]
        
        image_data = base64.b64decode(frame_base64)
        image = Image.open(io.BytesIO(image_data))
        return image
    except Exception as e:
        print(f"Error decoding frame: {e}")
        return None


def select_representative_frames(frames, max_frames=8):
    """
    Select a representative subset of frames for analysis.
    Evenly spaces frames across the interview timeline.
    """
    if len(frames) <= max_frames:
        return frames
    
    # Evenly space frame selection
    step = len(frames) / max_frames
    selected_indices = [int(i * step) for i in range(max_frames)]
    return [frames[i] for i in selected_indices]


def analyze_frames_batch(frames_base64_list, retries=3):
    """
    Analyze a batch of webcam frames for behavioral assessment using Gemini Vision.
    
    Args:
        frames_base64_list: List of base64-encoded image strings
        retries: Number of retry attempts on failure
    
    Returns:
        str: Behavioral analysis summary text
    """
    if not frames_base64_list:
        return "No webcam frames were captured during this interview. Behavioral analysis is not available."

    if not Config.GEMINI_API_KEY:
        return "Behavioral analysis is disabled (GEMINI_API_KEY not configured)."

    # Select representative frames (avoid sending too many to API)
    selected_frames = select_representative_frames(frames_base64_list, max_frames=8)
    
    # Decode frames to PIL images
    images = []
    for i, frame_b64 in enumerate(selected_frames):
        img = decode_base64_frame(frame_b64)
        if img:
            # Resize to reduce payload (max 512px on longest side)
            img.thumbnail((512, 512), Image.Resampling.LANCZOS)
            images.append(img)
    
    if not images:
        return "Failed to process webcam frames. Behavioral analysis is not available."

    print(f"Analyzing {len(images)} webcam frames with Gemini Vision...")

    # Build content list: images + prompt
    content_parts = []
    for i, img in enumerate(images):
        content_parts.append(f"Frame {i+1} of {len(images)} (captured during interview):")
        content_parts.append(img)
    content_parts.append(BEHAVIORAL_ANALYSIS_PROMPT)

    # Call Gemini Vision API with retry
    client = _get_client()
    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=content_parts
            )
            return response.text
        except Exception as e:
            print(f"Gemini Vision Error (Attempt {attempt + 1}/{retries}): {str(e)}")
            if attempt == retries - 1:
                return f"Behavioral analysis failed after {retries} attempts: {str(e)}"
            time.sleep(2 ** attempt)

    return "Behavioral analysis could not be completed."

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-default-key!'
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    MODEL = "deepseek-chat"
    MAX_QUESTIONS = 10

    # Gemini Vision API (for behavioral analysis)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("API_KEY")
    GEMINI_MODEL = "gemini-2.0-flash"

    # CV Upload settings
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
    MAX_CV_SIZE_MB = 5
    ALLOWED_CV_EXTENSIONS = {'pdf', 'docx'}

    # Frame analysis settings
    FRAME_ANALYSIS_MODE = "batch"  # "batch" = analyze all frames at end of interview
    MAX_FRAMES_STORED = 20  # Cap frames to avoid memory issues

    # ElevenLabs TTS settings
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
    ELEVENLABS_MALE_VOICE_ID = "cjVigY5qzO86Huf0OWal"    # Eric — Smooth, Trustworthy
    ELEVENLABS_FEMALE_VOICE_ID = "XrExE9yKIg1WjnnlVkGX"  # Matilda — Knowledgable, Professional
    ELEVENLABS_MODEL_ID = "eleven_flash_v2_5"              # Fast, low-latency model

    if not DEEPSEEK_API_KEY:
        raise Exception("Please set DEEPSEEK_API_KEY in your .env file.")

    if not GEMINI_API_KEY:
        print("WARNING: GEMINI_API_KEY not set. Video behavioral analysis will be disabled.")

    if not ELEVENLABS_API_KEY:
        print("WARNING: ELEVENLABS_API_KEY not set. TTS will fall back to browser speech synthesis.")

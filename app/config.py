import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-default-key!'
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    MODEL = "deepseek-chat"
    MAX_QUESTIONS = 10

    if not DEEPSEEK_API_KEY:
        raise Exception("Please set DEEPSEEK_API_KEY in your .env file.")

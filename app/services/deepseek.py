import time
from openai import OpenAI
from app.config import Config

client = OpenAI(
    api_key=Config.DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

def generate_with_retry(messages, retries=5):
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=Config.MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=2048
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"\nDeepSeek Error (Attempt {attempt + 1}/{retries}): {str(e)}")
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)

import time
from openai import OpenAI
from app.config import Config

client = OpenAI(
    api_key=Config.DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

def generate_with_retry(messages, retries=3):
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
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            
            # If all retries fail, fall back to Gemini
            print("DeepSeek API is unreachable. Falling back to Gemini API...")
            try:
                from google import genai
                from google.genai import types
                
                gemini_client = genai.Client(api_key=Config.GEMINI_API_KEY)
                
                # Convert OpenAI messages to Gemini format
                # System prompt usually goes to system_instruction in Gemini 2.0
                system_instruction = None
                gemini_contents = []
                
                for msg in messages:
                    if msg["role"] == "system":
                        system_instruction = msg["content"]
                    elif msg["role"] == "user":
                        gemini_contents.append(types.Content(role="user", parts=[types.Part.from_text(text=msg["content"])]))
                    elif msg["role"] == "assistant":
                        gemini_contents.append(types.Content(role="model", parts=[types.Part.from_text(text=msg["content"])]))
                        
                config = types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7,
                    max_output_tokens=2048
                )
                
                response = gemini_client.models.generate_content(
                    model=Config.GEMINI_MODEL,
                    contents=gemini_contents,
                    config=config
                )
                return response.text
            except Exception as gemini_err:
                print(f"Gemini fallback also failed: {gemini_err}")
                raise Exception("Both DeepSeek and Gemini APIs failed to respond.") from gemini_err

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

def check_answer_relevance(messages, answer):
    last_question = ""
    for msg in reversed(messages):
        if msg["role"] == "assistant":
            last_question = msg["content"]
            break

    prompt = [
        {"role": "system", "content": "You are an AI assistant evaluating an interview. Determine if the user's answer is relevant to the interview and the previous question. If the user asks an irrelevant question (e.g., 'what is the weather') or gives a completely off-topic response, answer with 'IRRELEVANT'. If the user is answering the question, asking for clarification about the interview, or engaging in normal interview dialogue, answer with 'RELEVANT'. Only respond with the exact word RELEVANT or IRRELEVANT."},
        {"role": "user", "content": f"Previous Question: {last_question}\n\nUser's input: {answer}"}
    ]
    
    response = generate_with_retry(prompt, retries=2)
    return "IRRELEVANT" not in response.upper()

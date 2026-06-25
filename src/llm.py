import os
import requests
from dotenv import load_dotenv

# Always load .env from the project root, regardless of working directory
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(_project_root, ".env"))

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free")

DEFAULT_MODEL = OPENROUTER_MODEL

def call_llm(messages: list, temperature: float = 0.7, response_format: str = "text", model: str = None) -> str:
    if not OPENROUTER_API_KEY:
        raise Exception("API key is not set. Please set OPENROUTER_API_KEY in .env")
        
    target_model = model or OPENROUTER_MODEL
    payload = {
        "model": target_model,
        "messages": messages,
        "temperature": temperature,
    }
    if response_format == "json_object":
        payload["response_format"] = {"type": "json_object"}

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "Yantra AI"
    }

    try:
        response = requests.post(
            OPENROUTER_API_URL,
            headers=headers,
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        if "choices" in data and len(data["choices"]) > 0:
            return data["choices"][0]["message"]["content"].strip()
        else:
            raise Exception("No response candidates found in OpenRouter API output.")
    except Exception as e:
        print(f"Error calling Yantra AI (OpenRouter): {e}")
        if 'response' in locals():
            print(f"Response: {response.text}")
            try:
                err_data = response.json()
                if "error" in err_data:
                    if isinstance(err_data["error"], dict) and "message" in err_data["error"]:
                        raise Exception(f"OpenRouter API Error: {err_data['error']['message']}")
                    else:
                        raise Exception(f"OpenRouter API Error: {err_data['error']}")
            except Exception as inner_e:
                if str(inner_e).startswith("OpenRouter API Error"):
                    raise inner_e
                pass
            raise Exception(f"OpenRouter API Error: {response.status_code} {response.reason} - {response.text[:100]}")
        raise Exception(f"Error calling AI: {str(e)}")

def invoke_yantra_ai(prompt, system_prompt="You are Yantra AI, an intelligent robotic system agent.", response_format="text", model=None):
    """
    Unified function to call Yantra AI via OpenRouter API.
    Supports both standard text output and structured JSON extraction.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]
    return call_llm(messages, response_format=response_format, model=model)


if __name__ == "__main__":
    # Quick test
    print("Testing Yantra AI (OpenRouter)...")
    result = invoke_yantra_ai("What is 2+2? Reply with just the number.")
    print(f"Yantra AI says: {result}")

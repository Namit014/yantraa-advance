import os
import requests
from dotenv import load_dotenv

load_dotenv()

<<<<<<< HEAD
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")  # sk-or-v1-...
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")

DEFAULT_MODEL = OPENROUTER_MODEL
=======
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

DEFAULT_MODEL = "openrouter/owl-alpha"
>>>>>>> 92d50e2abd44a499b418ea6d9bf60a2bae70368a

def call_llm(messages: list, temperature: float = 0.7, response_format: str = "text", model: str = None) -> str:
    target_model = model or OPENROUTER_MODEL
    payload = {
        "model": target_model,
        "messages": messages,
        "temperature": temperature,
    }
    if response_format == "json_object":
        payload["response_format"] = {"type": "json_object"}

    response = requests.post(
        OPENROUTER_API_URL,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def invoke_yantra_ai(prompt, system_prompt="You are Yantra AI, an intelligent robotic system agent.", response_format="text", model=None):
    """
    Unified function to call Yantra AI via OpenRouter API.
    Supports both standard text output and structured JSON extraction.
    """
<<<<<<< HEAD
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]
    try:
        # Pass model parameter if provided
        return call_llm(messages, response_format=response_format, model=model)
    except Exception as e:
        print(f"Error calling Yantra AI (OpenRouter): {e}")
        raise e
=======
    if not OPENROUTER_API_KEY:
        raise Exception("API key is not set. Please set OPENROUTER_API_KEY in .env")

    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "Yantra AI"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    }
    # Some models strictly enforce JSON if requested
    
    if response_format == "json_object":
        payload["response_format"] = {"type": "json_object"}
        
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)
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
>>>>>>> 92d50e2abd44a499b418ea6d9bf60a2bae70368a


if __name__ == "__main__":
    # Quick test
    print("Testing Yantra AI (OpenRouter)...")
    result = invoke_yantra_ai("What is 2+2? Reply with just the number.")
    print(f"Yantra AI says: {result}")

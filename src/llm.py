import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

DEFAULT_MODEL = "openrouter/owl-alpha"

def invoke_yantra_ai(prompt, system_prompt="You are Yantra AI, an intelligent robotic system agent.", response_format="text", model=DEFAULT_MODEL):
    """
<<<<<<< HEAD
    Unified function to call Yantra AI. Uses OpenRouter exclusively.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise Exception("API key is not set. Please set OPENROUTER_API_KEY in .env")

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
=======
    Unified function to call Yantra AI via OpenRouter API.
    Supports both standard text output and structured JSON extraction.
    """
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "Yantra AI"
>>>>>>> c765f6acfd98d8b4d8aefa54b2c9d8f736657b27
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    }
<<<<<<< HEAD
=======

    # Some models strictly enforce JSON if requested
    if response_format == "json_object":
        payload["response_format"] = {"type": "json_object"}
>>>>>>> c765f6acfd98d8b4d8aefa54b2c9d8f736657b27
    
    if response_format == "json_object":
        payload["response_format"] = {"type": "json_object"}
        
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        if "choices" in data and len(data["choices"]) > 0:
            return data["choices"][0]["message"]["content"].strip()
        else:
<<<<<<< HEAD
            raise Exception("No choices found in OpenRouter API output.")
=======
            raise Exception("No response candidates found in OpenRouter API output.")
>>>>>>> c765f6acfd98d8b4d8aefa54b2c9d8f736657b27
    except Exception as e:
        print(f"Error calling Yantra AI (OpenRouter): {e}")
        if 'response' in locals():
            print(f"Response: {response.text}")
<<<<<<< HEAD
=======
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
>>>>>>> c765f6acfd98d8b4d8aefa54b2c9d8f736657b27
        raise Exception(f"Error calling AI: {str(e)}")


if __name__ == "__main__":
    # Quick test
    print("Testing Yantra AI (OpenRouter)...")
    result = invoke_yantra_ai("What is 2+2? Reply with just the number.")
    print(f"Yantra AI says: {result}")

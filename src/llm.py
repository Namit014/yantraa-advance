import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

# We map the OPENROUTER_API_KEY environment variable to the Gemini API Key
# since the user pasted their Google key into that variable.
GEMINI_API_KEY = os.environ.get("OPENROUTER_API_KEY")

DEFAULT_MODEL = "openrouter/owl-alpha"

def invoke_yantra_ai(prompt, system_prompt="You are Yantra AI, an intelligent robotic system agent.", response_format="text", model=DEFAULT_MODEL):
    """
    Unified function to call Yantra AI. Uses OpenRouter exclusively.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise Exception("API key is not set. Please set OPENROUTER_API_KEY in .env")

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    }
    
    if response_format == "json_object":
        payload["response_format"] = {"type": "json_object"}
        
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        if "choices" in data and len(data["choices"]) > 0:
            return data["choices"][0]["message"]["content"].strip()
        else:
            raise Exception("No choices found in OpenRouter API output.")
    except Exception as e:
        print(f"Error calling Yantra AI (OpenRouter): {e}")
        if 'response' in locals():
            print(f"Response: {response.text}")
        raise Exception(f"Error calling AI: {str(e)}")


if __name__ == "__main__":
    # Quick test
    print("Testing Yantra AI (OpenRouter)...")
    result = invoke_yantra_ai("What is 2+2? Reply with just the number.")
    print(f"Yantra AI says: {result}")

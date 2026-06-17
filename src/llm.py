import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

# Your OpenRouter API Key
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# We use a fast, reliable model for Yantra AI. You can change this to any OpenRouter model.
DEFAULT_MODEL = "openrouter/free"

def invoke_yantra_ai(prompt, system_prompt="You are Yantra AI, an intelligent robotic system agent.", response_format="text", model=DEFAULT_MODEL):
    """
    Unified function to call Yantra AI via OpenRouter.
    Supports both standard text output and structured JSON extraction.
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:3000", # Required by OpenRouter
        "X-Title": "Yantra RAG" # Required by OpenRouter
    }
    
    payload = {
        "model": model,
        "max_tokens": 2500,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    }

    # Some models strictly enforce JSON if requested
    if response_format == "json_object":
        payload["response_format"] = {"type": "json_object"}
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Error calling Yantra AI (OpenRouter): {e}")
        if 'response' in locals():
            print(f"Response: {response.text}")
            try:
                err_data = response.json()
                if "error" in err_data:
                    if isinstance(err_data["error"], dict) and "message" in err_data["error"]:
                        return f"OpenRouter API Error: {err_data['error']['message']}"
                    else:
                        return f"OpenRouter API Error: {err_data['error']}"
            except Exception:
                pass
            return f"OpenRouter API Error: {response.status_code} {response.reason} - {response.text[:100]}"
        return f"Error calling AI: {str(e)}"

if __name__ == "__main__":
    # Quick test
    print("Testing Yantra AI...")
    result = invoke_yantra_ai("What is 2+2? Reply with just the number.")
    print(f"Yantra AI says: {result}")

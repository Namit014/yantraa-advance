import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

# We map the OPENROUTER_API_KEY environment variable to the Gemini API Key
# since the user pasted their Google key into that variable.
GEMINI_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# We use a fast, reliable model for Yantra AI. You can change this to any OpenRouter model.
DEFAULT_MODEL = os.environ.get("OPENROUTER_MODEL", "openrouter/owl-alpha")

def invoke_yantra_ai(prompt, system_prompt="You are Yantra AI, an intelligent robotic system agent.", response_format="text", model=DEFAULT_MODEL):
    """
    Unified function to call Yantra AI via Google Gemini API.
    Supports both standard text output and structured JSON extraction.
    """
    # Safeguard: If the frontend or other parts of the codebase still try to pass OpenRouter specific models,
    # we forcefully override it to use Gemini.
    if "openrouter" in model.lower() or "gpt" in model.lower():
        model = DEFAULT_MODEL

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
    
    headers = {
        "Content-Type": "application/json",
    }
    
    payload = {
        "systemInstruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ]
    }

    # Some models strictly enforce JSON if requested
    if response_format == "json_object":
        payload["generationConfig"] = {
            "responseMimeType": "application/json"
        }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        if "candidates" in data and len(data["candidates"]) > 0:
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        else:
            raise Exception("No response candidates found in Gemini API output.")
    except Exception as e:
        print(f"Error calling Yantra AI (Gemini): {e}")
        if 'response' in locals():
            print(f"Response: {response.text}")
            try:
                err_data = response.json()
                if "error" in err_data:
                    if isinstance(err_data["error"], dict) and "message" in err_data["error"]:
                        raise Exception(f"Gemini API Error: {err_data['error']['message']}")
                    else:
                        raise Exception(f"Gemini API Error: {err_data['error']}")
            except Exception as inner_e:
                if str(inner_e).startswith("Gemini API Error"):
                    raise inner_e
                pass
            raise Exception(f"Gemini API Error: {response.status_code} {response.reason} - {response.text[:100]}")
        raise Exception(f"Error calling AI: {str(e)}")

if __name__ == "__main__":
    # Quick test
    print("Testing Yantra AI (Gemini)...")
    result = invoke_yantra_ai("What is 2+2? Reply with just the number.")
    print(f"Yantra AI says: {result}")

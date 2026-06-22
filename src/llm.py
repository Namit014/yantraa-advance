import os
import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")  # sk-or-v1-...
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")

DEFAULT_MODEL = OPENROUTER_MODEL

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

if __name__ == "__main__":
    # Quick test
    print("Testing Yantra AI (OpenRouter)...")
    result = invoke_yantra_ai("What is 2+2? Reply with just the number.")
    print(f"Yantra AI says: {result}")

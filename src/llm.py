import os
import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
# Using a much smarter free model that reliably outputs JSON
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-lite-preview-02-05:free")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEFAULT_MODEL = "gemini-2.5-flash"

def _call_gemini(messages: list, temperature: float = 0.7, response_format: str = "text", model: str = "gemini-2.5-flash") -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
    
    system_instruction = None
    contents = []
    for msg in messages:
        if msg["role"] == "system":
            system_instruction = {"parts": [{"text": msg["content"]}]}
        else:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})
            
    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": 8192
        }
    }
    if system_instruction:
        payload["systemInstruction"] = system_instruction
        
    if response_format == "json_object":
        payload["generationConfig"]["responseMimeType"] = "application/json"
        
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError):
        raise Exception(f"Unexpected response from Gemini API: {data}")

def call_llm(messages: list, temperature: float = 0.7, response_format: str = "text", model: str = None) -> str:
    target_model = model or DEFAULT_MODEL
    
    if GEMINI_API_KEY and "gemini" in target_model.lower():
        try:
            return _call_gemini(messages, temperature, response_format, target_model)
        except Exception as e:
            print(f"Gemini API failed: {e}. Falling back to OpenRouter...")
            target_model = OPENROUTER_MODEL
    elif not GEMINI_API_KEY and target_model == DEFAULT_MODEL:
        target_model = OPENROUTER_MODEL

    if not OPENROUTER_API_KEY:
        if not GEMINI_API_KEY:
            raise Exception("No API keys available (GEMINI_API_KEY or OPENROUTER_API_KEY).")
        else:
            raise Exception("Gemini failed and no OPENROUTER_API_KEY fallback is available.")
        
    payload = {
        "model": target_model,
        "messages": messages,
        "temperature": temperature,
        # Cap max_tokens to prevent OpenRouter from estimating the max context window (65k) 
        # which exceeds free tier limits.
        "max_tokens": 1500,
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

import time

def invoke_yantra_ai(prompt, system_prompt="You are Yantra AI, an intelligent robotic system agent.", response_format="text", model=None, temperature=0.7):
    """
    Unified function to call Yantra AI via Google AI Studio or OpenRouter API fallback.
    Supports both standard text output and structured JSON extraction.
    Includes exponential backoff (2s, 5s, 10s, 20s) for rate limit resiliency.
    """
    if model is None:
        model = os.getenv("OPENROUTER_MODEL", "openrouter/free")
        
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]
    
    retries = [2, 5, 10, 20]
    for attempt, delay in enumerate(retries + [0]):
        try:
            return call_llm(messages, temperature=temperature, response_format=response_format, model=model)
        except Exception as e:
            err_str = str(e).lower()
            if delay > 0 and ("rate limit" in err_str or "429" in err_str or "busy" in err_str):
                print(f"[llm.py] Rate limit hit. Retrying in {delay} seconds... (Attempt {attempt+1}/{len(retries)})")
                time.sleep(delay)
            else:
                if delay > 0:
                    print(f"[llm.py] Transient error: {e}. Retrying in {delay}s... (Attempt {attempt+1}/{len(retries)})")
                    time.sleep(delay)
                else:
                    print(f"[llm.py] LLM invocation failed after all retries: {e}")
                    raise


if __name__ == "__main__":
    # Quick test
    print("Testing Yantra AI...")
    result = invoke_yantra_ai("What is 2+2? Reply with just the number.")
    print(f"Yantra AI says: {result}")

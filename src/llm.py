import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
FALLBACK_MODELS = [
    "openrouter/owl-alpha",
    "meta-llama/llama-3-8b-instruct:free",
    "nvidia/llama-3-8b-instruct:free",
    "openrouter/auto",
    "google/gemma-7b-it:free",
    "mistralai/mistral-7b-instruct:free"
]
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", FALLBACK_MODELS[0])

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
            "maxOutputTokens": 4000
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
        # which exceeds free tier limits, but allow enough for large JSON payloads.
        "max_tokens": 4000,
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

def invoke_yantra_ai(prompt, system_prompt="You are Yantra AI, an intelligent robotic system agent.", response_format="text", model=None, temperature=0.7):
    """
    Unified function to call Yantra AI via Google AI Studio or OpenRouter API fallback.
    Supports both standard text output and structured JSON extraction.
    """
    if model is None:
        model = os.getenv("OPENROUTER_MODEL", "openrouter/free")
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]
    return call_llm(messages, temperature=temperature, response_format=response_format, model=model)


import json
def call_llm_stream(messages: list, temperature: float = 0.7, response_format: str = "text", model: str = None):
    # If a specific model is passed (not None), try that first.
    # Otherwise, loop through all our fallback models.
    models_to_try = [model] if model else FALLBACK_MODELS
    
    if not OPENROUTER_API_KEY:
        if GEMINI_API_KEY:
            try:
                res = _call_gemini(messages, temperature, response_format, DEFAULT_MODEL)
                yield res
                return
            except Exception as e:
                yield "I'm experiencing high traffic. Please try again later."
                return
        yield "No API keys available for streaming."
        return

    last_error_str = ""

    for target_model in models_to_try:
        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 1000,
            "stream": True
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
                stream=True
            )
            response.raise_for_status()
            
            # Successfully connected, start streaming
            for line in response.iter_lines():
                if not line:
                    continue
                line_str = line.decode('utf-8').strip()
                if line_str.startswith("data: "):
                    data_content = line_str[6:]
                    if data_content == "[DONE]":
                        break
                    try:
                        chunk_json = json.loads(data_content)
                        delta = chunk_json.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if delta:
                            yield delta
                    except Exception:
                        pass
            
            # If we completed successfully, return out of the function so we don't try the next model
            return
            
        except Exception as e:
            # An error occurred with THIS model. Log it and continue to the next model.
            print(f"[Yantra AI] OpenRouter streaming failed for model {target_model}: {e}")
            last_error_str = str(e)
            continue
            
    # If we exhausted all OpenRouter fallback models, try Gemini as a final resort
    if GEMINI_API_KEY:
        print("[Yantra AI] All OpenRouter models failed. Falling back to Gemini API...")
        try:
            res = _call_gemini(messages, temperature, response_format, DEFAULT_MODEL)
            yield res
            return
        except Exception as gemini_err:
            print(f"[Yantra AI] Gemini fallback also failed: {gemini_err}")

    # If everything failed, yield a friendly error based on the last OpenRouter error
    if "429" in last_error_str or "Too Many Requests" in last_error_str:
        yield "I'm currently experiencing high traffic (Rate Limit Exceeded). Please try again in a few moments."
    elif "404" in last_error_str or "Not Found" in last_error_str:
        yield "The selected AI models are currently unavailable. Please try again later."
    elif "401" in last_error_str or "403" in last_error_str:
        yield "There is an issue with the AI API credentials. Please check the API key configuration."
    else:
        yield "An error occurred while communicating with the AI service. Please try again later."

def invoke_yantra_ai_chat_stream(messages: list, system_prompt: str = "You are Yantra AI, an intelligent robotic system agent.", response_format: str = "text", model: str = None, temperature: float = 0.7):
    # We do NOT hardcode openrouter/free here, because call_llm_stream manages fallbacks automatically
    full_messages = [{"role": "system", "content": system_prompt}] + messages
    return call_llm_stream(full_messages, temperature=temperature, response_format=response_format, model=model)


if __name__ == "__main__":
    # Quick test
    print("Testing Yantra AI...")
    result = invoke_yantra_ai("What is 2+2? Reply with just the number.")
    print(f"Yantra AI says: {result}")

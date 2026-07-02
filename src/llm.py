import os
import requests
import json
from dotenv import load_dotenv

load_dotenv(override=True)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "vllm").lower()

VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", os.getenv("VLLM_API_URL", "http://172.31.12.64:8000/v1")).rstrip("/")
VLLM_CHAT_API_URL = f"{VLLM_BASE_URL}/chat/completions"
VLLM_MODEL = os.getenv("VLLM_MODEL", "Qwen/Qwen3-14B-FP8")
VLLM_API_KEY = os.getenv("VLLM_API_KEY", "dummy")

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
# Using a much smarter free model that reliably outputs JSON
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/owl-alpha")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEFAULT_MODEL = "gemini-2.5-flash"

print(f"[Yantra AI] Starting up. Configured LLM_PROVIDER: {LLM_PROVIDER}")

def _call_gemini(messages: list, temperature: float = 0.7, response_format: str = "text", model: str = None) -> str:
    target_model = model or DEFAULT_MODEL
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={GEMINI_API_KEY}"
    
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

def _call_vllm(messages: list, temperature: float = 0.7, response_format: str = "text") -> str:
    payload = {
        "model": VLLM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 4096,
    }
    if response_format == "json_object":
        payload["response_format"] = {"type": "json_object"}

    headers = {
        "Authorization": f"Bearer {VLLM_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            VLLM_CHAT_API_URL,
            headers=headers,
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        if "choices" in data and len(data["choices"]) > 0:
            return data["choices"][0]["message"]["content"].strip()
        else:
            raise Exception("No response candidates found in vLLM API output.")
    except Exception as e:
        if 'response' in locals() and hasattr(response, 'text'):
            raise Exception(f"vLLM API Error: {response.status_code} - {response.text[:200]}")
        raise Exception(f"Error calling vLLM: {str(e)}")

def _call_openrouter(messages: list, temperature: float = 0.7, response_format: str = "text", model: str = None) -> str:
    target_model = model or OPENROUTER_MODEL
    
    payload = {
        "model": target_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 8192,
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

def call_llm(messages: list, temperature: float = 0.7, response_format: str = "text", model: str = None) -> str:
    fallback_order = ["gemini", "vllm", "openrouter"]
    
    # Providers to try: selected provider, then the rest in fallback_order
    providers_to_try = [LLM_PROVIDER]
    for p in fallback_order:
        if p != LLM_PROVIDER:
            providers_to_try.append(p)

    last_exception = None

    for provider in providers_to_try:
        try:
            if provider == "gemini":
                if not GEMINI_API_KEY:
                    raise Exception("GEMINI_API_KEY not set")
                return _call_gemini(messages, temperature, response_format, model)
                
            elif provider == "vllm":
                return _call_vllm(messages, temperature, response_format)
                
            elif provider == "openrouter":
                if not OPENROUTER_API_KEY:
                    raise Exception("OPENROUTER_API_KEY not set")
                return _call_openrouter(messages, temperature, response_format, model)
                
            else:
                raise Exception(f"Unknown LLM_PROVIDER: {provider}")
                
        except Exception as e:
            print(f"{provider.capitalize()} API failed: {e}. Falling back...")
            last_exception = e

    raise Exception(f"All LLM providers failed. Last error: {last_exception}")

def invoke_yantra_ai(prompt, system_prompt="You are Yantra AI, an intelligent robotic system agent.", response_format="text", model=None, temperature=0.7):
    """
    Unified function to call Yantra AI via selected provider with fallbacks.
    Supports both standard text output and structured JSON extraction.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]
    return call_llm(messages, temperature=temperature, response_format=response_format, model=model)


def _stream_vllm(messages: list, temperature: float = 0.7, response_format: str = "text"):
    payload = {
        "model": VLLM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 4096,
        "stream": True
    }
    if response_format == "json_object":
        payload["response_format"] = {"type": "json_object"}

    headers = {
        "Authorization": f"Bearer {VLLM_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            VLLM_CHAT_API_URL,
            headers=headers,
            json=payload,
            timeout=120,
            stream=True
        )
        response.raise_for_status()
        
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
    except Exception as e:
        print(f"Error in vLLM streaming call: {e}")
        raise

def _stream_openrouter(messages: list, temperature: float = 0.7, response_format: str = "text", model: str = None):
    target_model = model or OPENROUTER_MODEL
    
    payload = {
        "model": target_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 4000,
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
    except Exception as e:
        print(f"Error in OpenRouter streaming call: {e}")
        raise

def _stream_gemini(messages: list, temperature: float = 0.7, response_format: str = "text", model: str = None):
    target_model = model or DEFAULT_MODEL
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:streamGenerateContent?alt=sse&key={GEMINI_API_KEY}"
    
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
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120, stream=True)
        response.raise_for_status()
        
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
                    if "candidates" in chunk_json and len(chunk_json["candidates"]) > 0:
                        parts = chunk_json["candidates"][0].get("content", {}).get("parts", [])
                        if parts:
                            delta = parts[0].get("text", "")
                            if delta:
                                yield delta
                except Exception:
                    pass
    except Exception as e:
        print(f"Error in Gemini streaming call: {e}")
        raise

def call_llm_stream(messages: list, temperature: float = 0.7, response_format: str = "text", model: str = None):
    fallback_order = ["gemini", "vllm", "openrouter"]
    
    providers_to_try = [LLM_PROVIDER]
    for p in fallback_order:
        if p != LLM_PROVIDER:
            providers_to_try.append(p)
            
    last_exception = None
    
    for provider in providers_to_try:
        try:
            if provider == "gemini":
                if not GEMINI_API_KEY:
                    raise Exception("GEMINI_API_KEY not set")
                yield from _stream_gemini(messages, temperature, response_format, model)
                return
                
            elif provider == "vllm":
                yield from _stream_vllm(messages, temperature, response_format)
                return
                
            elif provider == "openrouter":
                if not OPENROUTER_API_KEY:
                    raise Exception("OPENROUTER_API_KEY not set")
                yield from _stream_openrouter(messages, temperature, response_format, model)
                return
                
            else:
                raise Exception(f"Unknown LLM_PROVIDER: {provider}")
                
        except Exception as e:
            print(f"{provider.capitalize()} streaming failed: {e}. Falling back...")
            last_exception = e
            
    yield f"Error in streaming LLM call: All providers failed. Last error: {str(last_exception)}"

def invoke_yantra_ai_chat_stream(messages: list, system_prompt: str = "You are Yantra AI, an intelligent robotic system agent.", response_format: str = "text", model: str = None, temperature: float = 0.7):
    full_messages = [{"role": "system", "content": system_prompt}] + messages
    return call_llm_stream(full_messages, temperature=temperature, response_format=response_format, model=model)

def check_vllm_health() -> bool:
    """Check if the vLLM server is accessible."""
    try:
        models_url = f"{VLLM_BASE_URL}/models"
        response = requests.get(models_url, timeout=5)
        return response.status_code == 200
    except Exception:
        return False

if __name__ == "__main__":
    # Quick test
    print("Testing Yantra AI...")
    print(f"Health of vLLM: {'Up' if check_vllm_health() else 'Down'}")
    result = invoke_yantra_ai("What is 2+2? Reply with just the number.")
    print(f"Yantra AI says: {result}")

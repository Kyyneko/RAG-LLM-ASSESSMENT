# llm/client.py

import os
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()


class LLMClientError(Exception):
    """Custom exception untuk error LLM client."""
    pass


class RateLimitError(LLMClientError):
    """Exception untuk rate limit error."""
    pass


class ModelError(LLMClientError):
    """Exception untuk model execution errors."""
    pass


def call_openrouter(messages, model=None, max_retries=10, timeout=90):
    """
    Mengirim permintaan chat completion ke OpenRouter API.
    
    FIXED: Accept messages as list of dicts (proper format)
    
    Args:
        messages (list): List of message dicts with 'role' and 'content'
        model (str): Model name (optional, defaults to LLM_MODEL env var)
        max_retries (int): Max retry attempts
        timeout (int): Request timeout
        
    Returns:
        str: LLM response content
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise LLMClientError("OPENROUTER_API_KEY tidak ditemukan di environment variables.")
    
    # VALIDATION: Messages must be list
    if not isinstance(messages, list):
        raise ValueError(f"messages must be list, got: {type(messages)}")
    
    if not messages:
        raise ValueError("messages list is empty!")
    
    # Validate each message
    for i, msg in enumerate(messages):
        if not isinstance(msg, dict):
            raise ValueError(f"Message {i} must be dict, got: {type(msg)}")
        if "role" not in msg or "content" not in msg:
            raise ValueError(f"Message {i} missing 'role' or 'content'")
    
    # Use LLM_MODEL from .env if model not specified
    # Fallback order: parameter > LLM_MODEL > google/gemma-3-27b-it:free (default)
    model_name = model or os.getenv("LLM_MODEL", "google/gemma-3-27b-it:free")
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5000",
        "X-Title": "SILAB-RAG"
    }
    
    payload = {
        "model": model_name,
        "messages": messages,  # FIXED: Use messages directly (list of dicts)
        "max_tokens": 8000,    # INCREASED: from 3000 to 8000
        "temperature": 0.7,
        "top_p": 0.9,
    }
    
    # DEBUG
    print(f"\n[DEBUG] Model: {model_name}")
    print(f"[DEBUG] Messages count: {len(messages)}")
    for i, msg in enumerate(messages):
        print(f"  [{i}] role={msg['role']}, length={len(msg.get('content', ''))}")
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"\n[LLM Request] Attempt {attempt}/{max_retries}")
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)
            
            print(f"[Response] Status: {response.status_code}")
            
            if response.status_code == 429:
                wait_time = min(2 ** attempt, 32)
                print(f"⚠️ Rate limit. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            
            if response.status_code != 200:
                error_detail = response.text
                print(f"❌ Error: {error_detail[:500]}")
                
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    raise ModelError(f"HTTP {response.status_code}: {error_detail}")
            
            data = response.json()
            
            if "choices" not in data or len(data["choices"]) == 0:
                raise ModelError("Response tidak mengandung 'choices'.")
            
            content = data["choices"][0]["message"]["content"]
            finish_reason = data["choices"][0].get("finish_reason", "")
            
            # Check for truncation
            if finish_reason == "length":
                print("⚠️ WARNING: Response truncated (hit max_tokens limit)")
            
            if "usage" in data:
                usage = data["usage"]
                print(f"✓ Success | Tokens: {usage.get('total_tokens', 'N/A')} "
                      f"(prompt: {usage.get('prompt_tokens', 'N/A')}, "
                      f"completion: {usage.get('completion_tokens', 'N/A')})")
            
            return content
        
        except requests.exceptions.Timeout:
            print(f"⚠️ Timeout on attempt {attempt}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)
            else:
                raise LLMClientError(f"Timeout after {max_retries} attempts")
        
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Request error: {str(e)}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)
            else:
                raise LLMClientError(f"Request failed: {str(e)}")
        
        except json.JSONDecodeError:
            print(f"⚠️ Invalid JSON response on attempt {attempt}")
            if attempt < max_retries:
                time.sleep(2)
            else:
                raise ModelError("Response is not valid JSON")
    
    raise RateLimitError(f"Failed after {max_retries} attempts")

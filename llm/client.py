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


def call_openrouter(messages, model=None, max_retries=10, timeout=120):
    """
    Mengirim permintaan chat completion ke OpenRouter API.
    
    FIXED: Accept messages as list of dicts (proper format)
    
    Args:
        messages (list): List of message dicts with 'role' and 'content'
        model (str): Model name (optional, defaults to LLM_MODEL env var)
        max_retries (int): Max retry attempts
        timeout (int): Request timeout (increased to 120s)
        
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
        "messages": messages,
        "max_tokens": 8000,
        "temperature": 0.7,
        "top_p": 0.9,
    }
    
    # DEBUG
    print(f"\n[DEBUG] Model: {model_name}")
    print(f"[DEBUG] API Key: {api_key[:20]}...{api_key[-10:]}")
    print(f"[DEBUG] Messages count: {len(messages)}")
    for i, msg in enumerate(messages):
        print(f"  [{i}] role={msg['role']}, length={len(msg.get('content', ''))}")
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"\n[LLM Request] Attempt {attempt}/{max_retries}")
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)
            
            print(f"[Response] Status: {response.status_code}")
            
            # Log response headers for debugging
            if 'x-ratelimit-remaining' in response.headers:
                print(f"[Response] Rate limit remaining: {response.headers['x-ratelimit-remaining']}")
            
            if response.status_code == 429:
                wait_time = min(2 ** attempt, 32)
                print(f"⚠️ Rate limit. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            
            if response.status_code != 200:
                error_detail = response.text
                print(f"❌ HTTP Error {response.status_code}")
                print(f"Response body: {error_detail[:1000]}")
                
                # Try to parse error as JSON
                try:
                    error_json = response.json()
                    if "error" in error_json:
                        error_msg = error_json["error"]
                        if isinstance(error_msg, dict):
                            error_msg = error_msg.get("message", str(error_msg))
                        print(f"API Error message: {error_msg}")
                        raise ModelError(f"OpenRouter API Error: {error_msg}")
                except json.JSONDecodeError:
                    pass
                
                if attempt < max_retries:
                    wait_time = min(2 ** attempt, 16)
                    print(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise ModelError(f"HTTP {response.status_code}: {error_detail[:500]}")
            
            # Parse JSON response
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse JSON response: {str(e)}")
                print(f"Raw response: {response.text[:500]}")
                raise ModelError(f"Invalid JSON response from API: {str(e)}")
            
            # DEBUG: Print entire response structure
            print(f"[DEBUG] Response keys: {list(data.keys())}")
            
            # Check for error in response
            if "error" in data:
                error_info = data["error"]
                if isinstance(error_info, dict):
                    error_msg = error_info.get("message", str(error_info))
                else:
                    error_msg = str(error_info)
                print(f"❌ API returned error: {error_msg}")
                raise ModelError(f"OpenRouter API Error: {error_msg}")
            
            # Check for choices
            if "choices" not in data:
                print(f"❌ Response missing 'choices' field")
                print(f"Available fields: {list(data.keys())}")
                print(f"Full response: {json.dumps(data, indent=2)[:1000]}")
                
                # Check if model is still loading
                if "model" in data and "status" in data:
                    if data.get("status") == "loading":
                        wait_time = min(2 ** attempt, 30)
                        print(f"⚠️ Model is still loading. Waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                
                raise ModelError(f"Response missing 'choices' field. Response: {json.dumps(data)[:500]}")
            
            if len(data["choices"]) == 0:
                print(f"❌ Choices array is empty")
                raise ModelError("Response 'choices' array is empty")
            
            # Extract content
            choice = data["choices"][0]
            if "message" not in choice:
                print(f"❌ Choice missing 'message' field")
                print(f"Choice structure: {json.dumps(choice, indent=2)}")
                raise ModelError("Choice missing 'message' field")
            
            content = choice["message"].get("content", "")
            if not content:
                print(f"❌ Message content is empty")
                raise ModelError("Message content is empty")
            
            finish_reason = choice.get("finish_reason", "")
            
            # Check for truncation
            if finish_reason == "length":
                print("⚠️ WARNING: Response truncated (hit max_tokens limit)")
            
            # Log usage stats
            if "usage" in data:
                usage = data["usage"]
                print(f"✓ Success | Tokens: {usage.get('total_tokens', 'N/A')} "
                      f"(prompt: {usage.get('prompt_tokens', 'N/A')}, "
                      f"completion: {usage.get('completion_tokens', 'N/A')})")
            
            print(f"✓ Generated {len(content)} characters")
            return content
        
        except ModelError:
            # Re-raise ModelError without retry
            if attempt < max_retries:
                wait_time = min(2 ** attempt, 16)
                print(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                raise
        
        except requests.exceptions.Timeout:
            print(f"⚠️ Timeout on attempt {attempt} (waited {timeout}s)")
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
        
        except json.JSONDecodeError as e:
            print(f"⚠️ Invalid JSON response on attempt {attempt}: {str(e)}")
            print(f"Raw response: {response.text[:500]}")
            if attempt < max_retries:
                time.sleep(2)
            else:
                raise ModelError(f"Response is not valid JSON: {str(e)}")
    
    raise RateLimitError(f"Failed after {max_retries} attempts")

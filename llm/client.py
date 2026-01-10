import os
import json
import time
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


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
    
    if not isinstance(messages, list):
        raise ValueError(f"messages harus berupa list, diterima: {type(messages)}")
    
    if not messages:
        raise ValueError("messages list kosong!")
    
    for i, msg in enumerate(messages):
        if not isinstance(msg, dict):
            raise ValueError(f"Message {i} harus berupa dict, diterima: {type(msg)}")
        if "role" not in msg or "content" not in msg:
            raise ValueError(f"Message {i} tidak memiliki 'role' atau 'content'")
    
    # Model from env var, default to GPT-OSS 120B
    default_model = "openai/gpt-oss-120b:free"
    model_name = model or os.getenv("LLM_MODEL", default_model)
    
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
    
    logger.debug(f"Model: {model_name}")
    logger.debug(f"API Key: {api_key[:20]}...{api_key[-10:]}")
    logger.debug(f"Message count: {len(messages)}")
    for i, msg in enumerate(messages):
        logger.debug(f"  [{i}] role={msg['role']}, length={len(msg.get('content', ''))}")
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"LLM Request attempt {attempt}/{max_retries}")
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)
            
            logger.debug(f"Response status: {response.status_code}")
            
            if 'x-ratelimit-remaining' in response.headers:
                logger.debug(f"Rate limit remaining: {response.headers['x-ratelimit-remaining']}")
            
            if response.status_code == 429:
                if attempt >= 5:
                    raise RateLimitError(
                        "Rate limit tercapai. API OpenRouter sedang sibuk. "
                        "Silakan tunggu beberapa menit dan coba lagi."
                    )
                wait_time = min(2 ** attempt, 15)
                logger.warning(f"Rate limit hit. Retrying in {wait_time}s (attempt {attempt}/5)")
                time.sleep(wait_time)
                continue
            
            if response.status_code != 200:
                error_detail = response.text
                logger.error(f"HTTP Error {response.status_code}")
                logger.debug(f"Response body: {error_detail[:1000]}")
                
                try:
                    error_json = response.json()
                    if "error" in error_json:
                        error_msg = error_json["error"]
                        if isinstance(error_msg, dict):
                            error_msg = error_msg.get("message", str(error_msg))
                        logger.error(f"API error message: {error_msg}")
                        raise ModelError(f"OpenRouter API Error: {error_msg}")
                except json.JSONDecodeError:
                    pass
                
                if attempt < max_retries:
                    wait_time = min(2 ** attempt, 16)
                    logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise ModelError(f"HTTP {response.status_code}: {error_detail[:500]}")
            
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {str(e)}")
                logger.debug(f"Raw response: {response.text[:500]}")
                raise ModelError(f"Response JSON tidak valid dari API: {str(e)}")
            
            logger.debug(f"Response keys: {list(data.keys())}")
            
            if "error" in data:
                error_info = data["error"]
                if isinstance(error_info, dict):
                    error_msg = error_info.get("message", str(error_info))
                else:
                    error_msg = str(error_info)
                logger.error(f"API returned error: {error_msg}")
                raise ModelError(f"OpenRouter API Error: {error_msg}")
            
            if "choices" not in data:
                logger.error("Response missing 'choices' field")
                logger.debug(f"Available fields: {list(data.keys())}")
                logger.debug(f"Full response: {json.dumps(data, indent=2)[:1000]}")
                
                if "model" in data and "status" in data:
                    if data.get("status") == "loading":
                        wait_time = min(2 ** attempt, 30)
                        logger.warning(f"Model still loading. Waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                
                raise ModelError(f"Response tidak memiliki field 'choices'. Response: {json.dumps(data)[:500]}")
            
            if len(data["choices"]) == 0:
                logger.error("Empty choices array")
                raise ModelError("Array 'choices' di response kosong")
            
            choice = data["choices"][0]
            if "message" not in choice:
                logger.error("Choice missing 'message' field")
                logger.debug(f"Choice structure: {json.dumps(choice, indent=2)}")
                raise ModelError("Choice tidak memiliki field 'message'")
            
            content = choice["message"].get("content", "")
            if not content:
                logger.error("Empty message content")
                raise ModelError("Konten message kosong")
            
            finish_reason = choice.get("finish_reason", "")
            
            if finish_reason == "length":
                logger.warning("Response truncated (max_tokens limit reached)")
            
            if "usage" in data:
                usage = data["usage"]
                logger.info(f"Tokens used: {usage.get('total_tokens', 'N/A')} "
                           f"(prompt: {usage.get('prompt_tokens', 'N/A')}, "
                           f"completion: {usage.get('completion_tokens', 'N/A')})")

            logger.info(f"Successfully generated {len(content)} characters")
            return content
        
        except ModelError:
            if attempt < max_retries:
                wait_time = min(2 ** attempt, 16)
                logger.info(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                raise
        
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout on attempt {attempt} (waited {timeout}s)")
            if attempt < max_retries:
                time.sleep(2 ** attempt)
            else:
                raise LLMClientError(f"Timeout setelah {max_retries} percobaan")
        
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error: {str(e)}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)
            else:
                raise LLMClientError(f"Request gagal: {str(e)}")
        
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON response on attempt {attempt}: {str(e)}")
            logger.debug(f"Raw response: {response.text[:500]}")
            if attempt < max_retries:
                time.sleep(2)
            else:
                raise ModelError(f"Response bukan JSON valid: {str(e)}")
    
    raise RateLimitError(f"Gagal setelah {max_retries} percobaan")

import requests
import json
import os

# Minimal test case
api_key = os.getenv("OPENROUTER_API_KEY", "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")

url = "https://openrouter.ai/api/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

# Test 1: Minimal payload
payload1 = {
    "model": "google/gemini-2.0-flash-exp:free",
    "messages": [
        {"role": "user", "content": "Hello"}
    ]
}

print("Test 1: Minimal payload")
print(f"Payload: {json.dumps(payload1, indent=2)}")

try:
    response = requests.post(url, headers=headers, json=payload1, timeout=30)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "="*80 + "\n")

# Test 2: With system message
payload2 = {
    "model": "google/gemini-2.0-flash-exp:free",
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say hello"}
    ],
    "max_tokens": 100
}

print("Test 2: With system message")
print(f"Payload: {json.dumps(payload2, indent=2)}")

try:
    response = requests.post(url, headers=headers, json=payload2, timeout=30)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"Error: {e}")
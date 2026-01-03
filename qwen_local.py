# qwen_local.py
"""
Local Qwen client adapter (restored).
Talks to a local HTTP server exposing an OpenAI-compatible /v1/chat/completions endpoint.
"""
import os
import requests


class LocalQwenClient:
    def __init__(self, api_base: str = None, model: str = "qwen-2.5-32b", timeout: int = 60):
        self.api_base = api_base or os.getenv("QWEN_LOCAL_API_BASE") or "http://localhost:8000/v1"
        self.model = model
        self.timeout = timeout

    def chat(self, messages, temperature: float = 0.0, max_tokens: int = 1024) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        url = f"{self.api_base.rstrip('/')}/chat/completions"
        resp = requests.post(url, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        j = resp.json()

        try:
            return j["choices"][0]["message"]["content"].strip()
        except Exception:
            if "choices" in j and len(j["choices"]) > 0 and "text" in j["choices"][0]:
                return j["choices"][0]["text"].strip()
            if "text" in j:
                return j["text"].strip()
            raise RuntimeError("Unexpected response format from local Qwen server")


if __name__ == "__main__":
    client = LocalQwenClient()
    msgs = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say hello in one sentence."},
    ]
    print(client.chat(msgs))

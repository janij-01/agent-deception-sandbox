"""OpenAI-compatible chat client. The key stays in the environment."""

import json
import os
import subprocess


class ChatClient:
    def __init__(self, model: str, api_key: str, base_url: str, timeout: int = 90):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def complete(self, system: str, user: str, seed: int) -> str:
        url = self.base_url + "/chat/completions"
        body = {
            "model": self.model,
            "temperature": 0.7,
            "seed": seed,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        result = subprocess.run(
            [
                "curl",
                "-sS",
                "--max-time",
                str(self.timeout),
                "-w",
                "\n%{http_code}",
                "-X",
                "POST",
                url,
                "-H",
                f"Authorization: Bearer {self.api_key}",
                "-H",
                "Content-Type: application/json",
                "--data-binary",
                "@-",
            ],
            input=json.dumps(body).encode(),
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            detail = result.stderr.decode(errors="replace")[:500]
            raise RuntimeError(f"model API request failed: {detail}")
        raw = result.stdout.decode(errors="replace")
        text, _, status = raw.rpartition("\n")
        if status.strip() != "200":
            raise RuntimeError(f"model API HTTP {status.strip()}: {text[:500]}")
        try:
            payload = json.loads(text)
            return payload["choices"][0]["message"]["content"]
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("model API returned no message content") from exc


def client_from_env(model: str | None) -> ChatClient:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Export it, or pass an OpenAI-compatible "
            "base URL with OPENAI_BASE_URL."
        )
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
    chosen = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    return ChatClient(chosen, api_key, base_url)

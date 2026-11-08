"""Model clients. Keys stay in the environment and are never written to results."""

import json
import os
import subprocess
import time

ADAPTION_URL = "https://api.prod.adaptionlabs.ai/api/v1/responses"


def _post_json(url: str, api_key: str, body: dict, timeout: int) -> dict:
    result = subprocess.run(
        [
            "curl",
            "-sS",
            "--max-time",
            str(timeout),
            "-w",
            "\n%{http_code}",
            "-X",
            "POST",
            url,
            "-H",
            f"Authorization: Bearer {api_key}",
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
        detail = result.stderr.decode(errors="replace")[:500].replace(api_key, "[redacted]")
        raise RuntimeError(f"model API request failed: {detail}")
    raw = result.stdout.decode(errors="replace")
    text, _, status = raw.rpartition("\n")
    if status.strip() != "200":
        detail = text[:500].replace(api_key, "[redacted]")
        raise RuntimeError(f"model API HTTP {status.strip()}: {detail}")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("model API returned non-JSON") from exc


TRANSIENT = ("HTTP 429", "HTTP 500", "HTTP 502", "HTTP 503", "HTTP 504", "request failed")


def _post_with_retry(url: str, api_key: str, body: dict, timeout: int, attempts: int = 4) -> dict:
    """Retry rate limits, gateway errors and curl timeouts with backoff (2, 4, 8 s)."""
    for attempt in range(attempts):
        try:
            return _post_json(url, api_key, body, timeout)
        except RuntimeError as exc:
            if attempt == attempts - 1 or not any(code in str(exc) for code in TRANSIENT):
                raise
            time.sleep(2 ** (attempt + 1))
    raise AssertionError("unreachable")


class AdaptionClient:
    """Adaption Responses API. Memory and tools stay off so trials do not share state."""

    def __init__(self, model: str, api_key: str, timeout: int = 180):
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def complete(self, system: str, user: str, seed: int) -> str:
        del seed  # This API has no seed parameter. The trial seed is still logged.
        body = {
            "model": self.model,
            "instructions": system,
            "input": user,
            "temperature": 0.7,
            "max_output_tokens": 8192,
            "tool_choice": "none",
            "agentic_memory": False,
            "store": False,
        }
        payload = _post_with_retry(ADAPTION_URL, self.api_key, body, self.timeout)
        text = payload.get("output_text") or ""
        status = payload.get("status")
        if text.strip() and status in (None, "completed", "incomplete"):
            return text
        err = payload.get("error") or payload.get("incomplete_details") or status
        raise RuntimeError(f"model API status {status}: {err}")


class ChatClient:
    def __init__(self, model: str, api_key: str, base_url: str, timeout: int = 90):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def complete(self, system: str, user: str, seed: int) -> str:
        payload = _post_with_retry(
            self.base_url + "/chat/completions",
            self.api_key,
            {
                "model": self.model,
                "temperature": 0.7,
                "seed": seed,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            self.timeout,
        )
        try:
            return payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("model API returned no message content") from exc


def client_from_env(model: str | None):
    adaption_key = os.environ.get("ADAPTION_API_KEY", "").strip()
    if adaption_key:
        chosen = model or os.environ.get("ADAPTION_MODEL", "qwen3.8-27b")
        return AdaptionClient(chosen, adaption_key)
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "Set ADAPTION_API_KEY or OPENAI_API_KEY. Adaption is used when its key is present."
        )
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
    chosen = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    return ChatClient(chosen, api_key, base_url)

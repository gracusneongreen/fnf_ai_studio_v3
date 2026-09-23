"""Provider-neutral, cost-aware AI connector.

The connector never attempts to bypass quotas or payment controls.  It selects
local Ollama first, then explicitly configured free-tier endpoints, and returns
an actionable error when no provider is configured.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional


class CloudAIError(RuntimeError):
    """Raised when a configured AI provider cannot complete a request."""


@dataclass(frozen=True)
class CloudAIConfig:
    cloud_free: bool = False
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2"
    huggingface_model: Optional[str] = None
    request_timeout: float = 30.0


class FreeAIConnector:
    """Small standard-library connector for local and free-tier providers."""

    def __init__(self, config: CloudAIConfig = CloudAIConfig()) -> None:
        self.config = config

    def status(self) -> Dict[str, Any]:
        return {
            "cloud_free": self.config.cloud_free,
            "ollama_url": self.config.ollama_url,
            "ollama_model": self.config.ollama_model,
            "huggingface_configured": bool(
                self.config.huggingface_model
                and os.getenv("HF_TOKEN")
            ),
        }

    def chat(self, prompt: str) -> str:
        if not prompt.strip():
            raise CloudAIError("prompt must not be empty")
        try:
            return self._ollama_chat(prompt)
        except (CloudAIError, urllib.error.URLError, TimeoutError) as ollama_error:
            if self.config.cloud_free and self.config.huggingface_model:
                return self._huggingface_chat(prompt)
            raise CloudAIError(
                "No reachable local Ollama or configured free-tier provider. "
                "Start Ollama or set HF_TOKEN/HF model; paid providers are not "
                "used by --cloud-free."
            ) from ollama_error

    def _ollama_chat(self, prompt: str) -> str:
        payload = json.dumps(
            {
                "model": self.config.ollama_model,
                "prompt": prompt,
                "stream": False,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.config.ollama_url.rstrip('/')}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self.config.request_timeout
            ) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise CloudAIError("Ollama request failed") from exc
        text = result.get("response")
        if not isinstance(text, str):
            raise CloudAIError("Ollama returned no response text")
        return text

    def _huggingface_chat(self, prompt: str) -> str:
        token = os.getenv("HF_TOKEN")
        if not token or not self.config.huggingface_model:
            raise CloudAIError("HF_TOKEN and huggingface_model are required")
        payload = json.dumps({"inputs": prompt}).encode("utf-8")
        request = urllib.request.Request(
            f"https://api-inference.huggingface.co/models/{self.config.huggingface_model}",
            data=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self.config.request_timeout
            ) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise CloudAIError("Hugging Face request failed") from exc
        if isinstance(result, list) and result and isinstance(result[0], dict):
            text = result[0].get("generated_text")
            if isinstance(text, str):
                return text
        raise CloudAIError("Hugging Face returned no generated text")

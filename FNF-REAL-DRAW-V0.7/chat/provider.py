"""OpenAI-compatible local provider layer for LM Studio, vLLM and similar servers."""
from __future__ import annotations
import json, os, urllib.error, urllib.request
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()

@dataclass
class ProviderConfig:
    provider: str
    model: str
    base_url: str
    api_key: str
    json_mode: bool

DEFAULTS = {
    "lmstudio": ("http://localhost:1234/v1", "local"),
    "vllm": ("http://localhost:8000/v1", "local"),
    "openai-compatible": ("http://localhost:1234/v1", "local"),
}

def load_config() -> ProviderConfig:
    provider=os.getenv("FNF_CHAT_PROVIDER","lmstudio").strip().lower()
    if provider not in DEFAULTS:
        raise ValueError("Unknown provider. Use lmstudio, vllm, or openai-compatible.")
    default_url, default_key=DEFAULTS[provider]
    return ProviderConfig(
        provider=provider,
        model=os.getenv("FNF_CHAT_MODEL","").strip(),
        base_url=(os.getenv("FNF_CHAT_BASE_URL","").strip() or default_url).rstrip("/"),
        api_key=os.getenv("FNF_CHAT_API_KEY","").strip() or default_key,
        json_mode=os.getenv("FNF_CHAT_JSON_MODE","true").lower() in {"1","true","yes","on"},
    )

def list_models(config: ProviderConfig) -> list[str]:
    req=urllib.request.Request(config.base_url+"/models", headers={"Authorization":f"Bearer {config.api_key}"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data=json.loads(r.read().decode())
        return [x.get("id","") for x in data.get("data",[]) if x.get("id")]
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
        return []

def chat(config: ProviderConfig, messages: list[dict]) -> str:
    if not config.model:
        models=list_models(config)
        if not models:
            raise RuntimeError("No model selected and /models returned no models. Set FNF_CHAT_MODEL in .env.")
        config.model=models[0]
    payload={"model":config.model,"messages":messages,"temperature":0.2}
    if config.json_mode:
        payload["response_format"]={"type":"json_object"}
    body=json.dumps(payload).encode()
    req=urllib.request.Request(
        config.base_url+"/chat/completions", data=body,
        headers={"Authorization":f"Bearer {config.api_key}","Content-Type":"application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            data=json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail=e.read().decode(errors="replace")
        raise RuntimeError(f"{config.provider} HTTP {e.code}: {detail}") from e
    return data["choices"][0]["message"]["content"]

# Local AI Chat

The chat layer uses the OpenAI-compatible API contract so LM Studio and vLLM can share one client.

Set FNF_CHAT_PROVIDER and FNF_CHAT_BASE_URL in .env. If FNF_CHAT_MODEL is empty, V0.7 queries /models and selects the first returned model.

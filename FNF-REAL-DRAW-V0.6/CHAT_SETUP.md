# AI Chat setup

V0.6 uses .env for provider and model selection.

Install:
python -m pip install -r requirements.txt

Create .env:
Copy-Item .env.example .env

OpenAI:
FNF_CHAT_PROVIDER=openai
FNF_CHAT_MODEL=gpt-5.6-luna
OPENAI_API_KEY=YOUR_API_KEY

OpenAI-compatible:
FNF_CHAT_PROVIDER=openai-compatible
FNF_CHAT_MODEL=YOUR_MODEL_ID
FNF_CHAT_API_KEY=YOUR_KEY_IF_REQUIRED
FNF_CHAT_BASE_URL=http://localhost:1234/v1

Ollama:
FNF_CHAT_PROVIDER=ollama
FNF_CHAT_MODEL=llama3.2
FNF_CHAT_BASE_URL=http://localhost:11434/v1

Start:
python cli.py chat

The startup line shows the active provider and model. Never commit .env.

# AI Chat setup

V0.6 now includes an AI chat copilot. It understands natural-language requests and returns structured generation jobs.

PowerShell:
```powershell
$env:FNF_CHAT_API_KEY="YOUR_API_KEY"
$env:FNF_CHAT_MODEL="gpt-4o-mini"
python cli.py chat
```

Optional OpenAI-compatible endpoint:
```powershell
$env:FNF_CHAT_BASE_URL="https://YOUR-ENDPOINT/v1"
```

Examples:
- wygeneruj animację z character.png
- zrób idle, singLEFT, singDOWN, singUP i singRIGHT
- przygotuj plan oryginalnej postaci i zachowaj spójność ubrań

The first release is a copilot. The local animate command remains the deterministic execution path; a later version can add a permission-gated action runner.

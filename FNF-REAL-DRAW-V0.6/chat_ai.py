"""FNF-REAL-DRAW V0.6 — CLI AI chat copilot."""
from __future__ import annotations
import json, os, urllib.request, urllib.error
from dataclasses import dataclass

SYSTEM_PROMPT = """You are FNF-REAL-DRAW Assistant, a CLI copilot for an original 2D rhythm-game asset pipeline.
Help create original characters, poses, animation plans, sprite exports, charts and visual effects.
FNF animation names may be used as technical schema references, but do not reproduce copyrighted character artwork.
Return concise JSON: {"reply":"...","action":"none|animate|generate_character|export","parameters":{}}.
Never invent a local file the user did not provide."""

@dataclass
class ChatConfig:
    api_key: str
    model: str
    base_url: str

def load_config():
    key=os.getenv("FNF_CHAT_API_KEY","")
    if not key: raise RuntimeError("Brak FNF_CHAT_API_KEY. Ustaw klucz API.")
    return ChatConfig(key, os.getenv("FNF_CHAT_MODEL","gpt-4o-mini"),
                      os.getenv("FNF_CHAT_BASE_URL","https://api.openai.com/v1").rstrip("/"))

def ask(config, messages):
    payload={"model":config.model,"messages":[{"role":"system","content":SYSTEM_PROMPT},*messages],
             "temperature":0.2,"response_format":{"type":"json_object"}}
    req=urllib.request.Request(config.base_url+"/chat/completions",
        data=json.dumps(payload).encode(),headers={"Authorization":"Bearer "+config.api_key,"Content-Type":"application/json"},method="POST")
    try:
        with urllib.request.urlopen(req,timeout=120) as r: data=json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Chat API HTTP {e.code}: {e.read().decode(errors='replace')}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Nie można połączyć z Chat API: {e}") from e
    content=data["choices"][0]["message"]["content"]
    try: return json.loads(content)
    except json.JSONDecodeError: return {"reply":content,"action":"none","parameters":{}}

def run_chat():
    config=load_config(); messages=[]
    print("FNF-REAL-DRAW AI CHAT")
    print("Wpisz 'exit' aby zakończyć.\n")
    while True:
        try: user=input("Ty > ").strip()
        except (EOFError,KeyboardInterrupt): print(); break
        if user.lower() in {"exit","quit"}: break
        if not user: continue
        messages.append({"role":"user","content":user})
        result=ask(config,messages)
        messages.append({"role":"assistant","content":json.dumps(result)})
        print("AI >",result.get("reply",""))
        if result.get("action","none")!="none":
            print("ACTION >",result["action"])
            print(json.dumps(result.get("parameters",{}),indent=2,ensure_ascii=False))

if __name__=="__main__": run_chat()

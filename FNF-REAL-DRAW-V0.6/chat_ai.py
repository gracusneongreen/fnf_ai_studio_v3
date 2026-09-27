"""FNF-REAL-DRAW V0.6 — provider/model-selectable CLI AI chat."""
from __future__ import annotations
import json, os, urllib.error, urllib.request
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None
if load_dotenv:
    load_dotenv()

SYSTEM_PROMPT = """You are FNF-REAL-DRAW Assistant, a CLI copilot for an original 2D rhythm-game asset pipeline.
Help create original characters, poses, animation plans, sprite exports, charts and visual effects.
FNF animation names may be used as technical schema references, but do not reproduce copyrighted character artwork.
Return concise JSON: {"reply":"...","action":"none|animate|generate_character|export","parameters":{}}.
Never invent a local file the user did not provide."""

PROVIDERS = {
    "openai": {"name":"OpenAI","base_url":"https://api.openai.com/v1","key_env":"OPENAI_API_KEY","default_model":"gpt-5.6-luna"},
    "openai-compatible": {"name":"OpenAI-compatible","base_url":"","key_env":"FNF_CHAT_API_KEY","default_model":"gpt-5.6-luna"},
    "ollama": {"name":"Ollama","base_url":"http://localhost:11434/v1","key_env":"OLLAMA_API_KEY","default_model":"llama3.2"},
}

def load_config():
    name=os.getenv("FNF_CHAT_PROVIDER","openai").strip().lower()
    if name not in PROVIDERS:
        raise RuntimeError("Unknown FNF_CHAT_PROVIDER. Choose: " + ", ".join(PROVIDERS))
    p=PROVIDERS[name]
    key=os.getenv(p["key_env"],"") or ("ollama" if name=="ollama" else "")
    if not key:
        raise RuntimeError(f"Missing {p['key_env']}. Put it in .env.")
    base=os.getenv("FNF_CHAT_BASE_URL","").strip() or p["base_url"]
    model=os.getenv("FNF_CHAT_MODEL","").strip() or p["default_model"]
    return name,p,key,base.rstrip("/"),model

def ask(config,messages):
    name,p,key,base,model=config
    payload={"model":model,"messages":[{"role":"system","content":SYSTEM_PROMPT},*messages],"temperature":0.2,"response_format":{"type":"json_object"}}
    req=urllib.request.Request(base+"/chat/completions",data=json.dumps(payload).encode(),headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},method="POST")
    try:
        with urllib.request.urlopen(req,timeout=120) as r:
            data=json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{p['name']} HTTP {e.code}: {e.read().decode(errors='replace')}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Cannot connect to {p['name']}: {e}") from e
    try:
        content=data["choices"][0]["message"]["content"]
    except (KeyError,IndexError,TypeError) as e:
        raise RuntimeError(f"Unexpected response from {p['name']}: {data}") from e
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"reply":content,"action":"none","parameters":{}}

def run_chat():
    config=load_config()
    _,p,_,_,model=config
    print(f"FNF-REAL-DRAW AI CHAT | provider={p['name']} | model={model}")
    print("Wpisz exit aby zakończyć.\n")
    messages=[]
    while True:
        try:
            user=input("Ty > ").strip()
        except (EOFError,KeyboardInterrupt):
            print()
            break
        if user.lower() in {"exit","quit"}:
            break
        if not user:
            continue
        messages.append({"role":"user","content":user})
        result=ask(config,messages)
        messages.append({"role":"assistant","content":json.dumps(result)})
        print("AI >",result.get("reply",""))
        if result.get("action","none")!="none":
            print("ACTION >",result["action"])
            print(json.dumps(result.get("parameters",{}),indent=2,ensure_ascii=False))

if __name__=="__main__":
    run_chat()

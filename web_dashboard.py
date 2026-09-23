"""Local FNF-OMNI-STUDIO-V2 web dashboard.

The dashboard binds to loopback by default and exposes only configured app
launch targets. It deliberately avoids shell command interpolation.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from cloud_ai_connector import CloudAIError
from osworld_bridge import OSWorldBridge
from studio import FNFOMNIStudioV2, STUDIO_NAME


@dataclass(frozen=True)
class AppSpec:
    app_id: str
    name: str
    role: str
    env_var: str
    candidates: tuple[str, ...]
    guide: str


APP_SPECS = (
    AppSpec(
        "psych-engine",
        "FNF Psych Engine",
        "Game executable / workspace",
        "FNF_PSYCH_ENGINE_PATH",
        ("PsychEngine", "psychengine", "FNF-PsychEngine"),
        "Set FNF_PSYCH_ENGINE_PATH to the executable or workspace directory.",
    ),
    AppSpec(
        "sprite-editor",
        "Krita / Aseprite",
        "Sprite & background editor",
        "FNF_SPRITE_EDITOR_PATH",
        ("krita", "aseprite"),
        "Set FNF_SPRITE_EDITOR_PATH to Krita or Aseprite.",
    ),
    AppSpec(
        "video-editor",
        "CapCut / Video Editor",
        "Video editor",
        "FNF_VIDEO_EDITOR_PATH",
        ("capcut",),
        "Set FNF_VIDEO_EDITOR_PATH to your local video editor executable.",
    ),
    AppSpec(
        "workspace",
        "Local Terminal",
        "Workspace folder",
        "FNF_WORKSPACE",
        (),
        "Set FNF_WORKSPACE to a project folder; launch opens a terminal there.",
    ),
)


class ConnectedApps:
    """Resolve configured desktop applications without accepting raw commands."""

    def __init__(self, specs=APP_SPECS) -> None:
        self.specs = specs
        self.active_app: Optional[str] = None

    def _resolve(self, spec: AppSpec) -> Optional[Path]:
        configured = os.getenv(spec.env_var)
        if configured:
            candidate = Path(configured).expanduser()
            if candidate.exists():
                return candidate
        for name in spec.candidates:
            executable = shutil.which(name)
            if executable:
                return Path(executable)
        return None

    def status(self) -> list[dict[str, Any]]:
        result = []
        for spec in self.specs:
            resolved = self._resolve(spec)
            is_workspace = spec.app_id == "workspace"
            connected = resolved is not None and (
                resolved.is_dir() if is_workspace else resolved.exists()
            )
            result.append(
                {
                    "id": spec.app_id,
                    "name": spec.name,
                    "role": spec.role,
                    "env_var": spec.env_var,
                    "connected": connected,
                    "target": str(resolved) if connected else None,
                    "guide": spec.guide,
                    "active": spec.app_id == self.active_app,
                }
            )
        return result

    def target(self, app_id: str) -> dict[str, Any]:
        self._spec(app_id)
        self.active_app = app_id
        return {"active_app": app_id, "apps": self.status()}

    def launch(self, app_id: str) -> dict[str, Any]:
        spec = self._spec(app_id)
        resolved = self._resolve(spec)
        if resolved is None:
            raise RuntimeError(
                f"{spec.name} is not connected; follow the {spec.env_var} setup guide"
            )
        if app_id == "workspace":
            terminal = shutil.which("x-terminal-emulator") or shutil.which("konsole")
            if terminal is None:
                raise RuntimeError("no supported terminal launcher found")
            process = subprocess.Popen([terminal], cwd=resolved)
        elif resolved.is_dir():
            process = subprocess.Popen(
                ["xdg-open", str(resolved)],
                cwd=resolved,
            )
        else:
            process = subprocess.Popen([str(resolved)], cwd=resolved.parent)
        self.active_app = app_id
        return {"app_id": app_id, "pid": process.pid, "target": str(resolved)}

    def _spec(self, app_id: str) -> AppSpec:
        for spec in self.specs:
            if spec.app_id == app_id:
                return spec
        raise KeyError(f"unknown app id: {app_id}")


class DashboardService:
    """Application API shared by HTTP handlers and tests."""

    def __init__(
        self,
        studio: Optional[FNFOMNIStudioV2] = None,
        apps: Optional[ConnectedApps] = None,
        bridge: Optional[OSWorldBridge] = None,
    ) -> None:
        self.studio = studio or FNFOMNIStudioV2()
        self.apps = apps or ConnectedApps()
        self.bridge = bridge or OSWorldBridge()

    def status(self) -> dict[str, Any]:
        return {
            "studio": self.studio.status(),
            "apps": self.apps.status(),
        }

    def chat(self, message: str) -> dict[str, Any]:
        prompt = message.strip()
        if not prompt:
            raise ValueError("message must not be empty")
        if prompt.lower() == "/status":
            return {"reply": json.dumps(self.status(), indent=2), "mode": "engine"}
        if prompt.lower() == "/connect":
            return {"reply": json.dumps(self.apps.status(), indent=2), "mode": "engine"}
        if prompt.lower().startswith("/target "):
            result = self.apps.target(prompt.split(maxsplit=1)[1])
            return {"reply": f"Targeted {result['active_app']}.", "mode": "engine"}
        if prompt.lower().startswith("/launch "):
            result = self.apps.launch(prompt.split(maxsplit=1)[1])
            return {
                "reply": f"Launched {result['app_id']} (PID {result['pid']}).",
                "mode": "engine",
            }
        try:
            reply = self.studio.ai.chat(prompt)
            return {"reply": reply, "mode": "ai", "target": self.apps.active_app}
        except CloudAIError:
            target = self.apps.active_app or "the selected app"
            return {
                "reply": (
                    "Free chat mode is ready for coding, design, FNF lore, "
                    "planning, and general questions. No local/free model is "
                    f"reachable right now, so I did not invent an answer. "
                    f"Current action target: {target}. Start Ollama or configure "
                    "HF_TOKEN to enable model-backed replies."
                ),
                "mode": "fallback",
                "target": self.apps.active_app,
            }

    def screenshot(self) -> dict[str, Any]:
        output = self.studio.config.output_dir / "dashboard-screenshot.png"
        self.bridge.screenshot(output)
        return {"path": str(output)}


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FNF-OMNI-STUDIO-V2</title>
<style>
:root{color-scheme:dark;--bg:#090b14;--panel:#121729;--line:#2a3457;--text:#e8edff;--muted:#929dbc;--cyan:#6fe7ff;--pink:#ff6fae;--green:#6ff0b0}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 80% 0,#222957 0,#090b14 43%);font:14px Inter,system-ui,sans-serif;color:var(--text)}
.shell{max-width:1240px;margin:auto;padding:28px}.top{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px}
h1{font-size:28px;margin:0}.eyebrow{color:var(--cyan);letter-spacing:.12em;font-size:11px;font-weight:700}
.tabs{display:flex;gap:8px;margin-bottom:18px}.tab,.button{border:1px solid var(--line);background:#151c32;color:var(--text);padding:10px 14px;border-radius:10px;cursor:pointer}.tab.active,.button.primary{background:linear-gradient(135deg,#244b70,#57305e);border-color:#6585bb}
.grid{display:grid;grid-template-columns:1.25fr .9fr;gap:18px}.panel{background:rgba(18,23,41,.88);border:1px solid var(--line);border-radius:16px;padding:18px;box-shadow:0 14px 42px #0003}
.panel h2{font-size:17px;margin:0 0 5px}.sub{color:var(--muted);margin:0 0 16px}.cards{display:grid;gap:10px}.card{border:1px solid var(--line);border-radius:13px;padding:14px;background:#10162a}.cardrow{display:flex;justify-content:space-between;gap:12px}.status{font-size:12px;color:var(--muted)}.status.ok{color:var(--green)}.status.off{color:#ff9a9a}
.actions{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap}.button.small{padding:7px 10px;font-size:12px}.chatlog{height:310px;overflow:auto;border:1px solid var(--line);border-radius:12px;padding:12px;background:#090d1b}.msg{margin:0 0 12px;white-space:pre-wrap;line-height:1.45}.msg b{color:var(--cyan)}textarea{width:100%;min-height:82px;resize:vertical;background:#0a0f20;border:1px solid var(--line);border-radius:12px;color:var(--text);padding:11px;margin-top:12px}
.pill{padding:5px 8px;border-radius:99px;background:#1e2940;color:var(--cyan);font-size:11px}.hidden{display:none}@media(max-width:850px){.grid{grid-template-columns:1fr}.shell{padding:16px}}
</style>
</head>
<body><main class="shell">
<header class="top"><div><div class="eyebrow">FNF AI VIDEO GENERATION & EDITING ENGINE</div><h1>FNF-OMNI-STUDIO-V2</h1></div><span id="target" class="pill">Target: none</span></header>
<nav class="tabs"><button class="tab active" data-tab="studio">Studio</button><button class="tab" data-tab="connect">Connect Your Apps</button></nav>
<section id="studio" class="grid">
<div class="panel"><h2>Free unrestricted AI chat mode</h2><p class="sub">Ask about code, design, FNF lore, planning, or engine operations. Slash commands execute local tasks.</p><div id="chatlog" class="chatlog"><p class="msg"><b>Studio:</b> Ready. Try /status, /connect, /target psych-engine, or ask any general question.</p></div><textarea id="prompt" placeholder="Ask anything or type an engine command..."></textarea><div class="actions"><button class="button primary" id="send">Send message</button><button class="button" id="shot">Capture desktop</button></div></div>
<div class="panel"><h2>Engine status</h2><p class="sub">Local runtime and active computer-use target.</p><div id="status"></div></div>
</section>
<section id="connect" class="panel hidden"><h2>Connect Your Apps</h2><p class="sub">Configure paths locally, then target or launch an app through the human-like cursor and computer-use pipeline.</p><div id="apps" class="cards"></div></section>
</main>
<script>
const $=s=>document.querySelector(s), esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
async function api(path,opts={}){let r=await fetch(path,{headers:{'Content-Type':'application/json'},...opts});let d=await r.json();if(!r.ok)throw Error(d.error||'Request failed');return d}
function renderStatus(d){$('#status').innerHTML='<pre>'+esc(JSON.stringify(d.studio,null,2))+'</pre>';$('#target').textContent='Target: '+(d.apps.find(a=>a.active)?.name||'none')}
function renderApps(apps){$('#apps').innerHTML=apps.map(a=>`<article class="card"><div class="cardrow"><div><strong>${esc(a.name)}</strong><div class="status">${esc(a.role)}</div></div><span class="status ${a.connected?'ok':'off'}">${a.connected?'Connected':'Not connected'}</span></div><p class="status">${esc(a.guide)}</p>${a.target?`<div class="status">Target: ${esc(a.target)}</div>`:''}<div class="actions"><button class="button small" onclick="targetApp('${a.id}')">Target</button><button class="button small" onclick="launchApp('${a.id}')">Launch</button></div></article>`).join('')}
async function refresh(){let d=await api('/api/status');renderStatus(d);renderApps(d.apps)}
async function targetApp(id){try{let d=await api('/api/apps/target',{method:'POST',body:JSON.stringify({app_id:id})});renderApps(d.apps);$('#target').textContent='Target: '+id;add('System','Targeted '+id)}catch(e){add('System',e.message)}}
async function launchApp(id){try{let d=await api('/api/apps/launch',{method:'POST',body:JSON.stringify({app_id:id})});add('System',`Launched ${id} (PID ${d.pid})`);refresh()}catch(e){add('System',e.message)}}
function add(who,text){$('#chatlog').innerHTML+=`<p class="msg"><b>${esc(who)}:</b> ${esc(text)}</p>`;$('#chatlog').scrollTop=999999}
async function send(){let p=$('#prompt').value.trim();if(!p)return;add('You',p);$('#prompt').value='';try{let d=await api('/api/chat',{method:'POST',body:JSON.stringify({message:p})});add('Studio',d.reply);refresh()}catch(e){add('Studio',e.message)}}
document.querySelectorAll('.tab').forEach(b=>b.onclick=()=>{document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));b.classList.add('active');document.querySelectorAll('section[id]').forEach(s=>s.classList.toggle('hidden',s.id!==b.dataset.tab));if(b.dataset.tab==='connect')refresh()});
$('#send').onclick=send;$('#prompt').addEventListener('keydown',e=>{if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)){e.preventDefault();send()}});$('#shot').onclick=async()=>{try{let d=await api('/api/screenshot',{method:'POST'});add('System','Desktop screenshot saved to '+d.path)}catch(e){add('System',e.message)}};refresh();
</script></body></html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    service: DashboardService

    def _json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict[str, Any]:
        size = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(size) or b"{}")

    def do_GET(self) -> None:
        if urlparse(self.path).path == "/api/status":
            self._json(self.service.status())
            return
        if urlparse(self.path).path == "/":
            body = INDEX_HTML.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            body = self._body()
            if path == "/api/chat":
                self._json(self.service.chat(str(body.get("message", ""))))
            elif path == "/api/apps/target":
                self._json(self.service.apps.target(str(body["app_id"])))
            elif path == "/api/apps/launch":
                self._json(self.service.apps.launch(str(body["app_id"])))
            elif path == "/api/screenshot":
                self._json(self.service.screenshot())
            else:
                self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        except (KeyError, ValueError, RuntimeError, CloudAIError) as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def log_message(self, _format: str, *_args: Any) -> None:
        return


def create_dashboard_server(
    service: Optional[DashboardService] = None,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> ThreadingHTTPServer:
    selected = service or DashboardService()

    class BoundHandler(DashboardHandler):
        pass

    BoundHandler.service = selected
    return ThreadingHTTPServer((host, port), BoundHandler)


def run_dashboard(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = create_dashboard_server(host=host, port=port)
    print(f"{STUDIO_NAME} dashboard: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

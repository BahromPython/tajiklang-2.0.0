"""TajikBlocks — a small local visual editor for TajikLang.

It has no account, cloud service, or JavaScript package dependency.  The
standalone TajikLang application starts it on ``127.0.0.1`` and opens a browser;
blocks generate ordinary, editable TajikLang source and the same interpreter
runs that source through a local JSON endpoint.
"""

from __future__ import annotations

import json
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from . import CheckFailed, run_source
from .errors import TajikLangError


def run_blocks_source(source: str, base_dir: Path | None = None) -> dict[str, str]:
    """Run visual-editor code and return student-facing output only."""
    lines: list[str] = []
    try:
        run_source(source, output=lines.append, base_dir=base_dir, check=True)
        return {"output": "\n".join(lines), "error": ""}
    except CheckFailed as error:
        return {"output": "", "error": error.format()}
    except TajikLangError as error:
        return {"output": "", "error": error.format()}


class BlocksHandler(BaseHTTPRequestHandler):
    """Only two routes: the editor and a same-machine run endpoint."""

    server_version = "TajikBlocks"
    sys_version = ""

    def log_message(self, _format: str, *_args: object) -> None:
        pass  # A student's terminal should not fill with browser access logs.

    def _send_json(self, value: dict[str, str], status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if urlparse(self.path).path not in ("/", "/index.html"):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        payload = BLOCKS_HTML.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if urlparse(self.path).path != "/api/run":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        length = int(self.headers.get("Content-Length", "0"))
        if length > 200_000:
            self._send_json({"output": "", "error": "Барнома аз ҳад калон аст."}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            return
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            source = data["source"]
            if not isinstance(source, str):
                raise ValueError
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, ValueError):
            self._send_json({"output": "", "error": "Рамзи қабулшуда дуруст нест."}, HTTPStatus.BAD_REQUEST)
            return
        self._send_json(run_blocks_source(source, Path.cwd()))


def _serve(server: ThreadingHTTPServer, title: str, open_browser: bool) -> None:
    host, port = server.server_address[:2]
    address = f"http://{host}:{port}/"
    print(f"{title}: {address}")
    print("Барои қатъ кардан Ctrl+C-ро пахш кунед.")
    if open_browser:
        webbrowser.open(address)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер қатъ шуд.")
    finally:
        server.server_close()


def start_blocks(port: int = 8000, open_browser: bool = True) -> None:
    """Open the local TajikBlocks editor; the server never faces the network."""
    server = ThreadingHTTPServer(("127.0.0.1", port), BlocksHandler)
    _serve(server, "TajikBlocks омода аст", open_browser)


def start_preview(folder: Path, port: int = 8000, open_browser: bool = True) -> None:
    """Serve a built static TajikWeb directory on the local machine only."""
    if not folder.is_dir():
        raise FileNotFoundError(folder)

    class PreviewHandler(SimpleHTTPRequestHandler):
        def log_message(self, _format: str, *_args: object) -> None:
            pass

    handler: Callable[..., BaseHTTPRequestHandler] = lambda *args, **kwargs: PreviewHandler(
        *args, directory=str(folder), **kwargs
    )
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    _serve(server, "Пешнамоиши сомона омода аст", open_browser)


def start_in_thread(port: int = 0) -> tuple[ThreadingHTTPServer, threading.Thread]:
    """Test helper: run a local blocks server without opening a browser."""
    server = ThreadingHTTPServer(("127.0.0.1", port), BlocksHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


BLOCKS_HTML = r'''<!doctype html>
<html lang="tg" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TajikBlocks — барномасозии визуалӣ</title>
<style>
  :root { color-scheme: dark; --bg:#101622; --panel:#182131; --card:#222e43;
    --line:#344560; --ink:#eef5ff; --soft:#aebed4; --mint:#4de0ac; --violet:#ae8cff;
    --amber:#ffca72; --blue:#66b7ff; --red:#ff8c9b; }
  * { box-sizing:border-box } body { margin:0; min-height:100vh; font:16px/1.5 system-ui,Segoe UI,Tahoma,sans-serif; color:var(--ink); background:radial-gradient(circle at 82% -20%,#31466d 0,transparent 32rem),var(--bg); }
  header { display:flex; align-items:center; justify-content:space-between; gap:16px; padding:18px 24px; border-bottom:1px solid var(--line); background:#121a28d9; backdrop-filter:blur(12px); position:sticky; top:0; z-index:5; }
  .brand { display:flex; align-items:center; gap:12px; font-weight:800; font-size:1.25rem; letter-spacing:.01em }.mark { display:grid; place-items:center; width:38px; height:38px; border-radius:12px; color:#102117; background:linear-gradient(135deg,var(--mint),#7ee7ff); font-size:21px }.tag { color:var(--soft); font-size:.9rem; font-weight:400 }
  button { font:inherit; color:inherit; border:1px solid var(--line); border-radius:10px; padding:9px 13px; background:#26354e; cursor:pointer; transition:transform .15s ease, background .15s ease; } button:hover { transform:translateY(-1px); background:#30425f } button:focus-visible,input:focus-visible,textarea:focus-visible { outline:3px solid #66b7ff99; outline-offset:2px } .run { background:linear-gradient(135deg,#2fcf91,#57e6b5); border:0; color:#092319; font-weight:800 }.run:hover { background:linear-gradient(135deg,#45e9a8,#75f0c9) }
  main { display:grid; grid-template-columns:250px minmax(300px,1fr) minmax(280px,.8fr); gap:16px; padding:16px; max-width:1600px; margin:auto } .panel { background:#172132d9; border:1px solid var(--line); border-radius:16px; overflow:hidden; min-height:calc(100vh - 106px) }.head { padding:13px 16px; border-bottom:1px solid var(--line); font-weight:750; color:#dcecff }.hint { padding:0 16px 12px; color:var(--soft); font-size:.86rem }
  .palette { padding:12px; display:grid; gap:9px }.palette button { text-align:right; font-weight:700; border-right:5px solid var(--blue) }.palette button[data-type="var"] { border-color:var(--mint) }.palette button[data-type="if"] { border-color:var(--amber) }.palette button[data-type="loop"] { border-color:var(--violet) }.palette button[data-type="raw"] { border-color:var(--red) }
  #workspace { min-height:420px; padding:16px; display:grid; align-content:start; gap:10px; background:linear-gradient(90deg,#ffffff05 1px,transparent 1px),linear-gradient(#ffffff05 1px,transparent 1px); background-size:24px 24px }.empty { color:var(--soft); text-align:center; padding:70px 15px; border:1px dashed var(--line); border-radius:14px }
  .block { display:grid; grid-template-columns:26px 1fr auto; align-items:center; gap:9px; border-radius:12px; border:1px solid #4979aa; border-right:6px solid var(--blue); background:linear-gradient(100deg,#213d5b,#1d2a40); padding:10px; cursor:grab; box-shadow:0 7px 18px #0002 }.block.var { border-right-color:var(--mint); background:linear-gradient(100deg,#1e4b42,#1c2e3b) }.block.if { border-right-color:var(--amber); background:linear-gradient(100deg,#55432a,#2e2c35) }.block.loop { border-right-color:var(--violet); background:linear-gradient(100deg,#433467,#2d2b43) }.block.raw { border-right-color:var(--red); background:linear-gradient(100deg,#5b3440,#342a39) }.handle { color:#d2ddeb; cursor:grab }.block label { display:grid; grid-template-columns:auto minmax(70px,1fr); align-items:center; gap:7px; font-size:.9rem }.fields { display:flex; flex-wrap:wrap; gap:8px }.remove { padding:4px 8px; color:#ffd9de; background:transparent; border-color:#ffffff33 } input,textarea { min-width:0; border:1px solid #547094; border-radius:7px; background:#101927; color:var(--ink); padding:6px 8px; font:inherit } input { width:130px } textarea { width:100%; min-height:82px; resize:vertical; direction:ltr; text-align:left }
  .right { display:flex; flex-direction:column }.code-wrap,.output-wrap { padding:12px; display:flex; flex-direction:column; gap:8px }.code-wrap { flex:1; border-bottom:1px solid var(--line) } #code { flex:1; min-height:250px; color:#d5e9ff; background:#0d1522 }.output { min-height:150px; max-height:280px; overflow:auto; white-space:pre-wrap; direction:ltr; text-align:left; padding:11px; border:1px solid var(--line); border-radius:9px; background:#0d1522; color:#c7f7df }.output.error { color:#ffd1d7; border-color:#a24c5c }.mini { display:flex; gap:8px; justify-content:flex-end }.status { color:var(--soft); font-size:.86rem; min-height:1.4em }
  @media(max-width:980px) { main { grid-template-columns:220px 1fr }.right { grid-column:1/-1; min-height:450px }.panel { min-height:auto } } @media(max-width:650px) { header { padding:12px 14px }.tag { display:none } main { grid-template-columns:1fr; padding:10px }.palette { grid-template-columns:1fr 1fr }.right { grid-column:auto }.block { grid-template-columns:20px 1fr auto } }
</style>
</head>
<body>
<header><div class="brand"><span class="mark">◫</span><span>TajikBlocks <span class="tag">барномасозии визуалӣ бо забони тоҷикӣ</span></span></div><div class="mini"><button id="save">Нигоҳ доштан</button><button id="open">Кушодан</button><button class="run" id="run">▶ Иҷро</button></div></header>
<main>
  <aside class="panel"><div class="head">Блокҳоро интихоб кунед</div><div class="hint">Блокро пахш кунед, баъд онро бо муш ҷобаҷо кунед.</div><div class="palette">
    <button data-type="print">🗨️ Навис</button><button data-type="var">✦ Тағйирёбанда</button><button data-type="if">◆ Агар</button><button data-type="loop">↻ Давр</button><button data-type="function">ƒ Функсия</button><button data-type="raw">⌨️ Рамзи ман</button>
  </div></aside>
  <section class="panel"><div class="head">Майдони барнома</div><div id="workspace"><div class="empty">Аз тарафи рост як блок интихоб кунед.<br>Рамз дар панел худкор пайдо мешавад.</div></div></section>
  <section class="panel right"><div class="head">Рамзи TajikLang</div><div class="code-wrap"><textarea id="code" spellcheck="false" aria-label="Рамзи TajikLang"></textarea><div class="mini"><button id="copy">Нусха кардан</button><button id="reset">Аз нав</button></div></div><div class="output-wrap"><strong>Тағйирёбандаҳо</strong><div id="variables" class="status">Ҳоло тағйирёбанда нест.</div><strong>Натиҷа</strong><div id="status" class="status">Омода</div><pre id="output" class="output">Натиҷаи барнома ин ҷо мебарояд.</pre></div></section>
</main>
<script>
const blocks=[], workspace=document.querySelector('#workspace'), code=document.querySelector('#code'), output=document.querySelector('#output'), status=document.querySelector('#status'), variables=document.querySelector('#variables'); let dragging=null;
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const id=()=>Math.random().toString(36).slice(2);
function add(type){ const defaults={print:{text:'Салом Тоҷикистон!'},var:{name:'ном',value:'"Баҳром"'},if:{condition:'рост',text:'Шарт иҷро шуд'},loop:{start:'1',end:'5',text:'Рақам:'},function:{name:'салом',body:'навис("Салом")'},raw:{text:'# Рамзи худро ин ҷо нависед'}}; blocks.push({id:id(),type,...defaults[type]}); render(); }
function source(b){ if(b.type==='print')return `навис(${JSON.stringify(b.text)})`; if(b.type==='var')return `бигзор ${b.name||'ном'} = ${b.value||'0'}`; if(b.type==='if')return `агар ${b.condition||'рост'}:\n    навис(${JSON.stringify(b.text)})`; if(b.type==='loop')return `барои i аз ${b.start||'1'} то ${b.end||'5'}:\n    навис(${JSON.stringify(b.text)}, i)`; if(b.type==='function')return `функсия ${b.name||'салом'}():\n`+(b.body||'навис("Салом")').split('\n').map(line=>'    '+line).join('\n'); return b.text||''; }
function makeCode(){ return blocks.map(source).join('\n\n'); }
function field(label,key,value,large=false){return large?`<label>${label}<textarea data-key="${key}">${esc(value)}</textarea></label>`:`<label>${label}<input data-key="${key}"></label>`}
function render(){ workspace.innerHTML=''; if(!blocks.length){workspace.innerHTML='<div class="empty">Аз тарафи рост як блок интихоб кунед.<br>Рамз дар панел худкор пайдо мешавад.</div>'} blocks.forEach((b,index)=>{const el=document.createElement('article');el.className='block '+b.type;el.draggable=true;let fields=b.type==='print'?field('Матн','text',b.text):b.type==='var'?field('Ном','name',b.name)+field('Қимат','value',b.value):b.type==='if'?field('Шарт','condition',b.condition)+field('Агар рост бошад, навис','text',b.text):b.type==='loop'?field('Аз','start',b.start)+field('То','end',b.end)+field('Навис','text',b.text):b.type==='function'?field('Ном','name',b.name)+field('Бадани функсия','body',b.body,true):field('Рамзи TajikLang','text',b.text,true);el.innerHTML=`<span class="handle">⠿</span><div class="fields">${fields}</div><button class="remove" title="Нест кардан">×</button>`;el.querySelectorAll('input,textarea').forEach(input=>{input.value=b[input.dataset.key];input.addEventListener('input',()=>{b[input.dataset.key]=input.value;code.value=makeCode();showVariables()})});el.querySelector('.remove').onclick=()=>{blocks.splice(index,1);render()};el.addEventListener('dragstart',()=>dragging=index);el.addEventListener('dragover',e=>e.preventDefault());el.addEventListener('drop',e=>{e.preventDefault();if(dragging===null||dragging===index)return;const [moved]=blocks.splice(dragging,1);blocks.splice(index,0,moved);dragging=null;render()});workspace.appendChild(el)});code.value=makeCode();showVariables(); }
function showVariables(){const found=blocks.filter(b=>b.type==='var').map(b=>`${b.name||'ном'} = ${b.value||'0'}`);variables.textContent=found.length?found.join(' · '):'Ҳоло тағйирёбанда нест.'}
document.querySelectorAll('[data-type]').forEach(button=>button.onclick=()=>add(button.dataset.type)); code.addEventListener('input',()=>{ status.textContent='Рамз дастӣ тағйир ёфт — метавонед онро иҷро кунед.'}); document.querySelector('#reset').onclick=()=>{blocks.length=0;output.textContent='Натиҷаи барнома ин ҷо мебарояд.';output.className='output';status.textContent='Омода';render()};document.querySelector('#copy').onclick=async()=>{await navigator.clipboard.writeText(code.value);status.textContent='Рамз нусха шуд.'};document.querySelector('#save').onclick=()=>{localStorage.setItem('tajikblocks-project',JSON.stringify(blocks));status.textContent='Лоиҳаи блокҳо нигоҳ дошта шуд.'};document.querySelector('#open').onclick=()=>{try{const saved=JSON.parse(localStorage.getItem('tajikblocks-project')||'[]');blocks.splice(0,blocks.length,...saved);render();status.textContent='Лоиҳа кушода шуд.'}catch(_){status.textContent='Лоиҳаи нигоҳдошташуда хонда нашуд.'}};
document.querySelector('#run').onclick=async()=>{status.textContent='Иҷро шуда истодааст…';output.className='output';try{const res=await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source:code.value})});const result=await res.json();if(result.error){output.textContent=result.error;output.className='output error';status.textContent='Хато ёфт шуд.'}else{output.textContent=result.output||'Барнома чизе нанавишт.';status.textContent='Барнома иҷро шуд.'}}catch(_){output.textContent='Ба муҳаррики маҳаллӣ пайваст нашуд.';output.className='output error';status.textContent='Хато'}};
render();
</script></body></html>'''

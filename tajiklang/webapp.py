"""TajikWeb App — interactive TajikLang pages on localhost.

Static TajikWeb sites are ideal for GitHub Pages.  A page with buttons and
forms needs a live interpreter, so this runner keeps one interpreter in memory
and exposes it only on 127.0.0.1.  The browser never receives Python code or a
network-facing server.
"""

from __future__ import annotations

import json
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .errors import TajikLangError
from .interpreter import Interpreter
from .lexer import Lexer
from .parser import Parser


class AppError(Exception):
    pass


class WebApp:
    def __init__(self, source_path: Path) -> None:
        self.source_path = source_path
        self.output: list[str] = []
        source = source_path.read_text(encoding="utf-8")
        lexer = Lexer(source, str(source_path))
        program = Parser(lexer.tokenize(), lexer.lines).parse()
        self.interpreter = Interpreter(lexer.lines, self.output.append, base_dir=source_path.parent)
        try:
            self.interpreter.run(program)
        except TajikLangError as error:
            raise AppError(error.format()) from error
        if not hasattr(self.interpreter, "page_html"):
            raise AppError("Дар барнома «ворид саҳифа» ва «саҳифа.нависед(...)» лозим аст.")

    def page(self) -> str:
        html = self.interpreter.page_html()
        script = """<script>
async function tajikAction(name) {
  const response = await fetch('/амал/' + encodeURIComponent(name), {method:'POST'});
  const data = await response.json();
  if (data.error) { alert(data.error); return; }
  document.open(); document.write(data.html); document.close();
}
document.querySelectorAll('[data-tajik-action]').forEach(button => {
  button.addEventListener('click', () => tajikAction(button.dataset.tajikAction));
});
</script>"""
        return html.replace("</body>", script + "</body>")

    def action(self, name: str) -> str:
        handler = getattr(self.interpreter, "page_actions", {}).get(name)
        if handler is None:
            raise AppError("Ин амал дар саҳифа нест.")
        try:
            self.interpreter.call_from_host(handler, [])
        except TajikLangError as error:
            raise AppError(error.format()) from error
        return self.page()


def make_handler(app: WebApp):
    class Handler(BaseHTTPRequestHandler):
        server_version = "TajikWeb"
        sys_version = ""

        def log_message(self, _format: str, *_args: object) -> None:
            pass

        def _json(self, data: dict[str, str], status: HTTPStatus = HTTPStatus.OK) -> None:
            payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:  # noqa: N802
            if urlparse(self.path).path != "/":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            payload = app.page().encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self) -> None:  # noqa: N802
            prefix = "/амал/"
            path = urlparse(self.path).path
            if not path.startswith(prefix):
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            try:
                self._json({"html": app.action(path[len(prefix):]), "error": ""})
            except AppError as error:
                self._json({"html": "", "error": str(error)}, HTTPStatus.BAD_REQUEST)

    return Handler


def start(source_path: Path, port: int = 8010, open_browser: bool = True) -> None:
    app = WebApp(source_path)
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(app))
    address = f"http://127.0.0.1:{port}/"
    print(f"TajikWeb App омода аст: {address}")
    print("Барои қатъ кардан Ctrl+C-ро пахш кунед.")
    if open_browser:
        webbrowser.open(address)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер қатъ шуд.")
    finally:
        server.server_close()

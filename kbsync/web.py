"""Tiny local chat UI for the support bot: `python -m kbsync.web` then open http://127.0.0.1:8080.

Same retrieval and system prompt as `kbsync.ask`. The API key stays on the server and the
server binds to localhost only, so this is a test harness, not a public endpoint.
"""

from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from kbsync.ask import Reply, ask, format_reply
from kbsync.config import Config
from kbsync.log import configure_logging

log = logging.getLogger(__name__)

MAX_QUESTION_CHARS = 500
MAX_BODY_BYTES = 4096

PAGE = """<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Support bot</title>
<style>
  :root{color-scheme:light dark;--bg:#f6f7f9;--card:#fff;--ink:#1c2230;--muted:#6b7385;--line:#e2e5ec;--accent:#2f6fed}
  @media(prefers-color-scheme:dark){:root{--bg:#12151c;--card:#1b2030;--ink:#e8ebf2;--muted:#9097a8;--line:#2a3042;--accent:#6b9bff}}
  body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,sans-serif}
  main{max-width:760px;margin:0 auto;padding:24px 16px 120px}
  h1{font-size:18px;margin:0 0 4px} .sub{color:var(--muted);margin:0 0 20px;font-size:13px}
  .msg{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 16px;margin:12px 0}
  .q{border-left:3px solid var(--accent)} .msg ul{margin:8px 0;padding-left:20px}
  .src{margin-top:10px;font-size:13px;color:var(--muted)} .src a{color:var(--accent);word-break:break-all}
  .err{border-color:#d33;color:#d33}
  form{position:fixed;left:0;right:0;bottom:0;background:var(--bg);border-top:1px solid var(--line);padding:12px 16px}
  .row{max-width:760px;margin:0 auto;display:flex;gap:8px}
  input{flex:1;padding:10px 12px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--ink);font:inherit}
  button{padding:10px 18px;border:0;border-radius:8px;background:var(--accent);color:#fff;font:inherit;cursor:pointer}
  button:disabled{opacity:.5;cursor:wait}
</style>
<main>
  <h1>Support bot</h1>
  <p class="sub">Answers only from the synced support articles. Up to 5 bullets, up to 3 article URLs.</p>
  <div id="log"></div>
</main>
<form id="f"><div class="row">
  <input id="q" maxlength="500" placeholder="e.g. How do I add a YouTube video?" autocomplete="off" autofocus>
  <button id="go">Ask</button>
</div></form>
<script>
const logEl = document.getElementById("log"), q = document.getElementById("q"), go = document.getElementById("go");
const esc = s => s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
const inline = s => esc(s).replace(/\\*\\*(.+?)\\*\\*/g,"<strong>$1</strong>")
  .replace(/\\[([^\\]]+)\\]\\((https?:\\/\\/[^)\\s]+)\\)/g,'<a href="$2" target="_blank" rel="noopener">$1</a>')
  .replace(/(^|[^"'>])(https?:\\/\\/[^\\s<]+)/g,'$1<a href="$2" target="_blank" rel="noopener">$2</a>');
function render(text){            // bullets -> <ul>, everything else -> paragraphs; input is escaped first
  let html = "", open = false;
  for (const line of text.split("\\n")) {
    const m = line.match(/^\\s*[*-]\\s+(.*)$/);
    if (m) { if (!open) { html += "<ul>"; open = true; } html += "<li>" + inline(m[1]) + "</li>"; continue; }
    if (open) { html += "</ul>"; open = false; }
    if (line.trim()) html += "<p>" + inline(line) + "</p>";
  }
  return html + (open ? "</ul>" : "");
}
function add(cls, html){ const d = document.createElement("div"); d.className = "msg " + cls; d.innerHTML = html;
  logEl.appendChild(d); d.scrollIntoView({block:"end"}); return d; }
document.getElementById("f").addEventListener("submit", async e => {
  e.preventDefault();
  const question = q.value.trim(); if (!question) return;
  q.value = ""; go.disabled = true; add("q", "<strong>" + esc(question) + "</strong>");
  const wait = add("", "<em>Searching the articles...</em>");
  try {
    const r = await fetch("/api/ask", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({question})});
    const data = await r.json();
    wait.remove();
    if (!r.ok) { add("err", esc(data.error || "Request failed")); return; }
    const src = data.sources.length ? '<div class="src">Retrieved from: ' + data.sources.map(s =>
      '<a href="' + esc(s.url) + '" target="_blank" rel="noopener">' + esc(s.title) + "</a>").join(" | ") + "</div>" : "";
    add("", render(data.text) + src);
  } catch (err) { wait.remove(); add("err", "Network error: " + esc(String(err))); }
  finally { go.disabled = false; q.focus(); }
});
</script>
</html>
"""


def answer_payload(raw_body: bytes, ask_fn: Callable[[str], Reply]) -> tuple[int, dict]:
    """Validate a POST /api/ask body and shape the JSON response; returns (status, body)."""
    try:
        data = json.loads(raw_body or b"{}")
        question = str(data.get("question", "")).strip() if isinstance(data, dict) else ""
    except (ValueError, UnicodeDecodeError):
        return 400, {"error": "body must be JSON like {\"question\": \"...\"}"}
    if not question:
        return 400, {"error": "question is required"}
    if len(question) > MAX_QUESTION_CHARS:
        return 400, {"error": f"question is longer than {MAX_QUESTION_CHARS} characters"}
    try:
        reply = ask_fn(question)
    except Exception:
        log.exception("ask failed")
        return 502, {"error": "the model request failed; please try again"}
    return 200, {"text": format_reply(reply), "sources": [{"title": s.title, "url": s.url} for s in reply.sources]}


def make_server(host: str, port: int, ask_fn: Callable[[str], Reply]) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 (http.server API)
            if self.path in ("/", "/index.html"):
                self._send(200, PAGE.encode(), "text/html; charset=utf-8")
            else:
                self._send(404, b'{"error":"not found"}', "application/json")

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/api/ask":
                self._send(404, b'{"error":"not found"}', "application/json")
                return
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY_BYTES:
                self._send(413, b'{"error":"body too large"}', "application/json")
                return
            status, payload = answer_payload(self.rfile.read(length), ask_fn)
            self._send(status, json.dumps(payload).encode(), "application/json")

        def log_message(self, fmt: str, *args) -> None:
            log.info("http " + fmt, *args)

    return ThreadingHTTPServer((host, port), Handler)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    config = Config.from_env()
    configure_logging(config.log_level)
    config.require_gemini()

    from kbsync.gemini_store import ensure_store, make_client
    from kbsync.job import STORE_DISPLAY_NAME

    client = make_client(config.gemini_api_key)
    store = ensure_store(client, config.gemini_file_search_store, STORE_DISPLAY_NAME)
    server = make_server(args.host, args.port, lambda question: ask(client, config.gemini_model, store, question))
    log.info("serving on http://%s:%d (store %s, model %s)", args.host, args.port, store, config.gemini_model)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()

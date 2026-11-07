"""Tiny local chat UI for the support bot: `python -m kbsync.web` then open http://127.0.0.1:8080.

Same retrieval and system prompt as `kbsync.ask`. The API key stays on the server and the
server binds to localhost only, so this is a test harness, not a public endpoint.

POST /api/ask {"question": "..."} streams newline-delimited JSON (application/x-ndjson), one
object per line, flushed as it is produced:

    {"type": "delta", "text": "<incremental provider text>"}          (zero or more)
    {"type": "done", "text": "<full reply with Article URL lines>", "sources": [{"title", "url"}]}
    {"type": "error", "error": "<sanitized message>"}                  (instead of done)

Exactly one terminal event ends a well-formed stream. Bad input is a 400 and a provider failure
before any text a 502, both as JSON `{"error": ...}`; neither is ever followed by a stream.
"""

from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Callable, Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from kbsync.ask import Delta, StreamEvent, ask_stream, format_reply
from kbsync.config import Config
from kbsync.log import configure_logging

log = logging.getLogger(__name__)

MAX_QUESTION_CHARS = 500
MAX_BODY_BYTES = 4096
CHAT_PAGE_PATH = Path(__file__).with_name("chat.html")

MODEL_FAILED = "the model request failed; please try again"
STREAM_ENDED = "the answer ended unexpectedly; please try again"

StreamFn = Callable[[str], Iterator[StreamEvent]]


class InvalidQuestion(ValueError):
    """The request body is not a usable question; the message is safe to show the user."""


def parse_question(raw_body: bytes) -> str:
    """Validate a POST /api/ask body and return the trimmed question."""
    try:
        data = json.loads(raw_body or b"{}")
    except ValueError:  # includes UnicodeDecodeError
        data = None
    if not isinstance(data, dict):
        raise InvalidQuestion('body must be a JSON object like {"question": "..."}')
    question = data.get("question", "")
    if not isinstance(question, str):
        raise InvalidQuestion("question must be a string")
    question = question.strip()
    if not question:
        raise InvalidQuestion("question is required")
    if len(question) > MAX_QUESTION_CHARS:
        raise InvalidQuestion(f"question is longer than {MAX_QUESTION_CHARS} characters")
    return question


def wire_event(event: StreamEvent) -> dict:
    if isinstance(event, Delta):
        return {"type": "delta", "text": event.text}
    return {
        "type": "done",
        "text": format_reply(event.reply),
        "sources": [{"title": s.title, "url": s.url} for s in event.reply.sources],
    }


def _error_event(message: str) -> dict:
    return {"type": "error", "error": message}


def _log_failure(where: str, exc: Exception) -> None:
    # Class and HTTP-style code only: provider messages and tracebacks may echo request details.
    log.error("ask failed %s: %s code=%s", where, type(exc).__name__, getattr(exc, "code", None))


def make_server(host: str, port: int, stream_fn: StreamFn) -> ThreadingHTTPServer:
    page = CHAT_PAGE_PATH.read_bytes()  # read once at startup; a missing file fails fast

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _send_error(self, status: int, message: str) -> None:
            self._send(status, json.dumps({"error": message}).encode(), "application/json")

        def _write_event(self, event: dict) -> None:
            self.wfile.write(json.dumps(event, ensure_ascii=False).encode("utf-8") + b"\n")
            self.wfile.flush()

        def _pump(self, first: StreamEvent, stream: Iterator[StreamEvent]) -> None:
            """Relay events until exactly one terminal event has been written."""
            event = first
            while True:
                wire = wire_event(event)
                self._write_event(wire)
                if wire["type"] == "done":
                    return
                try:
                    event = next(stream)
                except StopIteration:
                    self._write_event(_error_event(STREAM_ENDED))
                    return
                except Exception as exc:
                    _log_failure("mid-stream", exc)
                    self._write_event(_error_event(MODEL_FAILED))
                    return

        def do_GET(self) -> None:  # noqa: N802 (http.server API)
            if self.path in ("/", "/index.html"):
                self._send(200, page, "text/html; charset=utf-8")
            else:
                self._send_error(404, "not found")

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/api/ask":
                self._send_error(404, "not found")
                return
            try:
                length = int(self.headers.get("Content-Length") or 0)
                if length < 0:
                    raise ValueError
            except ValueError:
                self._send_error(400, "invalid Content-Length")
                return
            if length > MAX_BODY_BYTES:
                self._send_error(413, "body too large")
                return
            try:
                question = parse_question(self.rfile.read(length))
            except InvalidQuestion as exc:
                self._send_error(400, str(exc))
                return

            # Pull the first event before committing to HTTP 200 so a provider that fails
            # immediately (bad key, quota, network) is reported as a real error status.
            try:
                stream = iter(stream_fn(question))
                first = next(stream, None)
            except Exception as exc:
                _log_failure("before stream", exc)
                self._send_error(502, MODEL_FAILED)
                return
            if first is None:
                log.error("ask failed before stream: provider returned no events")
                self._send_error(502, MODEL_FAILED)
                return

            # No Content-Length: the body is delimited by closing the connection.
            self.close_connection = True
            try:
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson")
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Accel-Buffering", "no")
                self.send_header("Connection", "close")
                self.end_headers()
                self._pump(first, stream)
            except OSError:
                log.info("client disconnected mid-stream")
            finally:
                close = getattr(stream, "close", None)
                if close is not None:
                    close()  # releases the provider connection if the stream is unfinished

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
    server = make_server(args.host, args.port, lambda question: ask_stream(client, config.gemini_model, store, question))
    log.info("serving on http://%s:%d (store %s, model %s)", args.host, args.port, store, config.gemini_model)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()

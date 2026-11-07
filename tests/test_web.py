import http.client
import json
import threading
from contextlib import contextmanager

import pytest

from kbsync.ask import Delta, Done, Reply, Source
from kbsync.web import MAX_QUESTION_CHARS, make_server

TIMEOUT_S = 5  # barrier / socket timeout: a regression fails fast instead of hanging


@contextmanager
def _serve(stream_fn):
    server = make_server("127.0.0.1", 0, stream_fn)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()


def _post(port: int, raw: bytes) -> tuple[http.client.HTTPConnection, http.client.HTTPResponse]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=TIMEOUT_S)
    conn.request("POST", "/api/ask", body=raw, headers={"Content-Type": "application/json"})
    return conn, conn.getresponse()


def _body(**fields) -> bytes:
    return json.dumps(fields).encode()


def _read_events(response: http.client.HTTPResponse) -> list[dict]:
    return [json.loads(line) for line in response.read().decode().splitlines()]


def test_unknown_route_is_a_404():
    with _serve(lambda q: iter([])) as port:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=TIMEOUT_S)
        conn.request("GET", "/missing")
        assert conn.getresponse().status == 404


def test_early_delta_reaches_the_client_before_the_producer_finishes():
    release = threading.Event()

    def stream(question):
        yield Delta("Hello ")
        assert release.wait(TIMEOUT_S)  # the final events cannot exist until the client has seen the delta
        yield Delta("world")
        yield Done(Reply("Hello world", [Source("Doc", "https://h/1")]))

    with _serve(stream) as port:
        conn, response = _post(port, _body(question="hi"))
        assert response.status == 200
        assert response.getheader("Content-Type") == "application/x-ndjson"
        assert response.getheader("Content-Length") is None

        assert json.loads(response.readline()) == {"type": "delta", "text": "Hello "}  # times out if buffered
        release.set()
        rest = _read_events(response)
        conn.close()

    assert rest == [
        {"type": "delta", "text": "world"},
        {
            "type": "done",
            "text": "Hello world\n\nArticle URL: https://h/1",
            "sources": [{"title": "Doc", "url": "https://h/1"}],
        },
    ]


def test_question_is_trimmed_before_it_reaches_the_model():
    seen = []

    def stream(question):
        seen.append(question)
        yield Done(Reply("ok", []))

    with _serve(stream) as port:
        conn, response = _post(port, _body(question="  hi  "))
        assert _read_events(response) == [{"type": "done", "text": "ok", "sources": []}]
        conn.close()

    assert seen == ["hi"]


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"not json",
        b"\xff\xfe",
        b"[]",
        b'"question"',
        _body(question=""),
        _body(question="   "),
        _body(other="x"),
        _body(question=123),
        _body(question=["hi"]),
        _body(question="x" * (MAX_QUESTION_CHARS + 1)),
    ],
)
def test_bad_input_is_a_400_and_never_calls_the_model(raw):
    calls = []

    def stream(question):
        calls.append(question)
        yield Done(Reply("unreachable", []))

    with _serve(stream) as port:
        conn, response = _post(port, raw)
        status, payload = response.status, json.loads(response.read())
        conn.close()

    assert status == 400 and payload["error"]
    assert calls == []


def _raises_when_called(question):
    raise RuntimeError("secret internal detail")


def _raises_on_first_pull(question):
    raise RuntimeError("secret internal detail")
    yield  # pragma: no cover  (makes this a generator)


@pytest.mark.parametrize("stream_fn", [_raises_when_called, _raises_on_first_pull])
def test_provider_failure_before_any_text_is_a_502_without_leaking_details(stream_fn):
    with _serve(stream_fn) as port:
        conn, response = _post(port, _body(question="hi"))
        status, raw = response.status, response.read()
        conn.close()

    assert status == 502
    assert json.loads(raw)["error"] and b"secret" not in raw


def test_provider_failure_after_partial_text_ends_with_a_sanitized_error_and_no_done():
    def stream(question):
        yield Delta("partial")
        raise RuntimeError("secret internal detail")

    with _serve(stream) as port:
        conn, response = _post(port, _body(question="hi"))
        assert response.status == 200
        raw = response.read()
        conn.close()

    events = [json.loads(line) for line in raw.decode().splitlines()]
    assert [e["type"] for e in events] == ["delta", "error"]
    assert events[1]["error"] and b"secret" not in raw


def test_stream_that_ends_without_a_terminal_event_gets_an_error_event():
    def stream(question):
        yield Delta("cut off")

    with _serve(stream) as port:
        conn, response = _post(port, _body(question="hi"))
        events = _read_events(response)
        conn.close()

    assert [e["type"] for e in events] == ["delta", "error"]


def test_client_disconnect_closes_the_producer_instead_of_draining_it():
    client_gone = threading.Event()
    closed = threading.Event()

    def stream(question):
        try:
            yield Delta("first")
            assert client_gone.wait(TIMEOUT_S)  # nothing may be drained before the client leaves
            for _ in range(100_000):  # bounded so a regression cannot spin forever
                yield Delta("x")
        except GeneratorExit:
            closed.set()
            raise

    with _serve(stream) as port:
        conn, response = _post(port, _body(question="hi"))
        assert json.loads(response.readline())["type"] == "delta"
        response.close()  # the response owns a dup of the socket file; close both ends
        conn.close()
        client_gone.set()

        assert closed.wait(TIMEOUT_S)

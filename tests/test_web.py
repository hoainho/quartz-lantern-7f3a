import json
import threading
import urllib.error
import urllib.request

import pytest

from kbsync.ask import Reply, Source
from kbsync.web import MAX_QUESTION_CHARS, answer_payload, make_server


def _ask(question: str) -> Reply:
    return Reply(text=f"* answer to {question}", sources=[Source("Doc", "https://h/1")])


def _body(**fields) -> bytes:
    return json.dumps(fields).encode()


def test_valid_question_returns_text_and_sources():
    status, payload = answer_payload(_body(question="  hi  "), _ask)

    assert status == 200
    assert payload == {
        "text": "* answer to hi\n\nArticle URL: https://h/1",
        "sources": [{"title": "Doc", "url": "https://h/1"}],
    }


@pytest.mark.parametrize(
    "raw",
    [b"", b"not json", b"[]", _body(question=""), _body(question="   "), _body(other="x"), _body(question="x" * (MAX_QUESTION_CHARS + 1))],
)
def test_bad_input_is_rejected_without_calling_the_model(raw):
    def boom(_):
        raise AssertionError("model must not be called")

    status, payload = answer_payload(raw, boom)

    assert status == 400 and "error" in payload


def test_model_failure_becomes_a_502_without_leaking_details():
    def fail(_):
        raise RuntimeError("secret internal detail")

    status, payload = answer_payload(_body(question="hi"), fail)

    assert status == 502
    assert "secret" not in json.dumps(payload)


def test_http_round_trip_serves_page_and_answers_over_the_wire():
    server = make_server("127.0.0.1", 0, _ask)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        assert b"Support bot" in urllib.request.urlopen(base + "/").read()
        req = urllib.request.Request(
            base + "/api/ask", data=_body(question="hi"), headers={"Content-Type": "application/json"}
        )
        assert json.load(urllib.request.urlopen(req))["text"].startswith("* answer to hi")
        with pytest.raises(urllib.error.HTTPError) as err:
            urllib.request.urlopen(base + "/missing")
        assert err.value.code == 404
    finally:
        server.shutdown()
        server.server_close()

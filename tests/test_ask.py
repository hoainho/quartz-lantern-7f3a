from types import SimpleNamespace as NS

import pytest

from kbsync.ask import (
    Delta,
    Done,
    EmptyReply,
    Reply,
    Source,
    ask_stream,
    extract_sources,
    format_reply,
    load_system_prompt,
    title_from_url,
)


def _chunk(url, title="T", extra=()):
    meta = [NS(key="article_url", string_value=url)] if url else []
    meta += [NS(key=k, string_value=v) for k, v in extra]
    return NS(retrieved_context=NS(title=title, custom_metadata=meta))


def _response(*chunks, grounded=True):
    grounding = NS(grounding_chunks=list(chunks)) if grounded else None
    return NS(candidates=[NS(grounding_metadata=grounding)])


def test_system_prompt_is_the_verbatim_assignment_text():
    prompt = load_system_prompt()
    assert prompt.startswith("You are OptiBot, the customer-support bot for OptiSigns.com.")
    assert 'Cite up to 3 "Article URL:" lines per reply.' in prompt
    assert prompt.count("\n") == 4


def test_sources_are_deduplicated_ordered_and_capped_at_three():
    response = _response(
        _chunk("https://h/1", "One"),
        _chunk("https://h/1", "One again"),
        _chunk(None, "No metadata"),
        _chunk("https://h/2"),
        _chunk("https://h/3"),
        _chunk("https://h/4"),
    )

    assert [s.url for s in extract_sources(response)] == ["https://h/1", "https://h/2", "https://h/3"]


def test_ungrounded_or_empty_response_has_no_sources():
    assert extract_sources(_response(grounded=False)) == []
    assert extract_sources(NS(candidates=None)) == []
    assert extract_sources(_response(NS(retrieved_context=None))) == []


def test_format_appends_only_urls_the_model_did_not_already_cite():
    reply = Reply(
        text="- Click Add.\nArticle URL: https://h/1\n",
        sources=[Source("One", "https://h/1"), Source("Two", "https://h/2")],
    )

    assert format_reply(reply) == "- Click Add.\nArticle URL: https://h/1\n\nArticle URL: https://h/2"
    assert format_reply(Reply("Plain answer", [])) == "Plain answer"


def test_source_title_is_readable_and_comes_from_the_article_url_not_the_file_name():
    url = "https://s.example/hc/en-us/articles/360051014713-How-to-Use-YouTube-with-OptiSigns"
    response = _response(_chunk(url, title="360051014713-how-to-use-youtube-with-optisigns.md"))

    assert extract_sources(response)[0].title == "How to Use YouTube with OptiSigns"
    assert title_from_url("https://h/articles/12345") == "12345"  # no slug: keep the id


def test_model_that_wrote_markdown_links_instead_of_the_prefix_still_gets_article_url_lines():
    reply = Reply(
        text="Steps...\n\nSee [Guide](https://h/1) for more.",
        sources=[Source("Guide", "https://h/1"), Source("Other", "https://h/2")],
    )

    assert format_reply(reply).endswith("\n\nArticle URL: https://h/1\nArticle URL: https://h/2")


class _Stream:
    """Stands in for the SDK's chunk iterator; records whether it was closed."""

    def __init__(self, chunks, fail_after=None):
        self._chunks = iter(chunks)
        self._fail_after = fail_after
        self._served = 0
        self.closed = False

    def __iter__(self):
        return self

    def __next__(self):
        if self._fail_after is not None and self._served >= self._fail_after:
            raise RuntimeError("provider broke")
        self._served += 1
        return next(self._chunks)

    def close(self):
        self.closed = True


class _Client:
    def __init__(self, stream):
        self.stream = stream
        self.kwargs = None
        self.models = self

    def generate_content_stream(self, **kwargs):
        self.kwargs = kwargs
        return self.stream


def _piece(text, *chunks):
    response = _response(*chunks, grounded=bool(chunks))
    response.text = text
    return response


def test_stream_yields_text_as_it_arrives_and_aggregates_late_grounding_across_chunks():
    stream = _Stream(
        [
            _piece("Hel"),
            _piece("", _chunk("https://h/1")),  # metadata-only chunk: no delta
            _piece("lo", _chunk("https://h/1"), _chunk("https://h/2")),
            _piece(None, _chunk("https://h/2"), _chunk("https://h/3"), _chunk("https://h/4")),
        ]
    )
    client = _Client(stream)

    events = list(ask_stream(client, "m", "stores/s", "q"))

    assert events == [
        Delta("Hel"),
        Delta("lo"),
        Done(
            Reply(
                "Hello",
                [Source("1", "https://h/1"), Source("2", "https://h/2"), Source("3", "https://h/3")],
            )
        ),
    ]
    assert stream.closed


def test_closing_the_stream_early_closes_the_provider_iterator():
    stream = _Stream([_piece("a"), _piece("b")])
    events = ask_stream(_Client(stream), "m", "stores/s", "q")

    assert next(events) == Delta("a")
    events.close()  # what the web layer does when the browser goes away

    assert stream.closed


def test_provider_failure_after_partial_text_propagates_without_a_done_event():
    stream = _Stream([_piece("partial"), _piece("never")], fail_after=1)
    events = ask_stream(_Client(stream), "m", "stores/s", "q")

    assert next(events) == Delta("partial")
    with pytest.raises(RuntimeError):
        next(events)
    assert stream.closed


@pytest.mark.parametrize("text", [None, "", "  \n"])
def test_stream_with_no_usable_text_fails_instead_of_reporting_success(text):
    stream = _Stream([_piece(text, _chunk("https://h/1"))])  # grounded, but the answer is empty
    events = ask_stream(_Client(stream), "m", "stores/s", "q")

    with pytest.raises(EmptyReply):
        list(events)
    assert stream.closed

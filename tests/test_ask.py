from types import SimpleNamespace as NS

from kbsync.ask import Reply, Source, extract_sources, format_reply, load_system_prompt, title_from_url


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

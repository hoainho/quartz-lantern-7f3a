import json

from kbsync.document import build_document, slugify
from kbsync.zendesk import Article


def _article(**overrides) -> Article:
    fields = dict(
        id=42,
        title="How to Add a YouTube Video",
        url="https://h.example/hc/en-us/articles/42-how-to-add-a-youtube-video",
        updated_at="2026-01-01T00:00:00Z",
        body_html="<h2>Steps</h2><p>Click <strong>Add</strong>.</p>",
    )
    fields.update(overrides)
    return Article(**fields)


def test_slugify_is_ascii_hyphenated_and_bounded():
    assert slugify("Café: Menu Boards & More!") == "cafe-menu-boards-more"
    assert slugify("!!!") == "article"
    assert len(slugify("a" * 300)) == 80


def test_filename_uses_stable_id_prefix():
    assert build_document(_article()).filename == "42-how-to-add-a-youtube-video.md"


def test_file_has_parseable_front_matter_and_title_heading():
    doc = build_document(_article(title='Say "hi": now'))
    head, rest = doc.content.split("\n---\n", 1)
    meta = dict(line.split(": ", 1) for line in head.splitlines()[1:])
    assert json.loads(meta["title"]) == 'Say "hi": now'
    assert json.loads(meta["article_id"]) == "42"
    assert json.loads(meta["content_hash"]) == doc.content_hash
    assert rest.lstrip().startswith('# Say "hi": now\n\n## Steps')


def test_hash_ignores_updated_at_but_tracks_text_and_title():
    base = build_document(_article())
    assert build_document(_article(updated_at="2027-05-05T00:00:00Z")).content_hash == base.content_hash
    assert build_document(_article(body_html="<p>Different</p>")).content_hash != base.content_hash
    assert build_document(_article(title="Renamed")).content_hash != base.content_hash

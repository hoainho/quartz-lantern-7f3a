"""End-to-end through job.run: HTML articles -> Markdown files -> delta sync, no network."""

from pathlib import Path

from kbsync import job
from kbsync.config import Config
from kbsync.document import build_document
from kbsync.scrape import scrape
from kbsync.store import RemoteDocument
from kbsync.zendesk import Article


class MemoryStore:
    def __init__(self):
        self.items: dict[str, RemoteDocument] = {}
        self.n = 0

    def list_documents(self):
        return list(self.items.values())

    def upload(self, document):
        self.n += 1
        self.items[f"docs/{self.n}"] = RemoteDocument(f"docs/{self.n}", document.article_id, document.content_hash)

    def delete(self, remote_name):
        del self.items[remote_name]


def _article(i: int, body: str = "<h2>Steps</h2><p>Click <b>Add</b>.</p>", updated: str = "2026-01-01T00:00:00Z"):
    return Article(i, f"Article {i}", f"https://h.example/{i}", updated, body)


def _config(data_dir: Path) -> Config:
    return Config(
        zendesk_base_url="https://h.example",
        zendesk_locale="en-us",
        min_articles=2,
        data_dir=data_dir,
        log_level="INFO",
        gemini_api_key="k",
    )


def _run(config: Config, articles: list[Article], store: MemoryStore):
    return job.run(
        config,
        scrape_fn=lambda c: scrape(c, fetch=lambda base, locale: articles),
        store_factory=lambda c: store,
    )


def test_daily_runs_upload_only_what_changed(tmp_path):
    config = _config(tmp_path / "articles")
    store = MemoryStore()

    day1 = _run(config, [_article(1), _article(2), _article(3)], store)
    day2 = _run(config, [_article(1), _article(2), _article(3)], store)
    edited = _article(1, body="<p>New text</p>")
    touched = _article(2, updated="2026-02-02T00:00:00Z")  # metadata-only change, same text
    day3 = _run(config, [edited, touched], store)  # article 3 was unpublished

    assert (day1.added, day1.updated, day1.skipped, day1.removed) == (3, 0, 0, 0)
    assert (day2.added, day2.updated, day2.skipped, day2.removed) == (0, 0, 3, 0)
    assert (day3.added, day3.updated, day3.skipped, day3.removed) == (0, 1, 1, 1)
    assert day3.failed == 0
    assert sorted((r.article_id, r.content_hash) for r in store.items.values()) == [
        (1, build_document(edited).content_hash),
        (2, build_document(touched).content_hash),
    ]
    assert sorted(p.name for p in (tmp_path / "articles").glob("*.md")) == ["1-article-1.md", "2-article-2.md"]

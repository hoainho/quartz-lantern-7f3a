from pathlib import Path

import pytest

from kbsync.config import Config
from kbsync.scrape import TooFewArticles, build_documents, scrape, write_documents
from kbsync.zendesk import Article


def _articles(n: int) -> list[Article]:
    return [
        Article(
            id=i,
            title=f"Article {i}",
            url=f"https://h.example/hc/en-us/articles/{i}",
            updated_at="2026-01-01T00:00:00Z",
            body_html=f"<p>Body {i}</p>",
        )
        for i in range(1, n + 1)
    ]


def _config(tmp_path: Path, min_articles: int) -> Config:
    return Config(
        zendesk_base_url="https://h.example",
        zendesk_locale="en-us",
        min_articles=min_articles,
        data_dir=tmp_path / "out",
        log_level="INFO",
    )


def test_scrape_writes_one_file_per_article(tmp_path):
    docs = scrape(_config(tmp_path, 3), fetch=lambda base, locale: _articles(3))

    files = sorted(p.name for p in (tmp_path / "out").glob("*.md"))
    assert files == ["1-article-1.md", "2-article-2.md", "3-article-3.md"]
    assert [d.article_id for d in docs] == [1, 2, 3]
    assert "Body 2" in (tmp_path / "out" / "2-article-2.md").read_text(encoding="utf-8")


def test_scrape_refuses_when_below_minimum_and_writes_nothing(tmp_path):
    with pytest.raises(TooFewArticles):
        scrape(_config(tmp_path, 5), fetch=lambda base, locale: _articles(2))
    assert not (tmp_path / "out").exists()


def test_write_documents_removes_stale_files_and_keeps_others(tmp_path):
    out = tmp_path / "out"
    scrape(_config(tmp_path, 1), fetch=lambda base, locale: _articles(3))
    (out / "notes.txt").write_text("keep me")

    write_documents(build_documents(_articles(1)), out)

    assert sorted(p.name for p in out.iterdir()) == ["1-article-1.md", "notes.txt"]

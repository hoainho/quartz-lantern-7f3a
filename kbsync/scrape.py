"""Scrape the Help Center into Markdown files: `python -m kbsync.scrape`."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from pathlib import Path

from kbsync.config import Config
from kbsync.document import Document, build_document
from kbsync.log import configure_logging
from kbsync.zendesk import Article, fetch_articles

log = logging.getLogger(__name__)


class TooFewArticles(RuntimeError):
    """The source returned fewer articles than expected; refuse to sync from it."""


def build_documents(articles: Iterable[Article]) -> list[Document]:
    return [build_document(article) for article in articles]


def write_documents(documents: list[Document], out_dir: Path) -> None:
    """Make `out_dir` mirror `documents`: write each file, delete stale .md files."""
    out_dir.mkdir(parents=True, exist_ok=True)
    keep = {doc.filename for doc in documents}
    for doc in documents:
        (out_dir / doc.filename).write_text(doc.content, encoding="utf-8")
    for stale in out_dir.glob("*.md"):
        if stale.name not in keep:
            stale.unlink()
            log.info("removed stale file=%s", stale.name)


def scrape(
    config: Config,
    fetch: Callable[[str, str], Iterable[Article]] = fetch_articles,
) -> list[Document]:
    """Fetch, convert and write every article; fail loudly if the source looks empty."""
    documents = build_documents(fetch(config.zendesk_base_url, config.zendesk_locale))
    if len(documents) < config.min_articles:
        raise TooFewArticles(
            f"got {len(documents)} articles, expected at least {config.min_articles}"
        )
    write_documents(documents, config.data_dir)
    log.info("scraped articles=%d dir=%s", len(documents), config.data_dir)
    return documents


def main() -> None:
    config = Config.from_env()
    configure_logging(config.log_level)
    scrape(config)


if __name__ == "__main__":
    main()

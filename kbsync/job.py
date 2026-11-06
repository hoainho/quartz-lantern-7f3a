"""The daily job: scrape the Help Center, then sync the delta into the vector store."""

from __future__ import annotations

import logging
from collections.abc import Callable

from kbsync.config import Config
from kbsync.document import Document
from kbsync.log import configure_logging
from kbsync.scrape import scrape
from kbsync.store import VectorStore
from kbsync.sync import SyncResult, sync

log = logging.getLogger(__name__)

STORE_DISPLAY_NAME = "support-articles"


def build_store(config: Config) -> VectorStore:
    from kbsync.gemini_store import GeminiStore, ensure_store, make_client

    client = make_client(config.gemini_api_key)
    name = ensure_store(client, config.gemini_file_search_store, STORE_DISPLAY_NAME)
    return GeminiStore(client, name)


def run(
    config: Config,
    scrape_fn: Callable[[Config], list[Document]] = scrape,
    store_factory: Callable[[Config], VectorStore] = build_store,
) -> SyncResult:
    config.require_gemini()  # fail before touching the network
    documents = scrape_fn(config)
    return sync(store_factory(config), documents, workers=config.upload_workers)


def main() -> int:
    """Exit code: 0 clean run, 1 any failure (bad config, empty source, failed uploads)."""
    try:
        config = Config.from_env()
        configure_logging(config.log_level)
        result = run(config)
    except Exception:
        configure_logging("INFO")
        log.exception("job failed")
        return 1
    return 1 if result.failed else 0

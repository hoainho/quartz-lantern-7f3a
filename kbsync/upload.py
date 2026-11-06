"""Upload Markdown documents to the vector store; `python -m kbsync.upload` does the initial load."""

from __future__ import annotations

import logging
import sys
from collections.abc import Iterable
from dataclasses import dataclass

from kbsync.chunking import DEFAULT_CHUNKING, ChunkingConfig, estimate_chunks
from kbsync.config import Config
from kbsync.document import Document
from kbsync.log import configure_logging
from kbsync.store import VectorStore

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class UploadStats:
    files: int
    chunks_estimated: int
    failed: int


def upload_documents(
    store: VectorStore,
    documents: Iterable[Document],
    chunking: ChunkingConfig = DEFAULT_CHUNKING,
) -> UploadStats:
    """Upload each document independently so one bad file cannot block the rest."""
    files = chunks = failed = 0
    for document in documents:
        try:
            store.upload(document)
        except Exception:
            failed += 1
            log.exception("upload failed article_id=%d file=%s", document.article_id, document.filename)
            continue
        files += 1
        chunks += estimate_chunks(document.content, chunking)
        log.debug("uploaded article_id=%d file=%s", document.article_id, document.filename)
    log.info("uploaded files=%d chunks_estimated=%d failed=%d", files, chunks, failed)
    return UploadStats(files, chunks, failed)


def initial_load(config: Config) -> UploadStats:
    """Scrape and upload everything into an EMPTY store (refuses otherwise)."""
    from google import genai

    from kbsync.gemini_store import GeminiStore, ensure_store
    from kbsync.scrape import scrape

    config.require_gemini()
    client = genai.Client(api_key=config.gemini_api_key)
    store_name = ensure_store(client, config.gemini_file_search_store, "support-articles")
    store = GeminiStore(client, store_name)
    existing = store.list_documents()
    if existing:
        raise RuntimeError(
            f"store {store_name} already holds {len(existing)} documents; "
            "run main.py (delta sync) instead of the initial load"
        )
    log.info("loading into store=%s (set GEMINI_FILE_SEARCH_STORE to reuse it)", store_name)
    return upload_documents(store, scrape(config))


def main() -> None:
    config = Config.from_env()
    configure_logging(config.log_level)
    stats = initial_load(config)
    sys.exit(1 if stats.failed else 0)


if __name__ == "__main__":
    main()

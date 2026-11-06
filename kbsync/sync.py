"""Apply the delta between freshly scraped documents and the vector store."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from kbsync.chunking import DEFAULT_CHUNKING, ChunkingConfig, estimate_chunks
from kbsync.delta import compute_delta
from kbsync.document import Document
from kbsync.store import RemoteDocument, VectorStore

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class SyncResult:
    added: int
    updated: int
    skipped: int
    removed: int
    failed: int
    chunks_estimated: int


def _delete_all(store: VectorStore, copies: list[RemoteDocument], reason: str) -> int:
    """Delete each copy; return how many deletions failed (they are retried next run)."""
    failures = 0
    for copy in copies:
        try:
            store.delete(copy.name)
        except Exception:
            failures += 1
            log.exception("delete failed reason=%s name=%s", reason, copy.name)
    return failures


def sync(
    store: VectorStore,
    documents: list[Document],
    chunking: ChunkingConfig = DEFAULT_CHUNKING,
) -> SyncResult:
    """Upload only new/changed documents, then clean up what they replace.

    Order matters: an old copy is deleted only after its replacement is indexed,
    so a failed upload never leaves an article missing from the knowledge base.
    """
    delta = compute_delta(documents, store.list_documents())
    added = updated = failed = chunks = 0

    for kind, batch in (("added", delta.added), ("updated", delta.updated)):
        for doc in batch:
            try:
                store.upload(doc)
            except Exception:
                failed += 1
                log.exception("upload failed kind=%s article_id=%d file=%s", kind, doc.article_id, doc.filename)
                continue
            chunks += estimate_chunks(doc.content, chunking)
            if kind == "added":
                added += 1
            else:
                updated += 1
                failed += _delete_all(store, delta.superseded.get(doc.article_id, []), "superseded")

    for doc in delta.skipped:  # surplus duplicates from an interrupted earlier run
        failed += _delete_all(store, delta.superseded.get(doc.article_id, []), "duplicate")

    removed = len(delta.removed)
    removal_failures = _delete_all(store, delta.removed, "removed-at-source")
    failed += removal_failures
    removed -= removal_failures

    result = SyncResult(added, updated, len(delta.skipped), removed, failed, chunks)
    log.info(
        "sync done added=%d updated=%d skipped=%d removed=%d failed=%d chunks_estimated=%d",
        result.added, result.updated, result.skipped, result.removed, result.failed, result.chunks_estimated,
    )
    return result

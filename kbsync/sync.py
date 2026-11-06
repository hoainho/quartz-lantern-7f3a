"""Apply the delta between freshly scraped documents and the vector store."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
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


# A scrape that suddenly lacks many articles is more likely a source outage than mass
# unpublishing; deletions beyond this budget are refused (and the run exits non-zero).
MAX_REMOVED_FRACTION = 0.2
MIN_REMOVAL_ALLOWANCE = 5
PROGRESS_EVERY = 25


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
    workers: int = 1,
) -> SyncResult:
    """Upload only new/changed documents, then clean up what they replace.

    Order matters: an old copy is deleted only after its replacement is indexed,
    so a failed upload never leaves an article missing from the knowledge base.
    """
    remote = store.list_documents()
    delta = compute_delta(documents, remote)
    added = updated = failed = chunks = 0

    jobs = [("added", doc) for doc in delta.added] + [("updated", doc) for doc in delta.updated]
    finished = 0
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        pending = {pool.submit(store.upload, doc): (kind, doc) for kind, doc in jobs}
        for future in as_completed(pending):
            kind, doc = pending[future]
            finished += 1
            try:
                future.result()
            except Exception:
                failed += 1
                log.exception("upload failed kind=%s article_id=%d file=%s", kind, doc.article_id, doc.filename)
                continue
            finally:
                if finished % PROGRESS_EVERY == 0 or finished == len(jobs):
                    log.info("progress uploaded=%d/%d", finished, len(jobs))
            chunks += estimate_chunks(doc.content, chunking)
            if kind == "added":
                added += 1
            else:
                updated += 1
                failed += _delete_all(store, delta.superseded.get(doc.article_id, []), "superseded")

    for doc in delta.skipped:  # surplus duplicates from an interrupted earlier run
        failed += _delete_all(store, delta.superseded.get(doc.article_id, []), "duplicate")

    removed_articles = len({r.article_id for r in delta.removed})
    allowed = max(MIN_REMOVAL_ALLOWANCE, int(MAX_REMOVED_FRACTION * len({r.article_id for r in remote})))
    if removed_articles > allowed:
        # A partial or broken source response must never wipe the knowledge base.
        log.error(
            "refusing to delete %d articles (limit %d); check the source, then re-run",
            removed_articles, allowed,
        )
        removed = 0
        failed += len(delta.removed)
    else:
        removal_failures = _delete_all(store, delta.removed, "removed-at-source")
        failed += removal_failures
        removed = len(delta.removed) - removal_failures

    result = SyncResult(added, updated, len(delta.skipped), removed, failed, chunks)
    log.info(
        "sync done added=%d updated=%d skipped=%d removed=%d failed=%d chunks_estimated=%d",
        result.added, result.updated, result.skipped, result.removed, result.failed, result.chunks_estimated,
    )
    return result

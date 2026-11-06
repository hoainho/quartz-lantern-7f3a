from kbsync.chunking import ChunkingConfig
from kbsync.document import Document
from kbsync.store import RemoteDocument
from kbsync.sync import SyncResult, sync

CFG = ChunkingConfig(10, 2)


def _doc(article_id: int, content_hash: str = "h", words: int = 5) -> Document:
    return Document(
        article_id=article_id,
        filename=f"{article_id}-x.md",
        content=" ".join(["w"] * words),
        content_hash=content_hash,
        title="x",
        url=f"https://h/{article_id}",
        updated_at="2026-01-01T00:00:00Z",
    )


class MemoryStore:
    """In-memory VectorStore; can be told to fail specific operations."""

    def __init__(self, fail_upload=(), fail_delete=()):
        self.items: dict[str, RemoteDocument] = {}
        self.uploads: list[int] = []
        self.deletes: list[str] = []
        self._fail_upload = set(fail_upload)
        self._fail_delete = set(fail_delete)
        self._n = 0

    def list_documents(self):
        return list(self.items.values())

    def upload(self, document):
        if document.article_id in self._fail_upload:
            raise RuntimeError("indexing failed")
        self._n += 1
        name = f"docs/{self._n}"
        self.items[name] = RemoteDocument(name, document.article_id, document.content_hash)
        self.uploads.append(document.article_id)

    def delete(self, remote_name):
        if remote_name in self._fail_delete:
            raise RuntimeError("delete failed")
        del self.items[remote_name]
        self.deletes.append(remote_name)


def test_first_run_adds_everything_and_second_run_is_a_no_op():
    store = MemoryStore()
    docs = [_doc(1), _doc(2, words=19)]

    first = sync(store, docs, CFG)
    second = sync(store, docs, CFG)

    assert first == SyncResult(added=2, updated=0, skipped=0, removed=0, failed=0, chunks_estimated=1 + 3)
    assert second == SyncResult(added=0, updated=0, skipped=2, removed=0, failed=0, chunks_estimated=0)
    assert store.uploads == [1, 2]  # nothing re-uploaded


def test_changed_article_is_replaced_and_old_copy_deleted_after_upload():
    store = MemoryStore()
    sync(store, [_doc(1, "v1"), _doc(2, "a")], CFG)
    old_name = next(n for n, r in store.items.items() if r.article_id == 1)

    result = sync(store, [_doc(1, "v2"), _doc(2, "a")], CFG)

    assert (result.added, result.updated, result.skipped) == (0, 1, 1)
    assert old_name in store.deletes
    assert sorted((r.article_id, r.content_hash) for r in store.items.values()) == [(1, "v2"), (2, "a")]


def test_failed_upload_keeps_the_old_copy_so_the_article_never_disappears():
    store = MemoryStore()
    sync(store, [_doc(1, "v1")], CFG)
    store._fail_upload = {1}

    result = sync(store, [_doc(1, "v2")], CFG)

    assert (result.updated, result.failed) == (0, 1)
    assert [r.content_hash for r in store.items.values()] == ["v1"]
    assert store.deletes == []


def test_article_removed_at_source_is_deleted_and_counted():
    store = MemoryStore()
    sync(store, [_doc(1), _doc(2)], CFG)

    result = sync(store, [_doc(1)], CFG)

    assert (result.removed, result.skipped, result.failed) == (1, 1, 0)
    assert [r.article_id for r in store.items.values()] == [1]


def test_failed_deletion_is_reported_and_retried_on_the_next_run():
    store = MemoryStore()
    sync(store, [_doc(1), _doc(2)], CFG)
    stuck = next(n for n, r in store.items.items() if r.article_id == 2)
    store._fail_delete = {stuck}

    first = sync(store, [_doc(1)], CFG)
    store._fail_delete = set()
    second = sync(store, [_doc(1)], CFG)

    assert (first.removed, first.failed) == (0, 1)
    assert (second.removed, second.failed) == (1, 0)


def test_duplicate_left_by_an_interrupted_run_is_cleaned_up_while_skipping():
    store = MemoryStore()
    sync(store, [_doc(1, "v1")], CFG)
    store.upload(_doc(1, "v1"))  # simulate a duplicate

    result = sync(store, [_doc(1, "v1")], CFG)

    assert (result.skipped, result.failed) == (1, 0)
    assert len(store.items) == 1

import logging

from kbsync.chunking import ChunkingConfig
from kbsync.document import Document
from kbsync.upload import UploadStats, upload_documents


def _doc(i: int, words: int) -> Document:
    return Document(
        article_id=i,
        filename=f"{i}-a.md",
        content=" ".join(["w"] * words),
        content_hash=f"h{i}",
        title=f"A{i}",
        url=f"https://h.example/{i}",
        updated_at="2026-01-01T00:00:00Z",
    )


class RecordingStore:
    def __init__(self, fail_on=()):
        self.uploaded = []
        self._fail_on = set(fail_on)

    def upload(self, document):
        if document.article_id in self._fail_on:
            raise RuntimeError("indexing failed")
        self.uploaded.append(document.article_id)


def test_counts_files_and_estimated_chunks():
    store = RecordingStore()
    cfg = ChunkingConfig(10, 2)

    stats = upload_documents(store, [_doc(1, 5), _doc(2, 11), _doc(3, 19)], cfg)

    assert stats == UploadStats(files=3, chunks_estimated=1 + 2 + 3, failed=0)
    assert store.uploaded == [1, 2, 3]


def test_one_failure_is_counted_and_does_not_stop_the_rest(caplog):
    store = RecordingStore(fail_on={2})

    with caplog.at_level(logging.INFO):
        stats = upload_documents(store, [_doc(1, 5), _doc(2, 5), _doc(3, 5)], ChunkingConfig(10, 2))

    assert stats == UploadStats(files=2, chunks_estimated=2, failed=1)
    assert store.uploaded == [1, 3]
    assert "uploaded files=2 chunks_estimated=2 failed=1" in caplog.text

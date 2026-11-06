from types import SimpleNamespace as NS

import pytest

from kbsync.chunking import ChunkingConfig
from kbsync.document import Document
from kbsync.gemini_store import GeminiStore, UploadFailed, ensure_store


def _meta(**pairs):
    return [NS(key=k, string_value=v) for k, v in pairs.items()]


class FakeClient:
    """Minimal stand-in for genai.Client covering only what the adapter calls."""

    def __init__(self, documents=(), ops_until_done=0, error=None, stores=()):
        self.documents = list(documents)
        self.stores = list(stores)
        self.upload_calls = []
        self.delete_calls = []
        self.created = []
        self.polls = 0
        self._ops_until_done = ops_until_done
        self._error = error
        self.file_search_stores = NS(
            documents=NS(list=self._list, delete=self._delete),
            upload_to_file_search_store=self._upload,
            get=lambda name: NS(name=name),
            create=self._create,
            list=lambda: iter(self.stores),
        )
        self.operations = NS(get=self._get_operation)

    def _list(self, parent):
        self.listed_parent = parent
        return iter(self.documents)

    def _delete(self, name, config):
        self.delete_calls.append((name, config))

    def _create(self, config):
        self.created.append(config)
        return NS(name="fileSearchStores/new-1")

    def _upload(self, *, file_search_store_name, file, config):
        self.upload_calls.append((file_search_store_name, file.read(), config))
        return NS(done=self._ops_until_done == 0, error=self._error if self._ops_until_done == 0 else None)

    def _get_operation(self, operation):
        self.polls += 1
        done = self.polls >= self._ops_until_done
        return NS(done=done, error=self._error if done else None)


def _doc() -> Document:
    return Document(
        article_id=42,
        filename="42-add-video.md",
        content="# Add video\n",
        content_hash="abc",
        title="Add video",
        url="https://h.example/42",
        updated_at="2026-01-01T00:00:00Z",
    )


def _store(client, **kwargs):
    return GeminiStore(client, "fileSearchStores/s1", sleep=lambda s: None, **kwargs)


def test_list_documents_reads_sync_state_and_skips_foreign_documents():
    client = FakeClient(
        documents=[
            NS(name="fileSearchStores/s1/documents/a", custom_metadata=_meta(article_id="7", content_hash="h7")),
            NS(name="fileSearchStores/s1/documents/manual", custom_metadata=None),
            NS(name="fileSearchStores/s1/documents/bad", custom_metadata=_meta(article_id="x", content_hash="h")),
        ]
    )

    remote = _store(client).list_documents()

    assert [(r.name, r.article_id, r.content_hash) for r in remote] == [
        ("fileSearchStores/s1/documents/a", 7, "h7")
    ]
    assert client.listed_parent == "fileSearchStores/s1"


def test_upload_sends_content_metadata_and_chunking_then_waits_for_indexing():
    client = FakeClient(ops_until_done=3)

    _store(client, chunking=ChunkingConfig(300, 30)).upload(_doc())

    store, body, config = client.upload_calls[0]
    assert store == "fileSearchStores/s1"
    assert body == b"# Add video\n"
    assert config.display_name == "42-add-video.md"
    assert {m.key: m.string_value for m in config.custom_metadata} == {
        "article_id": "42",
        "content_hash": "abc",
        "updated_at": "2026-01-01T00:00:00Z",
        "article_url": "https://h.example/42",
    }
    ws = config.chunking_config.white_space_config
    assert (ws.max_tokens_per_chunk, ws.max_overlap_tokens) == (300, 30)
    assert client.polls == 3


def test_upload_raises_when_indexing_reports_an_error():
    with pytest.raises(UploadFailed, match="boom"):
        _store(FakeClient(error="boom")).upload(_doc())


def test_upload_raises_on_timeout_instead_of_polling_forever():
    ticks = iter(range(0, 1000, 100))
    store = GeminiStore(
        FakeClient(ops_until_done=10**6),
        "fileSearchStores/s1",
        timeout_s=250,
        sleep=lambda s: None,
        clock=lambda: next(ticks),
    )
    with pytest.raises(UploadFailed, match="timed out"):
        store.upload(_doc())


def test_delete_forces_removal_of_the_named_document():
    client = FakeClient()
    _store(client).delete("fileSearchStores/s1/documents/a")
    assert client.delete_calls == [("fileSearchStores/s1/documents/a", {"force": True})]


def test_ensure_store_uses_explicit_name_without_listing_or_creating():
    client = FakeClient(stores=[NS(name="fileSearchStores/other", display_name="kb")])
    assert ensure_store(client, "fileSearchStores/s1", "kb") == "fileSearchStores/s1"
    assert client.created == []


def test_ensure_store_finds_yesterdays_store_by_display_name():
    client = FakeClient(
        stores=[
            NS(name="fileSearchStores/unrelated", display_name="other"),
            NS(name="fileSearchStores/kb-1", display_name="kb"),
        ]
    )
    assert ensure_store(client, "", "kb") == "fileSearchStores/kb-1"
    assert client.created == []


def test_ensure_store_creates_only_when_no_store_matches():
    client = FakeClient(stores=[NS(name="fileSearchStores/unrelated", display_name="other")])
    assert ensure_store(client, "", "kb") == "fileSearchStores/new-1"
    assert client.created == [{"display_name": "kb"}]


def test_ensure_store_refuses_to_guess_between_duplicates():
    client = FakeClient(
        stores=[NS(name="fileSearchStores/a", display_name="kb"), NS(name="fileSearchStores/b", display_name="kb")]
    )
    with pytest.raises(RuntimeError, match="2 file search stores"):
        ensure_store(client, "", "kb")
    assert client.created == []

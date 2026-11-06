"""Gemini File Search adapter for the VectorStore protocol.

Sync state (article id, content hash) lives in each document's
`custom_metadata`, so the job needs no database or persistent disk.
"""

from __future__ import annotations

import io
import logging
import time
from collections.abc import Callable
from typing import Any

from google.genai import types

from kbsync.chunking import DEFAULT_CHUNKING, ChunkingConfig
from kbsync.document import Document
from kbsync.store import RemoteDocument

log = logging.getLogger(__name__)

MIME_TYPE = "text/markdown"
META_ARTICLE_ID = "article_id"
META_CONTENT_HASH = "content_hash"
META_UPDATED_AT = "updated_at"
META_ARTICLE_URL = "article_url"


class UploadFailed(RuntimeError):
    pass


def ensure_store(client: Any, name: str, display_name: str) -> str:
    """Resolve the store to sync into, without needing any stored state.

    An explicit `name` must exist. Otherwise reuse the store whose display name
    matches (so a fresh container finds yesterday's store) and create it only
    when none exists. Several matches are ambiguous, so the job refuses to guess.
    """
    stores = client.file_search_stores
    if name:
        return stores.get(name=name).name
    matches = [s for s in stores.list() if s.display_name == display_name]
    if len(matches) > 1:
        raise RuntimeError(
            f"{len(matches)} file search stores are named {display_name!r}; "
            "set GEMINI_FILE_SEARCH_STORE to pick one"
        )
    if matches:
        log.info("reusing file search store name=%s", matches[0].name)
        return matches[0].name
    created = stores.create(config={"display_name": display_name})
    log.info("created file search store name=%s", created.name)
    return created.name


class GeminiStore:
    def __init__(
        self,
        client: Any,
        store_name: str,
        chunking: ChunkingConfig = DEFAULT_CHUNKING,
        poll_interval_s: float = 2.0,
        timeout_s: float = 300.0,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._client = client
        self._store = store_name
        self._chunking = chunking
        self._poll_interval_s = poll_interval_s
        self._timeout_s = timeout_s
        self._sleep = sleep
        self._clock = clock

    def list_documents(self) -> list[RemoteDocument]:
        remote: list[RemoteDocument] = []
        for doc in self._client.file_search_stores.documents.list(parent=self._store):
            meta = {m.key: m.string_value for m in (doc.custom_metadata or [])}
            article_id, content_hash = meta.get(META_ARTICLE_ID), meta.get(META_CONTENT_HASH)
            if not (article_id and article_id.isdigit() and content_hash):
                log.warning("ignoring document without sync metadata name=%s", doc.name)
                continue
            remote.append(RemoteDocument(doc.name, int(article_id), content_hash))
        return remote

    def upload(self, document: Document) -> None:
        operation = self._client.file_search_stores.upload_to_file_search_store(
            file_search_store_name=self._store,
            file=io.BytesIO(document.content.encode("utf-8")),
            config=types.UploadToFileSearchStoreConfig(
                mime_type=MIME_TYPE,
                display_name=document.filename,
                custom_metadata=[
                    types.CustomMetadata(key=META_ARTICLE_ID, string_value=str(document.article_id)),
                    types.CustomMetadata(key=META_CONTENT_HASH, string_value=document.content_hash),
                    types.CustomMetadata(key=META_UPDATED_AT, string_value=document.updated_at),
                    types.CustomMetadata(key=META_ARTICLE_URL, string_value=document.url),
                ],
                chunking_config=types.ChunkingConfig(
                    white_space_config=types.WhiteSpaceConfig(
                        max_tokens_per_chunk=self._chunking.max_tokens_per_chunk,
                        max_overlap_tokens=self._chunking.max_overlap_tokens,
                    )
                ),
            ),
        )
        self._wait(operation, document.filename)

    def delete(self, remote_name: str) -> None:
        self._client.file_search_stores.documents.delete(name=remote_name, config={"force": True})

    def _wait(self, operation: Any, label: str) -> None:
        deadline = self._clock() + self._timeout_s
        while not operation.done:
            if self._clock() >= deadline:
                raise UploadFailed(f"timed out after {self._timeout_s:.0f}s indexing {label}")
            self._sleep(self._poll_interval_s)
            operation = self._client.operations.get(operation)
        error = getattr(operation, "error", None)
        if error:
            raise UploadFailed(f"indexing {label} failed: {error}")

"""Provider-neutral view of the remote knowledge base.

Scraper and delta logic depend only on this module, so a different vector
store can be supported by adding another adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from kbsync.document import Document


@dataclass(frozen=True)
class RemoteDocument:
    name: str  # provider resource name, used for deletion
    article_id: int
    content_hash: str


class VectorStore(Protocol):
    def list_documents(self) -> list[RemoteDocument]:
        """Every document currently in the store, with its sync state."""

    def upload(self, document: Document) -> None:
        """Index `document`, tagging it with article id, hash, url and updated_at."""

    def delete(self, remote_name: str) -> None:
        """Remove one document by its provider resource name."""

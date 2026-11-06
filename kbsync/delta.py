"""Decide what to upload, keep or delete by comparing fresh documents with remote state."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from kbsync.document import Document
from kbsync.store import RemoteDocument


@dataclass(frozen=True)
class Delta:
    added: list[Document] = field(default_factory=list)  # article id not in the store
    updated: list[Document] = field(default_factory=list)  # id present, content hash differs
    skipped: list[Document] = field(default_factory=list)  # id present, hash identical
    # Old or duplicate copies per article id. For `updated` articles they may be
    # deleted only after the replacement is indexed; for `skipped` ones right away.
    superseded: dict[int, list[RemoteDocument]] = field(default_factory=dict)
    removed: list[RemoteDocument] = field(default_factory=list)  # article no longer at source


def compute_delta(documents: list[Document], remote: list[RemoteDocument]) -> Delta:
    by_article: dict[int, list[RemoteDocument]] = defaultdict(list)
    for item in remote:
        by_article[item.article_id].append(item)

    delta = Delta()
    for doc in documents:
        copies = by_article.get(doc.article_id, [])
        if not copies:
            delta.added.append(doc)
            continue
        current = next((c for c in copies if c.content_hash == doc.content_hash), None)
        if current is None:
            delta.updated.append(doc)
            delta.superseded[doc.article_id] = list(copies)
            continue
        delta.skipped.append(doc)
        extras = [c for c in copies if c is not current]  # leftovers of an interrupted run
        if extras:
            delta.superseded[doc.article_id] = extras

    live_ids = {doc.article_id for doc in documents}
    delta.removed.extend(c for aid, copies in by_article.items() if aid not in live_ids for c in copies)
    return delta

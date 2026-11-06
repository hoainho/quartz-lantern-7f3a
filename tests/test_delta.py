from kbsync.delta import compute_delta
from kbsync.document import Document
from kbsync.store import RemoteDocument


def _doc(article_id: int, content_hash: str) -> Document:
    return Document(
        article_id=article_id,
        filename=f"{article_id}-x.md",
        content="x",
        content_hash=content_hash,
        title="x",
        url=f"https://h/{article_id}",
        updated_at="2026-01-01T00:00:00Z",
    )


def _remote(name: str, article_id: int, content_hash: str) -> RemoteDocument:
    return RemoteDocument(name=name, article_id=article_id, content_hash=content_hash)


def _ids(docs):
    return [d.article_id for d in docs]


def test_empty_store_means_everything_is_added():
    delta = compute_delta([_doc(1, "a"), _doc(2, "b")], [])

    assert _ids(delta.added) == [1, 2]
    assert not delta.updated and not delta.skipped and not delta.removed and not delta.superseded


def test_same_hash_is_skipped_and_changed_hash_is_updated_with_old_copy_superseded():
    remote = [_remote("r1", 1, "a"), _remote("r2", 2, "old")]

    delta = compute_delta([_doc(1, "a"), _doc(2, "new")], remote)

    assert _ids(delta.skipped) == [1]
    assert _ids(delta.updated) == [2]
    assert delta.superseded == {2: [remote[1]]}
    assert not delta.added and not delta.removed


def test_articles_gone_from_source_are_removed():
    remote = [_remote("r1", 1, "a"), _remote("r9", 9, "z"), _remote("r9b", 9, "z2")]

    delta = compute_delta([_doc(1, "a")], remote)

    assert [r.name for r in delta.removed] == ["r9", "r9b"]
    assert _ids(delta.skipped) == [1]


def test_duplicate_copies_keep_the_matching_one_and_schedule_extras_for_deletion():
    remote = [_remote("stale", 1, "old"), _remote("good", 1, "a"), _remote("dup", 1, "a")]

    delta = compute_delta([_doc(1, "a")], remote)

    assert _ids(delta.skipped) == [1]
    assert [r.name for r in delta.superseded[1]] == ["stale", "dup"]


def test_update_supersedes_every_existing_copy():
    remote = [_remote("c1", 1, "x"), _remote("c2", 1, "y")]

    delta = compute_delta([_doc(1, "new")], remote)

    assert _ids(delta.updated) == [1]
    assert [r.name for r in delta.superseded[1]] == ["c1", "c2"]

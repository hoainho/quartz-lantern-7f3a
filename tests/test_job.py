from pathlib import Path

import pytest

from kbsync import job
from kbsync.config import Config
from kbsync.document import Document
from kbsync.store import RemoteDocument
from kbsync.sync import SyncResult


def _config(api_key="k") -> Config:
    return Config(
        zendesk_base_url="https://h.example",
        zendesk_locale="en-us",
        min_articles=1,
        data_dir=Path("unused"),
        log_level="INFO",
        gemini_api_key=api_key,
    )


def _doc(i: int) -> Document:
    return Document(i, f"{i}-x.md", "x y z", f"h{i}", "x", f"https://h/{i}", "2026-01-01T00:00:00Z")


class FakeStore:
    def __init__(self):
        self.uploaded = []

    def list_documents(self):
        return []

    def upload(self, document):
        self.uploaded.append(document.article_id)

    def delete(self, remote_name):
        raise AssertionError("nothing to delete")


def test_run_scrapes_then_syncs_the_delta_into_the_store():
    store = FakeStore()

    result = job.run(_config(), scrape_fn=lambda c: [_doc(1), _doc(2)], store_factory=lambda c: store)

    assert (result.added, result.failed) == (2, 0)
    assert store.uploaded == [1, 2]


def test_run_without_api_key_fails_before_scraping_or_connecting():
    def boom(*_):
        raise AssertionError("must not be reached")

    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        job.run(_config(api_key=""), scrape_fn=boom, store_factory=boom)


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        (SyncResult(1, 0, 5, 0, 0, 3), 0),
        (SyncResult(1, 0, 5, 0, 2, 3), 1),
    ],
)
def test_main_exit_code_reflects_failed_operations(monkeypatch, result, expected):
    monkeypatch.setattr(job.Config, "from_env", classmethod(lambda cls: _config()))
    monkeypatch.setattr(job, "configure_logging", lambda level: None)
    monkeypatch.setattr(job, "run", lambda config: result)
    assert job.main() == expected


def test_main_returns_one_and_logs_when_the_run_raises(monkeypatch, caplog):
    monkeypatch.setattr(job.Config, "from_env", classmethod(lambda cls: _config()))
    monkeypatch.setattr(job, "configure_logging", lambda level: None)  # keep caplog's handler

    def explode(config):
        raise RuntimeError("source returned nothing")

    monkeypatch.setattr(job, "run", explode)

    assert job.main() == 1
    assert "job failed" in caplog.text

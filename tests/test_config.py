import pytest

from kbsync import config as config_module
from kbsync.config import Config


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch):
    monkeypatch.setattr(config_module, "load_dotenv", lambda: None)  # ignore a developer's .env
    for key in (
        "ZENDESK_BASE_URL", "ZENDESK_LOCALE", "MIN_ARTICLES", "DATA_DIR", "LOG_LEVEL",
        "GEMINI_API_KEY", "GEMINI_FILE_SEARCH_STORE", "GEMINI_MODEL",
    ):
        monkeypatch.delenv(key, raising=False)


def test_defaults_and_trailing_slash_trimmed(monkeypatch):
    monkeypatch.setenv("ZENDESK_BASE_URL", "https://h.example/")

    cfg = Config.from_env()

    assert cfg.zendesk_base_url == "https://h.example"
    assert (cfg.zendesk_locale, cfg.min_articles, cfg.log_level) == ("en-us", 30, "INFO")
    assert cfg.gemini_api_key == "" and cfg.gemini_file_search_store == ""


def test_missing_base_url_is_an_error():
    with pytest.raises(ValueError, match="ZENDESK_BASE_URL"):
        Config.from_env()


def test_require_gemini_fails_fast_without_key(monkeypatch):
    monkeypatch.setenv("ZENDESK_BASE_URL", "https://h.example")
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        Config.from_env().require_gemini()

    monkeypatch.setenv("GEMINI_API_KEY", "k")
    Config.from_env().require_gemini()

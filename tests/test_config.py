import pytest

from kbsync import config as config_module
from kbsync.config import DEFAULT_ZENDESK_BASE_URL, Config


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch):
    monkeypatch.setattr(config_module, "load_dotenv", lambda: None)  # ignore a developer's .env
    for key in (
        "ZENDESK_BASE_URL", "ZENDESK_LOCALE", "MIN_ARTICLES", "DATA_DIR", "LOG_LEVEL",
        "GEMINI_API_KEY", "API_KEY", "GEMINI_FILE_SEARCH_STORE", "GEMINI_MODEL",
    ):
        monkeypatch.delenv(key, raising=False)


def test_runs_with_defaults_only_so_docker_needs_just_an_api_key():
    cfg = Config.from_env()

    assert cfg.zendesk_base_url == DEFAULT_ZENDESK_BASE_URL
    assert (cfg.zendesk_locale, cfg.min_articles, cfg.log_level) == ("en-us", 30, "INFO")
    assert cfg.gemini_api_key == "" and cfg.gemini_file_search_store == ""


def test_base_url_override_has_trailing_slash_trimmed(monkeypatch):
    monkeypatch.setenv("ZENDESK_BASE_URL", "https://h.example/")
    assert Config.from_env().zendesk_base_url == "https://h.example"


def test_api_key_alias_is_accepted_and_gemini_key_wins(monkeypatch):
    monkeypatch.setenv("API_KEY", "from-alias")
    assert Config.from_env().gemini_api_key == "from-alias"

    monkeypatch.setenv("GEMINI_API_KEY", "from-gemini")
    assert Config.from_env().gemini_api_key == "from-gemini"


def test_require_gemini_fails_fast_without_key(monkeypatch):
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        Config.from_env().require_gemini()

    monkeypatch.setenv("API_KEY", "k")
    Config.from_env().require_gemini()

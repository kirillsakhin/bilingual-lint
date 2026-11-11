import pytest

from bilingual_lint.config import RULE_DEFAULTS, Config, ConfigError, parse_langs


def write(tmp_path, text):
    path = tmp_path / ".bilingual-lint.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_defaults_without_a_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = Config.load(None)
    assert config.fail_on == "error" and config.langs is None
    assert config.rules == RULE_DEFAULTS and config.rules is not RULE_DEFAULTS


def test_file_overrides(tmp_path):
    (tmp_path / "terms.yaml").write_text("- {en: Buyer, ru: Покупатель}\n", encoding="utf-8")
    config = Config.load(write(tmp_path, (
        "langs: en,es\nfail_on: warning\nglossary: terms.yaml\nlow_confidence: 0.7\n"
        "rules:\n  BI011: {enabled: false}\n  BI006: {severity: error}\n"
        "llm: {max_pairs: 5}\n")))
    assert config.langs == ("en", "es") and config.fail_on == "warning"
    assert config.glossary == [{"en": "Buyer", "ru": "Покупатель"}]
    assert config.low_confidence == 0.7
    assert config.rules["BI011"]["enabled"] is False
    assert config.rules["BI006"]["severity"] == "error"
    assert config.llm["max_pairs"] == 5 and config.llm["timeout_seconds"] == 60


@pytest.mark.parametrize("text", [
    "unknown_key: 1", "fail_on: info", "langs: english", "langs: en,en",
    "low_confidence: 3", "rules: {BI999: {enabled: false}}",
    "rules: {BI001: {nope: 1}}", "rules: {BI001: {severity: fatal}}",
    "llm: {temperature: 1}", "glossary: missing.yaml", "- a list",
])
def test_bad_config_is_rejected(tmp_path, text):
    with pytest.raises(ConfigError):
        Config.load(write(tmp_path, text))


def test_parse_langs():
    assert parse_langs("EN, ru") == ("en", "ru")
    assert parse_langs(["en", "es"]) == ("en", "es")

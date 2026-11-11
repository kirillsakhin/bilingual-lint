import json

from typer.testing import CliRunner

from bilingual_lint.cli import app

from .helpers import write_plain, write_two_column

runner = CliRunner()
CLEAN = [("2.1. The price is USD 150,000.", "2.1. Цена составляет 150 000 долларов США.")]
DEFECT = [("2.1. The price is USD 150,000.", "2.1. Цена составляет 105 000 долларов США.")]


def report(tmp_path, rows, *args):
    source = write_two_column(tmp_path / "doc.docx", rows)
    out = tmp_path / "report.json"
    result = runner.invoke(app, ["check", str(source), "--format", "json",
                                 "--output", str(out), *args])
    return result, json.loads(out.read_text(encoding="utf-8")) if out.exists() else None


def test_clean_document_exits_zero(tmp_path):
    result, data = report(tmp_path, CLEAN)
    assert result.exit_code == 0, result.output
    assert data["summary"]["by_severity"].get("error") is None
    assert data["source"] == {"paths": [str(tmp_path / "doc.docx")], "mode": "two-column",
                              "lang_a": "en", "lang_b": "ru", "pairs": 1, "unpaired": 0}


def test_defect_exits_one_and_is_reported(tmp_path):
    result, data = report(tmp_path, DEFECT)
    assert result.exit_code == 1
    (finding,) = [f for f in data["findings"] if f["rule_id"] == "BI002"]
    assert finding["severity"] == "error" and finding["pair_no"] == 1
    assert finding["text_a"] == DEFECT[0][0] and finding["text_b"] == DEFECT[0][1]
    assert finding["location_a"] == "table 1, row 1"


def test_rules_filter_and_fail_on(tmp_path):
    result, data = report(tmp_path, DEFECT, "--rules", "BI010")
    assert result.exit_code == 0
    assert data["rules"]["ran"] == ["BI010"]
    assert "BI002" in data["rules"]["disabled"]
    warning_only = [("5.2. See clause 3.1.", "5.2. См. п. 3.4.")]
    assert report(tmp_path, warning_only)[0].exit_code == 0
    assert report(tmp_path, warning_only, "--fail-on", "warning")[0].exit_code == 1


def test_two_files_mode(tmp_path):
    en = write_plain(tmp_path / "en.docx", [a for a, _ in DEFECT])
    ru = write_plain(tmp_path / "ru.docx", [b for _, b in DEFECT])
    out = tmp_path / "r.json"
    result = runner.invoke(app, ["check", str(en), str(ru), "--format", "json",
                                 "--output", str(out)])
    assert result.exit_code == 1
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["source"]["mode"] == "two-files"
    assert data["summary"]["by_rule"]["BI002"] == 1


def test_language_pair_without_wordlists_runs_neutral_rules_only(tmp_path):
    rows = [("The price is 1,500 EUR.", "El precio es de 1.700 EUR.")]
    result, data = report(tmp_path, rows, "--langs", "en,es")
    assert result.exit_code == 1
    assert data["summary"]["by_rule"] == {"BI002": 1}
    assert data["rules"]["skipped"] == ["BI004", "BI005", "BI008", "BI010", "BI011"]


def test_glossary_option(tmp_path):
    glossary = tmp_path / "glossary.yaml"
    glossary.write_text("- {en: Goods, ru: Товар}\n", encoding="utf-8")
    rows = [("The Goods are delivered.", "Продукция поставляется.")]
    result, data = report(tmp_path, rows, "--glossary", str(glossary),
                          "--fail-on", "warning")
    assert result.exit_code == 1 and data["summary"]["by_rule"]["BI008"] == 1


def test_usage_errors_exit_two(tmp_path):
    source = write_two_column(tmp_path / "doc.docx", CLEAN)
    cases = [
        ["check", str(tmp_path / "missing.docx")],
        ["check", str(source), "--format", "xml"],
        ["check", str(source), "--fail-on", "info"],
        ["check", str(source), "--rules", "BI999"],
        ["check", str(source), "--langs", "english"],
        ["check", str(source), "--output", str(tmp_path / "x.txt")],
        ["check", str(source), str(source), str(source)],
        ["check", str(source), "--config", str(tmp_path / "none.yaml")],
    ]
    for args in cases:
        result = runner.invoke(app, args)
        assert result.exit_code == 2, (args, result.output)


def test_console_output_keeps_square_brackets(tmp_path):
    rows = [("Pay 5 units to [client name].", "Оплатить 6 единиц [имя клиента].")]
    source = write_two_column(tmp_path / "doc.docx", rows)
    result = runner.invoke(app, ["check", str(source)])
    assert result.exit_code == 1
    assert "[client name]" in result.output and "BI001" in result.output


def test_markdown_report(tmp_path):
    source = write_two_column(tmp_path / "doc.docx", DEFECT)
    result = runner.invoke(app, ["check", str(source), "--format", "md"])
    assert result.exit_code == 1
    assert "## BI002 · error · pair 1" in result.output
    assert "| en (table 1, row 1) | ru (table 1, row 1) |" in result.output


def test_version_rules_and_init(tmp_path, monkeypatch):
    assert runner.invoke(app, ["--version"]).output.startswith("bilingual-lint ")
    listing = runner.invoke(app, ["rules"]).output
    assert all(f"BI{n:03d}" in listing for n in range(12))
    monkeypatch.chdir(tmp_path)
    assert runner.invoke(app, ["init"]).exit_code == 0
    assert (tmp_path / ".bilingual-lint.yaml").is_file()
    assert runner.invoke(app, ["init"]).exit_code == 2
    source = write_two_column(tmp_path / "doc.docx", CLEAN)
    assert runner.invoke(app, ["check", str(source)]).exit_code == 0

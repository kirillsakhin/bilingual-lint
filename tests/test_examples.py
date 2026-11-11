"""The bundled examples: every planted defect is found, the clean file is clean."""
import importlib.util
import json
import re
from collections import Counter
from pathlib import Path

from typer.testing import CliRunner

from bilingual_lint.cli import app

runner = CliRunner()
ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"

spec = importlib.util.spec_from_file_location("build_examples", EXAMPLES / "build_examples.py")
build_examples = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_examples)


def norm(text: str) -> str:
    text = text.replace("\r\n", "\n").strip()
    text = re.sub(r'"version": "[^"]+"', '"version": "X"', text)
    # Paths vary by invocation directory and OS separator.
    return re.sub(r'"paths": \[[^\]]*\]', '"paths": "X"', text, flags=re.DOTALL)


def run(tmp_path, *files, fmt="json"):
    out = tmp_path / f"report.{fmt}"
    result = runner.invoke(app, ["check", *[str(EXAMPLES / f) for f in files],
                                 "--format", fmt, "--output", str(out)])
    return result, out.read_text(encoding="utf-8")


def test_committed_examples_match_the_builder(tmp_path):
    from bilingual_lint.loaders import load
    doc = load([EXAMPLES / "sample_en_ru.docx"])
    assert [(p.a.text, p.b.text) for p in doc.pairs] == build_examples.SAMPLE


def test_clean_example_has_no_findings_that_fail(tmp_path):
    result, text = run(tmp_path, "clean_en_ru.docx")
    assert result.exit_code == 0, text
    assert json.loads(text)["summary"]["total"] == 0


def test_every_planted_defect_is_found(tmp_path):
    result, text = run(tmp_path, "sample_en_ru.docx")
    assert result.exit_code == 1
    by_rule = json.loads(text)["summary"]["by_rule"]
    for rule, count in Counter(build_examples.PLANTED).items():
        assert by_rule.get(rule, 0) >= count, (rule, by_rule)
    # the '3 (двух)' row also shows up as a plain number difference
    assert by_rule.get("BI001") == 1
    assert set(by_rule) == set(build_examples.PLANTED) | {"BI001"}


def test_sample_json_golden(tmp_path):
    _, text = run(tmp_path, "sample_en_ru.docx")
    golden = (ROOT / "tests" / "golden" / "sample_en_ru.json").read_text(encoding="utf-8")
    assert norm(text) == norm(golden)


def test_sample_md_golden(tmp_path):
    _, text = run(tmp_path, "sample_en_ru.docx", fmt="md")
    golden = (ROOT / "tests" / "golden" / "sample_en_ru.md").read_text(encoding="utf-8")
    assert re.sub(r"Source: .*", "Source: X", text.strip()) == \
        re.sub(r"Source: .*", "Source: X", golden.replace("\r\n", "\n").strip())


def test_two_file_example_finds_the_same_fact_defects(tmp_path):
    result, text = run(tmp_path, "sample_en.docx", "sample_ru.docx")
    assert result.exit_code == 1
    data = json.loads(text)
    assert data["source"]["mode"] == "two-files"
    for rule in ("BI002", "BI003", "BI004", "BI005", "BI009", "BI010"):
        assert data["summary"]["by_rule"].get(rule, 0) >= 1, (rule, data["summary"])
    assert data["source"]["unpaired"] == 1  # the heading with no Russian counterpart

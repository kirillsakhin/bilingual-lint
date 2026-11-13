import json

import pytest

from benchmark import adjudicate

RESULTS = [
    {"pairs": 40, "clean_findings": [
        ["BI001", "error", 5, "numbers differ — en only: 100,000 · ru only: 10 000"],
        ["BI003", "error", 19, "times differ — en only: 11 a.m."],
        ["BI011", "info", 2, "possible negation mismatch"]]},
    {"pairs": 60, "clean_findings": [["BI001", "error", 0, "numbers differ — en only: 5"]]},
]
REAL = "0|5|BI001|numbers differ — en only: 100,000 · ru only: 10 000"
FALSE = "0|19|BI003|times differ — en only: 11 a.m."
DOCS = [[("a", "b")] * 40, [("first a", "first b")] * 60]


def test_only_errors_are_listed_and_each_has_a_stable_key():
    found = adjudicate.error_findings(RESULTS)
    assert [item[0] for item in found] == [REAL, FALSE, "1|0|BI001|numbers differ — en only: 5"]


def test_tally_counts_an_unjudged_finding_as_a_false_flag():
    verdicts = {REAL: {"verdict": "real", "note": "the Russian text has 10 000"},
                FALSE: {"verdict": "false", "note": "same time, written differently"}}
    assert adjudicate.tally(RESULTS, verdicts) == {
        "error_findings": 3, "real": 1, "false": 1, "open": 1, "false_per_100_pairs": 2.0}
    assert adjudicate.tally(RESULTS, {})["false_per_100_pairs"] == 3.0


def test_load_returns_nothing_for_a_missing_file_and_rejects_a_bad_verdict(tmp_path):
    assert adjudicate.load(tmp_path / "dev.json") == {}
    path = tmp_path / "dev.json"
    path.write_text(json.dumps({REAL: {"verdict": "maybe"}}), encoding="utf-8")
    with pytest.raises(ValueError, match="verdict must be one of"):
        adjudicate.load(path)


def test_worksheet_lists_only_the_findings_without_a_verdict():
    sheet = adjudicate.worksheet(RESULTS, DOCS, {REAL: {"verdict": "real"}})
    assert REAL not in sheet
    assert f"## `{FALSE}`" in sheet
    assert "- A: first a" in sheet and "- B: first b" in sheet

from benchmark import score

from .helpers import EN, RU

ROWS = list(zip(EN, RU, strict=True))


def test_lint_rows_reports_a_changed_figure_on_its_row(tmp_path):
    clean = score.lint_rows(ROWS, tmp_path)
    broken = [*ROWS]
    broken[2] = (EN[2].replace("48", "84"), RU[2])
    new = [f for f in score.lint_rows(broken, tmp_path) if f not in set(clean)]
    assert new, "the linter should say something new about the changed row"
    assert {f[2] for f in new} == {2}
    assert all(f[1] in score.RANK for f in new)


def test_lint_rows_is_quiet_on_matching_text(tmp_path):
    rows = [("The fee is 500 euros.", "Вознаграждение составляет 500 евро.")]
    assert [f for f in score.lint_rows(rows, tmp_path) if f[1] == "error"] == []


def test_pairing_is_whole_on_equal_files_and_counts_only_rows_with_a_partner(tmp_path):
    assert score.pairing(ROWS, tmp_path) == (8, 8)
    right, total = score.pairing(ROWS, tmp_path, missing=3, side="b")
    assert total == 7
    assert 0 <= right <= 7


def test_score_document_catches_planted_figures_and_reports_misses():
    result = score.score_document(ROWS, seed=1)
    by_operator = {}
    for case in result["cases"]:
        by_operator.setdefault(case["operator"], []).append(case)
    assert {"digit", "date", "drop"} <= set(by_operator)
    assert all(case["caught_any"] for case in by_operator["digit"])
    assert all(case["caught_any"] for case in by_operator["drop"])
    assert result["pairs"] == 8
    assert result["pairing"] == {"right": 8, "total": 8}
    assert result["pairing_one_missing"]["total"] == 14


def test_a_defect_on_a_row_that_was_already_flagged_still_counts():
    rows = [*ROWS]
    rows[2] = (EN[2].replace("48", "49"), RU[2])      # flagged before any mutation
    result = score.score_document(rows, seed=1, operators=("digit",))
    assert any(f[2] == 2 for f in result["clean_findings"])
    on_row = [case for case in result["cases"] if case["row"] == 2]
    assert on_row and all(case["caught_any"] for case in on_row)


def fake_result(caught: int, planted: int, operator: str = "digit", errors: int = 0) -> dict:
    cases = [{"operator": operator, "caught_expected": i < caught, "caught_any": i < caught}
             for i in range(planted)]
    return {"pairs": 50, "cases": cases,
            "clean_findings": [["BI001", "error", i, "m"] for i in range(errors)],
            "pairing": {"right": 50, "total": 50},
            "pairing_one_missing": {"right": 90, "total": 98}}


def test_summarise_adds_up_operators_groups_and_rates():
    summary = score.summarise([fake_result(9, 10, errors=2), fake_result(4, 4, "drop")])
    assert summary["documents"] == 2 and summary["pairs"] == 100
    assert summary["operators"]["digit"]["recall_any"] == 0.9
    assert summary["figures"] == {"planted": 10, "caught": 9, "recall": 0.9}
    assert summary["paragraphs"]["recall"] == 1.0
    assert summary["clean_flags_per_100_pairs"]["error"] == 2.0
    assert summary["pairing_accuracy"] == 1.0
    assert summary["pairing_accuracy_one_missing"] == round(180 / 196, 4)


def test_targets_mark_met_missed_and_unmeasured():
    summary = score.summarise([fake_result(9, 10, errors=2)])
    rows = {name: (value, met) for name, value, _, met in score.targets(summary)}
    assert rows["figures_recall"] == (0.9, False)
    assert rows["paragraphs_recall"] == (None, None)
    assert rows["error_flags_per_100_pairs"] == (4.0, False)
    assert rows["pairing_accuracy"] == (round(90 / 98, 4), False)
    judged = {name: (value, met) for name, value, _, met in score.targets(summary, 1.5)}
    assert judged["error_flags_per_100_pairs"] == (1.5, True)

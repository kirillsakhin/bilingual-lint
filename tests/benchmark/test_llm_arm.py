import json

import pytest

from benchmark import llm_arm

from .helpers import EN, RU

ROWS = list(zip(EN, RU, strict=True))


def test_render_numbers_rows_from_one_and_marks_an_empty_cell():
    text = llm_arm.render([("One.", "Один."), ("Two.", "")])
    assert text == "Row 1\nen: One.\nru: Один.\n\nRow 2\nen: Two.\nru: (empty)"


def test_parse_reads_rows_and_ignores_numbers_out_of_range():
    reply = 'Here you go: {"rows": [{"row": 2, "reason": "x"}, {"row": 99}, 3]}'
    assert llm_arm.parse(reply, row_count=8) == {1, 2}
    assert llm_arm.parse('{"rows": []}', row_count=8) == set()


@pytest.mark.parametrize("reply", ["no json here", '{"lines": [1]}', '{"rows": 3}'])
def test_parse_rejects_a_reply_in_another_shape(reply):
    with pytest.raises(ValueError):
        llm_arm.parse(reply, row_count=8)


def reviewer(clean_rows=(), blind_to=()):
    """A stand-in model: names the rows that differ from the clean text, except
    the operators' rows listed in blind_to, plus clean_rows on every call."""
    def complete(system, user):
        named = set(clean_rows)
        blocks = user.split("\n\n")
        for number, (block, (a, b)) in enumerate(zip(blocks, ROWS, strict=True), start=1):
            if block != f"Row {number}\nen: {a}\nru: {b}" and number - 1 not in blind_to:
                named.add(number)
        return json.dumps({"rows": [{"row": n, "reason": "differs"} for n in sorted(named)]})
    return complete


def test_compare_document_scores_caught_missed_and_excluded():
    perfect = llm_arm.compare_document(ROWS, 1, reviewer(), per_operator=None)
    assert perfect["clean_rows"] == []
    assert {case["outcome"] for case in perfect["cases"]} == {"caught"}
    blind = llm_arm.compare_document(ROWS, 1, reviewer(blind_to={0}), per_operator=None)
    assert {case["outcome"] for case in blind["cases"] if case["row"] == 0} == {"missed"}
    noisy = llm_arm.compare_document(ROWS, 1, reviewer(clean_rows={1}), per_operator=None)
    assert noisy["clean_rows"] == [0]
    assert {case["outcome"] for case in noisy["cases"] if case["row"] == 0} == {"excluded"}


def test_a_failed_call_is_counted_not_guessed():
    def broken(system, user):
        raise TimeoutError("no answer")
    result = llm_arm.compare_document(ROWS, 1, broken)
    assert result["clean_rows"] is None
    assert {case["outcome"] for case in result["cases"]} == {"failed"}
    summary = llm_arm.summarise([result])
    assert summary["clean_documents_failed"] == 1
    assert all(row["recall"] is None for row in summary["operators"].values())


def test_summarise_gives_recall_per_operator_and_the_noise_rate():
    results = [llm_arm.compare_document(ROWS, 1, reviewer(clean_rows={1}), per_operator=None)]
    summary = llm_arm.summarise(results)
    assert summary["clean_rows_named_per_100_pairs"] == 12.5
    assert summary["extra_rows_named_per_mutated_copy"] == 0
    digit = summary["operators"]["digit"]
    assert digit["recall"] == 1.0 and digit["excluded"] >= 1


def test_a_failed_call_is_sent_again_after_a_growing_pause():
    calls, pauses = [], []

    def flaky(system, user):
        calls.append(user)
        if len(calls) < 3:
            raise RuntimeError("overloaded")
        return "ok"

    complete = llm_arm.with_retries(flaky, attempts=4, pause=10, sleep=pauses.append)
    assert complete("s", "u") == "ok"
    assert len(calls) == 3
    assert pauses == [10, 20]


def test_the_last_failure_is_raised():
    def broken(system, user):
        raise RuntimeError("down")

    complete = llm_arm.with_retries(broken, attempts=3, pause=1, sleep=lambda s: None)
    with pytest.raises(RuntimeError, match="down"):
        complete("s", "u")

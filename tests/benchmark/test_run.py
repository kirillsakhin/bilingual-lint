import json

import pytest

from benchmark import freeze, run

from .helpers import EN, RU, make_set


@pytest.fixture
def tree(tmp_path, monkeypatch):
    """Invented UN-format data, a matching freeze, and a git that says 'clean'."""
    data = tmp_path / "data"
    make_set(data, "devset", en_lines=EN, ru_lines=RU)
    make_set(data, "testset", en_lines=EN[::-1], ru_lines=RU[::-1])
    frozen = tmp_path / "FROZEN.json"
    frozen.write_text(json.dumps(freeze.snapshot(data)), encoding="utf-8")
    monkeypatch.setattr(freeze, "FROZEN", frozen)
    monkeypatch.setattr(freeze.problems, "__defaults__", (None, frozen, freeze.MUTATE))
    state = {"dirty": ""}
    monkeypatch.setattr(
        run, "_git", lambda *args: state["dirty"] if args[0] == "status" else "abc1234")
    return {"data": data, "out": tmp_path / "results", "adj": tmp_path / "adjudication",
            "git": state, "lines": []}


def score(tree, part, **kwargs):
    options = {"limit": None, "per_operator": None, **kwargs}
    return run.run_score(part, tree["data"], options["limit"], options["per_operator"],
                         tree["out"], tree["adj"], echo=tree["lines"].append)


def test_dev_run_writes_a_record_with_the_numbers_and_their_provenance(tree):
    assert score(tree, "dev") == 0
    record = json.loads((tree["out"] / "dev.json").read_text(encoding="utf-8"))
    assert record["part"] == "dev" and record["commit"] == "abc1234"
    assert record["data_sha256"] == freeze.set_hash(tree["data"], "devset")
    assert record["summary"]["pairs"] == 8
    assert [row[0] for row in record["targets"]] == list(run.TARGET_LABELS)
    assert any(line.startswith("| Measure | Target | Result | Met |")
               for line in tree["lines"])


def test_holdout_is_scored_once(tree):
    assert score(tree, "holdout") == 0
    assert (tree["out"] / "holdout.json").exists()
    tree["lines"].clear()
    assert score(tree, "holdout") == 2
    assert tree["lines"] == ["refused: the hold-out has already been scored; it is scored once"]


def test_holdout_refuses_sampling_a_dirty_tree_and_a_broken_freeze(tree):
    assert score(tree, "holdout", limit=1) == 2
    tree["git"]["dirty"] = " M benchmark/score.py"
    assert score(tree, "holdout") == 2
    tree["git"]["dirty"] = ""
    target = tree["data"] / "testset" / "UNv1.0.testset.en"
    target.write_bytes(target.read_bytes() + b"One more line.\n")
    assert score(tree, "holdout") == 2
    assert not (tree["out"] / "holdout.json").exists()
    assert "refused: the hold-out is scored whole: no --limit, no --per-operator" in tree["lines"]
    assert "refused: the git tree has uncommitted changes" in tree["lines"]
    assert "refused: the testset files differ from the frozen ones" in tree["lines"]


def test_contracts_need_no_data_and_score_every_operator(tree):
    assert run.run_score("contracts", None, None, 1, tree["out"], tree["adj"],
                         echo=tree["lines"].append) == 0
    record = json.loads((tree["out"] / "contracts.json").read_text(encoding="utf-8"))
    assert record["summary"]["documents"] == 3 and record["data_sha256"] is None
    assert set(record["summary"]["operators"]) == set(run.llm_arm.OPERATORS)


def test_a_verdict_file_moves_a_finding_out_of_the_false_flags(tree):
    make = tree["data"] / "devset" / "UNv1.0.devset.en"
    make.write_text(make.read_text(encoding="utf-8").replace("48 delegations", "49 delegations"),
                    encoding="utf-8", newline="\n")
    assert score(tree, "dev", per_operator=1) == 0
    record = json.loads((tree["out"] / "dev.json").read_text(encoding="utf-8"))
    assert record["adjudication"]["open"] >= 1
    sheet = []
    assert run.run_worksheet("dev", tree["data"], tree["out"], tree["adj"],
                             echo=sheet.append) == 0
    keys = [line[4:-1] for line in sheet[0].splitlines() if line.startswith("## `")]
    tree["adj"].mkdir()
    (tree["adj"] / "dev.json").write_text(
        json.dumps({key: {"verdict": "real", "note": "planted by the test"} for key in keys},
                   ensure_ascii=False), encoding="utf-8")
    assert score(tree, "dev", per_operator=1) == 0
    judged = json.loads((tree["out"] / "dev.json").read_text(encoding="utf-8"))["adjudication"]
    assert judged["open"] == 0 and judged["real"] == len(keys)
    assert judged["false_per_100_pairs"] == 0.0


def test_llm_run_puts_the_model_and_the_linter_side_by_side(tree):
    def complete(system, user):
        return json.dumps({"rows": []})
    assert run.run_llm("dev", tree["data"], 1, "fake/model", tree["out"], complete,
                       echo=tree["lines"].append) == 0
    record = json.loads((tree["out"] / "llm_dev.json").read_text(encoding="utf-8"))
    assert record["model"] == "fake/model" and record["documents"] == 1
    assert record["model_summary"]["operators"]["digit"]["recall"] == 0.0
    assert record["linter_summary"]["operators"]["digit"]["recall_any"] == 1.0


def test_llm_on_the_holdout_waits_for_the_linter_score(tree):
    assert run.run_llm("holdout", tree["data"], 1, "fake/model", tree["out"],
                       lambda s, u: "{}", echo=tree["lines"].append) == 2
    assert tree["lines"] == ["refused: score the hold-out with the linter first"]

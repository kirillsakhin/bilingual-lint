import json

from benchmark import freeze

from .helpers import make_set


def frozen_tree(tmp_path):
    data = tmp_path / "data"
    make_set(data, "devset")
    make_set(data, "testset")
    mutate = tmp_path / "mutate.py"
    mutate.write_bytes(b"A = 1\nB = 2\n")
    record = {"mutate_sha256": freeze.code_hash(mutate)}
    for part in ("devset", "testset"):
        record[f"{part}_sha256"] = freeze.set_hash(data, part)
    frozen = tmp_path / "FROZEN.json"
    frozen.write_text(json.dumps(record), encoding="utf-8")
    return data, mutate, frozen


def test_code_hash_ignores_line_endings_and_sees_a_real_change(tmp_path):
    lf, crlf, other = tmp_path / "lf.py", tmp_path / "crlf.py", tmp_path / "other.py"
    lf.write_bytes(b"A = 1\nB = 2\n")
    crlf.write_bytes(b"A = 1\r\nB = 2\r\n")
    other.write_bytes(b"A = 1\nB = 3\n")
    assert freeze.code_hash(lf) == freeze.code_hash(crlf)
    assert freeze.code_hash(lf) != freeze.code_hash(other)


def test_an_intact_tree_has_no_problems(tmp_path):
    data, mutate, frozen = frozen_tree(tmp_path)
    assert freeze.problems(data, frozen, mutate) == []
    assert freeze.problems(None, frozen, mutate) == []


def test_a_changed_mutation_tool_is_reported(tmp_path):
    data, mutate, frozen = frozen_tree(tmp_path)
    mutate.write_bytes(b"A = 1\nB = 3\n")
    assert freeze.problems(data, frozen, mutate) == ["mutate.py has changed since the freeze"]


def test_changed_data_is_reported(tmp_path):
    data, mutate, frozen = frozen_tree(tmp_path)
    target = data / "testset" / "UNv1.0.testset.en"
    target.write_bytes(target.read_bytes() + b"One more line.\n")
    assert freeze.problems(data, frozen, mutate) == [
        "the testset files differ from the frozen ones"]


def test_no_freeze_file_is_a_problem(tmp_path):
    assert freeze.problems(None, tmp_path / "FROZEN.json") == [
        "FROZEN.json does not exist: nothing has been frozen"]


def test_snapshot_records_the_tool_the_archive_and_both_sets(tmp_path):
    data, _, _ = frozen_tree(tmp_path)
    archive = tmp_path / "sets.tar.gz"
    archive.write_bytes(b"not really an archive")
    record = freeze.snapshot(data, archive)
    assert record["mutate_sha256"] == freeze.code_hash(freeze.MUTATE)
    assert record["archive"] == "sets.tar.gz" and len(record["archive_sha256"]) == 64
    assert record["devset_sha256"] == freeze.set_hash(data, "devset")
    assert record["testset_sha256"] == freeze.set_hash(data, "testset")

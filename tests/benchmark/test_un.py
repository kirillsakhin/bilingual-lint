import pytest

from benchmark import un

from .helpers import make_set


def test_load_set_reads_aligned_rows_with_their_document(tmp_path):
    rows = un.load_set(make_set(tmp_path), "devset")
    assert len(rows) == 5
    assert rows[3] == ("Sentence 3 of the report.", "Предложение 3 доклада.", "2015/a/69/1")


def test_load_set_refuses_files_of_different_length(tmp_path):
    make_set(tmp_path, ru_lines=["только одна строка"])
    with pytest.raises(ValueError, match="differ in length"):
        un.load_set(tmp_path, "devset")


def test_load_set_refuses_an_unknown_part(tmp_path):
    with pytest.raises(ValueError, match="part must be one of"):
        un.load_set(tmp_path, "trainset")


def test_documents_cuts_blocks_and_keeps_the_tail(tmp_path):
    docs = un.documents(un.load_set(make_set(tmp_path), "devset"), block=2)
    assert [len(d) for d in docs] == [2, 2, 1]
    assert docs[0][0] == ("Sentence 0 of the report.", "Предложение 0 доклада.")


def test_set_hash_is_stable_and_sees_a_changed_byte(tmp_path):
    make_set(tmp_path)
    first = un.set_hash(tmp_path, "devset")
    assert first == un.set_hash(tmp_path, "devset")
    target = tmp_path / "devset" / "UNv1.0.devset.ru"
    target.write_bytes(target.read_bytes().replace("доклада".encode(), "отчёта".encode(), 1))
    assert un.set_hash(tmp_path, "devset") != first

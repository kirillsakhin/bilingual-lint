from benchmark.contracts import CONTRACTS
from benchmark.mutate import OPERATORS, all_mutations


def test_three_contracts_with_two_filled_columns():
    assert [c["name"] for c in CONTRACTS] == ["services", "loan", "lease"]
    for contract in CONTRACTS:
        assert len(contract["rows"]) == 15
        assert all(a.strip() and b.strip() for a, b in contract["rows"])
        assert all(len(contract["parties"][side]) == 2 for side in ("a", "b"))


def test_every_operator_finds_work_in_every_contract():
    for contract in CONTRACTS:
        seen = {mutation.operator for _, mutation in
                all_mutations(contract["rows"], 1, contract["parties"])}
        assert seen == set(OPERATORS), contract["name"]


def test_party_names_appear_on_their_own_side():
    for contract in CONTRACTS:
        text_a = " ".join(a for a, _ in contract["rows"])
        text_b = " ".join(b for _, b in contract["rows"])
        assert all(name in text_a for name in contract["parties"]["a"])
        assert all(name in text_b for name in contract["parties"]["b"])

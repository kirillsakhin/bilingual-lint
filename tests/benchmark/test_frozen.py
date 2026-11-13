from benchmark import freeze


def test_the_mutation_tool_is_unchanged_since_the_freeze():
    assert freeze.problems() == []

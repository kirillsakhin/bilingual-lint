from bilingual_lint.config import RULE_DEFAULTS, Config
from bilingual_lint.models import Severity
from bilingual_lint.rules import ALL_RULES, run_all
from bilingual_lint.rules.base import Rule

from .helpers import make_doc


def test_every_rule_is_registered_once_and_has_defaults():
    ids = [rule.id for rule in ALL_RULES]
    assert ids == [f"BI{n:03d}" for n in range(1, 12)]
    assert set(ids) | {"BI000"} == set(RULE_DEFAULTS)
    for rule in ALL_RULES:
        assert isinstance(rule, Rule)
        assert RULE_DEFAULTS[rule.id]["severity"] == rule.default_severity.value


def test_run_all_sorts_and_reports_what_ran():
    doc = make_doc([("See clause 3.1.", "См. п. 3.4."), ("Pay 5 units.", "Оплатить 6 единиц.")])
    findings, ran, disabled, skipped = run_all(doc, Config())
    assert [f.rule_id for f in findings] == ["BI001", "BI006", "BI010"]
    assert ran == [f"BI{n:03d}" for n in range(12)] and disabled == [] and skipped == []


def test_run_all_respects_disabled_and_only():
    doc = make_doc([("Pay 5 units.", "Оплатить 6 единиц.")])
    config = Config()
    config.rules["BI001"]["enabled"] = False
    findings, ran, disabled, _ = run_all(doc, config, only={"BI001", "BI002"})
    assert findings == [] and ran == ["BI002"] and "BI001" in disabled


def test_low_confidence_pairs_are_downgraded():
    doc = make_doc([("Pay 5 units.", "Оплатить 6 единиц.")], mode="two-files")
    doc.pairs[0].confidence = 0.3
    (finding,) = run_all(doc, Config(), only={"BI001"})[0]
    assert finding.severity is Severity.WARNING
    assert finding.context["pairing"] == "low confidence — check the pairing first"


def test_rules_needing_wordlists_are_skipped_for_other_pairs():
    doc = make_doc([("Pay 5 units.", "Pagar 6 unidades.")], lang_a="en", lang_b="es")
    findings, ran, _, skipped = run_all(doc, Config())
    assert skipped == ["BI004", "BI005", "BI008", "BI010", "BI011"]
    assert [f.rule_id for f in findings] == ["BI001"]


def test_strict_separators_expose_a_convention_mix_up():
    rows = [("A fee of 1,000 units.", "Плата в размере 1,000 единиц.")]
    assert run_all(make_doc(rows), Config(), only={"BI001"})[0] == []
    config = Config()
    config.rules["BI001"]["strict_separators"] = True
    findings, *_ = run_all(make_doc(rows), config, only={"BI001"})
    assert [f.rule_id for f in findings] == ["BI001"]

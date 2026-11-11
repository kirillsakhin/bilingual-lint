import sys
import types

import pytest

from bilingual_lint.config import LLM_DEFAULTS, Config
from bilingual_lint.llm.reviewer import LlmUnavailable, run_llm_pass, unsettled_pairs
from bilingual_lint.models import Severity
from bilingual_lint.rules import run_all

from .helpers import make_doc

ROWS = [
    ("The Seller may not assign its rights.", "Продавец вправе уступать права."),
    ("Pay 5 units.", "Оплатить 6 единиц."),
]


def fake_litellm(monkeypatch, answers):
    calls = []

    def completion(model, messages, timeout):
        calls.append(messages[1]["content"])
        content = answers[len(calls) - 1]
        if isinstance(content, Exception):
            raise content
        message = types.SimpleNamespace(content=content)
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])

    monkeypatch.setitem(sys.modules, "litellm", types.SimpleNamespace(completion=completion))
    return calls


def prepared():
    doc = make_doc(ROWS)
    findings, *_ = run_all(doc, Config())
    return doc, findings


def test_only_unsettled_pairs_are_sent(monkeypatch):
    doc, findings = prepared()
    assert [p.pair_no for p in unsettled_pairs(findings)] == [1]
    calls = fake_litellm(monkeypatch, ['{"label": "differs", "reason": "negation lost"}'])
    status = run_llm_pass(doc, findings, dict(LLM_DEFAULTS), "test/model")
    assert len(calls) == 1 and "may not assign" in calls[0] and "5 units" not in calls[0]
    assert status == {"requested": True, "model": "test/model", "completed": 1,
                      "failed": 0, "capped": False}
    (suggestion,) = [f for f in findings if f.rule_id == "LLM"]
    assert suggestion.severity is Severity.INFO
    assert suggestion.message == "model suggestion: meaning differs — negation lost"
    bi011 = next(f for f in findings if f.rule_id == "BI011")
    assert bi011.context["llm"] == {"label": "differs", "reason": "negation lost"}


def test_scope_all_sends_every_complete_pair(monkeypatch):
    doc, findings = prepared()
    calls = fake_litellm(monkeypatch, ['{"label": "same", "reason": "ok"}'] * 2)
    status = run_llm_pass(doc, findings, dict(LLM_DEFAULTS, scope="all"), "test/model")
    assert len(calls) == 2 and "5 units" in calls[1]
    assert status["completed"] == 2


def test_gate_turns_differs_into_an_error(monkeypatch):
    doc, findings = prepared()
    fake_litellm(monkeypatch, ['{"label": "differs", "reason": "x"}'])
    run_llm_pass(doc, findings, dict(LLM_DEFAULTS), "test/model", gate=True)
    assert next(f for f in findings if f.rule_id == "LLM").severity is Severity.ERROR


def test_same_adds_no_finding_and_unclear_is_kept(monkeypatch):
    doc, findings = prepared()
    fake_litellm(monkeypatch, ['Sure: {"label": "same", "reason": "equivalent"}'])
    run_llm_pass(doc, findings, dict(LLM_DEFAULTS), "test/model")
    assert not [f for f in findings if f.rule_id == "LLM"]
    doc, findings = prepared()
    fake_litellm(monkeypatch, ['{"label": "unclear", "reason": "cannot tell"}'])
    run_llm_pass(doc, findings, dict(LLM_DEFAULTS), "test/model", gate=True)
    assert next(f for f in findings if f.rule_id == "LLM").severity is Severity.INFO


def test_failures_are_counted_not_hidden(monkeypatch):
    for bad in (RuntimeError("boom"), "no json here", '{"label": "maybe"}'):
        doc, findings = prepared()
        fake_litellm(monkeypatch, [bad])
        status = run_llm_pass(doc, findings, dict(LLM_DEFAULTS), "test/model")
        assert (status["completed"], status["failed"]) == (0, 1)
        assert not [f for f in findings if f.rule_id == "LLM"]


def test_cap_is_reported(monkeypatch):
    doc, findings = prepared()
    calls = fake_litellm(monkeypatch, [])
    status = run_llm_pass(doc, findings, dict(LLM_DEFAULTS, max_pairs=0), "test/model")
    assert calls == [] and status["capped"] is True


def test_missing_extra_gives_a_clear_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "litellm", None)
    doc, findings = prepared()
    with pytest.raises(LlmUnavailable, match=r"bilingual-lint\[llm\]"):
        run_llm_pass(doc, findings, dict(LLM_DEFAULTS), "test/model")

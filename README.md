# bilingual-lint

[![CI](https://github.com/kirillsakhin/bilingual-lint/actions/workflows/ci.yml/badge.svg)](https://github.com/kirillsakhin/bilingual-lint/actions/workflows/ci.yml)

A linter for bilingual legal documents. Give it a contract in two languages and it
reports where the two versions disagree: a different amount, a different date, a
missing paragraph, a clause that makes English prevail on the left and Russian on
the right. Deterministically, offline, the same way every time.

## Why

A bilingual contract is one deal written twice. Every number, date, deadline and
party name has to be the same in both columns, and nobody enjoys checking that by
eye on page 40.

The obvious 2026 answer is "have an LLM compare the two versions". It helps with
meaning, but it is the wrong tool for facts: it can pass a changed digit in one
clause and flag the same thing in another, and two runs disagree with each other.

So bilingual-lint does it the other way around. Rules check the facts: they catch
the same defect every time, need no API key and send nothing anywhere. A model
comes second, optionally, and only for the pairs the rules cannot settle.

It does not judge translation style or quality. It checks what must be identical.

## Install

From a clone of this repository:

```
pip install -e .
```

Python 3.10 or newer. The optional model pass needs `pip install -e ".[llm]"`.

## Quickstart

A two-column bilingual DOCX:

```
bilingual-lint check contract.docx
```

A source file and its translation:

```
bilingual-lint check contract_en.docx contract_ru.docx
```

Against the bundled sample ([`examples/sample_en_ru.docx`](examples/sample_en_ru.docx),
an invented contract with twelve planted defects), `--format md` gives, in part:

```
# bilingual-lint report

- Mode: two-column, en / ru
- Pairs checked: 13 (0 without a counterpart)
- Findings: 12, 8 error, 3 warning, 1 info

## BI002 · error · pair 4

amounts differ — en only: 150,000 · ru only: 105 000

## BI005 · error · pair 5

duration day type differs — business against calendar days (en: 10, ru: 10)

## BI010 · error · pair 9

the two sides disagree on which language prevails — en side: en · ru side: ru

## BI004 · error · pair 10

digits and words disagree on the ru side — 3 against "двух"
```

The clean copy of the same contract ([`examples/clean_en_ru.docx`](examples/clean_en_ru.docx))
produces no findings.

Exit codes: `0` nothing at or above the threshold, `1` findings, `2` the input
could not be read or the command was wrong. That makes it usable as a gate after
a translation step.

## Rules

| Code | Checks | Default | Languages |
|---|---|---|---|
| BI000 | Notes about the file: tracked changes, comments, text outside the bilingual table | info | any |
| BI001 | A number or percentage appears on one side only | error | any |
| BI002 | A money amount or its currency differs | error | any |
| BI003 | A date differs, or agrees only under one day/month reading (`02/03/2025`) | error | any |
| BI004 | Digits and words disagree on the same side: `ten (15)` | error | en, ru |
| BI005 | A time period differs in length, unit or day type (30 days vs 30 business days) | error | en, ru |
| BI006 | A clause number or cross-reference differs | warning | any |
| BI007 | A segment is missing, empty, untranslated or far off in length | error | any |
| BI008 | A defined term or glossary term is rendered inconsistently | warning | en, ru |
| BI009 | A registration number, IBAN, e-mail or URL differs | error | any |
| BI010 | The prevailing-language clause is one-sided or contradicts itself | error | en, ru |
| BI011 | Obligation, permission or negation wording differs (heuristic) | info | en, ru |

"any" rules work for every language pair. The others need a wordlist and currently
ship for English and Russian; for other pairs they are skipped, and the report
says which.

### How numbers are compared

`1,000` is one thousand in English and exactly one in Russian. bilingual-lint does
not guess: an ambiguous number keeps both readings and matches if either agrees
with the other side. Set `strict_separators: true` to read each language by its
own convention only.

A number spelled out on one side (`two copies` / `2 экземпляра`) is not a defect.

## Two separate files

Paragraphs are paired deterministically: first at anchors (clause numbers and
paragraphs with a unique set of digits), then by length between anchors. A
paragraph with no partner becomes a finding. Each pair has a confidence value; for
low-confidence pairs the report says "check the pairing first" and errors are
shown as warnings.

## Options

```
bilingual-lint check FILE [FILE]
  --langs en,es         name the two languages (needed when they share a script)
  --glossary terms.yaml term pairs to enforce:  - {en: Buyer, ru: Покупатель}
  --config FILE         use this config file instead of ./.bilingual-lint.yaml
  --format console|json|md
  --output report.json
  --fail-on error|warning
  --rules BI001,BI010   run only these rules
  --llm MODEL           optional model pass (see below)
  --llm-gate            treat a model answer of "differs" as an error
bilingual-lint rules    list the rules
bilingual-lint init     write a starter .bilingual-lint.yaml
```

## Optional model pass

`--llm` sends only the pairs the rules flagged but could not settle (BI011 and
low-confidence pairs) to a model through [litellm](https://github.com/BerriAI/litellm)
and asks one question: do these two texts say the same thing? Answers are marked
as model suggestions and do not change the exit code unless you pass `--llm-gate`.

**Without `--llm`, no text leaves your machine.** With it, the flagged pairs go to
the provider of the model you chose. Decide whether that is acceptable for the
document in front of you.

## Limits

- DOCX only. No PDF, no scanned documents.
- Headers, footers, footnotes and text boxes anchored outside the body are not read.
- Tracked changes are read as if accepted; the report says when a file has them.
- Word-based rules exist for English and Russian only.
- BI011 is a wordlist heuristic and will produce false flags; it is `info` for that reason.
- In two-file mode a short missing paragraph next to a long one can be absorbed
  into its neighbour instead of being reported as missing.
- No accuracy figures are published yet. A benchmark on public bilingual texts
  with planted defects is the next milestone; until then, treat the tool as a
  second pair of eyes, not as proof that a document is clean.

## Development

```
pip install -e ".[dev]"
pytest -q
ruff check .
python examples/build_examples.py   # rebuild the example documents
```

## Licence

MIT. See [LICENSE](LICENSE).

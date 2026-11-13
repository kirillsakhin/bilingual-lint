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
comes second, optionally, and by default only for the pairs the rules cannot
settle.

It does not judge translation style or quality. It checks what must be identical.

## Install

```
pip install bilingual-lint
```

Python 3.10 or newer. The optional model pass needs
`pip install "bilingual-lint[llm]"`.

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
| BI002 | A money amount or its currency differs, or the two sides name different currencies | error | any |
| BI003 | A date or a time of day differs, or a date agrees only under one day/month reading (`02/03/2025`) | error | any |
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
  --llm-scope SCOPE     flagged (default) or all
bilingual-lint rules    list the rules
bilingual-lint init     write a starter .bilingual-lint.yaml
```

## Optional model pass

`--llm` sends only the pairs the rules flagged but could not settle (BI011 and
low-confidence pairs) to a model through [litellm](https://github.com/BerriAI/litellm)
and asks one question: do these two texts say the same thing? Answers are marked
as model suggestions and do not change the exit code unless you pass `--llm-gate`.

`--llm-scope all` sends every pair instead, up to `llm.max_pairs`. That is the
only way to catch wording dropped from one side when no number or defined term
gives it away, and it means the whole document goes to the provider. Pairs with
nothing to compare (the same text on both sides, or no words at all) are not
sent; the report counts them as skipped.

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
- The [benchmark](#benchmark) plants one defect at a time in UN prose and in
  three invented contracts. It does not show that a document with no findings
  is clean: treat the tool as a second pair of eyes.

## Benchmark

Measured on the test set of the United Nations Parallel Corpus v1.0:
4,000 English and Russian sentence pairs cut into 100 documents.
One defect at a time was planted by a tool that was frozen before any rule was
tuned and shares no code with the linter. The test set was held out, pinned by
hash and scored once, at commit `1ad1e09` (released as 0.1.2). Method, limits
and how to run it again: [benchmark/README.md](benchmark/README.md).

| Measure | Target | Result | Met |
|---|---|---|---|
| Planted number, amount, date and identifier defects caught | at least 0.98 | 0.9989 | yes |
| Dropped paragraphs caught | at least 0.95 | 1.0 | yes |
| False flags on clean pairs, error severity, per 100 pairs | at most 3.0 | 1.9 | yes |
| Correct pairing in two-file mode | at least 0.95 | 0.9885 | yes |

All four targets were met on the hold-out.

The linter raised 96 error-level findings on the unmodified text. Read by
hand, 20 are real differences between the two published versions (a line
cut short, a figure present on one side only) and 76 are false flags. With
every finding counted as a false flag the rate is 2.4 per 100 pairs. In
two-file mode the pairing figure above is with one paragraph missing from one
side; with nothing missing, pairing was correct
for 0.9985 of the rows.

| Planted defect | Planted | Caught | Recall |
|---|---|---|---|
| a digit changed | 2736 | 2736 | 1.0 |
| the day of a date changed | 711 | 711 | 1.0 |
| a clause or paragraph reference changed | 283 | 283 | 1.0 |
| a currency changed | 69 | 65 | 0.942 |
| a negation dropped (BI011, an `info` hint) | 32 | 21 | 0.6562 |
| a paragraph dropped | 7153 | 7153 | 1.0 |

### Invented contracts (45 rows, weaker evidence)

UN documents have almost no prices, bank details, party names or
prevailing-language clauses, so those defects were planted in three invented
contracts. The contracts were written by the author of the rules.

| Planted defect | Planted | Caught | Recall |
|---|---|---|---|
| a digit changed | 38 | 38 | 1.0 |
| the day of a date changed | 14 | 14 | 1.0 |
| a clause or paragraph reference changed | 8 | 8 | 1.0 |
| a currency changed | 14 | 13 | 0.9286 |
| "business days" changed to "days" | 13 | 12 | 0.9231 |
| a negation dropped (BI011, an `info` hint) | 10 | 4 | 0.4 |
| the prevailing language flipped | 6 | 6 | 1.0 |
| an identifier changed | 6 | 6 | 1.0 |
| a party name swapped | 25 | 25 | 1.0 |
| a paragraph dropped | 78 | 78 | 1.0 |

### Against a model reading the whole document

`anthropic/claude-sonnet-5` was given the same mutated copies of the first 25
hold-out documents, one planted defect of each kind per document, and asked to
name the rows that differ. A defect on a row the model had already named in
the clean copy is left out of its count.

| Planted defect | Model | Linter |
|---|---|---|
| a digit changed | 25 of 25 | 25 of 25 |
| the day of a date changed | 23 of 23 | 24 of 24 |
| a clause or paragraph reference changed | 22 of 22 | 22 of 22 |
| a currency changed | 10 of 11 | 10 of 11 |
| a negation dropped (BI011, an `info` hint) | 4 of 4 | 4 of 4 |
| a paragraph dropped | 25 of 25 | 25 of 25 |

On clean text the model named 4.4 rows per 100 pairs, and on a mutated copy
it named 0.17 rows besides the planted one. One model, one run, one prompt.

## Development

```
pip install -e ".[dev]"
pytest -q
ruff check .
python examples/build_examples.py   # rebuild the example documents
```

## Licence

MIT. See [LICENSE](LICENSE).

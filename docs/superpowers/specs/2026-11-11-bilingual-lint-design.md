# bilingual-lint — v0.1 design

Date: 2026-11-11. Status: draft for review. Licence: MIT.

## 1. What it is

A command-line linter for bilingual legal documents. Give it a contract in two
languages and it reports where the two versions disagree: a different amount, a
different date, a missing paragraph, a clause that prevails in one language on the
left and in the other on the right.

It does not judge translation style or quality. It checks the things that must be
identical in both versions, and it checks them the same way every time.

## 2. Who it is for

- Lawyers signing or reviewing a two-language contract.
- Translators and translation vendors doing a final check before delivery.
- Anyone running a machine or LLM translation pipeline who wants a deterministic
  gate after it.

## 3. Decisions already made

| Decision | Choice |
|---|---|
| Input | Two-column bilingual DOCX, and two separate DOCX files |
| Languages | Language-neutral core checks; word-based checks for English and Russian |
| Licence | MIT |
| Stack | Python >= 3.10, typer, rich, pyyaml, python-docx (same family as billing-lint) |
| LLM | Optional extra, off by default, never the first line of review |

## 4. Approaches considered

**A. Rules first, LLM second (chosen).** Deterministic extraction and comparison
of facts on each paired segment. An optional LLM pass looks only at pairs the rules
cannot settle. Repeatable, offline, usable as a CI gate, cheap to benchmark.

**B. LLM pairwise review with rule guards.** Send every pair to a model and use
rules as a safety net. Catches more meaning drift, but results vary between runs,
it needs an API key and it sends contract text to a third party by default.

**C. Quality-estimation model scoring.** Score each pair with a multilingual
embedding or QE model. Good at "something is off here", poor at saying what, and
weak exactly where contracts break: a single changed digit barely moves a score.

A is chosen. B survives as the optional pass. C is not built.

## 5. Pipeline

```
load -> segment -> pair -> extract facts -> compare (rules) -> report
                                              \-> optional LLM pass on unsettled pairs
```

Each stage is a separate module with a typed interface, so each can be tested alone.

### 5.1 Load

- **Two-column DOCX.** Find tables where one column is mostly Latin script and the
  other mostly Cyrillic (script detection per cell, majority vote per column).
  Each row is one pair. Text outside such tables is reported as unpaired, not
  dropped. For pairs that share a script (for example English and Spanish) the
  user names the columns with `--langs en,es`; the tool does not guess.
- **Two files.** Read both as ordered paragraph lists, including table cells.
- **Tracked changes.** The document is read as if all changes were accepted. If
  tracked changes or comments are present, the report says so at the top.
- **Refusals.** Not a DOCX, password-protected, or no bilingual content found:
  exit code 2 with a plain reason. No guessing.

### 5.2 Segment

A row or paragraph is split into sentences only when both sides split into the
same number of sentences. Otherwise the pair stays whole. This keeps findings
precise without inventing alignments.

### 5.3 Pair (two-file mode only)

Deterministic alignment in two passes:

1. **Anchors.** Clause numbers, headings and paragraphs with a unique numeric
   signature pin the two texts together.
2. **Between anchors.** Length-based dynamic programming (Gale-Church style),
   allowing 1-1, 1-2, 2-1, 1-0 and 0-1 matches.

Every pair carries a confidence value. Low-confidence pairs are labelled as such
in the report, and their findings are downgraded to "check pairing first". Segments
left unpaired become findings of their own (BI007). Nothing is silently skipped.

### 5.4 Extract facts

For each side of a pair, extract a normalised set of facts:

- numbers (handling `1,000.00`, `1 000,00`, `1.000,00`, non-breaking spaces)
- money amounts with currency (`USD`, `$`, `долл. США`, `RUB`, `₽`, `руб.`)
- dates (numeric and written month names in EN and RU)
- percentages
- durations with unit and day type (calendar, business, banking)
- clause numbers and cross-references
- identifiers: registration and tax numbers, IBAN, email, URL
- numbers written in words next to digits, e.g. `ten (10)`, `десять (10)`

Extraction lives apart from the rules so that both can be tested independently.

## 6. Rules in v0.1

Codes use the prefix `BI`. Severity is `error`, `warning` or `info`.

| Code | Checks | Severity | Language |
|---|---|---|---|
| BI000 | File structure: unreadable, not bilingual, tracked changes present | error / info | neutral |
| BI001 | Numbers differ between the two sides | error | neutral |
| BI002 | Amount or currency differs | error | neutral + EN/RU |
| BI003 | Dates differ; ambiguous day/month order such as `02/03/2025` | error / warning | neutral + EN/RU |
| BI004 | Digits and words disagree inside one side, e.g. `ten (15)` | error | EN/RU |
| BI005 | Duration differs in value, unit or day type (30 days vs 30 business days) | error | EN/RU |
| BI006 | Clause number or cross-reference differs | warning | neutral |
| BI007 | Missing, extra or empty segment; text left untranslated; length ratio far off | error / warning | neutral |
| BI008 | Term consistency: a defined term or party name rendered two different ways; glossary violations | warning | EN/RU |
| BI009 | Identifiers differ (tax number, IBAN, email, URL) | error | neutral |
| BI010 | Prevailing-language clause: missing on one side, or each side names a different language | error | EN/RU |
| BI011 | Obligation and negation cues differ (shall / may / must not vs обязан / вправе / не вправе) | info | EN/RU |

Notes:

- **BI008** learns term pairs from the document's own definitions (`"Buyer"` /
  `«Покупатель»`) and from an optional user glossary in YAML.
- **BI011** is a wordlist heuristic and will produce false flags. It is `info`
  only, never fails a run by default, and is the main feeder for the LLM pass.
- Rules for language pairs other than EN/RU run the neutral checks only, and the
  report says which checks were skipped.

## 7. Optional LLM pass

- Installed with `bilingual-lint[llm]`, switched on with `--llm`.
- Looks only at pairs flagged by BI011 or with low-confidence findings.
- Returns one of three labels per pair: same meaning, differs, unclear. "Unclear"
  is kept as a finding.
- Findings are marked as model suggestions and do not change the exit code unless
  the user asks for that.
- Without `--llm` no text leaves the machine. The README states this plainly.

## 8. Output

- Console report (rich), with user text escaped.
- JSON for tooling.
- Markdown report with the two sides of each flagged pair shown next to each other.
- Exit codes: 0 clean, 1 findings at or above the chosen severity, 2 input error.
- Config in `.bilingual-lint.yaml`: severity threshold, disabled rules, glossary
  path, number-format hints.

Not in v0.1: writing comments back into the DOCX, an HTML viewer.

## 9. Benchmark

The repository publishes a benchmark and whatever numbers it produces.

- **Source texts.** Public parallel EN/RU legal texts whose licence allows reuse.
  Candidates: UN documents, WIPO treaty texts [TO CONFIRM: licence terms for each
  source before any text is committed]. No client or firm documents, ever.
- **Planted defects.** A mutation tool changes one thing per copy: a digit, a
  currency, a date, a day type, a clause reference, a dropped paragraph, a swapped
  party, a flipped prevailing-language clause, a dropped negation. The mutation
  tool is written and frozen before the rules are tuned, and it does not share
  code with the extractors.
- **Clean arm.** Unmodified pairs measure the false-flag rate. Real discrepancies
  found in the public texts are adjudicated by hand and reported separately.
- **Protocol.** A development set for tuning and a holdout set pinned by hash and
  scored once. Reading holdout failures means pinning a new holdout.
- **Comparison arm.** One whole-document LLM review of the same mutated files, to
  test the claim that rules-first is more reliable for this class of error.

Targets fixed before scoring (targets, not results):

| Measure | Target |
|---|---|
| Recall on planted number, amount, date and identifier defects | >= 98% |
| Recall on dropped or extra paragraphs | >= 95% |
| False flags on clean pairs, `error` severity | <= 3 per 100 pairs |
| Correct pairing in two-file mode | >= 95% of paragraphs |

If a target is missed, the README says so.

## 10. Testing

- Unit tests per extractor and per rule, each with a failing and a passing case.
- Every rule is proven able to fail: remove the fix, the test goes red.
- Golden reports for bundled example documents, in JSON and Markdown.
- DOCX fixtures are created in Word-compatible form and opened in Word once before
  release.
- A guard test keeps firm names and internal terms out of the repository.
- CI on Ubuntu and Windows across supported Python versions.

## 11. Out of scope for v0.1

- PDF input and OCR
- Wordlists for languages other than English and Russian
- Translation quality or style scoring
- Fixing or rewriting the document
- Comments written back into Word, HTML viewer, Word add-in
- Embedding-based alignment

## 12. Provenance

Built clean, in public, with no code shared with any internal system. What carries
over is the lesson: check the facts with rules, and use a model only where rules
run out.

## 13. Open items

1. Licence terms of the benchmark source texts [TO CONFIRM].
2. Package name `bilingual-lint` was free on PyPI on 2026-11-11; not reserved.
3. Right-to-left and CJK pairs are untested; the neutral checks should work in
   principle, with no claim made.

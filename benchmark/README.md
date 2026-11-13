# Benchmark

How often does bilingual-lint catch a planted defect, and how often does it
flag text that has none? This folder holds the tool that plants the defects,
the scorer, the results and everything needed to run it again.

## Method

- **Text.** English and Russian from the development and test sets of the
  United Nations Parallel Corpus v1.0: 4,000 aligned sentences each, from
  official documents of 2015. The sets are samples, so a benchmark document is
  a block of 40 consecutive sentences: 100 documents per set.
- **Planted defects.** `mutate.py` changes one thing on one side of one row: a
  digit, the day of a date, a clause reference, a currency, a day type
  ("business days" to "days"), a negation, the prevailing language, an
  identifier, a party name, or a whole paragraph. It uses the standard library
  only and shares no code with the linter.
- **A catch.** Each copy is written to a DOCX and linted the way a user's file
  is. A defect is caught when the linter says something about the changed row
  that it did not say about the clean copy.
- **Clean text.** Error-level findings on unmodified text were read by a person
  and marked as a false flag or as a real difference between the two published
  versions. A finding nobody judged counts as a false flag.
- **Protocol.** `mutate.py` and both sets were pinned by hash in `FROZEN.json`
  before any rule was tuned. The development set was used for tuning. The test
  set is the hold-out: the tool refuses to score it twice.
- **Comparison.** A model was given the same mutated copies as whole documents
  and asked to name the rows that differ. It saw the first 25 documents of each
  set, one planted defect of each kind per document.
- **Contracts.** UN documents have almost no prices, bank details, party names
  or prevailing-language clauses. Those defects are planted in three invented
  contracts (`contracts.py`). The contracts were written by the author of the
  rules, so that result is weaker evidence and is reported on its own.

## Limits

- The text is UN prose, not contracts. Contract-only defects rest on 45
  invented rows.
- One language pair. Defects are planted in two-column DOCX files; two-file
  mode is used for the pairing measure only.
- One model, one run, one prompt for the comparison.
- While the archive's format was inspected, six sentences of the test set were
  printed and seven pattern counts were taken over its English file. No linter
  was run on it and no code changed because of it.
- The verdicts on clean text are one reader's. A line that is cut short in
  the corpus, or a page reference that differs between the two editions, was
  counted as a real difference; the note beside each verdict says why.

## Run it again

The UN server refuses automated downloads, so fetch the archive in a browser:
<https://www.un.org/dgacm/sites/www.un.org.dgacm/files/files/UNCORPUS/UNv1.0.testsets.tar.gz>

```bash
mkdir -p benchmark/data && cp UNv1.0.testsets.tar.gz benchmark/data/
cd benchmark/data && tar -xzf UNv1.0.testsets.tar.gz && cd ../..
python -m pytest tests/benchmark/test_frozen.py -q
python -m benchmark.run dev --data benchmark/data/testsets
python -m benchmark.run contracts
```

`FROZEN.json` holds the SHA-256 of the archive and of each set. The hold-out
result in `results/holdout.json` records the commit it was scored at; to
reproduce it, check out that commit, delete the result file and run
`python -m benchmark.run holdout --data benchmark/data/testsets`.

The data belongs to the United Nations Parallel Corpus; see `NOTICE` in the
repository root for the attribution and the disclaimer.

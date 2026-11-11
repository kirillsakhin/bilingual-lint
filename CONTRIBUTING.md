# Contributing

Thanks for taking a look.

## Setup

```
pip install -e ".[dev]"
pytest -q
ruff check .
```

## Ground rules

- **Rules first.** A check that can be done deterministically is done
  deterministically. The model pass is for what rules cannot settle.
- **Every rule has two tests:** a clean case that must stay silent and a defect
  that must be found. A rule that cannot be made to fail is not a rule.
- **No real documents.** Examples and fixtures are invented. Do not add client,
  firm or personal data to the repository, in any form.
- **Say what you could not read.** If the tool cannot determine something, it
  reports that or stays silent. It does not guess.

## Adding a language

Add `src/bilingual_lint/wordlists/<code>.yaml` with the same keys as `en.yaml`.
Entries are regular-expression fragments. The word-based rules pick the language
up automatically once both languages of a pair have a wordlist. Add tests next
to the existing English and Russian ones.

## Adding a rule

One file in `src/bilingual_lint/rules/`, one entry in `ALL_RULES`, one entry in
`RULE_DEFAULTS`, one row in the README table, and tests.

# Changelog

## 0.1.0 — unreleased

First version.

- Input: two-column bilingual DOCX, or two separate DOCX files paired by
  clause numbers, digit signatures and length.
- Twelve rules, BI000 to BI011: numbers, amounts and currency, dates,
  digits against words, durations and day types, clause references, missing or
  untranslated text, defined terms and glossary, identifiers, the
  prevailing-language clause, obligation and negation cues.
- Language-neutral rules for any pair; word-based rules for English and Russian.
- Console, JSON and Markdown reports; exit codes for use as a pipeline gate.
- Optional model pass (`--llm`) for pairs the rules cannot settle. Off by default.

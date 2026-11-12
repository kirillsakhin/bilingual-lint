# Changelog

## 0.1.0 — 2026-11-12

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
  `--llm-scope all` sends every pair instead, to catch wording dropped from one
  side when no number or term gives it away. Pairs with the same text on both
  sides, or with no words, are skipped; headings and labels no longer come back
  as "unclear".
- After a first run over real two-column documents: times of day are compared
  (`21:00` against `9 p.m.`); a currency named without an amount is compared;
  a clause reference worded differently on one side no longer reads as a
  number mismatch; a defined term matches its singular and plural and keeps
  its capital letter; a Latin name kept on a non-Latin side is not reported as
  untranslated; fewer false negation and obligation cues (`No. 15`, `unless`,
  `shall be entitled to`).

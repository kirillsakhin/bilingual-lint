from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from . import __version__
from .config import LLM_SCOPES, RULE_DEFAULTS, Config, ConfigError, load_glossary, parse_langs
from .loaders import LoaderError, load
from .models import Severity
from .report.console import render_console
from .report.json_out import to_json
from .report.markdown import to_markdown
from .rules import ALL_RULES, run_all, sort_key
from .segment import refine

app = typer.Typer(add_completion=False,
                  help="A linter for bilingual legal documents.")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"bilingual-lint {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """bilingual-lint: find where two language versions of a contract disagree."""


def _fail(message: str) -> typer.Exit:
    typer.secho(f"error: {message}", err=True, fg=typer.colors.RED)
    return typer.Exit(2)


@app.command()
def check(
    files: list[Path] = typer.Argument(
        ..., help="One two-column bilingual DOCX, or two DOCX files (source, translation)"),
    langs: Optional[str] = typer.Option(
        None, "--langs", help="Two language codes, e.g. en,ru (left,right or first,second)"),
    config_path: Optional[Path] = typer.Option(
        None, "--config", help="Path to .bilingual-lint.yaml"),
    glossary: Optional[Path] = typer.Option(
        None, "--glossary", help="YAML glossary of term pairs"),
    output_format: str = typer.Option("console", "--format", help="console | json | md"),
    output: Optional[Path] = typer.Option(
        None, "--output", help="Write the report to a file (json/md only)"),
    fail_on: Optional[str] = typer.Option(
        None, "--fail-on", help="error | warning (default from config)"),
    rules_filter: Optional[str] = typer.Option(
        None, "--rules", help="Comma-separated rule IDs to run (e.g. BI001,BI010)"),
    llm: Optional[str] = typer.Option(
        None, "--llm",
        help='Run the model pass: a litellm model string, or "default" for the '
             "configured llm.model. Sends flagged text to that model's provider."),
    llm_gate: bool = typer.Option(
        False, "--llm-gate", help="Treat a model answer of 'differs' as an error"),
    llm_scope: Optional[str] = typer.Option(
        None, "--llm-scope",
        help="flagged: only pairs the rules could not settle (default). "
             "all: every pair, up to llm.max_pairs; sends the whole document."),
) -> None:
    """Lint a bilingual document and report findings."""
    if output_format not in ("console", "json", "md"):
        raise _fail(f"unknown --format {output_format!r} (use console, json or md)")
    if fail_on not in (None, "error", "warning"):
        raise _fail("--fail-on must be error or warning")
    if output_format == "console" and output:
        raise _fail("--output requires --format json or --format md")
    if len(files) > 2:
        raise _fail("pass one bilingual DOCX, or two DOCX files")
    try:
        config = Config.load(config_path)
        if langs:
            config.langs = parse_langs(langs)
        if glossary:
            config.glossary = load_glossary(glossary)
    except ConfigError as exc:
        raise _fail(str(exc)) from exc
    only: Optional[set] = None
    if rules_filter:
        only = {r.strip().upper() for r in rules_filter.split(",") if r.strip()}
        unknown = only - set(RULE_DEFAULTS)
        if unknown:
            raise _fail(f"unknown rule ids: {', '.join(sorted(unknown))}")
    try:
        doc = refine(load(files, config.langs))
    except LoaderError as exc:
        raise _fail(str(exc)) from exc

    findings, ran, disabled, skipped = run_all(doc, config, only=only)

    llm_status: dict = {"requested": False}
    if llm is not None:
        from .llm.reviewer import LlmUnavailable, run_llm_pass

        model = config.llm["model"] if llm in ("default", "") else llm
        if llm_scope is not None:
            config.llm["scope"] = llm_scope
        if config.llm["scope"] not in LLM_SCOPES:
            raise _fail(f"unknown llm scope {config.llm['scope']!r} (use flagged or all)")
        try:
            llm_status = run_llm_pass(doc, findings, config.llm, model, gate=llm_gate)
        except LlmUnavailable as exc:
            raise _fail(str(exc)) from exc
        findings.sort(key=sort_key)

    if output_format == "json":
        text = to_json(doc, findings, ran, disabled, skipped, llm_status)
    elif output_format == "md":
        text = to_markdown(doc, findings, ran, disabled, skipped, llm_status)
    else:
        text = None
    if text is not None and output:
        output.write_text(text, encoding="utf-8")
    elif text is not None:
        typer.echo(text)
    else:
        render_console(doc, findings, ran, disabled, skipped, llm_status)

    threshold = Severity(fail_on or config.fail_on).rank
    if any(f.severity.rank >= threshold for f in findings):
        raise typer.Exit(1)


@app.command("rules")
def rules_command() -> None:
    """List all rules with their default severities."""
    typer.echo("BI000  file-structure       info     any    notes about the file: "
               "tracked changes, comments, text outside the bilingual table")
    for rule in ALL_RULES:
        scope = "en/ru" if rule.needs_wordlists else "any"
        typer.echo(f"{rule.id}  {rule.name:<20} {rule.default_severity.value:<8} "
                   f"{scope:<6} {rule.description}")


STARTER_CONFIG = """\
# bilingual-lint configuration. Every key is optional; delete what you don't need.

# langs: en,ru          # needed only when the two languages share a script
fail_on: error          # exit 1 at or above this severity: error | warning
# glossary: glossary.yaml   # list of term pairs: - {en: Buyer, ru: Покупатель}
low_confidence: 0.5     # two-file mode: below this, findings say "check pairing first"

rules:
  # BI001:
  #   strict_separators: true   # read 1,000 by each language's own convention only
  # BI011:
  #   enabled: false

llm:
  model: anthropic/claude-sonnet-5
  max_pairs: 50
  timeout_seconds: 60
  scope: flagged   # or "all": every pair goes to the model, up to max_pairs
"""


@app.command()
def init() -> None:
    """Write a starter .bilingual-lint.yaml into the current directory."""
    target = Path(".bilingual-lint.yaml")
    if target.exists():
        raise _fail(f"{target} already exists — not overwriting")
    target.write_text(STARTER_CONFIG, encoding="utf-8")
    typer.echo(f"wrote {target}")

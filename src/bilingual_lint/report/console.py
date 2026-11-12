from __future__ import annotations

from rich.console import Console
from rich.markup import escape

from ..models import Document

STYLES = {"error": "bold red", "warning": "yellow", "info": "cyan"}
PREVIEW = 160


def _preview(text: str | None) -> str:
    if not text:
        return "—"
    flat = " ".join(text.split())
    return flat if len(flat) <= PREVIEW else flat[:PREVIEW - 1] + "…"


def render_console(doc: Document, findings: list, ran: list, disabled: list,
                   skipped: list, llm_status: dict | None = None,
                   console: Console | None = None) -> None:
    """Every string that comes from the document goes through escape():
    rich would otherwise read '[client name]' as markup and swallow it."""
    console = console or Console()
    names = ", ".join(str(path) for path in doc.source_paths)
    console.print(f"[bold]bilingual-lint[/bold] — {escape(names)}")
    console.print(f"mode={doc.mode} languages={escape(doc.lang_a)}/{escape(doc.lang_b)} "
                  f"pairs={len(doc.pairs)}")
    if skipped:
        console.print(f"not run for this language pair: {', '.join(skipped)}")
    console.print()
    for finding in findings:
        pair = finding.pair
        where = f"pair {pair.pair_no}" if pair else "document"
        style = STYLES[finding.severity.value]
        console.print(f"[{style}]{finding.severity.value:<7}[/{style}] "
                      f"{finding.rule_id}  {where}  {escape(finding.message)}")
        if finding.context.get("pairing"):
            console.print(f"         {escape(finding.context['pairing'])}", style="dim")
        if pair:
            a = pair.a.text if pair.a else None
            b = pair.b.text if pair.b else None
            console.print(f"         {escape(doc.lang_a)}: {escape(_preview(a))}", style="dim")
            console.print(f"         {escape(doc.lang_b)}: {escape(_preview(b))}", style="dim")
    counts: dict = {}
    for finding in findings:
        counts[finding.severity.value] = counts.get(finding.severity.value, 0) + 1
    summary = ", ".join(f"{count} {name}" for name, count in counts.items()) or "no findings"
    console.print()
    console.print(f"[bold]{summary}[/bold]")
    if llm_status and llm_status.get("requested"):
        console.print(f"model pass: {escape(str(llm_status['model']))}, "
                      f"{llm_status['completed']} reviewed, {llm_status['failed']} failed"
                      + (f", {llm_status['skipped']} skipped (nothing to compare)"
                         if llm_status.get("skipped") else ""))

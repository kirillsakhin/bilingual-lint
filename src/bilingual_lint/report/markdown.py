from __future__ import annotations

from ..models import Document
from .json_out import build_report


def _cell(text: str | None) -> str:
    if not text:
        return "—"
    return text.replace("|", "\\|").replace("\n", "<br>")


def to_markdown(doc: Document, findings: list, ran: list, disabled: list,
                skipped: list, llm_status: dict | None = None) -> str:
    report = build_report(doc, findings, ran, disabled, skipped, llm_status)
    source, summary = report["source"], report["summary"]
    names = ", ".join(f"`{path}`" for path in source["paths"])
    lines = [
        "# bilingual-lint report",
        "",
        f"- Source: {names}",
        f"- Mode: {source['mode']}, {source['lang_a']} / {source['lang_b']}",
        f"- Pairs checked: {source['pairs']} ({source['unpaired']} without a counterpart)",
        f"- Findings: {summary['total']}"
        + "".join(f", {count} {name}" for name, count in summary["by_severity"].items()),
    ]
    if skipped:
        lines.append(f"- Not run for this language pair: {', '.join(skipped)}")
    if disabled:
        lines.append(f"- Disabled: {', '.join(disabled)}")
    llm = report["llm_pass"]
    if llm.get("requested"):
        lines.append(f"- Model pass: {llm['model']}, {llm['completed']} pair(s) reviewed, "
                     f"{llm['failed']} failed"
                     + (f", {llm['skipped']} skipped (nothing to compare)"
                        if llm.get("skipped") else ""))
    lines.append("")
    if not report["findings"]:
        lines.append("No findings.")
    for item in report["findings"]:
        where = f"pair {item['pair_no']}" if item["pair_no"] else "document"
        lines.append(f"## {item['rule_id']} · {item['severity']} · {where}")
        lines.append("")
        lines.append(item["message"])
        if item["context"].get("pairing"):
            lines.append("")
            lines.append(f"_Pairing: {item['context']['pairing']}_")
        if item["pair_no"]:
            lines += [
                "",
                f"| {source['lang_a']} ({_cell(item['location_a'])}) "
                f"| {source['lang_b']} ({_cell(item['location_b'])}) |",
                "|---|---|",
                f"| {_cell(item['text_a'])} | {_cell(item['text_b'])} |",
            ]
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"

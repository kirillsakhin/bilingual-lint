"""Run the benchmark.

    python -m benchmark.run dev       --data benchmark/data/testsets
    python -m benchmark.run contracts
    python -m benchmark.run worksheet dev --data benchmark/data/testsets
    python -m benchmark.run llm dev   --data benchmark/data/testsets --llm-docs 25
    python -m benchmark.run holdout   --data benchmark/data/testsets

'holdout' scores the UN test set. It runs once: it needs a clean git tree and
an intact freeze, takes no sampling options, and refuses to run again."""
from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

import bilingual_lint

from . import adjudicate, freeze, llm_arm
from .contracts import CONTRACTS
from .score import score_document, summarise, targets
from .un import documents, load_set, set_hash

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
ADJUDICATION = HERE / "adjudication"
SEED = 20261113
UN_PART = {"dev": "devset", "holdout": "testset"}
TARGET_LABELS = {
    "figures_recall": "Recall on planted number, amount, date and identifier defects",
    "paragraphs_recall": "Recall on dropped paragraphs",
    "error_flags_per_100_pairs": "False flags on clean pairs, error severity, per 100 pairs",
    "pairing_accuracy": "Correct pairing in two-file mode",
}


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=HERE.parent, capture_output=True,
                          text=True, check=True).stdout.strip()


def load_documents(part: str, data: Path | None) -> tuple:
    """(documents, parties per document, data hash) for dev, holdout or contracts."""
    if part == "contracts":
        return ([c["rows"] for c in CONTRACTS], [c["parties"] for c in CONTRACTS], None)
    if data is None:
        raise SystemExit(f"'{part}' needs --data: the folder that holds devset/ and testset/")
    docs = documents(load_set(data, UN_PART[part]))
    return docs, [None] * len(docs), set_hash(data, UN_PART[part])


def score_all(docs: list, parties: list, per_operator: int | None, echo=print) -> list:
    results = []
    for number, (rows, names) in enumerate(zip(docs, parties, strict=True), start=1):
        results.append(score_document(rows, SEED, names, per_operator=per_operator))
        echo(f"  document {number}/{len(docs)}: {len(results[-1]['cases'])} planted defects")
    return results


def table(summary: dict, target_rows: list) -> str:
    lines = ["| Measure | Target | Result | Met |", "|---|---|---|---|"]
    for name, value, target, met in target_rows:
        shown = "not measured" if value is None else value
        verdict = {True: "yes", False: "no", None: "n/a"}[met]
        sign = "<=" if name == "error_flags_per_100_pairs" else ">="
        lines.append(f"| {TARGET_LABELS[name]} | {sign} {target} | {shown} | {verdict} |")
    lines += ["", "| Planted defect | Planted | Caught | Recall |", "|---|---|---|---|"]
    for name, row in summary["operators"].items():
        lines.append(f"| {name} | {row['planted']} | {row['any']} | {row['recall_any']} |")
    return "\n".join(lines)


def run_score(part: str, data: Path | None, limit: int | None, per_operator: int | None,
              out: Path, adjudication: Path, echo=print) -> int:
    if part == "holdout":
        stop = freeze.problems(data)
        if limit is not None or per_operator is not None:
            stop.append("the hold-out is scored whole: no --limit, no --per-operator")
        if (out / "holdout.json").exists():
            stop.append("the hold-out has already been scored; it is scored once")
        if _git("status", "--porcelain"):
            stop.append("the git tree has uncommitted changes")
        if stop:
            for reason in stop:
                echo(f"refused: {reason}")
            return 2
    docs, parties, data_hash = load_documents(part, data)
    if limit is not None:
        docs, parties = docs[:limit], parties[:limit]
    results = score_all(docs, parties, per_operator, echo)
    summary = summarise(results)
    verdicts = adjudicate.load(adjudication / f"{part}.json")
    judged = adjudicate.tally(results, verdicts)
    target_rows = targets(summary, judged["false_per_100_pairs"])
    record = {
        "part": part, "scored_on": datetime.date.today().isoformat(),
        "commit": _git("rev-parse", "HEAD"), "version": bilingual_lint.__version__,
        "seed": SEED, "limit": limit, "per_operator": per_operator,
        "data_sha256": data_hash, "summary": summary, "adjudication": judged,
        "targets": [list(row) for row in target_rows], "results": results,
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{part}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    echo(table(summary, target_rows))
    echo(f"clean text: {judged['error_findings']} error findings — {judged['real']} real "
         f"differences, {judged['false']} false flags, {judged['open']} not yet judged")
    return 0


def run_worksheet(part: str, data: Path | None, out: Path, adjudication: Path,
                  echo=print) -> int:
    record = json.loads((out / f"{part}.json").read_text(encoding="utf-8"))
    docs, _, _ = load_documents(part, data)
    verdicts = adjudicate.load(adjudication / f"{part}.json")
    echo(adjudicate.worksheet(record["results"], docs, verdicts))
    return 0


def run_llm(part: str, data: Path | None, llm_docs: int, model: str, out: Path,
            complete=None, echo=print) -> int:
    if part == "holdout" and not (out / "holdout.json").exists():
        echo("refused: score the hold-out with the linter first")
        return 2
    docs, parties, data_hash = load_documents(part, data)
    docs, parties = docs[:llm_docs], parties[:llm_docs]
    complete = complete or llm_arm.litellm_complete(model)
    model_results, linter_results = [], []
    for number, (rows, names) in enumerate(zip(docs, parties, strict=True), start=1):
        model_results.append(llm_arm.compare_document(rows, SEED, complete, names))
        linter_results.append(score_document(rows, SEED, names, per_operator=1))
        echo(f"  document {number}/{len(docs)}")
    record = {
        "part": part, "scored_on": datetime.date.today().isoformat(), "model": model,
        "seed": SEED, "documents": len(docs), "data_sha256": data_hash,
        "model_summary": llm_arm.summarise(model_results),
        "linter_summary": summarise(linter_results),
        "model_results": model_results,
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / f"llm_{part}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    echo("| Planted defect | Model recall | Linter recall |")
    echo("|---|---|---|")
    for name, row in record["model_summary"]["operators"].items():
        linter = record["linter_summary"]["operators"].get(name, {}).get("recall_any")
        echo(f"| {name} | {row['recall']} | {linter} |")
    return 0


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m benchmark.run", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["dev", "holdout", "contracts", "worksheet", "llm"])
    parser.add_argument("part", nargs="?", choices=["dev", "holdout", "contracts"])
    parser.add_argument("--data", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--per-operator", type=int)
    parser.add_argument("--llm-docs", type=int, default=25)
    parser.add_argument("--model", default="anthropic/claude-sonnet-5")
    parser.add_argument("--results", type=Path, default=RESULTS)
    parser.add_argument("--adjudication", type=Path, default=ADJUDICATION)
    args = parser.parse_args(argv)
    if args.command in ("worksheet", "llm") and args.part is None:
        parser.error(f"'{args.command}' needs a part: dev, holdout or contracts")
    if args.command == "worksheet":
        return run_worksheet(args.part, args.data, args.results, args.adjudication)
    if args.command == "llm":
        return run_llm(args.part, args.data, args.llm_docs, args.model, args.results)
    return run_score(args.command, args.data, args.limit, args.per_operator,
                     args.results, args.adjudication)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())

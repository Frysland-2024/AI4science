#!/usr/bin/env python3
"""Offline PR hygiene checks. Never delete or rewrite research material."""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

CODE_EXT = {".py", ".sh", ".bash", ".ps1", ".js", ".ts", ".tsx", ".jsx",
            ".c", ".cc", ".cpp", ".rs", ".go", ".ipynb", ".yml", ".yaml", ".toml"}
ARTIFACT_EXT = {".csv", ".json", ".jsonl", ".npy", ".npz", ".parquet", ".log"}
EVIDENCE_DOC = re.compile(
    r"^(?:xrd_robustness/reports/|reports/|logs/|docs/archive/|"
    r"docs/(?:RRUFF_|[A-Za-z0-9_-]*(?:AUDIT|VALIDATION|PROTOCOL|EVIDENCE|RESULTS|REPORT)"
    r"[A-Za-z0-9_-]*\.md$))", re.I)
IMPLEMENTED = re.compile(
    r"\b(?:fully implemented|implementation complete|feature implemented|"
    r"implementation finished|code implemented|deployed successfully)\b|"
    r"(?:实现完成|代码已实现|完成实现|已完成开发|已经部署完成|功能已交付)", re.I)
STATE_CLAIM = re.compile(
    r"(?:current\s+(?:research|execution|project)\s+(?:state|status|direction)|"
    r"official\s+(?:primary|current)\s+(?:benchmark|RRUFF)|"
    r"RRUFF[-–]Cu1011.{0,60}(?:primary|official|正式|主基准)|"
    r"(?:当前|现行)(?:的)?(?:研究方向|执行状态|科研状态))", re.I)
AUTHORITY_LINK = re.compile(r"\]\([^)\n]*CURRENT_STATE\.md(?:#[^)]*)?\)", re.I)
DOC_HEADER = re.compile(r"(?im)^(?:Document rationale|文档新增理由)\s*[:：]\s*")
EVIDENCE_HEADER = re.compile(r"(?im)^(?:Evidence rationale|实验报告理由|证据文档理由)\s*[:：]\s*")

@dataclass(frozen=True)
class Change:
    path: str
    status: str
    added: int = 0
    deleted: int = 0

    @property
    def is_added(self) -> bool:
        return self.status == "A"

    @property
    def is_deleted(self) -> bool:
        return self.status == "D"

    @property
    def markdown(self) -> bool:
        return self.path.lower().endswith(".md")

    @property
    def evidence_doc(self) -> bool:
        return self.markdown and bool(EVIDENCE_DOC.search(self.path))

    @property
    def code(self) -> bool:
        return Path(self.path).suffix.lower() in CODE_EXT

    @property
    def test(self) -> bool:
        return (self.path.startswith("tests/") or "/tests/" in self.path or
                Path(self.path).name.startswith("test_")) and self.code

    @property
    def artifact(self) -> bool:
        return (self.path.startswith(("xrd_robustness/reports/", "reports/", "logs/")) and
                Path(self.path).suffix.lower() in ARTIFACT_EXT)

def parse_git_diff(name_bytes: bytes, numstat_bytes: bytes) -> list[Change]:
    """Parse git diff --name-status/-numstat -z, including Unicode and renames."""
    names = iter(name_bytes.decode("utf-8", "surrogateescape").split("\0"))
    changes: dict[str, str] = {}
    for token in names:
        if not token:
            continue
        status = token[0]
        if status in ("R", "C"):
            next(names)  # source path
            path = next(names)
        else:
            path = next(names)
        changes[path] = status

    nums = iter(numstat_bytes.decode("utf-8", "surrogateescape").split("\0"))
    lines: dict[str, tuple[int, int]] = {}
    for token in nums:
        if not token:
            continue
        cells = token.split("\t", 2)
        if len(cells) != 3:
            raise ValueError(f"Bad numstat record {token!r}")
        add, delete, path = cells
        if path == "":
            next(nums)  # source path of detected rename
            path = next(nums)
        lines[path] = (0 if add == "-" else int(add),
                       0 if delete == "-" else int(delete))
    return [Change(path, status, *lines.get(path, (0, 0)))
            for path, status in sorted(changes.items())]

def git_changes(base: str, head: str) -> list[Change]:
    def diff(flag: str) -> bytes:
        return subprocess.check_output(
            ["git", "-c", "core.quotepath=false", "diff", "--find-renames",
             "-z", flag, f"{base}...{head}", "--"])
    return parse_git_diff(diff("--name-status"), diff("--numstat"))

def has_rationale(body: str, header: re.Pattern[str], paths: list[str]) -> bool:
    match = header.search(body)
    if not match:
        return False
    explanation = body[match.end():]
    return len(explanation.strip()) >= 35 and all(p in explanation for p in paths)

def audit(changes: list[Change], title: str = "", body: str = "",
          root: Path | None = None) -> tuple[list[str], list[str], dict[str, int]]:
    warnings: list[str] = []
    errors: list[str] = []
    active = [c for c in changes if not c.is_deleted]
    general = [c for c in active if c.markdown and not c.evidence_doc]
    evidence = [c for c in active if c.evidence_doc]
    new_general = [c for c in general if c.is_added]
    new_evidence = [c for c in evidence if c.is_added]
    code = [c for c in active if c.code]
    tests = [c for c in active if c.test]
    artifacts = [c for c in active if c.artifact]
    general_add = sum(c.added for c in general)
    code_add = sum(c.added for c in code)

    metrics = {
        "new_general_md": len(new_general),
        "new_evidence_md": len(new_evidence),
        "general_md_added": general_add,
        "general_md_removed": sum(c.deleted for c in general),
        "evidence_md_added": sum(c.added for c in evidence),
        "code_added": code_add,
        "code_removed": sum(c.deleted for c in code),
        "changed_test_files": len(tests),
        "changed_machine_evidence_files": len(artifacts),
    }

    if new_general and not has_rationale(
        body, DOC_HEADER, [c.path for c in new_general]
    ):
        errors.append("New general Markdown needs a substantive 'Document rationale:' "
                      "in the PR body, naming every new file and explaining why "
                      "existing canonical docs cannot accommodate it.")
    if len(new_general) >= 2:
        warnings.append(f"{len(new_general)} new general Markdown files: check overlap.")
    if len(new_general) >= 3:
        errors.append("3+ new general Markdown files: consolidate or split this PR. "
                      "Research reports use the separate evidence lane.")

    if new_evidence and not has_rationale(
        body, EVIDENCE_HEADER, [c.path for c in new_evidence]
    ):
        warnings.append("New experiment-report/archive Markdown lacks 'Evidence rationale:' "
                        "naming each new file and its underlying scientific evidence.")
    if len(new_evidence) >= 5:
        warnings.append("5+ new evidence documents: review opportunities to combine reports.")

    if general_add >= 300:
        warnings.append(f"General documentation adds {general_add} lines.")
    if general_add >= 900:
        errors.append(f"General documentation adds {general_add} lines (limit 900); "
                      "split/consolidate it or use the justified experiment report lane.")
    if code_add and general_add >= 150 and general_add > 3 * code_add:
        warnings.append("General Markdown additions exceed 3x code additions.")

    if code and not tests and not artifacts:
        warnings.append("Code/config changed without changed tests or machine evidence: "
                        "record actual verification in the PR.")
    if IMPLEMENTED.search(title + "\n" + body) and not (
        any(not c.path.startswith(".github/") for c in code) or artifacts
    ):
        warnings.append("PR claims implementation/deployment but changes neither "
                        "product code nor machine-readable result artifacts.")

    if root is not None:
        for change in new_general:
            path = root / change.path
            if not path.is_file():
                continue
            content = path.read_text(encoding="utf-8", errors="replace")
            if STATE_CLAIM.search(content) and not AUTHORITY_LINK.search(content):
                warnings.append(f"{change.path}: repeats a current-state claim without "
                                "linking to docs/CURRENT_STATE.md.")
    return warnings, errors, metrics

def summarize(warnings: list[str], errors: list[str], metrics: dict[str, int]) -> str:
    lines = ["### PR Hygiene Gate", "", "| Measurement | Value |", "| --- | ---: |"]
    lines.extend(f"| {key.replace('_', ' ')} | {value} |"
                 for key, value in metrics.items())
    lines += ["", f"**Result:** {'FAIL' if errors else 'PASS'} "
              f"({len(errors)} blocking, {len(warnings)} warnings)", ""]
    if errors:
        lines += ["**Blocking findings**", *[f"- {item}" for item in errors], ""]
    if warnings:
        lines += ["**Review prompts**", *[f"- {item}" for item in warnings], ""]
    lines += ["No auto-deletion. Heuristics do not prove semantic duplication "
              "or scientific/research validity."]
    return "\n".join(lines) + "\n"

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        changed = git_changes(args.base, args.head)
    except (subprocess.CalledProcessError, StopIteration, ValueError) as exc:
        print(f"::error::Cannot inspect PR diff: {exc}", file=sys.stderr)
        return 2
    warnings, errors, metrics = audit(
        changed, os.environ.get("PR_TITLE", ""),
        os.environ.get("PR_BODY", ""), args.root.resolve())
    message = summarize(warnings, errors, metrics)
    print(message)
    for warning in warnings:
        print(f"::warning::{warning}")
    for error in errors:
        print(f"::error::{error}")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as out:
            out.write(message)
    return int(bool(errors))

if __name__ == "__main__":
    sys.exit(main())

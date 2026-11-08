#!/usr/bin/env python3
"""Lightweight PR hygiene gate: stop document sprawl without erasing evidence.

Only inspects Git diffs and PR metadata. No API tokens, models, or file edits.
Scientific result artifacts and archived files are NOT capped as narrative docs.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import subprocess
import sys
from pathlib import PurePosixPath

MAX_NEW_NARRATIVE_DOCS = 2
MAX_NARRATIVE_ADDED_LINES = 400
REASONS = {
    "docs": re.compile(r"(?im)^(?:Docs rationale|文档理由)\s*[:：]\s*(.{25,})\s*$"),
    "exception": re.compile(r"(?im)^(?:Docs exception|文档例外)\s*[:：]\s*(.{30,})\s*$"),
    "decision": re.compile(r"(?im)^(?:Research decision|科研决策依据)\s*[:：]\s*(.{25,})\s*$"),
}
SOURCE_EXTENSIONS = {
    ".py", ".sh", ".ps1", ".bat", ".js", ".ts", ".tsx", ".cpp",
    ".c", ".h", ".rs", ".toml", ".yaml", ".yml", ".ipynb",
}
SOURCE_CONFIG_DIRS = ("configs/", "config/", "scripts/", ".github/workflows/")


def git(*args: str) -> str:
    proc = subprocess.run(["git", *args], capture_output=True, text=True,
                          encoding="utf-8", check=True)
    return proc.stdout


def changes_from_git(base: str, head: str) -> list[dict]:
    """Read NUL-delimited Git diff records without mangling Unicode or tabs.

    --no-renames preserves the original add/modify classification used by the
    documentation budget; binary files' '-' numstat values count as zero.
    """
    range_spec = f"{base}...{head}"
    name_fields = git("diff", "--no-renames", "--name-status", "-z", range_spec).split("\0")
    if name_fields[-1] != "":
        raise ValueError("Incomplete NUL-delimited git name-status output")
    if len(name_fields[:-1]) % 2:
        raise ValueError("Invalid NUL-delimited git name-status pairs")
    statuses = {
        name_fields[index + 1]: name_fields[index][0]
        for index in range(0, len(name_fields) - 1, 2)
    }

    changes = []
    for record in git("diff", "--no-renames", "--numstat", "-z", range_spec).split("\0"):
        if not record:
            continue
        parts = record.split("\t", 2)
        if len(parts) != 3:
            raise ValueError(f"Invalid git numstat record: {record!r}")
        added, removed, path = parts
        changes.append({
            "path": path, "status": statuses.get(path, "M"),
            "added": int(added) if added.isdigit() else 0,
            "removed": int(removed) if removed.isdigit() else 0,
        })
    return changes

def is_narrative(path: str) -> bool:
    if not path.lower().endswith(".md"):
        return False
    parts = PurePosixPath(path).parts
    if not parts or parts[0] == "archive" or "archive" in parts:
        return False
    if "reports" in parts or "report" in parts or "manifests" in parts:
        return False
    return True


def is_source(path: str) -> bool:
    if path.lower().endswith(".md"):
        return False
    p = PurePosixPath(path)
    return p.suffix.lower() in SOURCE_EXTENSIONS or (
        p.suffix.lower() in {".json", ".jsonl"}
        and any(segment in path.split("/") for segment in ("configs", "config"))
    )


def has_reason(body: str, key: str) -> bool:
    return bool(REASONS[key].search(body))


def normalized_stem(path: str) -> str:
    stem = PurePosixPath(path).stem.lower()
    stem = re.sub(r"20\d{2}[-_]?\d{2}[-_]?\d{2}|v\d{1,3}", "", stem)
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", stem)


def inspect(changes: list[dict], title: str, body: str,
            existing_docs: list[str] | None = None) -> tuple[list[str], list[str], dict]:
    active = [x for x in changes if x["status"] != "D"]
    narrative = [x for x in active if is_narrative(x["path"])]
    new = [x for x in narrative if x["status"] == "A"]
    doc_lines = sum(x["added"] for x in narrative)
    source = [x for x in active if is_source(x["path"])]
    source_lines = sum(x["added"] for x in source)
    errors, warnings = [], []
    rationale = has_reason(body, "docs")
    exception = has_reason(body, "exception")
    decision = has_reason(body, "decision")

    if new and not rationale:
        errors.append(
            "New narrative Markdown requires a meaningful 'Docs rationale:' "
            "in the PR body explaining why existing documents cannot hold it: "
            + ", ".join(x["path"] for x in new)
        )
    if len(new) > MAX_NEW_NARRATIVE_DOCS and not exception:
        errors.append(
            f"{len(new)} new narrative Markdown files exceed the default "
            f"limit of {MAX_NEW_NARRATIVE_DOCS}; explain the exception "
            "with 'Docs exception:' in PR body."
        )
    if doc_lines > MAX_NARRATIVE_ADDED_LINES and not exception:
        errors.append(
            f"{doc_lines} added narrative-document lines exceed the "
            f"per-PR default budget of {MAX_NARRATIVE_ADDED_LINES}; "
            "provide a substantive 'Docs exception:' if essential."
        )
    if any(x["path"] == "docs/PROJECT_HISTORY.md" for x in active) and not decision:
        errors.append(
            "PROJECT_HISTORY.md changed without a 'Research decision:' "
            "entry explaining the material research pivot or justified historical correction."
        )

    # Impl-type PRs should not quietly ship only descriptions or plans.
    if re.match(r"(?i)^\s*(feat|feature|perf|refactor)(\([^)]*\))?\s*[:：]", title):
        if not source:
            errors.append(
                "Implementation-style PR has no source/config/test changes; "
                "either deliver implementation or label it docs-only honestly."
            )
    if re.match(r"(?i)^\s*fix(\([^)]*\))?\s*[:：]", title) and not source:
        warnings.append("Fix PR has no code changes; verify this is deliberately docs-only.")

    if doc_lines >= 120 and source_lines > 0 and doc_lines > 4 * source_lines:
        warnings.append(
            f"Document-to-source additions are {doc_lines}:{source_lines} lines; "
            "check whether routine notes belong only in the PR description/Git history."
        )
    if existing_docs:
        baseline = [p for p in existing_docs if is_narrative(p)]
        for item in new:
            newstem = normalized_stem(item["path"])
            if len(newstem) < 9:
                continue
            similar = [
                p for p in baseline
                if PurePosixPath(p).parent == PurePosixPath(item["path"]).parent
                and difflib.SequenceMatcher(None, newstem, normalized_stem(p)).ratio() >= 0.86
            ]
            if similar:
                warnings.append(
                    f"{item['path']} resembles existing {similar[0]}; "
                    "review for duplicate content and link to the canonical file."
                )

    return errors, warnings, {
        "new_narrative_md": len(new),
        "narrative_added_lines": doc_lines,
        "source_changed_files": len(source),
        "source_added_lines": source_lines,
        "evidence_and_archives_exempt": sum(
            1 for x in active if x["path"].lower().endswith(".md")
            and not is_narrative(x["path"])
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="Pull request base SHA")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--event", default=os.getenv("GITHUB_EVENT_PATH", ""))
    args = parser.parse_args()
    if not args.event:
        parser.error("PR event JSON is required (or set GITHUB_EVENT_PATH)")
    with open(args.event, encoding="utf-8") as stream:
        event = json.load(stream)
    pr = event.get("pull_request") or {}
    if not pr.get("title"):
        parser.error("Pull request title missing from event JSON")
    diffs = changes_from_git(args.base, args.head)
    baseline_docs = git("ls-tree", "-r", "--name-only", args.base).splitlines()
    errors, warnings, summary = inspect(diffs, pr["title"], pr.get("body") or "", baseline_docs)
    print("PR Hygiene:", json.dumps(summary, ensure_ascii=False, sort_keys=True))
    for warning in warnings:
        print(f"::warning::{warning}")
    for error in errors:
        print(f"::error::{error}")
    if errors:
        print(f"PR Hygiene FAILED: {len(errors)} actionable issue(s); existing files remain untouched.")
        return 1
    print("PR Hygiene PASS (automated heuristics; human research review remains required).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

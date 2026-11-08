#!/usr/bin/env python3
"""Deterministic, offline checks of active AI4science documentation.

Uses AGENTS.md and docs/CURRENT_STATE.md as canonical inputs. This is not a
semantic AI reviewer. Historical archives are explicitly excluded.
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote

PUBLIC_DOCS = ("README.md", "docs/README.md",
               "docs/START_HERE_FOR_SUPERVISORS.md", "docs/REVIEWER_GUIDE.md")
SOURCES = ("AGENTS.md", "docs/CURRENT_STATE.md")
STALE_CLAIMS = (
    (r"\bno new experiments are (?:in scope|in the current thesis scope)\b",
     "Old write-up-only freeze presented as current"),
    (r"\bonly current undergraduate thesis line\b",
     "Outdated thesis freeze presented as current"),
    (r"\bunder the current thesis scope, no new evaluation is planned\b",
     "Outdated no-evaluation claim"),
    (r"\bcurrent thesis work is reporting and writing\b",
     "Outdated write-up-only scope"),
    (r"\bno (?:simulator|data),? (?:data,? )?training,? calibration,? or RRUFF benchmark work is being started\b",
     "Outdated no-experiment claim"),
    (r"\b(?:new RRUFF zero-shot evaluation|larger-parent training),? .*\b(?:are|is) deferred\b",
     "Old deferred scope presented as current"),
    (r"(?:当前|现阶段).{0,30}(?:仅写论文|只写论文|不再(?:做|进行)实验)",
     "Old current-only write-up claim"),
)
POSITIVE_UNRUN = (
    re.compile(r"\bV11\s+(?:full-scale\s+|large-scale\s+)?(?:HPO|training)\s+(?:has\s+)?(?:completed|finished|succeeded|is\s+complete)\b", re.I),
    re.compile(r"\b(?:154,975|108,478)[ -]?(?:parent\s+)?(?:HPO|training)\s+(?:has\s+)?(?:completed|finished|succeeded|is\s+complete)\b", re.I),
    re.compile(r"V11.{0,25}(?:调参|训练).{0,15}(?:已经完成|已完成|成功完成)", re.I),
)
PRIMARY_ID_CLAIM = re.compile(
    r"(?i)(?:(?:primary|official|current)\s+(?:real-domain\s+|zero-shot\s+)?"
    r"(RRUFF[-–](?:Cu)?\d{2,5})\b|"
    r"(RRUFF[-–](?:Cu)?\d{2,5})\b.{0,25}\b(?:is|as)\s+(?:our\s+|the\s+)?(?:primary|official|current)\b|"
    r"(?:正式|当前|主要)(?:的)?\s*(RRUFF[-–](?:Cu)?\d{2,5})\s*(?:主基准|测试集|真实域基准))"
)
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")

def read(root: Path, name: str) -> str:
    return (root / name).read_text(encoding="utf-8")

def active_agent_section(agents: str) -> str:
    match = re.search(r"(?m)^## Current research direction[^\n]*\n", agents)
    if not match:
        raise ValueError("AGENTS.md lacks current research heading")
    return re.split(r"(?m)^##\s", agents[match.end():], maxsplit=1)[0]

def current_facts(agents: str, state: str) -> tuple[str, bool, tuple[str, str]]:
    active = active_agent_section(agents)
    if not re.search(r"\*\*Active:\*\*.*\bPXRD\b", active):
        raise ValueError("Active research direction changed: review checker")
    benchmark = re.search(
        r"(?i)\*\*Decision:\s*(RRUFF[-–](?:Cu)?\d{2,5})\s+is\s+the\s+official\s+prospective\s+PRIMARY", state)
    if not benchmark:
        raise ValueError("CURRENT_STATE lacks an explicit official primary RRUFF benchmark")
    order = re.search(
        r"First complete\s*\[Issue\s*#(\d+)\].{0,260}?only then consider\s*\[Issue\s*#(\d+)\]",
        active, re.I | re.S)
    if not order:
        raise ValueError("AGENTS.md lacks explicit readiness-then-HPO issue order")
    unrun = "没有启动 HPO" in state[:6000] or "HPO 仍" in state[:6000]
    return benchmark.group(1), unrun, order.groups()

def markdown_links(text: str):
    text = re.sub(r"(?ms)^(\x60{3}|~~~).*?^\1[^\n]*$", "", text)
    for match in MARKDOWN_LINK.finditer(text):
        target = match.group(1).strip().split(' "', 1)[0].strip("<>")
        if not target or target.startswith(("https://", "http://", "mailto:", "#")):
            continue
        yield unquote(target.split("#", 1)[0])

def inspect(root: Path) -> list[str]:
    errors = []
    for name in SOURCES + PUBLIC_DOCS:
        if not (root / name).is_file():
            errors.append(f"{name}: required current document missing")
    if errors:
        return errors
    agents, state = (read(root, name) for name in SOURCES)
    try:
        benchmark, unrun, (ready, hpo) = current_facts(agents, state)
    except ValueError as exc:
        return [f"Canonical source failure: {exc}"]
    for doc in PUBLIC_DOCS:
        content = read(root, doc)
        if benchmark.casefold() not in content.casefold():
            errors.append(f"{doc}: official benchmark {benchmark} absent")
        for number, line in enumerate(content.splitlines(), 1):
            for pattern, reason in STALE_CLAIMS:
                if re.search(pattern, line, re.I):
                    errors.append(f"{doc}:{number}: {reason}")
            if unrun and any(pattern.search(line) for pattern in POSITIVE_UNRUN):
                errors.append(f"{doc}:{number}: V11 HPO/training claimed complete despite canonical unrun state")
            for claim in PRIMARY_ID_CLAIM.finditer(line):
                found = next(value for value in claim.groups() if value)
                if found.casefold() != benchmark.casefold():
                    prefix = line[max(0, claim.start() - 20):claim.start()]
                    if not re.search(r"historical|former|previous|superseded|旧|历史|曾经", prefix, re.I):
                        errors.append(f"{doc}:{number}: {found} presented as primary, expected {benchmark}")
            if unrun and re.search(r"\bRRUFF[-–]Cu1011\b.{0,80}\b(?:accuracy|Macro-F1|ECE)\s*[:=]\s*\d", line, re.I):
                errors.append(f"{doc}:{number}: unrun benchmark appears to have final numeric score")
            if re.search(r"\b(?:first|before|then|after)\b|先.*再|首先|之后", line, re.I) and f"#{hpo}" in line and f"#{ready}" in line:
                if re.search(rf"\bfirst\s+.*#{hpo}|先.*#{hpo}.*再.*#{ready}", line, re.I):
                    errors.append(f"{doc}:{number}: issue order reversed; #{ready} must precede #{hpo}")
        base = root / doc.rsplit("/", 1)[0] if "/" in doc else root
        for target in markdown_links(content):
            if not (base / target).exists():
                errors.append(f"{doc}: broken local link {target}")
    return errors

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    problems = inspect(parser.parse_args().root.resolve())
    if problems:
        for problem in problems:
            print(f"::error::{problem}")
        print(f"Docs Consistency FAILED ({len(problems)} checks). Semantic review is still required.")
        return 1
    print("Docs Consistency PASS: deterministic checks only, not semantic proof.")
    return 0

if __name__ == "__main__":
    sys.exit(main())

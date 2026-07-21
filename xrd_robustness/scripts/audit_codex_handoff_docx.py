#!/usr/bin/env python3
"""Audit the portable handoff DOCX structure without rendering or training."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import zipfile
from xml.etree import ElementTree as ET


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "docs" / "CODEX_ACCOUNT_HANDOFF.docx"
DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "codex_account_handoff_docx_audit.json"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--word-page-count", type=int, default=0)
    parser.add_argument(
        "--visual-note",
        default=(
            "LibreOffice is unavailable and headless Microsoft Word PDF export "
            "timed out; page-by-page raster QA was not completed on the source laptop."
        ),
    )
    return parser.parse_args()


def audit(path: Path, word_page_count: int, visual_note: str) -> dict[str, object]:
    required_members = {
        "[Content_Types].xml",
        "word/document.xml",
        "word/styles.xml",
        "word/settings.xml",
        "word/header1.xml",
        "word/footer1.xml",
    }
    required_text = (
        "XRD Robustness V9-T",
        "给下一个 Codex 的第一条指令",
        "lambda 调参完成度",
        "optimizer step 0",
        "台式机第一次接管",
        "独立授权",
        "胡皓天",
    )
    with zipfile.ZipFile(path) as archive:
        members = set(archive.namelist())
        corrupt_member = archive.testzip()
        root = ET.fromstring(archive.read("word/document.xml"))
    all_text = "".join(node.text or "" for node in root.iter(f"{{{W_NS}}}t"))
    paragraph_count = sum(1 for _ in root.iter(f"{{{W_NS}}}p"))
    table_count = sum(1 for _ in root.iter(f"{{{W_NS}}}tbl"))
    section_count = sum(1 for _ in root.iter(f"{{{W_NS}}}sectPr"))
    explicit_page_break_count = sum(
        1
        for node in root.iter(f"{{{W_NS}}}br")
        if node.attrib.get(f"{{{W_NS}}}type") == "page"
    )
    checks = {
        "docx_exists_and_nonempty": path.is_file() and path.stat().st_size > 0,
        "zip_integrity_passed": corrupt_member is None,
        "required_package_members_present": required_members <= members,
        "required_handoff_text_present": all(token in all_text for token in required_text),
        "paragraphs_present": paragraph_count >= 100,
        "tables_present": table_count >= 1,
        "section_properties_present": section_count >= 1,
        "explicit_cover_page_break_present": explicit_page_break_count >= 1,
        "microsoft_word_open_and_page_count_succeeded": word_page_count > 0,
    }
    structural_pass = all(checks.values())
    return {
        "schema_version": "codex-account-handoff-docx-audit-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": (
            "structural_pass_visual_not_completed"
            if structural_pass
            else "structural_fail"
        ),
        "input": str(path),
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
        "counts": {
            "paragraphs": paragraph_count,
            "tables": table_count,
            "sections": section_count,
            "explicit_page_breaks": explicit_page_break_count,
            "word_page_count": word_page_count,
        },
        "visual_render": {
            "completed": False,
            "reason": visual_note,
            "authority_impact": (
                "none: CODEX_HANDOFF.md is authoritative; the DOCX is a derived "
                "portable reading copy"
            ),
        },
    }


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).resolve()
    report = audit(input_path, args.word_page_count, args.visual_note)
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "failed_checks": report["failed_checks"],
                "output": str(output_path),
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["status"] == "structural_pass_visual_not_completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

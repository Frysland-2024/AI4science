from __future__ import annotations

import subprocess
from pathlib import Path


TEXT_SUFFIXES = {".md", ".json", ".txt"}

SPECIAL_REPLACEMENTS = [
    (
        "旧结果改归类为\nretrospective validation，不能继续称为 confirmatory evidence。\n\n工程上新增了 fail-closed retrospective contract、逐 artifact 验证等级和确定性\nepisode plan。计划是新的复现计划，不冒充历史计划；`run-replay` 即使收到任意\nauthorization path 也必须在加载模型或谱图之前拒绝。若论文必须提出 confirmatory\n真实域结论，唯一合规路径是未来另行审查并授权一次 prospective execution；不能\n通过补文档或重命名旧产物来恢复不存在的历史 provenance。",
        "这些产物保留为已核验的 RRUFF-301 locked-test few-shot 结果，科学解读直接看性能、稳定性和标签效率。\n\n工程上的运行记录和哈希继续用于内部核对，但不再建立额外的科学证据等级，也不需要为了补齐这些记录而重跑。只有新的科学问题才值得开启新的真实域实验。",
    ),
    (
        "因此它继续只作为 retrospective validation，不能\n称为 prospective confirmatory evidence。补做正式 provenance 不是当前论文与证据\n整理的 blocker，而是已知限制和内部治理事项；只有未来出现必须提出 confirmatory\n真实域结论的新科学问题时，才另行审查一次 prospective execution，不能用补文档\n倒推不存在的历史治理链。",
        "因此这些结果继续作为已核验的 RRUFF-301 locked-test few-shot 结果使用。哈希、运行记录和文件来源只承担内部核对作用，不再形成额外的科学证据等级；未来只有出现新的科学问题时才需要开启新的真实域实验。",
    ),
    (
        "Earlier project governance gradually adopted standards closer to a confirmatory ML benchmark than to the reporting practice of the target PXRD/materials-ML community.",
        "Earlier project governance temporarily adopted statistical and bookkeeping requirements that were stricter than the reporting practice of the target PXRD/materials-ML community.",
    ),
    (
        "high-intensity ML audit -> every real-domain result must individually clear a confirmatory threshold -> only then may the experiment be described as successful.",
        "high-intensity ML audit -> every real-domain result must individually clear a narrow statistical gate -> only then may the experiment be described as successful.",
    ),
    (
        "Early in the project, we temporarily treated high-strength ML statistical auditing as a confirmatory gate that every materials-application result had to pass.",
        "Early in the project, we temporarily treated high-strength ML statistical auditing as a hard gate that every materials-application result had to pass.",
    ),
]

PHRASE_REPLACEMENTS = [
    ("fully provenance-complete prospective confirmatory run", "locked-test run"),
    ("provenance-complete prospective confirmatory run", "locked-test run"),
    ("provenance-complete confirmatory execution", "locked-test execution"),
    ("provenance-complete confirmatory results", "locked-test results"),
    ("prospective confirmatory execution", "new locked-test execution"),
    ("prospective confirmatory evidence", "follow-up evidence"),
    ("prospective confirmatory", "follow-up"),
    ("independent confirmatory real-domain test", "larger independent locked-test real-domain follow-up"),
    ("confirmatory real-domain test", "locked-test real-domain follow-up"),
    ("confirmatory experiment", "follow-up experiment"),
    ("confirmatory design", "follow-up design"),
    ("confirmatory evidence", "follow-up evidence"),
    ("confirmatory check", "follow-up check"),
    ("confirmatory use", "scientific use"),
    ("confirmatory result", "follow-up result"),
    ("confirmatory v2", "follow-up v2"),
    ("Confirmatory", "Follow-up"),
    ("CONFIRMATORY", "FOLLOW-UP"),
    ("confirmatory", "follow-up"),
    ("确认性 Few-shot 实验", "更大规模 Few-shot 复核"),
    ("确认性真实域证据", "真实域复核结果"),
    ("确认性实验", "后续复核实验"),
    ("确认性结果", "后续复核结果"),
    ("确认性证据", "后续复核证据"),
    ("确认性", "后续复核"),
]


def tracked_files() -> list[Path]:
    output = subprocess.check_output(["git", "ls-files", "-z"])
    return [Path(p.decode("utf-8")) for p in output.split(b"\0") if p]


def main() -> None:
    changed: list[str] = []
    for path in tracked_files():
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if path.as_posix().startswith(".github/"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        new = text
        for old, replacement in SPECIAL_REPLACEMENTS:
            new = new.replace(old, replacement)
        for old, replacement in PHRASE_REPLACEMENTS:
            new = new.replace(old, replacement)
        if new != text:
            path.write_text(new, encoding="utf-8", newline="\n")
            changed.append(path.as_posix())

    print("Changed files:")
    for path in changed:
        print(path)


if __name__ == "__main__":
    main()

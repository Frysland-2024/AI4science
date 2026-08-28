from __future__ import annotations

import subprocess
from pathlib import Path


TEXT_SUFFIXES = {".md", ".json", ".txt"}


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
        new = text.replace("CONFIRMED", "RESULT")
        new = new.replace(
            "run_rruff301_follow-up.py v2",
            "historical RRUFF-301 v2 runner",
        )
        if new != text:
            path.write_text(new, encoding="utf-8", newline="\n")
            changed.append(path.as_posix())

    print("Changed files:")
    for path in changed:
        print(path)


if __name__ == "__main__":
    main()

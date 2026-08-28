from pathlib import Path

path = Path("docs/PROJECT_HISTORY.md")
text = path.read_text(encoding="utf-8")
text = text.replace("[CONFIRMED / SECONDARY]", "[SECONDARY RESULT]")
text = text.replace("[CONFIRMED]", "[RESULT]")
text = text.replace("run_rruff301_follow-up.py v2", "historical RRUFF-301 v2 runner")
path.write_text(text, encoding="utf-8", newline="\n")

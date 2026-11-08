#!/usr/bin/env python3
"""One-shot branch retirement (2026-11-09). Requires GITHUB_TOKEN: contents:write.

Safe invariants:
- Refuse if any PR is open.
- Never touch the branches in manifest.keep.
- Never touch a branch whose HEAD changed since the approved snapshot.
- Create and verify a *tag pointing to the exact tip SHA* BEFORE deleting a branch.
- Never force-update refs; on any error, keep the original branch.
- Do not modify files, commits, data, issues, PRs, or tags that already exist.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = "Frysland-2024/AI4science"
MANIFEST = Path("docs/BRANCH_RETIREMENT_20261109.json")
PREFIX = "branch-archive/2026-11-09/"

def api(method, path, payload=None, missing_ok=False):
    url = "https://api.github.com/repos/" + REPO + path
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "AI4science-branch-retirement-20261109",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data, headers, method=method), timeout=30) as response:
            body = response.read()
            return json.loads(body) if body else None
    except urllib.error.HTTPError as e:
        if e.code == 404 and missing_ok:
            return None
        raise RuntimeError(f"{method} {path}: HTTP {e.code}: {e.read()[:300]!r}") from e

def get_ref(kind, name):
    path = "/git/ref/" + kind + "/" + urllib.parse.quote(name, safe="/")
    return api("GET", path, missing_ok=True)

def main():
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    keep = set(m["keep"])
    assert {"main", "integrate/v11-server-pipeline-20261109", "issue55-resnet-js-search"} <= keep
    to_retire = m["retire"]
    assert len(to_retire) == len(set(to_retire))
    assert not (keep & set(to_retire))
    assert len(to_retire) > 10
    assert all(len(sha) == 40 for sha in to_retire.values())
    prs = api("GET", "/pulls?state=open&per_page=100")
    if prs:
        raise RuntimeError("Open PR exists; refuse retirement until reviewed: " + str([p["number"] for p in prs]))
    stats = {"retired": 0, "unchanged": 0, "skipped": 0}
    for branch, sha in sorted(to_retire.items()):
        try:
            before = get_ref("heads", branch)
            tagname = PREFIX + branch
            if before is None:
                tag = get_ref("tags", tagname)
                if tag and tag["object"]["sha"] == sha:
                    print("ALREADY RETIRED", branch)
                    stats["unchanged"] += 1
                else:
                    print("SKIP missing branch without matching archive tag", branch)
                    stats["skipped"] += 1
                continue
            if before["object"]["sha"] != sha:
                print("SKIP changed head", branch, before["object"]["sha"], "expected", sha)
                stats["skipped"] += 1
                continue
            tag = get_ref("tags", tagname)
            if tag is None:
                api("POST", "/git/refs", {"ref": "refs/tags/" + tagname, "sha": sha})
            elif tag["object"]["sha"] != sha:
                raise RuntimeError("Archive tag points to unexpected commit: " + tagname)
            tag = get_ref("tags", tagname)
            if tag is None or tag["object"]["sha"] != sha:
                raise RuntimeError("Archive tag verification failed")
            after = get_ref("heads", branch)
            if after is None or after["object"]["sha"] != sha:
                raise RuntimeError("Branch changed while archiving")
            api("DELETE", "/git/refs/heads/" + urllib.parse.quote(branch, safe="/"))
            if get_ref("heads", branch) is not None:
                raise RuntimeError("Branch still exists after DELETE")
            print("RETIRED", branch, "-> refs/tags/" + tagname, sha)
            stats["retired"] += 1
        except Exception as exc:
            print("SKIP ERROR", branch, repr(exc))
            stats["skipped"] += 1
    print("SUMMARY", json.dumps(stats))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("## AI4science historical branch retirement\n")
            f.write(f"- Retired with verified archive tags: **{stats['retired']}**\n")
            f.write(f"- Already retired: **{stats['unchanged']}**\n")
            f.write(f"- Skipped/needs follow-up: **{stats['skipped']}**\n")
            f.write("- Preserved branches: " + ", ".join(sorted(keep)) + "\n")
    return 0 if stats["skipped"] == 0 else 1

if __name__ == "__main__":
    sys.exit(main())

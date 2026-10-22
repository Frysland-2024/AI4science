from __future__ import annotations

import argparse
import sys

from .bridge import Bridge, GitHubIssues, create_issue_body, detect_repo, doctor, ensure_labels


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="research-task-bridge")
    parser.add_argument("--repo", help="GitHub repository in OWNER/REPO form")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="Check local prerequisites without showing credentials")
    sub.add_parser("init-labels", help="Create the bridge's GitHub labels")
    sub.add_parser("once", help="Claim and process at most one ready task")
    watch = sub.add_parser("watch", help="Poll GitHub Issues and process ready tasks")
    watch.add_argument("--interval", type=int, default=30, help="Poll interval in seconds")

    create = sub.add_parser("create", help="Create a task Issue from the local CLI")
    create.add_argument("--title", required=True)
    create.add_argument("--action", choices=("codex_read_only", "bridge_cpu_smoke", "requires_user_approval"), required=True)
    create.add_argument("--scope", choices=("docs", "source"), default="docs")
    create.add_argument("--request", required=True)
    create.add_argument("--dedupe-key", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo = args.repo or detect_repo()
    if not repo:
        print("Could not determine OWNER/REPO; pass --repo.", file=sys.stderr)
        return 2

    if args.command == "doctor":
        return 0 if doctor(repo) else 1
    if args.command == "init-labels":
        ensure_labels(repo)
        print(f"Bridge labels are ready in {repo}.")
        return 0
    if args.command == "create":
        issues = GitHubIssues(repo)
        url = issues.create(args.title, create_issue_body(args.action, args.scope, args.request, args.dedupe_key))
        print(url)
        return 0

    bridge = Bridge(repo)
    if args.command == "once":
        result = bridge.once()
        print(result)
        return 0
    if args.command == "watch":
        if args.interval < 5:
            print("--interval must be at least 5 seconds.", file=sys.stderr)
            return 2
        bridge.watch(args.interval)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

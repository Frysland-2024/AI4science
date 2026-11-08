#!/usr/bin/env python3
"""Fail closed on stale, incomplete, or altered V11 source snapshots."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile

from payload_contract import (
    PAYLOAD_CONTRACT_VERSION,
    PAYLOAD_MANIFEST_MEMBER,
    PAYLOAD_REQUIRED_FILES,
)


def _valid_member(member: str) -> bool:
    path = PurePosixPath(member)
    return (bool(member) and "\\" not in member and ":" not in member
            and not path.is_absolute() and ".." not in path.parts)


def _sha256_stream(stream) -> str:
    digest = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(block)
    return digest.hexdigest()


def read_and_validate_manifest(archive: Path) -> dict:
    with zipfile.ZipFile(archive, "r") as zf:
        infos=zf.infolist()
        names=[info.filename for info in infos]
        if len(names)!=len(set(names)):
            raise ValueError("source snapshot contains duplicate ZIP member names")
        for info in infos:
            if not _valid_member(info.filename.rstrip("/")):
                raise ValueError(f"source snapshot contains unsafe ZIP member: {info.filename}")
        regular_names={info.filename for info in infos if not info.is_dir()}
        if PAYLOAD_MANIFEST_MEMBER not in names:
            raise ValueError("source snapshot lacks its versioned payload manifest")
        manifest = json.loads(zf.read(PAYLOAD_MANIFEST_MEMBER).decode("utf-8"))
        if (not isinstance(manifest,dict)
            or manifest.get("schema") != "pxrd-v11-source-snapshot-v1"
            or manifest.get("contract_version") != PAYLOAD_CONTRACT_VERSION):
            raise ValueError("source snapshot contract version is stale or unsupported")
        files = manifest.get("files")
        if not isinstance(files, dict) or not files:
            raise ValueError("source snapshot manifest has no file hashes")
        if tuple(manifest.get("required_files", ())) != PAYLOAD_REQUIRED_FILES:
            raise ValueError("source snapshot required-file contract mismatch")
        if not set(PAYLOAD_REQUIRED_FILES).issubset(files):
            raise ValueError("source snapshot manifest omits required source files")
        if regular_names!=set(files)|{PAYLOAD_MANIFEST_MEMBER}:
            raise ValueError("source snapshot contains unmanifested or missing files")
        for member, expected in files.items():
            if (not _valid_member(member) or not member.startswith("AI4science/")
                or member not in names):
                raise ValueError(f"source snapshot member missing or unsafe: {member}")
            if not isinstance(expected, str) or len(expected) != 64:
                raise ValueError(f"invalid source snapshot SHA256 entry: {member}")
            with zf.open(member, "r") as stream:
                actual = _sha256_stream(stream)
            if actual.lower() != expected.lower():
                raise ValueError(f"source snapshot member hash mismatch: {member}")
    return manifest


def verify_extracted_tree(manifest: dict, extracted_root: Path) -> None:
    extracted_root = Path(extracted_root).resolve()
    manifest_path=extracted_root/"server_migration"/"source_snapshot_manifest.json"
    if (not manifest_path.is_file()
        or json.loads(manifest_path.read_text(encoding="utf-8"))!=manifest):
        raise ValueError("extracted source snapshot manifest missing or changed")
    for member, expected in manifest["files"].items():
        parts = PurePosixPath(member).parts
        if not parts or parts[0] != "AI4science":
            raise ValueError(f"unexpected extracted member root: {member}")
        path = extracted_root.joinpath(*parts[1:]).resolve()
        if extracted_root not in path.parents or not path.is_file():
            raise ValueError(f"extracted source file missing or unsafe: {member}")
        with path.open("rb") as stream:
            actual = _sha256_stream(stream)
        if actual.lower() != str(expected).lower():
            raise ValueError(f"extracted source file hash mismatch: {member}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--extracted-root", type=Path)
    args = parser.parse_args()
    manifest = read_and_validate_manifest(args.archive)
    if args.extracted_root is not None:
        verify_extracted_tree(manifest, args.extracted_root)
    print(json.dumps({
        "status": "PASS",
        "contract_version": manifest["contract_version"],
        "verified_files": len(manifest["files"]),
        "source_git_commit": manifest.get("source_git_commit"),
    }, sort_keys=True))


if __name__ == "__main__":
    main()

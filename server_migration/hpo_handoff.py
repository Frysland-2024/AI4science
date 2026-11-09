#!/usr/bin/env python3
"""Transfer verified V11 HPO selection evidence from Windows to Linux without test data.

Export includes the Optuna DB, all trial metadata, selected/confirmation checkpoints,
and the frozen Validation *index*, but not the multi-GiB Validation arrays.
On the final-training machine, panels must be independently reproduced and hashed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STUDY_REL = Path("server_runs/v11_a0_js_optuna")
MANIFEST = "handoff_manifest.json"
VERSION = "v11-hpo-handoff-v2"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_index_digest(index: dict) -> str:
    return hashlib.sha256(json.dumps(
        index, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")).hexdigest()


def _args_from_contract(contract: dict) -> argparse.Namespace:
    return argparse.Namespace(
        trials=contract["max_new_trials"],
        hpo_steps=contract["hpo_steps"],
        confirm_steps=contract["confirmation_steps"],
        final_steps=contract["final_steps"],
        eval_every=contract["eval_interval_steps"],
        batch_size=contract["batch_size_parents"],
        microbatch_size=contract.get("microbatch_size_parents",contract["batch_size_parents"]),
        sampling_mode=contract.get("sampling_mode","random_batch"),
        prefetch_workers=contract["prefetch_workers"],
        prefetch_batches=contract["prefetch_batches"],
        native_threads=contract["native_threads"],
        worker_peak_cache=contract["worker_peak_cache"],
        validation_bf16=contract["validation_precision"] == "bf16",
        max_gpu_hours=contract["max_gpu_hours"],
    )


def export_handoff(root: Path, output: Path) -> dict:
    import one_click_v11 as runner

    root = root.resolve()
    study = root / STUDY_REL
    contract_file = study / "contract.json"
    rec_file = study / "final_recommendation.json"
    if not contract_file.is_file() or not rec_file.is_file():
        raise RuntimeError("HPO and independent confirmation must be complete before export")
    contract = _read(contract_file)
    recommendation = _read(rec_file)
    args = _args_from_contract(contract)
    if runner.contract(args) != contract:
        raise RuntimeError("Source/config fingerprints differ from the completed HPO contract")
    runner.validate_final_recommendation(study, args, contract_file, contract)
    if recommendation.get("status") != "hpo_and_confirmation_completed":
        raise RuntimeError("Incomplete HPO recommendation; refusing export")

    selected = recommendation["best_hpo_trial"]
    confirm_seeds = contract["confirmation_seeds"]
    files = {
        "contract.json": contract_file,
        "final_recommendation.json": rec_file,
        "gradient_gate.json":study / "gradient_gate.json",
        "handoff_validation_panel_index.json": study / "validation_panels_v11/panel_index.json",
    }
    for number in range(contract["max_new_trials"]):
        name = f"hpo_{number:03d}"
        for fname in ("contract.json", "result.json"):
            files[f"trials/{name}/{fname}"] = study / "trials" / name / fname
        if number == selected:
            for fname in ("best.pt", "last.pt"):
                files[f"trials/{name}/{fname}"] = study / "trials" / name / fname
    for seed in confirm_seeds:
        name = f"confirm_{seed}"
        for fname in ("contract.json", "result.json", "best.pt", "last.pt"):
            files[f"trials/{name}/{fname}"] = study / "trials" / name / fname

    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite handoff: {output}")
    with tempfile.TemporaryDirectory(prefix="v11-handoff-") as td:
        snapshot = Path(td) / "optuna.sqlite3"
        with sqlite3.connect(str(study / "optuna.sqlite3")) as source:
            with sqlite3.connect(str(snapshot)) as target:
                source.backup(target)
        files["optuna.sqlite3"] = snapshot
        for name, path in files.items():
            if not path.is_file():
                raise FileNotFoundError(f"Missing handoff evidence: {name}")
        manifest = {
            "version": VERSION,
            "study": STUDY_REL.as_posix(),
            "selection_source": "frozen simulated Validation only",
            "rruff_or_test_scores_included": False,
            "contract_sha256": sha256(contract_file),
            "validation_index_sha256": _canonical_index_digest(_read(files["handoff_validation_panel_index.json"])),
            "files": {name: sha256(path) for name, path in sorted(files.items())},
        }
        if manifest["validation_index_sha256"] != recommendation["validation_panel_index_sha256"]:
            raise RuntimeError("Validation panel identity differs from selected HPO")
        temporary = output.with_name(output.name + ".partial")
        try:
            with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1, allowZip64=True) as archive:
                for name, path in sorted(files.items()):
                    archive.write(path, arcname=name)
                archive.writestr(MANIFEST, json.dumps(manifest, sort_keys=True, indent=2))
            temporary.replace(output)
        finally:
            temporary.unlink(missing_ok=True)
    return {"archive": str(output), "sha256": sha256(output), "file_count": len(files),
            "selected_trial": selected, "confirmation_seeds": confirm_seeds}


def import_handoff(root: Path, archive_path: Path) -> dict:
    """No arbitrary ZIP extraction: explicit allowlist, verified bytes, no overwrite."""
    root = root.resolve()
    target = root / STUDY_REL
    archive_path = archive_path.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        if archive.namelist().count(MANIFEST) != 1:
            raise RuntimeError("Handoff manifest is absent or duplicated")
        manifest = json.loads(archive.read(MANIFEST))
        if manifest.get("version") != VERSION or manifest.get("study") != STUDY_REL.as_posix():
            raise RuntimeError("Incompatible HPO handoff contract")
        files = manifest.get("files")
        if not isinstance(files, dict) or not files:
            raise RuntimeError("Empty/malformed handoff manifest")
        names = set(archive.namelist())
        if names != set(files) | {MANIFEST}:
            raise RuntimeError("Extra, missing, or repeated handoff archive members")
        for name, expected in files.items():
            relative = Path(name)
            if (relative.is_absolute() or ".." in relative.parts or "\\" in name
                    or ":" in name or not isinstance(expected, str) or len(expected) != 64):
                raise RuntimeError(f"Unsafe or invalid handoff member: {name}")
            digest = hashlib.sha256()
            with archive.open(name) as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != expected:
                raise RuntimeError(f"Handoff hash mismatch: {name}")
        if files.get("contract.json") != manifest.get("contract_sha256"):
            raise RuntimeError("HPO contract hash missing")
        index_obj = json.loads(archive.read("handoff_validation_panel_index.json"))
        if _canonical_index_digest(index_obj) != manifest.get("validation_index_sha256"):
            raise RuntimeError("Validation index identity missing or mismatched")
        recommendation = json.loads(archive.read("final_recommendation.json"))
        if "gradient_gate.json" not in files:
            raise RuntimeError("Missing frozen TRAIN gradient prior in HPO handoff")
        frozen_gate=json.loads(archive.read("gradient_gate.json"))
        frozen_contract=json.loads(archive.read("contract.json"))
        import one_click_v11 as runner
        if (frozen_gate.get("status")!="TRAIN_ONLY_GRADIENT_GATE_PASS"
                or frozen_gate.get("science_identity_sha256")!=runner.gradient_science_identity(frozen_contract)
                or frozen_contract.get("schema")!="v11_154975_gradient_informed_three_parameter_v3"
                or recommendation.get("gradient_gate_sha256")!=files["gradient_gate.json"]):
            raise RuntimeError("HPO handoff gradient-gate science protocol mismatch")
        if (recommendation.get("status") != "hpo_and_confirmation_completed"
                or recommendation.get("contract_sha256") != manifest["contract_sha256"]
                or recommendation.get("validation_panel_index_sha256") != manifest["validation_index_sha256"]):
            raise RuntimeError("Handoff recommendation and frozen evidence are inconsistent")
        # Preflight all destinations before any write.
        for name, expected in files.items():
            dst = target / name
            if dst.exists() and sha256(dst) != expected:
                raise RuntimeError(f"Conflicting existing HPO evidence: {dst}")
        for name, expected in files.items():
            dst = target / name
            if not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                temp = dst.with_name(dst.name + ".handoff-partial")
                try:
                    with archive.open(name) as source, temp.open("wb") as sink:
                        for block in iter(lambda: source.read(1024 * 1024), b""):
                            sink.write(block)
                    if sha256(temp) != expected:
                        raise RuntimeError(f"Imported HPO hash mismatch: {name}")
                    temp.replace(dst)
                finally:
                    temp.unlink(missing_ok=True)
    return {"archive_sha256": sha256(archive_path), "imported_files": len(files),
            "study_directory": str(target), "status": "imported_unscored"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("export", "import"))
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    target = args.archive or (args.root / "_local/v11_hpo_handoff.zip")
    result = (export_handoff(args.root, target) if args.action == "export"
              else import_handoff(args.root, target))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

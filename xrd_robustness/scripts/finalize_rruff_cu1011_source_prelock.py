"""Private reproducibility-checked RRUFF-1011 Cu-domain prelock:
source manifest, model grid, labels, subgroup disjointness.
No ML inference or benchmark model scoring.
"""
from pathlib import Path
import csv,json,hashlib,collections
import numpy as np
import os
ROOT=Path(os.environ.get("AI4SCIENCE_ROOT",str(Path(__file__).resolve().parents[2])))
BASE=Path(os.environ.get("RRUFF_AUDIT_DIR",str(ROOT/"_local/rruff_benchmark_prospective_20261104")))
q=list(csv.DictReader((BASE/"RRUFF_1034_CORRECTED_SOURCE_PHYSICS_AUDIT_20261104.csv").open(encoding="utf8",newline="")))
m=list(csv.DictReader((BASE/"RRUFF_1034_MAIN_PROSPECTIVE_QA_AUDITED_NOT_FROZEN.csv").open(encoding="utf8",newline="")))
p=list(csv.DictReader((BASE/"RRUFF_1034_SOURCE_LABEL_PREPROCESS_QA_20261104.csv").open(encoding="utf8",newline="")))
assert len(q)==len(m)==len(p)==1034
by_m={r["sample_variant_id"]:r for r in m}
by_p={r["variant_id"]:r for r in p}
npz=BASE/"RRUFF_1011_CU_FULL_10_80_DENSE_V11_SOURCE_PREPROC_NOT_FROZEN_20261104.npz"
arr=np.load(npz,allow_pickle=False)
ids=list(arr["sample_ids"])
labels=list(arr["crystal_system_labels"])
inputs=arr["xrd_input"]
observed=arr["observation_mask"]
assert ids==[x["sample_variant_id"] for x in q if x["assigned_source_subgroup"]=="CU_FULL_10_80_DENSE"]
assert len(ids)==1011 and len(set(ids))==1011
assert inputs.shape==(1011,3501)
assert observed.shape==inputs.shape and bool(observed.all())
assert bool(np.isfinite(inputs).all()) and float(inputs.min())>=0
assert bool(np.allclose(inputs.max(axis=1),1,atol=1e-6,rtol=0))
EXPECTED_ORDER=("triclinic","monoclinic","orthorhombic","tetragonal","trigonal","hexagonal","cubic")
from importlib.machinery import SourceFileLoader
# Read exact label order from the current model source, not a remembered value.
text=(ROOT/"xrd_robustness/src/xrd_robustness/structure_data.py").read_text(encoding="utf8")
assert all(f'"{x}"' in text for x in EXPECTED_ORDER)
assert len(labels)==len(ids)
for j,sid in enumerate(ids):
    assert labels[j]==by_m[sid]["final_candidate_system"]
    assert by_p[sid]["main_label"]==labels[j]
    assert by_p[sid]["source_members_sha_verified"]=="True"
    assert by_p[sid]["source_id_valid"]=="True"
    assert by_p[sid]["raw_file_declared_calculated"]=="False"
    assert by_p[sid]["main_DIF_cell_valid"]=="True"
    assert by_p[sid]["DIF_parsed_crystal_system"]==labels[j]
groups=collections.defaultdict(list)
for item in q:
    groups[item["assigned_source_subgroup"]].append(item["sample_variant_id"])
assert {k:len(v) for k,v in groups.items()}=={
    "CU_FULL_10_80_DENSE":1011,
    "CU_PARTIAL_10_80_DENSE":3,
    "MO_RADIATION_SEPARATE_PROTOCOL":19,
    "QUARANTINE_SPARSE_IRREGULAR_XY":1
}
assert set(groups["CU_FULL_10_80_DENSE"])==set(ids)
assert {i for g in groups.values() for i in g}==set(by_m)
assert sum(len(g) for g in groups.values())==1034
assert {"R040049-1","R040064-1"}.issubset(ids)
assert len([x for x in q if x["xy_coordinate_repairs_count"]!="0"])==19
assert sum(int(x["duplicate_theta_aggregation_count"])>0 for x in q)==1
digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
locked=BASE/"RRUFF_1011_CUKA_MAIN_SOURCE_PRELOCK_20261104.csv"
fields=list(m[0])+["v11_label_index","v11_fixed_theta_min","v11_fixed_theta_max",
                   "v11_step_deg","v11_input_bins","v11_input_max_normalized",
                   "radiation_basis","raw_diffraction_axis_repaired","source_qa_row_sha256"]
rows=[]
for i,sid in enumerate(ids):
    orig=by_m[sid];audit=next(a for a in q if a["sample_variant_id"]==sid)
    qa=by_p[sid]
    records={**orig,
             "v11_label_index":EXPECTED_ORDER.index(labels[i]),
             "v11_fixed_theta_min":10.0,"v11_fixed_theta_max":80.0,
             "v11_step_deg":.02,"v11_input_bins":3501,
             "v11_input_max_normalized":"AFTER_RESAMPLING",
             "radiation_basis":"CuKa assumed; DIF source 1.541838A; RAW explicit Mo absent",
             "raw_diffraction_axis_repaired":audit["xy_coordinate_repairs_count"],
             "source_qa_row_sha256":hashlib.sha256(json.dumps(qa,sort_keys=True,ensure_ascii=False).encode()).hexdigest()}
    rows.append(records)
with locked.open("w",encoding="utf8",newline="") as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
contract={
  "schema":"rruff-1011-cu-domain-source-prelock-v1",
  "date":"2026-11-04",
  "source_case_counts":{"broad_prospective_1034":1034,
                        "main_Cu_full_density_10_to_80":1011,
                        "Mo_experimental_separate":19,"Cu_partial_angle":3,
                        "sparse_irregular_quarantined":1},
  "primary_1011_crystal_system_distribution":dict(collections.Counter(labels)),
  "class_to_model_index":{name:i for i,name in enumerate(EXPECTED_ORDER)},
  "source_provenance_verify":"1034 per-source RAW and DIF SHA256, exact ID, local RRUFF URL, sample owner/source and DIF space group metadata; 1011 full-window Cu compatibility",
  "main_caveat":"Original RAW wavelength often not explicit; Cu assumed from paired DIF and peak-location correspondence. 134 alias SG symbols within 1011 validated by symmetry family and raw class but still may need independent canonical setting review. 2 admitted mildly mixed source specimens have source quality flags; do not call exact Lee-threshold-certified.",
  "source_preprocessing_protocol":{
      "source_zip":"E:/AI4science/RRUFF/XY_RAW.zip",
      "parse_numeric_lines":"Only after ##FILETYPE=... before ##END=, exponential numeric notation accepted; 0<2theta<180; isolated impossible negative 2theta discarded but source bytes preserved",
      "axis_repair":"19 source rows have x coordinate obvious lost-leading-digit typo repaired using neighbouring native sampling; 1 duplicate theta pair averaged (source and corrected values in repair JSON)",
      "reference_wavelength":"Original Cu-compatible source group only; V11 wavelength 1.54184A",
      "grid_start":10.0,"grid_stop":80.0,"grid_step":.02,"model_length":3501,
      "resampling":"linear within all source-supported measured 2theta; negative clip, no background removal, maximum normalize AFTER resampling on exact model grid",
      "source_mask":"Every retained 1011 profile covers all 3501 input 2theta bins; no out-of-support extrapolation or padded zeros in main cohort",
      "normalization":"xrd_input maximum=1 per row, finite and nonnegative"
  },
  "snapshot":{
    "main_Cu_1011_manifest_sha256":digest(locked),
    "main_Cu_1011_npz_sha256":digest(npz),
    "1034_metadata_source_audit_sha256":digest(BASE/"RRUFF_1034_CORRECTED_SOURCE_PHYSICS_AUDIT_20261104.csv"),
    "1034_original_stated_candidate_manifest_sha256":digest(BASE/"RRUFF_1034_MAIN_PROSPECTIVE_QA_AUDITED_NOT_FROZEN.csv"),
    "repair_log_sha256":digest(BASE/"RRUFF_1034_RAW_THETA_TYPO_RECONSTRUCTION_20261104.json"),
    "original_local_RRUFF_RAW_zip_sha256":"948a133482bb3c99da80194cc2848933aee668129beb209150f7f850cd4b0587",
    "original_local_RRUFF_DIF_zip_sha256":"3b540db61664cacdd22268ffbac6ab586ca6bce389b7399cc3e9baaeb6607b03"
  },
  "run_status":"SOURCE_METADATA_AND_ENGINEERING_PRELOCKED__MODEL_HOLDOUT_NOT_EVALUATED",
  "final_test_not_evaluated":True,
  "label_structure_independent_vetting_note":"No crystallographic experimental independent space-group solution available for every RRUFF mineral; source-derived labels are reference-based. No proof of sample impurity-free beyond source quality flags.",
  "source_archive_untouched":True,
  "previous_cohort_manifests_unchanged":True,
  "recommendation":"Use 1011 primary for exact CuKa/full-grid source-consistent benchmark; 19 Mo and 3 partial Cu should be separately reported only with a preregistered domain protocol; reject 1 232-point sparse RAW for dense-spectrum input. Do not pretend source-filtered 1011 matches Bin Cao's separate 1003 sample IDs."
}
out=BASE/"RRUFF_1011_CUKA_MAIN_SOURCE_PRELOCK_CONTRACT_20261104.json"
out.write_text(json.dumps(contract,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
print(json.dumps({"status":"PASS","n":len(ids),"class_counts":contract["primary_1011_crystal_system_distribution"],
  "source_repaired_records":19,"duplicated_angle_sources":1,
  "next_groups":{k:len(v) for k,v in groups.items()},
  "file":str(locked),"sha256":digest(locked),
  "npz_sha256":digest(npz),"contract":str(out)},ensure_ascii=False,indent=2),flush=True)

"""RRUFF-1034 corrected source verification and physically explicit V11 preprocessing.

Corrects first-pass scientific-notation parser bug, repairs isolated x-coordinate
typos with same-neighbour expected sampling (without altering source ZIP),
classifies 19 explicit Mo wavelength cases, isolates 3 Cu partial and 1 sparse
"RAW" profile. Saves 1011 full-window Cu candidates and layered diagnostics.
NO model inference, no Test scoring. Old manifests and v1 receipts immutable.
"""
from __future__ import annotations
from pathlib import Path
import csv,json,re,zipfile,hashlib,collections,math
import numpy as np
from scipy.ndimage import percentile_filter,gaussian_filter1d
from scipy.signal import find_peaks

import os
ROOT=Path(os.environ.get("AI4SCIENCE_ROOT",str(Path(__file__).resolve().parents[2])))
BASE=Path(os.environ.get("RRUFF_AUDIT_DIR",str(ROOT/"_local/rruff_benchmark_prospective_20261104")))
MAN=BASE/"RRUFF_1034_MAIN_PROSPECTIVE_QA_AUDITED_NOT_FROZEN.csv"
rows=list(csv.DictReader(MAN.open(encoding="utf8",newline="")))
assert len(rows)==1034
GRID=np.round(10.+.02*np.arange(3501,dtype=np.float64),8)
RE_NUM=r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?'
XY_RE=re.compile(r'^\s*('+RE_NUM+r')\s*,\s*('+RE_NUM+r')\s*$',re.M)
META_RE=re.compile(r'^##([^=\n]+)=([^\n]*)',re.M)
WAVELEN_RE=re.compile(r'X-RAY WAVELENGTH:\s*([0-9.]+)',re.I)
DIF_RE=re.compile(r'^\s*('+RE_NUM+r')\s+('+RE_NUM+r')\s+'+RE_NUM+r'\s+[+-]?\d+\s+[+-]?\d+\s+[+-]?\d+',re.M)
L_CU=1.541838
L_MO=.71073
def sha(data):return hashlib.sha256(data).hexdigest()
def meta(data):
    return {k.strip().upper():v.strip() for k,v in META_RE.findall(data.decode("utf8","replace").replace("\r","\n"))}
def parse(data):
    text=data.decode("utf8","replace").replace("\r","\n")
    # Numeric citation/header dates (e.g. "2009, 10") are not diffraction data.
    if "##FILETYPE=" not in text:
        raise ValueError("No explicit RAW powder source delimiter")
    body=text.split("##FILETYPE=",1)[1]
    if "##END=" in body:body=body.split("##END=",1)[0]
    values=np.asarray([(float(x),float(y)) for x,y in XY_RE.findall(body)],dtype=np.float64)
    if len(values)==0:raise ValueError("Unparseable XRD source file")
    if np.any(~np.isfinite(values)):raise ValueError("Nonfinite original x-y data")
    # Physical two-theta is 0..180 degrees; the source R130034 begins with
    # a clearly corrupted '-2009, 10' extra line before proper 10.0000.
    # Do not turn this numeric typo into a genuine measured diffraction point.
    impossible=(values[:,0]<0)|(values[:,0]>180)
    if int(impossible.sum())>1:
        raise ValueError("More than one impossible angular source datum")
    values=values[~impossible]
    return values
def radiate(m):
    desc=m.get("DIFFRACTION SAMPLE DESCRIPTION","")
    if re.search(r'(?i)\busing\s+Mo\s+radiation|\bmolybdenum\b',desc):return "Mo_explicit_description"
    if re.search(r'(?i)\busing\s+Cu\s+radiation|\bCu.?K',desc):return "Cu_explicit_description"
    return "unspecified_source_assumed_Cu_from_DIF"
def repair_axes(raw,step_guess):
    x=np.asarray(raw[:,0],dtype=float).copy()
    y=np.asarray(raw[:,1],dtype=float).copy()
    repairs=[]
    # Do not change source archived bytes; only source-copy angular typos that are
    # bracketed by two consistent neighbouring positions.
    for j in range(1,len(x)-1):
        if x[j-1]<x[j]<x[j+1]:continue
        left,right=float(x[j-1]),float(x[j+1])
        if not(left<right) or right-left>.051 or (right-left)<step_guess*.8:
            continue
        # Recover lost tens digits whenever a decimal-suffix uniquely indicates
        # the intended coordinate. If otherwise ambiguous, use midpoint and FLAG.
        opts=[]
        for k in range(1,10):
            v=round(left+k*step_guess,6)
            if v<right-1e-6:opts.append(v)
        if not opts:continue
        original=float(x[j])
        suffix=round(original%1,5)
        favored=[v for v in opts if abs(round(v%1,5)-suffix)<.0003]
        if len(favored)==1:
            val=favored[0];evidence="same_fractional_digits"
        elif len(opts)==1:
            val=opts[0];evidence="unique_grid_position"
        else:
            val=min(opts,key=lambda v:abs(v-(left+right)/2))
            evidence="ambiguous_grid_midpoint"
        if val<=left or val>=right:continue
        repairs.append({"index":j,"source_theta":original,"reconstructed_theta":val,
                        "neighbors":[left,right],"method":evidence})
        x[j]=val
    # Recheck all x; sorting would hide a broad mix-up. Only singular source
    # duplicated 2theta coordinates are eligible for deterministic intensity
    # mean aggregation, and never when profile is genuinely sparse.
    n_nonmon=int(np.sum(np.diff(x)<=0))
    condensed=0
    if n_nonmon and len(x)>1000 and n_nonmon<=4:
        xs,inv,counts=np.unique(x,return_inverse=True,return_counts=True)
        if len(xs)!=len(x) and np.all(np.diff(xs)>0):
            sums=np.bincount(inv,weights=y)
            y=sums/counts
            x=xs
            condensed=int(sum(counts>1))
    valid=bool(np.all(np.diff(x)>0))
    return x,y,repairs,condensed,valid
def is_dense(x):
    if len(x)<1000:return False
    dif=np.diff(x)
    if len(dif)==0:return False
    m=float(np.median(dif))
    # Less than 0.4 degree largest gap for a dense laboratory profile, instead
    # of silently joining isolated reflection intensities into fake spectra.
    return bool(np.max(dif)<=.40 and m<.11)
def project_to_cu(x):
    argument=(L_CU/L_MO)*np.sin(np.deg2rad(x/2))
    good=argument<=1.
    cu=np.rad2deg(2*np.arcsin(np.clip(argument[good],0,1)))
    return cu,good
def observed_peak_support(x,y):
    bg=percentile_filter(y,10,size=301 if len(y)>301 else 21,mode="nearest")
    signal=gaussian_filter1d(np.maximum(y-bg,0),1.3)
    ids,_=find_peaks(signal,prominence=max(1,float(np.max(signal))*.025),distance=max(1,int(.12/max(.001,float(np.median(np.diff(x)))))))
    return x[ids]
spectra=np.zeros((len(rows),len(GRID)),dtype=np.float32)
coverage=np.zeros_like(spectra,dtype=np.bool_)
quality=[]
repairs_all=[]
counter=collections.Counter()
with zipfile.ZipFile(ROOT/"RRUFF/XY_RAW.zip") as rz,zipfile.ZipFile(ROOT/"RRUFF/DIF.zip") as dz:
 for i,row in enumerate(rows):
    sid=row["sample_variant_id"]
    rbytes=rz.read(row["raw_member"]);dbytes=dz.read(row["dif_member"])
    assert sha(rbytes)==row["raw_sha256"],sid
    assert sha(dbytes)==row["dif_sha256"],sid
    md=meta(rbytes)
    if md.get("RRUFFID","")!=row["base_rruff_id"]:raise RuntimeError("SOURCE ID MISMATCH "+sid)
    raw=parse(rbytes)
    native_step=float(np.median(np.diff(raw[:,0]))) if len(raw)>1 else 0
    if native_step<=0: native_step=.01
    x,y,repairs,agg,monotone=repair_axes(raw,native_step)
    if not monotone and len(x)>0 and np.all(np.isfinite(x)) and len(x)<=300:
        # irregular powder-peak list, intentionally NOT faked into a full XRD
        # continuum by sorting and interpolation.
        classification="QUARANTINE_SPARSE_IRREGULAR_XY"
    else:
        classification="PENDING"
    rad=radiate(md)
    if classification=="PENDING":
        if not monotone or not is_dense(x):
            classification="QUARANTINE_NON_DENSE_OR_UNREPAIRED"
        elif rad=="Mo_explicit_description":
            classification="MO_RADIATION_SEPARATE_PROTOCOL"
        else:
            if x[0]<=10.0001 and x[-1]>=79.9999:
                classification="CU_FULL_10_80_DENSE"
            else:
                classification="CU_PARTIAL_10_80_DENSE"
    diftxt=dbytes.decode("utf8","replace").replace("\r","\n")
    wv=WAVELEN_RE.search(diftxt)
    difwave=float(wv.group(1)) if wv else None
    if rad=="Mo_explicit_description":
        transformed,keep=project_to_cu(x)
        tx=transformed;ty=y[keep]
    else:
        tx=x.copy();ty=y.copy()
    gridmask=(GRID>=tx[0]-1e-8)&(GRID<=tx[-1]+1e-8) if len(tx) else np.zeros(len(GRID),dtype=bool)
    if classification not in ("QUARANTINE_SPARSE_IRREGULAR_XY","QUARANTINE_NON_DENSE_OR_UNREPAIRED") and not np.all(np.diff(tx)>0):raise RuntimeError("Nonmonotone projected x "+sid)
    coverage[i]=gridmask
    anchor=(tx>=10)&(tx<=80)
    vpeak=float(np.max(np.maximum(0,ty[anchor]))) if np.any(anchor) else 0.
    if np.any(gridmask) and vpeak>0 and classification not in ("QUARANTINE_SPARSE_IRREGULAR_XY","QUARANTINE_NON_DENSE_OR_UNREPAIRED"):
        sample=np.maximum(0,np.interp(GRID[gridmask],tx,ty)).astype(np.float64)
        # Match V11's max-normalized input on the exact resampled model grid:
        # interpolation can shift/narrow the observed maximum vs native bins.
        max_resampled=float(np.max(sample))
        if max_resampled<=0 or not np.isfinite(max_resampled):
            raise RuntimeError("Resampled model input lacks positive signal: "+sid)
        spectra[i,gridmask]=(sample/max_resampled).astype(np.float32)
    else:
        # Do not generate a fabricated smoothed spectrum for sparse cases
        spectra[i,:]=0
    dif_refl=np.asarray([(float(a),float(b)) for a,b in DIF_RE.findall(diftxt)],dtype=np.float64).reshape((-1,2))
    matchratio=None
    if classification=="CU_FULL_10_80_DENSE" and len(dif_refl)>=2:
        loc=observed_peak_support(tx,ty)
        subset=dif_refl[(dif_refl[:,0]>=10)&(dif_refl[:,0]<=80)]
        subset=subset[np.argsort(subset[:,1])[::-1]][:12]
        if len(subset):
            best=0
            for shift in np.arange(-.2,.201,.04):
                matches=sum((len(loc) and np.min(abs(loc-(p+shift)))<=.28) for p,_ in subset)
                best=max(best,int(matches))
            matchratio=round(best/len(subset),4)
    for change in repairs:
        repairs_all.append({"sample_variant_id":sid,**change})
    counter[classification]+=1
    if repairs:counter["records_with_theta_typos_repaired"]+=1
    if agg:counter["records_with_duplicate_theta_averaged"]+=1
    if row["label_evidence_tier"].startswith("B_"):counter["alias_label_independent_review_required"]+=1
    counter["total"]+=1
    if rad=="Mo_explicit_description" and difwave and abs(difwave-L_CU)<.002:
        counter["Mo_RAW_with_Cu_DIF_lambda_CONFLICT"]+=1
    if i%260==0:
        print(json.dumps({"step":"FIXED_SOURCE","read":i+1,"count":len(rows),
                          "current_class":classification}),flush=True)
    quality.append({
      "sample_variant_id":sid,
      "base_rruff_id":row["base_rruff_id"],
      "mineral":row["mineral_name"],
      "source_radiation_class":rad,
      "DIF_reference_wavelength_A":difwave or "",
      "Mo_original_RAW_with_Cu_DIF":(rad=="Mo_explicit_description" and difwave and abs(difwave-L_CU)<.002),
      "native_points_parsed_including_scientific_notation":len(raw),
      "first_native_theta":round(float(raw[0,0]),6),
      "last_native_theta":round(float(raw[-1,0]),6),
      "native_theta_width":round(float(raw[-1,0]-raw[0,0]),6),
      "scientific_notation_exponents_count":len(re.findall(r'[Ee][-+]?\d+',rbytes.decode("utf8","replace").replace("\r","\n"))),
      "xy_coordinate_repairs_count":len(repairs),
      "duplicate_theta_aggregation_count":agg,
      "after_repair_monotone":monotone,
      "after_repair_dense":is_dense(x) if monotone else False,
      "assigned_source_subgroup":classification,
      "Cu_theta_equivalent_min":round(float(tx[0]),5) if len(tx) else "",
      "Cu_theta_equivalent_max":round(float(tx[-1]),5) if len(tx) else "",
      "V11_grid_covered_bins":int(np.sum(gridmask)),
      "V11_grid_missing_bins":len(GRID)-int(np.sum(gridmask)),
      "signal_valid":bool(np.max(spectra[i])>0 and np.isfinite(spectra[i]).all()),
      "experimental_peak_reference_Cu_main_top12_alignment":matchratio if matchratio is not None else "",
      "space_group_symbol":row["dif_space_group"],
      "seven_crystal_system_label":row["final_candidate_system"],
      "label_evidence_tier":row["label_evidence_tier"],
      "explicit_mixed_phase":row["mixed_phase_warning"],
      "LEE_mixed_quality_tier":row.get("LEE_mixture_evidence_tier",""),
      "model_prediction_scored":"NO",
    })
assert len(quality)==len(rows)==1034
assert sum(counter[k] for k in ("CU_FULL_10_80_DENSE","CU_PARTIAL_10_80_DENSE","MO_RADIATION_SEPARATE_PROTOCOL","QUARANTINE_SPARSE_IRREGULAR_XY","QUARANTINE_NON_DENSE_OR_UNREPAIRED"))==1034
assert all(q["signal_valid"] for q in quality if q["assigned_source_subgroup"] not in ("QUARANTINE_SPARSE_IRREGULAR_XY","QUARANTINE_NON_DENSE_OR_UNREPAIRED"))
assert len({q["sample_variant_id"] for q in quality})==1034
file=BASE/"RRUFF_1034_CORRECTED_SOURCE_PHYSICS_AUDIT_20261104.csv"
with file.open("w",newline="",encoding="utf-8") as f:
    writer=csv.DictWriter(f,fieldnames=list(quality[0]));writer.writeheader();writer.writerows(quality)
repairfile=BASE/"RRUFF_1034_RAW_THETA_TYPO_RECONSTRUCTION_20261104.json"
repairfile.write_text(json.dumps(repairs_all,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
masksha={}
for group in ("CU_FULL_10_80_DENSE","CU_PARTIAL_10_80_DENSE","MO_RADIATION_SEPARATE_PROTOCOL","QUARANTINE_SPARSE_IRREGULAR_XY","QUARANTINE_NON_DENSE_OR_UNREPAIRED"):
    indexes=[i for i,q in enumerate(quality) if q["assigned_source_subgroup"]==group]
    if not indexes:continue
    p=BASE/("RRUFF_"+str(len(indexes))+"_"+group+"_V11_SOURCE_PREPROC_NOT_FROZEN_20261104.npz")
    np.savez_compressed(p,xrd_input=spectra[indexes,:],
        observation_mask=coverage[indexes,:],
        sample_ids=np.array([rows[i]["sample_variant_id"] for i in indexes]),
        crystal_system_labels=np.array([rows[i]["final_candidate_system"] for i in indexes]))
    masksha[group]={"n":len(indexes),"file":str(p),"sha256":sha(p.read_bytes())}
summary={
 "status":"REPAIRED_1034_SOURCE_AUDIT_COMPLETED__NO_FINAL_MODEL_FREEZE",
 "version":"rruff-v11-source-physics-audit-v2",
 "corrected_source_counts":dict(counter),
 "groups":masksha,
 "audit_csv":{"path":str(file),"sha256":sha(file.read_bytes())},
 "repair_log":{"path":str(repairfile),"sha256":sha(repairfile.read_bytes())},
 "source_radiation_policy":{
    "Cu":"RRUFF RAW radiation unspecified in headers; Cu assumption based on main DIF wavelength and physical peak alignment. Keep source wavelength evidence tier.",
    "Mo":"19 RAW descriptions explicitly state use of Mo radiation. For Mo diagnostic array only, transform each measured Mo theta to hypothetical Cu theta using Bragg law with lambdaMo=0.71073A and lambdaCu=1.541838A. True Cu irradiation intensities are NOT reproduced, so not eligible for original Cu-main benchmark without a separate real-domain policy.",
    "sparse":"Irregular 232-point Harmotome RAW list has no dense measured continuum; never infer artificial full-grid intensities by interpolation."
 },
 "model_grid":"V11 fixed 10-80 0.02 deg (3501 bins); linear interpolate inside actual angular source coverage, clip negative, maximum-normalize, zero outside support with explicit observation mask, no background subtraction.",
 "quality_labels":"A directly pymatgen-parsed DIF SG, B alias-family plus original RAW consistency (independent crystallographic setting review desirable); trigonal labels from SG supersede hexagonal-axis raw headers",
 "original_1034_manifest_sha256":sha(MAN.read_bytes()),
 "no_model_scoring":True,
 "next":"Choose and preregister main fully Cu-native full-window group and how to report 19 Mo/3 Cu partial/1 sparse separately, then freeze exactly SHA-defined inputs before V11 HPO final Test. Source-only audit cannot guarantee all independent crystal structures/experimental diffraction wavelength for unspecified Cu sources."
}
summfile=BASE/"RRUFF_1034_CORRECTED_SOURCE_AUDIT_20261104.json"
summfile.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)

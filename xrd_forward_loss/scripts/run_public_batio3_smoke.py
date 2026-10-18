"""Public BaTiO3 (P4mm) feasibility smoke: forward parity, synthetic parameter regression A/B.
This is NOT an experimental-domain or a multi-structure generalization result.
Requires CUDA; uses existing HfCd pilot training machinery without modifying it.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import torch
from pymatgen.core import Structure, Lattice
from pymatgen.analysis.diffraction.xrd import XRDCalculator
from scipy.stats import qmc
from xrd_inversion.gpu_forward import CachedTetragonalGPUForward
from pxrd_forward_loss.training import fit
from pxrd_forward_loss.evaluation import evaluate_model
from pxrd_forward_loss.data import split_indices

ROOT = Path(__file__).resolve().parents[2]
CIF = ROOT / "xrd_forward_loss/data/public_cif/BaTiO3_COD_9014273_P4mm.cif"
CFG = ROOT / "xrd_inversion/configs/week1_formal_gate.json"

def make_structure_q(parent, q, cfg):
    u0 = (2*np.log(parent.lattice.a)+np.log(parent.lattice.c))/3
    v0 = np.log(parent.lattice.c/parent.lattice.a)
    u = u0 + float(q[0])*cfg["du_half_range"]
    v = v0 + float(q[1])*cfg["dv_half_range"]
    s=parent.copy()
    s.modify_lattice(Lattice.tetragonal(float(np.exp(u-v/3)),float(np.exp(u+2*v/3))))
    return s

def go(args):
    torch.manual_seed(20261018)
    np.random.seed(20261018)
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA_REQUIRED: no scientific run performed")
    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    parent = Structure.from_file(CIF)
    assert parent.composition.reduced_formula == "BaTiO3"
    assert len(parent)==5
    assert abs(parent.lattice.a-parent.lattice.b)<1e-5
    assert parent.lattice.c>parent.lattice.a
    forward = CachedTetragonalGPUForward(parent,grid_config=cfg["grid"],parameter_config=cfg["parameterization"],device="cuda",dtype=torch.float64)
    q0 = np.array([0.,0.,0.,-1.])
    axis=forward.axis.detach().cpu().numpy()
    ideal=forward.render(torch.as_tensor(q0[None],dtype=torch.float64,device="cuda"),compatibility=False)[0].detach().cpu().numpy()
    xrd=XRDCalculator(wavelength=cfg["grid"]["wavelength_angstrom"]).get_pattern(parent,two_theta_range=(10,80),scaled=True)
    positions=np.asarray(xrd.x)
    # Cross-check that Pymatgen peaks have signal at the same physical positions.
    indices=np.clip(np.rint((positions-10)/0.02).astype(int),0,len(axis)-1)
    peak_hits=float(np.mean([ideal[max(0,i-5):min(len(ideal),i+6)].max()>0.001 for i in indices]))
    if peak_hits<0.9:
        raise RuntimeError(f"physical peak-position gate FAILED, pymatgen peak coverage={peak_hits}")
    jac=forward.transformed_jacobian_numpy(q0)[:,:2]
    sing=np.linalg.svd(jac,compute_uv=False)
    condition=float(sing[0]/sing[1])
    if not np.isfinite(condition) or condition>1000:
        raise RuntimeError(f"identifiability gate failed: condition={condition}")
    out=Path(args.output)
    out.mkdir(parents=True,exist_ok=False)
    provenance={"scope":"one COD tetragonal BaTiO3 CIF; synthetic parameter draws; feasibility only",
      "cod_id":"9014273","cif_sha256":hashlib.sha256(CIF.read_bytes()).hexdigest(),
      "cif_source":"https://www.crystallography.net/cod/9014273.cif",
      "structural_reference_doi":"10.1103/PhysRev.105.856",
      "space_group_expected":"P4mm #99","a0_angstrom":parent.lattice.a,"c0_angstrom":parent.lattice.c,
      "pymatgen_peak_coverage":peak_hits,"jacobian_condition":condition}
    (out/"physical_gate.json").write_text(json.dumps(provenance,indent=2))
    if args.gate_only:
        print(json.dumps(provenance,indent=2));return
    # Fixed physical truth q. Measurement noise is NOT part of the differentiable renderer.
    q=(qmc.Sobol(2,scramble=True,seed=20261018).random_base2(args.sobol_power)*1.6-0.8).astype(np.float32)
    profiles=[]
    with torch.no_grad():
        for st in range(0,len(q),16):
            lattice=torch.as_tensor(q[st:st+16],dtype=torch.float64,device="cuda")
            nuisance=torch.tensor([[0.,-1.]],dtype=torch.float64,device="cuda").expand(len(lattice),2)
            p=forward.render(torch.cat([lattice,nuisance],axis=1),compatibility=False).cpu().numpy()
            profiles.extend(p)
    profiles=np.asarray(profiles)
    rng=np.random.default_rng(20261020)
    obs=[]
    for row in profiles:
        # simple count noise + background, as in the original Pilot; V9 five-nuisance
        # adapter is an independent Codex workstream, NOT claimed to be included.
        counts=rng.poisson(np.maximum(row,0)*40000+150)
        noisy=counts/np.max(counts)
        obs.append(np.log1p(100*noisy)/np.log(101))
    obs=np.asarray(obs,dtype=np.float32)
    clean=np.asarray(np.log1p(100*profiles)/np.log(101),dtype=np.float32)
    arrays={"q":q,"noisy":obs,"clean":clean}
    splits=split_indices(len(q),seed=20261019,train_fraction=.7,validation_fraction=.15)
    results={}
    for name,weight in (("A",0.0),("B",1.0)):
        trained=fit(arrays,splits,forward_model=forward,device=torch.device("cuda"),
          seed=20261021,epochs=args.epochs,learning_rate=.0005,batch_size=32,
          reconstruction_weight=weight,gradient_clip_norm=5.)
        ev=evaluate_model(trained["model"],arrays,splits["test"],forward_model=forward,
          device=torch.device("cuda"),a0=parent.lattice.a,c0=parent.lattice.c,
          du_half=cfg["parameterization"]["du_half_range"],dv_half=cfg["parameterization"]["dv_half_range"])
        results[name]={"train_seconds":trained["training_seconds"],"validation_mae":trained["best_validation_q_mae"],
          "test_parameter_mae_normalized":ev["parameter_mae_normalized"],
          "test_lattice_mae_angstrom":ev["lattice_mae_angstrom"],
          "test_clean_rmse":ev["reconstruction_rmse_transformed_clean"]}
    provenance.update({"sobol_power":args.sobol_power,"epochs":args.epochs,"seed":20261021,
      "counts":{"train":len(splits["train"]),"validation":len(splits["validation"]),"test":len(splits["test"])},
      "note":"Single seed screening only; lambda=1.0 inherited for engineering smoke, not validated for BaTiO3",
      "models":results})
    (out/"results.json").write_text(json.dumps(provenance,indent=2))
    print(json.dumps(provenance,indent=2))

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",default="xrd_forward_loss/reports/batio3_cod9014273_smoke")
    ap.add_argument("--gate-only",action="store_true")
    ap.add_argument("--epochs",type=int,default=4)
    ap.add_argument("--sobol-power",type=int,default=7)
    go(ap.parse_args())

"""P0/P1 measurement-aware forward and nuisance observability audit."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import torch
from scipy.optimize import least_squares
from pymatgen.analysis.diffraction.xrd import XRDCalculator
from pymatgen.core import Structure

from xrd_inversion.gpu_forward import CachedTetragonalGPUForward
from xrd_robustness.simulator import SimulationGrid, ideal_peak_table, simulate_from_peak_table
from xrd_robustness.physics import PhysicsParameters


def expected_profile(forward, q, eta):
    """Expected counts before stochastic readout; eta=(delta deg,FWHM deg,bg0,bg1,scale).

    Background terms are nonnegative endpoint fractions of the clean peak max;
    scale multiplies the clean normalized profile. This profile is intentionally
    not max-normalized, since doing so would erase scale information.
    """
    if q.shape[-1] != 2 or eta.shape[-1] != 5:
        raise ValueError("q must end in 2 and eta in 5 parameters")
    q_full = torch.cat((q, eta[..., :1] / float(forward.parameter_config["delta_half_range_deg"]),
                        torch.zeros_like(eta[..., :1])), dim=-1)
    # Set physical FWHM directly by inverting the cached log-q transform.
    lo = math.log(float(forward.parameter_config["fwhm_min_deg"]))
    hi = math.log(float(forward.parameter_config["fwhm_max_deg"]))
    width_q = (2.0 * torch.log(eta[..., 1].clamp_min(1e-8)) - lo - hi) / (hi - lo)
    q_full = torch.cat((q_full[..., :2], q_full[..., 2:3], width_q[..., None]), dim=-1)
    clean = forward.render(q_full, compatibility=False)
    axis = forward.axis
    t = (axis - axis.min()) / (axis.max() - axis.min())
    bg0 = eta[..., 2:3].clamp_min(0.0)
    bg1 = eta[..., 3:4].clamp_min(0.0)
    background = bg0 * (1.0 - t) + bg1 * t
    scale = eta[..., 4:5].clamp_min(0.1)
    return scale * clean + background


def _v9_clean(structure, axis_cfg):
    grid = SimulationGrid(axis_cfg["two_theta_min"], axis_cfg["two_theta_max"], axis_cfg["step"], axis_cfg["wavelength_angstrom"])
    pad = axis_cfg.get("peak_calculation_padding_deg", 0.0)
    padded = SimulationGrid(grid.two_theta_min-pad, grid.two_theta_max+pad, grid.step, grid.wavelength)
    peaks = ideal_peak_table(structure, padded)
    params = PhysicsParameters(delta_2theta_deg=0, fwhm_deg=.08, background_to_peak_ratio=0,
        noise_std_ratio=0, background_type="flat", severity_level=0, zero_shift_active=False,
        broadening_active=False, background_active=False, noise_active=False,
        preferred_orientation_active=False)
    return simulate_from_peak_table(peaks.positions, peaks.intensities, params, rng_seed=0,
        grid=grid, normalize=True, reflection_table=peaks)


def run_audit(root: Path, out: Path) -> dict:
    cif = root / "xrd_forward_loss/data/public_cif/BaTiO3_COD_9014273_P4mm.cif"
    cfg = json.loads((root / "xrd_inversion/configs/week1_formal_gate.json").read_text(encoding="utf-8"))
    structure = Structure.from_file(cif)
    if structure.composition.reduced_formula != "BaTiO3" or len(structure) != 5:
        raise RuntimeError("BaTiO3 CIF structure gate failed")
    sga = structure.get_space_group_info(symprec=1e-3)
    if sga != ("P4mm", 99):
        raise RuntimeError(f"expected P4mm #99, got {sga}")
    forward = CachedTetragonalGPUForward(structure, grid_config=cfg["grid"],
        parameter_config=cfg["parameterization"], device="cuda", dtype=torch.float64)
    q_probes = [np.array([0., 0.]), np.array([-.6,.6]), np.array([.6,-.6]), np.array([-.8,-.8])]
    renderer_rows=[]
    axis=forward.axis.cpu().numpy()
    for q in q_probes:
        qt=torch.tensor([q[0],q[1],0.,-1.],dtype=torch.float64,device="cuda")
        torch_profile=forward.render(qt,compatibility=False).cpu().numpy()
        # Pymatgen/V9 independent reference at the same q is obtained by scaling the cell.
        u0=(2*math.log(structure.lattice.a)+math.log(structure.lattice.c))/3
        v0=math.log(structure.lattice.c/structure.lattice.a)
        u=u0+q[0]*cfg["parameterization"]["du_half_range"]
        v=v0+q[1]*cfg["parameterization"]["dv_half_range"]
        from pymatgen.core import Lattice
        a=math.exp(u-v/3); c=math.exp(u+2*v/3)
        ref=Structure(lattice=Lattice.tetragonal(a,c),species=[site.species for site in structure],
            coords=structure.frac_coords,coords_are_cartesian=False)
        v9=_v9_clean(ref,cfg["grid"])
        delta=torch_profile-v9
        peaks=XRDCalculator(wavelength=cfg["grid"]["wavelength_angstrom"]).get_pattern(ref,
            two_theta_range=(cfg["grid"]["two_theta_min"],cfg["grid"]["two_theta_max"]),scaled=True)
        idx=np.clip(np.rint((np.asarray(peaks.x)-axis[0])/cfg["grid"]["step"]).astype(int),0,len(axis)-1)
        hits=float(np.mean([torch_profile[max(0,i-3):min(len(axis),i+4)].max()>.001 for i in idx])) if len(idx) else 0
        renderer_rows.append({"q":q.tolist(),"v9_max_abs":float(np.max(np.abs(delta)),),
            "v9_rmse":float(np.sqrt(np.mean(delta**2))),"pymatgen_peaks":int(len(idx)),"peak_coverage_7bin":hits})
    # P1: deterministic profile and gradient vs centered finite differences.
    q=torch.tensor([.13,-.17],dtype=torch.float64,device="cuda",requires_grad=True)
    eta=torch.tensor([.073,.12,.015,.03,1.0],dtype=torch.float64,device="cuda",requires_grad=True)
    target=expected_profile(forward,q.detach(),eta.detach())
    # Slightly displaced q makes a nonzero informative gradient.
    q_try=(q+torch.tensor([.01,-.01],device="cuda",dtype=torch.float64))
    loss=(expected_profile(forward,q_try,eta)-target).square().mean()
    grads=torch.autograd.grad(loss,(q,eta))
    fd=[]
    for i in range(2):
        d=torch.zeros_like(q); d[i]=1e-4
        plus=(expected_profile(forward,q_try.detach()+d,eta.detach())-target).square().mean()
        minus=(expected_profile(forward,q_try.detach()-d,eta.detach())-target).square().mean()
        fd.append(float(((plus-minus)/(2e-4)).cpu()))
    ag=grads[0].detach().cpu().numpy()
    fd=np.asarray(fd)
    fd_rel=float(np.max(np.abs(ag-fd)/np.maximum(1e-7,np.abs(ag)+np.abs(fd))))
    # Joint q / nuisance local information on expected profile; report singular values.
    x=torch.tensor([0.,0.,0.,.12,.015,.03,1.],dtype=torch.float64,device="cuda",requires_grad=True)
    def profile(z): return expected_profile(forward,z[:2],torch.cat((z[2:3],z[3:4],z[4:6],z[6:7])) )
    jac=torch.func.jacfwd(profile)(x).detach().cpu().numpy()
    sv=np.linalg.svd(jac,compute_uv=False)
    # Deployable profile fit: nuisance is estimated from the profile under
    # explicit bounds, never read from the target when constructing predictions.
    truth=np.array([.18,-.22,.037,.12,.004,.007,1.0],dtype=np.float64)
    truth_t=torch.as_tensor(truth,device="cuda",dtype=torch.float64)
    target_np=profile(truth_t).detach().cpu().numpy()
    def residual(z):
        with torch.no_grad():
            return profile(torch.as_tensor(z,device="cuda",dtype=torch.float64)).cpu().numpy()-target_np
    fit=least_squares(residual,np.array([.1,-.1,0.,.11,.003,.006,.95]),
        bounds=([-0.8,-0.8,-.06,.08,0.,0.,.7],[.8,.8,.06,.2,.02,.02,1.3]),
        max_nfev=100,ftol=1e-10,xtol=1e-10,gtol=1e-10)
    profile_fit={"success":bool(fit.success),"nfev":int(fit.nfev),"truth":truth.tolist(),
        "estimate":fit.x.tolist(),"rmse":float(np.sqrt(np.mean(fit.fun**2))),
        "q_error_max":float(np.max(np.abs(fit.x[:2]-truth[:2]))),
        "eta_error_max_scaled":float(np.max(np.abs((fit.x[2:]-truth[2:]) / np.array([.06,.12,.02,.02,.6]))))}
    # Deliberate old-objective mismatch: fixed clean forward is compared to
    # the deterministic expected observed profile at nonzero nuisance.
    qtrue=torch.as_tensor([.18,-.22],device="cuda",dtype=torch.float64)
    etrue=torch.as_tensor([.05,.12,.01,.015,1.0],device="cuda",dtype=torch.float64)
    observed_mu=expected_profile(forward,qtrue,etrue).detach()
    def clean_q(z):
        full=torch.cat((z,torch.zeros_like(z[:1]),torch.full_like(z[:1],-1.)))
        return forward.render(full,compatibility=False)
    qvar=qtrue.clone().requires_grad_(True)
    mismatch_loss=(clean_q(qvar)-observed_mu).square().mean()
    mismatch_grad=torch.autograd.grad(mismatch_loss,qvar)[0].detach().cpu().numpy()
    clean_fit=least_squares(lambda z:(clean_q(torch.as_tensor(z,device="cuda",dtype=torch.float64)).detach().cpu().numpy()-observed_mu.cpu().numpy()),
        np.array([.18,-.22]),bounds=([-0.8,-0.8],[.8,.8]),max_nfev=80,ftol=1e-10,xtol=1e-10,gtol=1e-10)
    expected_q=qtrue.clone().requires_grad_(True)
    expected_loss=(expected_profile(forward,expected_q,etrue)-observed_mu).square().mean()
    expected_grad=torch.autograd.grad(expected_loss,expected_q)[0].detach().cpu().numpy()
    mismatch={"q_true":qtrue.cpu().tolist(),"eta_true_diagnostic_only":etrue.cpu().tolist(),
      "clean_fixed_nuisance_gradient_at_q_true":mismatch_grad.tolist(),"expected_forward_gradient_at_q_true":expected_grad.tolist(),
      "clean_fixed_nuisance_best_q":clean_fit.x.tolist(),"clean_fit_q_displacement":(clean_fit.x-qtrue.cpu().numpy()).tolist(),
      "clean_fit_rmse":float(np.sqrt(np.mean(clean_fit.fun**2))),"expected_forward_rmse_at_truth":float(torch.sqrt(expected_loss).detach().cpu())}
    result={"cif_sha256":__import__('hashlib').sha256(cif.read_bytes()).hexdigest(),
      "formula":structure.composition.reduced_formula,"sites":len(structure),"space_group":sga[0],"space_group_number":sga[1],
      "a_angstrom":structure.lattice.a,"c_angstrom":structure.lattice.c,"wavelength_angstrom":cfg["grid"]["wavelength_angstrom"],
      "two_theta_range_deg":[cfg["grid"]["two_theta_min"],cfg["grid"]["two_theta_max"]],"step_deg":cfg["grid"]["step"],
      "renderer_probes":renderer_rows,"renderer_gate_passed":all(r["v9_rmse"]<2e-6 and r["peak_coverage_7bin"]>.95 for r in renderer_rows),
      "gradient_autograd_q":ag.tolist(),"gradient_finite_difference_q":fd.tolist(),"gradient_relative_error":fd_rel,
      "gradient_gate_passed":bool(np.isfinite(fd_rel) and fd_rel<.1 and np.linalg.norm(ag)>1e-10),
      "joint_q_eta_singular_values":sv.tolist(),"joint_q_eta_condition":float(sv[0]/sv[-1]),
      "joint_q_eta_rank":int(np.linalg.matrix_rank(jac,tol=sv[0]*1e-6)),
      "unknown_nuisance_profile_fit":profile_fit,
      "mismatched_clean_vs_measurement_aware":mismatch,
      "eta_definition":{"zero_shift_deg":"eta[0]","fwhm_deg":"eta[1]","background_endpoints_fraction_of_clean_peak":["eta[2]","eta[3]"],"relative_scale":"eta[4]"}}
    out.mkdir(parents=True,exist_ok=False)
    (out/"p0_p1_audit.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    return result

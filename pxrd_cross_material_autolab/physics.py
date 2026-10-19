"""CIF-specific kinematic powder forward and one shared bounded optimizer.

q is relative lattice displacement divided by 0.02 (dimensionless); eta units
are degrees, degrees, intensity multiplier, intensity offset, intensity slope.
Fractional coordinates/occupancies are fixed to the supplied candidate CIF.
"""
from __future__ import annotations
import time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from pymatgen.core import Structure, Lattice
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from pymatgen.analysis.diffraction.xrd import XRDCalculator, ATOMIC_SCATTERING_PARAMS

GATE_THRESHOLDS = {'peak_position_deg': 1e-5, 'relative_intensity': 2e-5,
 'jacobian_condition': 1e7, 'recovery_q_max': 0.06, 'recovery_rmse': 0.003,
 'gradient_relative': 0.01, 'min_peaks': 3, 'multistart_q_disagreement': 0.12}
ETA_NEUTRAL = np.array([0., .32, 1., .02, 0.])
ETA_BOUNDS = [(-.12,.12),(.22,.44),(.75,1.25),(0.,.08),(-.04,.04)]

class PowderModel:
 def __init__(self,cif_path,grid_size=1024):
  self.cif_path=str(cif_path); self.structure=Structure.from_file(cif_path)
  self.system=SpacegroupAnalyzer(self.structure,symprec=.01).get_crystal_system()
  if self.system not in ('cubic','tetragonal','hexagonal'):
   raise ValueError('Unsupported crystal system: '+self.system)
  self.ndim=1 if self.system=='cubic' else 2
  self.q0=np.array([self.structure.lattice.a] if self.ndim==1 else [self.structure.lattice.a,self.structure.lattice.c])
  self.q_bounds=[(-1.,1.)]*self.ndim; self.eta_bounds=ETA_BOUNDS.copy()
  self.grid=np.linspace(15.,85.,grid_size); self.wavelength=1.5406
  rmax=2*np.sin(np.deg2rad(88/2))/self.wavelength*1.025
  pts=self.structure.lattice.reciprocal_lattice_crystallographic.get_points_in_sphere([[0,0,0]],[0,0,0],rmax)
  hkl=np.array([np.rint(p[0]).astype(int) for p in pts if p[1]>0])
  if self.system=='cubic': keys=(hkl*hkl).sum(1)[:,None]
  elif self.system=='tetragonal': keys=np.stack([(hkl[:,:2]**2).sum(1),hkl[:,2]**2],1)
  else: keys=np.stack([hkl[:,0]**2+hkl[:,0]*hkl[:,1]+hkl[:,1]**2,hkl[:,2]**2],1)
  self.keys,self.group=np.unique(keys,axis=0,return_inverse=True)
  zs=[]; coeff=[]; coords=[]; occ=[]
  for site in self.structure:
   for sp,o in site.species.items():
    zs.append(sp.Z); coeff.append(ATOMIC_SCATTERING_PARAMS[sp.symbol]); coords.append(site.frac_coords); occ.append(o)
  atomic_phase=np.exp(2j*np.pi*(hkl@np.array(coords).T))*np.array(occ)
  unique_z=np.unique(zs); zs_array=np.array(zs)
  self.zs=unique_z
  self.coeff=np.array([coeff[zs.index(z)] for z in unique_z])
  self.phase=np.stack([atomic_phase[:,zs_array==z].sum(axis=1) for z in unique_z],axis=1)
  self.reference_max=None
  _,i=self.peaks(np.zeros(self.ndim)); self.reference_max=float(i.max())
 def lattice(self,q): return self.q0*(1+.02*np.asarray(q))
 def structure_at(self,q):
  p=self.lattice(q)
  lat=Lattice.cubic(p[0]) if self.system=='cubic' else (Lattice.tetragonal(*p) if self.system=='tetragonal' else Lattice.hexagonal(*p))
  return Structure(lat,[site.species for site in self.structure],self.structure.frac_coords)
 def peaks(self,q):
  p=self.lattice(q)
  if self.system=='cubic': g2=self.keys[:,0]/p[0]**2
  else: g2=self.keys[:,0]/p[0]**2*(4/3 if self.system=='hexagonal' else 1)+self.keys[:,1]/p[1]**2
  s2=g2[self.group]/4
  fs=self.zs[None,:]-41.78214*s2[:,None]*np.sum(self.coeff[None,:,:,0]*np.exp(-self.coeff[None,:,:,1]*s2[:,None,None]),axis=2)
  f=np.sum(fs*self.phase,axis=1)
  intensity=np.bincount(self.group,weights=np.abs(f)**2,minlength=len(g2))
  theta=np.arcsin(self.wavelength*np.sqrt(g2)/2)
  intensity*= (1+np.cos(2*theta)**2)/(np.sin(theta)**2*np.cos(theta))
  return np.rad2deg(2*theta),intensity
 def profile(self,q,eta=None):
  eta=ETA_NEUTRAL if eta is None else np.asarray(eta)
  pos,intensity=self.peaks(q); z,w,s,b,sl=eta
  y=np.exp(-4*np.log(2)*((self.grid[None,:]-pos[:,None]-z)/w)**2)
  base=(intensity[:,None]*y).sum(0)/self.reference_max
  return s*base+b+sl*(self.grid-self.grid.mean())/np.ptp(self.grid)
 def fit(self,observed,q_start,maxiter=100,maxfun=1000,eta_start=None):
  start=time.perf_counter(); observed=np.asarray(observed)
  x0=np.r_[np.clip(q_start,-1,1),ETA_NEUTRAL if eta_start is None else eta_start]
  def objective(x): return float(np.mean((self.profile(x[:self.ndim],x[self.ndim:])-observed)**2))
  result=minimize(objective,x0,method='L-BFGS-B',bounds=self.q_bounds+self.eta_bounds,
   options={'maxiter':maxiter,'maxfun':maxfun,'ftol':1e-12,'gtol':1e-7,'maxls':30})
  x=result.x; bounds=np.array(self.q_bounds+self.eta_bounds)
  return {'q':x[:self.ndim].tolist(),'eta':x[self.ndim:].tolist(),'rmse':float(np.sqrt(result.fun)),
   'nfev':int(result.nfev),'nit':int(result.nit),'success':bool(result.success),'message':str(result.message),
   'seconds':time.perf_counter()-start,'boundary_hit':bool(np.any(np.minimum(x-bounds[:,0],bounds[:,1]-x)<1e-5))}

def gate(model):
 """Development-only deterministic cases. Thresholds fixed before new held-out test."""
 checks={}; details={}; n=model.ndim
 distances=model.structure.distance_matrix+np.eye(len(model.structure))*100
 checks['site_geometry']=bool(model.structure.volume>0 and np.min(distances)>.5 and all(0<float(sum(site.species.values()))<=1.001 for site in model.structure))
 details['structure']={'formula':model.structure.composition.reduced_formula,'spacegroup':SpacegroupAnalyzer(model.structure,symprec=.01).get_space_group_number(),'minimum_site_distance_angstrom':float(np.min(distances)),'sites':len(model.structure),'volume_angstrom3':float(model.structure.volume)}
 checks['symmetric_positive_bounds']=all(np.all(model.lattice(np.full(n,v))>0) and np.all(np.isfinite(model.profile(np.full(n,v)))) for v in (-1.,0.,1.))
 checks['distinguishable_profiles']=not np.allclose(model.profile(np.full(n,-.35)),model.profile(np.full(n,.35)))
 checks['symmetry']=all(np.isclose(model.structure_at(np.full(n,v)).lattice.a,model.structure_at(np.full(n,v)).lattice.b) for v in (-1.,1.))
 try:
  parity=[]
  for scalar in (0.,-.35,.35):
   q=np.full(n,scalar); pos,intensity=model.peaks(q)
   keep=(pos>=15)&(pos<=85)&(intensity/intensity.max()>1e-5)
   pos=pos[keep]; intensity=intensity[keep]; order=np.argsort(pos); pos=pos[order]; intensity=intensity[order]
   # Merge accidental equal-d families independently of simulator grouping.
   merged=[]
   for p,i in zip(pos,intensity):
    if merged and abs(p-merged[-1][0])<1e-5: merged[-1][1]+=i
    else: merged.append([p,i])
   arr=np.array(merged); ref=XRDCalculator(wavelength=model.wavelength).get_pattern(model.structure_at(q),two_theta_range=(15,85))
   if len(arr)!=len(ref.x): raise ValueError(f'Peak count parity {len(arr)} != {len(ref.x)}')
   dp=float(np.max(np.abs(arr[:,0]-ref.x))); di=float(np.max(np.abs(arr[:,1]/arr[:,1].max()-ref.y/100)))
   parity.append({'q':q.tolist(),'position_deg':dp,'intensity':di,'peaks':len(arr)})
  checks['independent_pymatgen_parity']=all(x['position_deg']<GATE_THRESHOLDS['peak_position_deg'] and x['intensity']<GATE_THRESHOLDS['relative_intensity'] for x in parity)
  checks['positive_nonempty_peaks']=min(x['peaks'] for x in parity)>=GATE_THRESHOLDS['min_peaks']; details['parity']=parity
  conditions=[]; gradients=[]
  for scalar in (-.35,0.,.35):
   x=np.r_[np.full(n,scalar),ETA_NEUTRAL]
   def fn(x): return model.profile(x[:n],x[n:])
   def jac(h): return np.stack([(fn(x+np.eye(len(x))[i]*h)-fn(x-np.eye(len(x))[i]*h))/(2*h) for i in range(len(x))],1)
   j=jac(1e-4); j2=jac(5e-5); conditions.append(float(np.linalg.cond(j))); gradients.append(float(np.linalg.norm(j-j2)/np.linalg.norm(j2)))
  checks['jacobian_condition']=max(conditions)<GATE_THRESHOLDS['jacobian_condition']; checks['numerical_gradient']=max(gradients)<GATE_THRESHOLDS['gradient_relative']
  details['jacobian_conditions']=conditions; details['gradient_relative']=gradients
  recovery=[]
  for scalar in (-.18,.18):
   q=np.linspace(scalar,scalar*.6,n); eta=np.array([.035,.35,1.03,.025,.01]); y=model.profile(q,eta)
   fits=[model.fit(y,np.full(n,s),maxiter=180,maxfun=1800) for s in (0.,-.35,.35)]
   best=min(fits,key=lambda x:x['rmse']); err=float(np.max(np.abs(np.array(best['q'])-q)))
   disagreement=float(np.max(np.ptp(np.array([f['q'] for f in fits]),axis=0)))
   recovery.append({'q_true':q.tolist(),'q_error':err,'disagreement':disagreement,'fits':fits})
  checks['nonoracle_noiseless_recovery']=all(r['q_error']<GATE_THRESHOLDS['recovery_q_max'] and min(f['rmse'] for f in r['fits'])<GATE_THRESHOLDS['recovery_rmse'] for r in recovery)
  checks['multistart_stability']=all(r['disagreement']<GATE_THRESHOLDS['multistart_q_disagreement'] for r in recovery)
  details['recovery']=recovery
 except Exception as exc:
  checks['exception']=False; details['exception']=repr(exc)
 return {'status':'PASS' if checks and all(checks.values()) else 'FAIL','halt_simulator':not checks.get('independent_pymatgen_parity',False),'checks':checks,'details':details,'frozen_thresholds':dict(GATE_THRESHOLDS),'reconstruction_B':'SKIPPED: NumPy forward has no autograd implementation'}

def validate_material(material,config=None):
 return gate(PowderModel(material['cif_path'],grid_size=(config or {}).get('grid_size',1024)))


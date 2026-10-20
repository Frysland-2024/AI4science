"""Frozen measured-profile case series; never uses reference cells for inference."""
from pathlib import Path
import csv, hashlib, json, re, sys, time, zipfile
import numpy as np
from scipy.optimize import minimize
from scipy.signal import find_peaks
from pymatgen.analysis.diffraction.xrd import XRDCalculator
from pxrd_cross_material_autolab.physics import PowderModel
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'pxrd_heuristic_rruff_validation'
ARCH=Path(r'E:\AI4science\RRUFF')
AUDIT=Path(r'E:\AI4science\xrd_inversion\audits\rruff_domain_adaptation\sample_manifest.csv')
REPORT=BASE/'reports'
def sha(b): return hashlib.sha256(b).hexdigest()
def config(): return json.loads((BASE/'e2_preregistration.json').read_text())
def dump(path,x): path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(x,indent=2,allow_nan=False),encoding='utf-8')
def rows(): return {r['rruff_sample_id']:r for r in csv.DictReader(AUDIT.open(encoding='utf-8-sig'))}
def read_member(archive,member):
 with zipfile.ZipFile(ARCH/archive) as z:return z.read(member)
def audit():
 c=config(); rr=rows(); records=[]
 for sid in c['ids']:
  r=rr[sid]; raw=read_member('XY_RAW.zip',r['raw_selected_member']); meta=read_member('Refinement_Output_Data.zip',r['refinement_output_member']); text=meta.decode(errors='replace')
  waves={int(k):float(v) for k,v in re.findall(r'Wavelength #([123])\s*=\s*([0-9.]+)',text)}
  assert len(waves)==3 and r['raw_profile_kind']=='experimental_powder_candidate' and r['raw_metadata_mixture_or_contamination_caveat']=='False'
  assert r['mineral_name']=='Rutile' and r['measured_chemistry'] in ['TiO_2_','Ti_1.00_O_2_']
  assert raw.startswith(b'##NAMES=Rutile') and sid.split('-')[0] in text
  records.append({'sample_id':sid,'raw_member':r['raw_selected_member'],'raw_sha256':sha(raw),'refinement_member':r['refinement_output_member'],'refinement_sha256':sha(meta),'wavelengths_A':{str(k):v for k,v in waves.items()},'wave_rows':sorted(set(re.findall(r'^\s*[0-9.]+\s+[0-9.]+\s+-?\d+\s+-?\d+\s+-?\d+\s+([123])\s+',text,re.M))),'same_specimen_cif_proven':False,'raw_kind':r['raw_profile_kind'],'formula':r['measured_chemistry']})
 out={'config_sha256':sha((BASE/'e2_preregistration.json').read_bytes()),'template_sha256':sha((ROOT/c['template']).read_bytes()),'audit_csv_sha256':sha(AUDIT.read_bytes()),'records':records,'source_sha256':sha(Path(__file__).read_bytes()),'archive_sha256':{a:sha((ARCH/a).read_bytes()) for a in ['XY_RAW.zip','Refinement_Output_Data.zip']}}
 dump(REPORT/'e2_manifest.json',out);return out
class RealModel(PowderModel):
 def __init__(self,c,waves):
  super().__init__(ROOT/c['template'],grid_size=c['axis'][2]);self.grid=np.linspace(*c['axis']); self.waves=waves;self.eta_bounds=c['eta_bounds'];self.wavelength=waves[0]
 def profile(self,q,eta=None):
  eta=np.array([0,.15,1,.02,0] if eta is None else eta);z,w,s,b,sl=eta
  yy=0
  for wave,ratio in zip(self.waves,[2/3,1/3]):
   self.wavelength=wave;pos,i=self.peaks(q);yy=yy+ratio*(i[:,None]*np.exp(-4*np.log(2)*((self.grid[None,:]-pos[:,None]-z)/w)**2)).sum(0)/self.reference_max
  self.wavelength=self.waves[0]
  return s*yy+b+sl*(self.grid-self.grid.mean())/np.ptp(self.grid)
 def fit_real(self,y,start,c):
  t=time.perf_counter(); n=self.ndim; bounds=self.q_bounds+self.eta_bounds
  out=minimize(lambda x:float(np.mean((self.profile(x[:n],x[n:])-y)**2)),np.r_[start,c['eta_start']],bounds=bounds,method='L-BFGS-B',options=c['solver'])
  x=out.x; bb=np.array(bounds)
  return {'q':x[:n].tolist(),'eta':x[n:].tolist(),'cell_ac_A':self.lattice(x[:n]).tolist(),'rmse':float(np.sqrt(out.fun)),'success':bool(out.success),'message':str(out.message),'nfev':int(out.nfev),'nit':int(out.nit),'boundary':bool(np.any(np.minimum(x-bb[:,0],bb[:,1]-x)<1e-5)),'seconds':time.perf_counter()-t}
def run():
 if (REPORT/'e2_results.json').exists():return verify()
 t=time.perf_counter();c=config(); manifest=audit();rr=rows();result=[]
 for rec in manifest['records']:
  sid=rec['sample_id']; r=rr[sid]; raw=read_member('XY_RAW.zip',r['raw_selected_member']).decode(errors='replace')
  xy=np.array([[float(v) for v in line.split(',')] for line in raw.splitlines() if re.match(r'^\s*[-+]?\d',line) and ',' in line]); assert np.all(np.diff(xy[:,0])>0)
  waves=[rec['wavelengths_A'][str(k)] for k in [2,3]];m=RealModel(c,waves);assert xy[0,0]<=15 and xy[-1,0]>=85
  y=np.interp(m.grid,xy[:,0],xy[:,1]);y/=y.max()
  fits=[m.fit_real(y,q,c) for q in c['starts']];p3=min(fits[:3],key=lambda f:f['rmse']);best=min(fits,key=lambda f:f['rmse'])
  ht=time.perf_counter(); grid=[np.array([a,b]) for a in np.linspace(-.8,.8,9) for b in np.linspace(-.8,.8,9)];hq=min(grid,key=lambda q:np.mean((m.profile(q,c['eta_start'])-y)**2));hseconds=time.perf_counter()-ht;hfit=m.fit_real(y,hq,c)
  cellspan=float(np.max(np.ptp(np.array([f['cell_ac_A'] for f in fits]),axis=0)))
  pos,ii=m.peaks(best['q']);keep=(pos>=15)&(pos<=85)&(ii>=.1*ii.max()); pred=pos[keep]+best['eta'][0]
  oi,_=find_peaks(y,prominence=.08,distance=max(1,int(.2/(m.grid[1]-m.grid[0])))); obs=m.grid[oi]
  pd=np.min(abs(pred[:,None]-obs[None,:]),axis=1) if len(obs) else np.full(len(pred),999.)
  od=np.min(abs(obs[:,None]-pred[None,:]),axis=1) if len(pred) else np.full(len(obs),999.)
  x=np.r_[best['q'],best['eta']]; h=1e-4; jac=np.stack([(m.profile((x+np.eye(len(x))[j]*h)[:2],(x+np.eye(len(x))[j]*h)[2:])-m.profile((x-np.eye(len(x))[j]*h)[:2],(x-np.eye(len(x))[j]*h)[2:]))/(2*h) for j in range(len(x))],axis=1);condition=float(np.linalg.cond(jac))
  m.wavelength=waves[0];pp,pi=m.peaks([0,0]);pat=XRDCalculator(wavelength=waves[0]).get_pattern(m.structure_at([0,0]),two_theta_range=(15,85));valid=(pp>=15)&(pp<=85)&(pi>pi.max()*1e-5);parity=float(np.max(np.min(abs(pp[valid,None]-pat.x[None,:]),axis=1)))
  g=c['gates'];checks={'independent_bragg_parity':parity<g['parity_deg_max'],'strong_peak_count':len(pred)>=g['strong_peak_min'],'predicted_strong_coverage':float(np.mean(pd<=g['peak_tolerance_deg']))>=g['predicted_strong_coverage_min'],'observed_strong_coverage':len(obs)>0 and float(np.mean(od<=g['peak_tolerance_deg']))>=g['observed_strong_coverage_min'],'residual':best['rmse']<=g['profile_rmse_max'],'multistart_stability':cellspan<=g['multistart_cell_span_A_max'],'jacobian':condition<g['jacobian_condition_max'],'all_converged':all(f['success'] for f in fits),'no_bounds':not any(f['boundary'] for f in fits)}
  methods={'P0':dict(fits[0]),'P3':dict(p3),'H1':dict(hfit)};methods['P3']['seconds']=sum(f['seconds'] for f in fits[:3]);methods['P3']['nfev_total']=sum(f['nfev'] for f in fits[:3]);methods['H1']['seconds']+=hseconds;methods['H1']['extraction_seconds']=hseconds
  # Reference estimates are consumed strictly after all fitting and gate computation.
  reference=np.array([float(r['a_angstrom']),float(r['c_angstrom'])])
  for f in methods.values():f['reference_agreement_ac_A']=(np.array(f['cell_ac_A'])-reference).tolist()
  result.append({'sample_id':sid,'status':'PASS' if all(checks.values()) else 'PHYSICS_NOT_READY','checks':checks,'methods':methods,'five_start_fits':fits,'cell_span_A':cellspan,'jacobian_condition':condition,'independent_peak_parity_deg':parity,'predicted_strong_peaks':len(pred),'observed_strong_peaks':len(obs),'predicted_peak_coverage':float(np.mean(pd<=.15)),'observed_peak_coverage':float(np.mean(od<=.15)) if len(obs) else 0,'nearest_predicted_peak_residual_deg':pd.tolist(),'reference_ac_A':reference.tolist(),'axis_raw':[float(xy[0,0]),float(xy[-1,0]),len(xy)],'NN_status':'NOT_RUN','NN_reason':'No verified checkpoint for real doublet/nuisance protocol; physics gate decision precedes any neural inference.'})
  print(sid,result[-1]['status'],checks,flush=True)
 out={'experiment':'E2','status':'PHYSICS_NOT_READY' if not all(r['status']=='PASS' for r in result) else 'PHYSICS_READY_NN_NOT_RUN','manifest':manifest,'records':result,'seconds':time.perf_counter()-t,'NN_status':'NOT_RUN','interpretation':'Descriptive case series; same-ID reference agreement, not accuracy; no real labels used for training or initializer selection.'};dump(REPORT/'e2_results.json',out);report();return out

def verify():
 out=json.loads((REPORT/'e2_results.json').read_text());assert out['manifest']==audit()
 for r in out['records']:
  assert (r['status']=='PASS')==all(r['checks'].values())
  assert r['methods']['P3']['nfev_total']==sum(f['nfev'] for f in r['five_start_fits'][:3])
  assert np.isclose(r['cell_span_A'],np.max(np.ptp([f['cell_ac_A'] for f in r['five_start_fits']],axis=0)))
 print('E2 verification PASS');return out

def report():
 out=json.loads((REPORT/'e2_results.json').read_text())
 lines=['# E2 measured RRUFF case series','',out['status']+'; neural NOT_RUN.','', '| ID | Gate | RMSE | Cell span A | Failed gates |','|---|---|---|---|---|']
 for r in out['records']:lines.append('| '+r['sample_id']+' | '+r['status']+' | '+str(min(f['rmse'] for f in r['five_start_fits']))+' | '+str(r['cell_span_A'])+' | '+', '.join(k for k,v in r['checks'].items() if not v)+' |')
 lines+=['','All fits, costs, parity, peak coverage and post-fit reference agreement are in e2_results.json. P3 includes all three starts and H1 includes coarse extraction. Same-ID refined references are agreement estimates, not absolute accuracy. Independent COD template is not proven same specimen. Fixed doublet 2:1 ratio is a modeling assumption. Real profiles were not used for training or threshold selection. No population generalization or neural benefit is established.','', 'NN NOT_RUN: no verified checkpoint compatible with this real doublet/nuisance protocol. A failed physics gate stops the neural arm.',str(out['seconds'])+' seconds total. Raw spectra and ZIP members remain outside Git.']
 (REPORT/'RRUFF_REAL_RESULTS.md').write_text(chr(10).join(lines),encoding='utf-8')
if __name__=='__main__':
 action=sys.argv[1] if len(sys.argv)>1 else 'run';globals()[action]()

"""Exploratory post-primary mismatch stress. Primary frozen files are read only."""
from __future__ import annotations
import argparse, hashlib, json, time, traceback
from pathlib import Path
import numpy as np
from pymatgen.analysis.diffraction.xrd import XRDCalculator
from pxrd_cross_material_autolab.physics import PowderModel
from pxrd_cross_material_autolab.experiment import summarize
from pxrd_cross_material_autolab.manager import atomic, sha, source_hashes
HERE=Path(__file__).parent

def draw_parameters(material_id, config, ndim):
 offset=int(hashlib.sha256(material_id.encode()).hexdigest()[:8],16); n=config['parents_per_material']
 q=np.random.default_rng(config['parent_seed']+offset).uniform(-.8,.8,(n,ndim))
 rng=np.random.default_rng(config['nuisance_seed']+offset)
 eta=np.column_stack([rng.uniform(-.10,.10,n),rng.uniform(.24,.42,n),rng.uniform(.8,1.2,n),rng.uniform(.02,.06,n),rng.uniform(-.015,.015,n)])
 return q,eta,config['noise_seed']+offset

def render(model,q,eta,lorentz_fraction=.3,quadratic_background=.03):
 pattern=XRDCalculator(wavelength=model.wavelength).get_pattern(model.structure_at(q),scaled=False,two_theta_range=(10,95))
 z,w,s,b,sl=eta; delta=(model.grid[None,:]-pattern.x[:,None]-z)/w
 peaks=(1-lorentz_fraction)*np.exp(-4*np.log(2)*delta**2)+lorentz_fraction/(1+4*delta**2)
 xnorm=(model.grid-model.grid.mean())/np.ptp(model.grid)
 return s*(pattern.y[:,None]*peaks).sum(0)/model.reference_max+b+sl*xnorm+quadratic_background*xnorm**2

def noise(mu,seed,index):
 rng=np.random.default_rng(np.random.SeedSequence([seed,index]))
 return (rng.poisson(np.maximum(mu,0)*15000)/15000+rng.normal(0,.002,len(mu))).astype(np.float32)

def resolve_primary(primary,config):
 if (primary/'manager.lock').exists(): raise RuntimeError('Primary manager lock exists; primary must finish first')
 manifest=json.loads((primary/'manifest.json').read_text(encoding='utf-8-sig'))
 if manifest['identity']['source_sha256']!=source_hashes(): raise RuntimeError('Primary source hashes changed')
 pc=json.loads((primary/'config.json').read_text(encoding='utf-8-sig')); sources={m['id']:m for m in pc['materials']}; resolved={}; hashes={}
 for mid in config['materials']:
  d=primary/'materials'/mid; status=json.loads((d/'status.json').read_text())
  if (status.get('stage')!='experiment' or status.get('status')!='PASS'): raise RuntimeError('Primary experiment incomplete: '+mid)
  attempts=[p for p in d.glob('attempt_*') if (p/'result.json').exists()]
  if len(attempts)!=1: raise RuntimeError('Ambiguous primary attempt: '+mid)
  a=attempts[0]; result=json.loads((a/'result.json').read_text()); marker=json.loads((a/'test_opened.json').read_text())
  if sha(a/'training_selection.json')!=marker['selection_sha256']: raise RuntimeError('Selection mismatch: '+mid)
  if sha(a/'private'/'normalization.npz')!=result['data_hashes']['normalization.npz']: raise RuntimeError('Normalization mismatch: '+mid)
  selection=json.loads((a/'training_selection.json').read_text()); private=a/'private'
  for selected in selection['models']:
   p=private/f"best_{selected['seed']}.pt"
   if sha(p)!=selected['checkpoint_sha256']: raise RuntimeError('Checkpoint mismatch: '+str(p))
   hashes[str(p)]=sha(p)
  for p in [private/'normalization.npz',a/'training_selection.json',Path(sources[mid]['cif_path'])]: hashes[str(p)]=sha(p)
  if sha(Path(sources[mid]['cif_path']))!=sources[mid]['cif_sha256']: raise RuntimeError('CIF mismatch: '+mid)
  resolved[mid]=(sources[mid],a,selection)
 for p in [primary/'manifest.json',primary/'config.json',HERE/'config.json',HERE/'PREREGISTRATION.md',HERE/'run.py'] : hashes[str(p)]=sha(p)
 return resolved,hashes

def run(primary,output):
 import torch
 from torch import nn
 config=json.loads((HERE/'config.json').read_text(encoding='utf-8-sig')); resolved,hashes=resolve_primary(primary,config)
 output.mkdir(parents=True,exist_ok=False)
 created=time.time()
 atomic(output/'manifest.json',dict(status='FROZEN_BEFORE_STRESS',registered_after_primary_opened=True,created=created,hashes=hashes,primary_source_sha256=source_hashes(),config=config))
 torch.set_num_threads(1); ledger=json.loads((primary/'budget.json').read_text()); statuses={}; all_summary=[]
 def budget():
  if time.time()-ledger['pilot_started']>=config['wall_budget_seconds']: raise RuntimeError('PARTIAL: original global eight-hour wall budget exhausted')
  total_bytes=sum(p.stat().st_size for root in (primary,output) for p in root.rglob('*') if p.is_file())
  if total_bytes>=10000000000: raise RuntimeError('PARTIAL: combined primary plus stress disk budget exhausted')
 def verify_hashes():
  for p,digest in hashes.items():
   if sha(Path(p))!=digest: raise RuntimeError('Frozen stress dependency changed: '+p)
 try:
  for mid in config['materials']:
   budget(); verify_hashes(); material,a,selection=resolved[mid]; dest=output/mid; dest.mkdir()
   try:
    model=PowderModel(material['cif_path']); norm=np.load(a/'private'/'normalization.npz'); mean,std=norm['mean'],norm['std']; nets=[]
    for selected in selection['models']:
     net=nn.Sequential(nn.Linear(len(model.grid),256),nn.SiLU(),nn.Linear(256,128),nn.SiLU(),nn.Linear(128,model.ndim),nn.Tanh())
     net.load_state_dict(torch.load(a/'private'/f"best_{selected['seed']}.pt",map_location='cpu',weights_only=True)); net.eval(); nets.append((selected['seed'],net))
    q,eta,noise_seed=draw_parameters(mid,config,model.ndim); rows=[]
    atomic(dest/'opened.json',dict(time=time.time(),q_sha256=hashlib.sha256(q.tobytes()).hexdigest(),noise_seed=noise_seed))
    for i in range(len(q)):
     budget(); y=noise(render(model,q[i],eta[i],config['lorentz_fraction'],config['quadratic_background']),noise_seed,i)
     def record(method,seed,fits,elapsed,inference=0.):
      best=min(fits,key=lambda f:f['rmse'])
      row=dict(material=mid,method=method,seed=seed,parent=i,q_true_posthoc=q[i].tolist(),q_fit=best['q'],eta_fit=best['eta'],
       lattice_true_angstrom=model.lattice(q[i]).tolist(),lattice_fit_angstrom=model.lattice(best['q']).tolist(),
       lattice_abs_error_angstrom=np.abs(model.lattice(best['q'])-model.lattice(q[i])).tolist(),rmse=best['rmse'],success=best['success'],
       boundary_hit=best['boundary_hit'],seconds=elapsed+inference,inference_seconds=inference,nfev=sum(f['nfev'] for f in fits),attempts=fits,
       multistart_disagreement=float(np.max(np.ptp(np.array([f['q'] for f in fits]),axis=0))))
      rows.append(row)
      with (dest/'per_sample.jsonl').open('a',encoding='utf-8') as handle: handle.write(json.dumps(row,allow_nan=False)+'\n')
     for method,starts in [('P0',[0.]),('P3',[0.,-.5,.5])]:
      started=time.perf_counter(); fits=[model.fit(y,np.full(model.ndim,s),maxiter=config['maxiter'],maxfun=config['maxfun']) for s in starts]
      record(method,0,fits,time.perf_counter()-started)
     for seed,net in nets:
      started=time.perf_counter()
      with torch.no_grad(): guess=net(torch.tensor((y-mean)/std)[None]).numpy()[0]
      inference=time.perf_counter()-started; started=time.perf_counter(); fit=model.fit(y,guess,maxiter=config['maxiter'],maxfun=config['maxfun'])
      record('N+A',seed,[fit],time.perf_counter()-started,inference)
     with (dest/'events.jsonl').open('a',encoding='utf-8') as handle: handle.write(json.dumps(dict(event='sample_complete',completed=i+1,total=len(q),time=time.time()))+'\n')
    metrics=summarize(rows); atomic(dest/'metrics.json',metrics); all_summary.extend(metrics); statuses[mid]='PASS'
   except Exception as exc:
    statuses[mid]='FAIL'; atomic(dest/'failure.json',dict(error=repr(exc),traceback=traceback.format_exc(),time=time.time()))
    if 'PARTIAL:' in str(exc): raise
   atomic(output/'status.json',dict(status='NOT_RUN',stage='running',materials=statuses))
 except Exception as exc:
  atomic(output/'failure.json',dict(error=repr(exc),traceback=traceback.format_exc(),time=time.time()))
 finally:
  for mid in config['materials']: statuses.setdefault(mid,'NOT_RUN')
  state='PASS' if all(s=='PASS' for s in statuses.values()) else 'PARTIAL'
  atomic(output/'status.json',dict(status=state,materials=statuses,finished=time.time(),elapsed_seconds=time.time()-created)); atomic(output/'COMPARISON.json',all_summary)
  import csv
  if all_summary:
   with (output/'COMPARISON.csv').open('w',newline='',encoding='utf-8') as handle:
    writer=csv.DictWriter(handle,fieldnames=list(all_summary[0]));writer.writeheader();writer.writerows(all_summary)
  text='# 探索性独立渲染压力测试\n\n状态：'+state+'。在主测试打开后另行登记；不替代或挽救主要结果。\n\n独立 pymatgen 峰表、伪 Voigt 峰形与未建模二次背景；每材料 16 个新父样本，无重训。\n\n'
  for mid in config['materials']:
   text+=f"- {mid}: {statuses[mid]}\n"
   for r in all_summary:
    if r['material']==mid: text+=f"  {r['method']} seed={r['seed']}: q MAE={r['q_mae']:.6g}, cell MAE (Å)={r['lattice_mae_angstrom']}, mean seconds={r['mean_seconds']:.6g}, convergence={r['convergence_rate']:.3f}\n"
  (output/'OVERVIEW.md').write_text(text,encoding='utf-8')
 return state

def verify(output):
 manifest=json.loads((output/'manifest.json').read_text())
 for path,digest in manifest['hashes'].items():
  if sha(Path(path))!=digest: raise RuntimeError('Hash mismatch: '+path)
 for mid in manifest['config']['materials']:
  dest=output/mid
  if (dest/'metrics.json').exists():
   rows=[json.loads(line) for line in (dest/'per_sample.jsonl').read_text().splitlines()]
   if summarize(rows)!=json.loads((dest/'metrics.json').read_text()): raise RuntimeError('Metric recomputation mismatch: '+mid)
 return True

if __name__=='__main__':
 parser=argparse.ArgumentParser(); parser.add_argument('--primary',type=Path); parser.add_argument('--verify',action='store_true'); parser.add_argument('--output',type=Path,required=True); args=parser.parse_args()
 if args.verify: print('VERIFIED' if verify(args.output) else 'FAIL')
 else:
  if args.primary is None: parser.error('--primary required for run')
  raise SystemExit(0 if run(args.primary,args.output)=='PASS' else 2)

"""Frozen posthoc heuristic comparison; original private artifacts are read only."""
from __future__ import annotations
import csv,hashlib,itertools,json,time,traceback
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.signal import find_peaks
from pxrd_cross_material_autolab.physics import PowderModel,ETA_NEUTRAL
from pxrd_cross_material_autolab.experiment import splits,summarize
ROOT=Path(__file__).resolve().parent
OLD=Path('E:/AI4science/_local/worktrees/pxrd_cross_material_autolab_20261019')
OUT=ROOT/'reports'/'e1'
IDS=['batio3','mgo','ceo2','rutile','zno','silicon','grossular']
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True); tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8');tmp.replace(p)
def event(kind,**data):
 OUT.mkdir(parents=True,exist_ok=True)
 with (OUT/'events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(dict(time=time.time(),kind=kind,**data))+'\n')
def attempt(mid):
 p=OLD/'pxrd_cross_material_autolab/runs/pilot_20261019/materials'/mid
 return OLD/read(p/'status.json')['attempt']
def audit():
 cfg=read(OLD/'pxrd_cross_material_autolab/runs/pilot_20261019/config.json');manifest=read(OLD/'pxrd_cross_material_autolab/runs/pilot_20261019/manifest.json')
 assert sha(OLD/'pxrd_cross_material_autolab/runs/pilot_20261019/config.json')==manifest['identity']['config_sha256']
 for name in ('physics.py','experiment.py'):
  p=OLD/'pxrd_cross_material_autolab'/name
  expected=next(v for k,v in manifest['identity']['source_sha256'].items() if k.endswith('\\'+name))
  assert sha(p)==expected and sha(p)==sha(ROOT.parent/'pxrd_cross_material_autolab'/name)
 records=[]
 for mid in IDS:
  a=attempt(mid); result=read(a/'result.json');sel=read(a/'training_selection.json');arts=read(a/'artifacts.json')
  assert sha(a/'result.json')==arts['result.json'] and sha(a/'training_selection.json')==arts['training_selection.json']
  hashes={}
  for name,expected in result['data_hashes'].items():
   p=a/'private'/name;assert sha(p)==expected;hashes[name]=sha(p)
  for model in sel['models']:
   p=a/'private'/f"best_{model['seed']}.pt";assert sha(p)==model['checkpoint_sha256'];hashes[p.name]=sha(p)
  mat=next(m for m in cfg['materials'] if m['id']==mid);assert sha(ROOT.parent/mat['cif_path'])==mat['cif_sha256']
  norm=np.load(a/'private/normalization.npz');train=np.load(a/'private/train_val.npz')['train']
  assert np.array_equal(norm['mean'],train.mean(0)) and np.array_equal(norm['std'],np.maximum(train.std(0),.02))
  assert norm['mean'].shape==(1024,) and np.load(a/'private/test.npz')['observed'].shape==(77,1024)
  assert read(a/'split_manifest.json')['indices']=={k:v.tolist() for k,v in splits(cfg).items()}
  records.append(dict(material=mid,hashes=hashes,cif_sha256=mat['cif_sha256'],training_seconds=sel['training_seconds'],normalization='exact train-only recomputed',grid='linspace(15,85,1024)',q='(cell/reference-1)/0.02'))
 result=dict(status='PASS',materials=records,source_sha256={n:sha(ROOT.parent/'pxrd_cross_material_autolab'/n) for n in ('physics.py','experiment.py')},config_sha256=sha(OLD/'pxrd_cross_material_autolab/runs/pilot_20261019/config.json'))
 write(OUT/'audit.json',result);return result

def h1(model,observed):
 """Only measured strongest peaks and candidate Bragg positions; no labels."""
 idx,_=find_peaks(observed,prominence=max(float(np.ptp(observed))*.025,.001),distance=3)
 if not len(idx):return np.zeros(model.ndim)
 idx=idx[np.argsort(observed[idx])[-12:]]; obs=model.grid[idx]; weights=np.maximum(observed[idx]-np.percentile(observed,10),1e-8);weights/=weights.sum()
 best=(float('inf'),None)
 for values in itertools.product(np.linspace(-.8,.8,9),repeat=model.ndim):
  pos,intensity=model.peaks(values);valid=(pos>=15)&(pos<=85);pos=pos[valid];intensity=intensity[valid]
  strong=pos[np.argsort(intensity)[-12:]]
  score=float(np.sum(weights*np.min((obs[:,None]-strong[None,:])**2,axis=1)))
  if score<best[0]:best=(score,np.array(values))
 return best[1]

def wall_fit(model,obs,starts,deadline):
 bounds=np.array(model.q_bounds+model.eta_bounds);fits=[]
 for start in starts:
  if time.perf_counter()>=deadline:break
  x0=np.r_[start,ETA_NEUTRAL];best=[float('inf'),x0.copy()];nfev=0;nit=0;success=False;message='wall budget'
  def objective(x):
   nonlocal nfev
   if time.perf_counter()>=deadline:raise TimeoutError('fixed wall deadline')
   value=float(np.mean((model.profile(x[:model.ndim],x[model.ndim:])-obs)**2));nfev+=1
   if value<best[0]:best[:]=[value,x.copy()]
   return value
  def callback(x):
   nonlocal nit
   nit+=1
  try:
   r=minimize(objective,x0,method='L-BFGS-B',bounds=bounds,callback=callback,options=dict(maxiter=100,maxfun=600,ftol=1e-12,gtol=1e-7,maxls=30));nit=int(r.nit);success=bool(r.success);message=str(r.message)
  except TimeoutError:pass
  if np.isfinite(best[0]):
   x=best[1];fits.append(dict(q=x[:model.ndim].tolist(),eta=x[model.ndim:].tolist(),rmse=float(np.sqrt(best[0])),nfev=nfev,nit=nit,success=success,message=message,boundary_hit=bool(np.any(np.minimum(x-bounds[:,0],bounds[:,1]-x)<1e-5))))
 return fits

def run():
 import torch
 from torch import nn
 torch.set_num_threads(1)
 audit_result=audit();prereg=ROOT/'E1_PREREGISTRATION.md';identity=dict(prereg_sha256=sha(prereg),source_sha256=sha(__file__),audit_sha256=sha(OUT/'audit.json'))
 if (OUT/'freeze.json').exists():assert read(OUT/'freeze.json')['identity']==identity
 else:write(OUT/'freeze.json',dict(time=time.time(),identity=identity))
 cfg=read(OLD/'pxrd_cross_material_autolab/runs/pilot_20261019/config.json');begun=time.time();event('run_started')
 for mid in IDS:
  dest=OUT/f'{mid}.jsonl'
  if (OUT/f'{mid}.complete.json').exists():continue
  if dest.exists():raise RuntimeError('Interrupted material cannot automatically reopen test: '+mid)
  a=attempt(mid);mat=next(m for m in cfg['materials'] if m['id']==mid);model=PowderModel(ROOT.parent/mat['cif_path']);d=dict(cfg['data']);offset=int(hashlib.sha256(mid.encode()).hexdigest()[:8],16)
  q=np.random.default_rng(d['parent_seed']+offset).uniform(-.8,.8,(d['parents'],model.ndim));assert hashlib.sha256(q.tobytes()).hexdigest()==read(a/'split_manifest.json')['q_parent_sha256']
  test=np.load(a/'private/test.npz')['observed'];norm=np.load(a/'private/normalization.npz');nets={}
  for seed in cfg['training']['seeds']:
   net=nn.Sequential(nn.Linear(1024,256),nn.SiLU(),nn.Linear(256,128),nn.SiLU(),nn.Linear(128,model.ndim),nn.Tanh());net.load_state_dict(torch.load(a/'private'/f'best_{seed}.pt',map_location='cpu',weights_only=True));net.eval();nets[seed]=net
  methods=[('P0',0),('P3',0),('H1',0)]+[('N+A',s) for s in nets];rows=[];event('material_opened',material=mid)
  # Each method sees identical paired profile; truth is used only after fitting.
  for local,parent in enumerate(splits(cfg)['test']):
   obs=test[local]
   for budget in ('equal_eval','equal_wall'):
    for rep in range(3 if local<12 and budget=='equal_eval' else 1):
     order=(local+rep)%len(methods);ordered=methods[order:]+methods[:order]
     for method,seed in ordered:
      if time.time()-begun>9500:raise RuntimeError('bounded E1 wall exhausted')
      start=time.perf_counter();deadline=start+.05
      if method=='H1':starts=[h1(model,obs)]
      elif method=='N+A':
       with torch.no_grad():guess=nets[seed](torch.tensor((obs-norm['mean'])/norm['std'])[None]).numpy()[0]
       starts=[guess]
      else:starts=[np.full(model.ndim,s) for s in ([0,-.5,.5] if method=='P3' else [0])]
      extraction=time.perf_counter()-start
      fits=wall_fit(model,obs,starts,deadline) if budget=='equal_wall' else [model.fit(obs,s,maxiter=100,maxfun=600//len(starts)) for s in starts]
      elapsed=time.perf_counter()-start
      if not fits:
       # Initializer exhausted deadline: record actual failure, finite neutral fallback evaluation charged.
       fit=model.fit(obs,np.zeros(model.ndim),maxiter=0,maxfun=1);fit['success']=False;fit['message']='initializer exhausted wall deadline; neutral fallback';fits=[fit];elapsed=time.perf_counter()-start
      best=min(fits,key=lambda f:f['rmse']);truth=q[parent]
      row=dict(material=mid,method=method,seed=seed,parent=int(parent),budget=budget,repeat=rep,q_true_posthoc=truth.tolist(),q_fit=best['q'],eta_fit=best['eta'],lattice_abs_error_angstrom=np.abs(model.lattice(best['q'])-model.lattice(truth)).tolist(),rmse=best['rmse'],success=best['success'],boundary_hit=best['boundary_hit'],seconds=elapsed,initializer_seconds=extraction,nfev=sum(f['nfev'] for f in fits),iterations=sum(f['nit'] for f in fits),attempts=fits,wall_deadline_overrun_seconds=max(0.,elapsed-.05) if budget=='equal_wall' else 0.)
      rows.append(row)
      with dest.open('a',encoding='utf-8') as f:f.write(json.dumps(row,allow_nan=False)+'\n')
   if local%10==0:event('progress',material=mid,parents=local+1)
  write(OUT/f'{mid}.complete.json',dict(rows=len(rows),sha256=sha(dest),elapsed_seconds=time.time()-begun));event('material_completed',material=mid)
 report();return verify()

def report():
 summary=[]
 for mid in IDS:
  p=OUT/f'{mid}.jsonl'
  if not p.exists():continue
  rows=[json.loads(line) for line in p.read_text(encoding='utf-8').splitlines()]
  for budget in ('equal_eval','equal_wall','timing_rotations'):
   group=[r for r in rows if (r['budget']==budget and r['repeat']==0) or (budget=='timing_rotations' and r['budget']=='equal_eval' and r['parent'] in [x['parent'] for x in rows if x['repeat']==2])]
   for s in summarize(group):
    g=[r for r in group if r['method']==s['method'] and r['seed']==s['seed']];s.update(budget=budget,mean_iterations=float(np.mean([r['iterations'] for r in g])),mean_initializer_seconds=float(np.mean([r['initializer_seconds'] for r in g])),mean_wall_overrun_seconds=float(np.mean([r['wall_deadline_overrun_seconds'] for r in g])))
    summary.append(s)
 decisions=[]
 for mid in IDS:
  primary=[r for r in summary if r['material']==mid and r['budget']=='equal_eval'];wall=[r for r in summary if r['material']==mid and r['budget']=='equal_wall'];checks=[]
  for neural in [r for r in primary if r['method']=='N+A']:
   nw=next(r for r in wall if r['method']=='N+A' and r['seed']==neural['seed'])
   for baseline in [r for r in primary if r['method']!='N+A']:
    bw=next(r for r in wall if r['method']==baseline['method'])
    passed=bool(neural['q_mae']<=1.05*baseline['q_mae'] and np.all(np.array(neural['lattice_mae_angstrom'])<=1.05*np.array(baseline['lattice_mae_angstrom'])) and neural['mean_seconds']<.8*baseline['mean_seconds'] and neural['convergence_rate']>=baseline['convergence_rate'] and neural['boundary_rate']<=baseline['boundary_rate'] and nw['q_mae']<=1.05*bw['q_mae'] and np.all(np.array(nw['lattice_mae_angstrom'])<=1.05*np.array(bw['lattice_mae_angstrom'])))
    checks.append(dict(seed=neural['seed'],baseline=baseline['method'],passed=passed))
  decisions.append(dict(material=mid,decision='NEURAL_INCREMENTAL_VALUE' if len(checks)==9 and all(x['passed'] for x in checks) else 'NOT_ESTABLISHED',checks=checks))
 write(OUT/'decisions.json',decisions)
 if (OUT/'audit.json').exists():
  costs=[dict(material=r['material'],historical_training_seconds=r['training_seconds'],historical_training_amortized_seconds_per_prediction=r['training_seconds']/231) for r in read(OUT/'audit.json')['materials']]
  write(OUT/'training_cost.json',costs)
 write(OUT/'summary.json',summary)
 if summary:
  with (OUT/'summary.csv').open('w',encoding='utf-8',newline='') as f:
   w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
 text=['# E1：神经初始化与物理初始化的固定事后比较','', '旧测试已打开；本次为固定一次性探索，不是新确认性测试。每材料77个父样本，三神经种子共享父样本，重复计时不增加独立样本数。H1只用观测峰和候选CIF。全流程CPU；未重新训练。','', '主比较总maxfun=600（P3每起点200，有限差分可超限）；敏感性共享50毫秒墙钟，包含初始化和全部起点。墙钟截止以单次函数调用粒度执行，记录超时。前三轮旋转计时覆盖前12父样本；方法顺序随父样本旋转。','', '|材料|方法|种子|q MAE|晶格MAE Å|均时 ms|p95 ms|收敛率|','|---|---|---|---|---|---|---|---|']
 for s in summary:
  if s['budget']=='equal_eval':text.append(f"|{s['material']}|{s['method']}|{s['seed']}|{s['q_mae']:.6g}|{s['lattice_mae_angstrom']}|{1000*s['mean_seconds']:.3f}|{1000*s['p95_seconds']:.3f}|{s['convergence_rate']:.3f}|")
 text+=['','不因只胜过P3就宣布AI有效。比较P0/H1同等精度及时间；所有种子都必须满足预注册的增量价值规则。完整函数次数、迭代、边界和各预算见summary.csv，逐样本全部尝试见各材料JSONL。训练为历史成本，见audit.json；未将历史汇总伪装新结果。']
 (ROOT/'reports/HEURISTIC_RESULTS.md').write_text('\n'.join(text)+'\n',encoding='utf-8');return summary

def verify():
 freeze=read(OUT/'freeze.json');assert freeze['identity']['source_sha256']==sha(__file__) and freeze['identity']['prereg_sha256']==sha(ROOT/'E1_PREREGISTRATION.md')
 for mid in IDS:
  complete=read(OUT/f'{mid}.complete.json');assert sha(OUT/f'{mid}.jsonl')==complete['sha256']
  rows=[json.loads(x) for x in (OUT/f'{mid}.jsonl').read_text(encoding='utf-8').splitlines()];assert len(rows)==1068
  keys=[(r['budget'],r['method'],r['seed'],r['parent'],r['repeat']) for r in rows];assert len(keys)==len(set(keys))
 before=read(OUT/'summary.json');after=report();assert before==after
 result=dict(status='PASS',materials=7,rows=7476,recomputation=True,source_and_prereg_frozen=True);write(OUT/'verification.json',result);return result
if __name__=='__main__':
 import sys
 try:print(json.dumps(globals()[sys.argv[1] if len(sys.argv)>1 else 'audit'](),ensure_ascii=False))
 except Exception as exc:event('failure',error=repr(exc),traceback=traceback.format_exc());raise

from __future__ import annotations
import copy, csv, hashlib, importlib.util, json, math, sys, time, traceback
from pathlib import Path
import numpy as np
import scipy.optimize
import torch
import torch.nn.functional as F
ROOT=Path(__file__).resolve().parents[1]; OUT=Path(__file__).resolve().parent; DATA_DIR=OUT/'fresh_data'; CKDIR=OUT/'local_checkpoints'
CONF=json.loads((OUT/'frozen_retrain_config.json').read_text(encoding='utf-8'))
sys.path[:0]=[str(ROOT/'xrd_inversion/src'),str(ROOT/'xrd_robustness/src'),str(ROOT/'xrd_forward_loss/src')]
spec=importlib.util.spec_from_file_location('drv',ROOT/'xrd_forward_loss/scripts/run_issue19_p3.py');d=importlib.util.module_from_spec(spec);sys.modules[spec.name]=d;spec.loader.exec_module(d)
from pxrd_forward_loss.model import MeasurementAwareRegressor, ParameterRegressor
torch.set_num_threads(1); SEEDS=CONF['training']['paired_seeds']; METHODS=('A','B','C');CONDS=('simple','v9'); LAMBDAS=CONF['training']['lambda_candidates_for_B_and_C']; LIMIT=CONF['training']['max_measured_gpu_training_seconds']
LOG=OUT/'execution_log.jsonl'
def log(event,**kw):
 with LOG.open('a',encoding='utf-8') as f:f.write(json.dumps({'time_local':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'event':event,**kw},ensure_ascii=False)+'\n')
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def save_json(path,obj):path.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
def metrics(model,x,q,indices):
 ids=torch.as_tensor(indices,device=x.device,dtype=torch.long);model.eval()
 with torch.no_grad():
  outs=model(x.index_select(0,ids)); p=outs[0] if isinstance(outs,tuple) else outs
  return float(torch.mean(torch.abs(p-q.index_select(0,ids))).cpu())
def run_one(method,cond,seed,lam,arrays,splits,forward,base_cfg,used):
 tr=base_cfg['training'];torch.manual_seed(seed);torch.cuda.manual_seed_all(seed);np.random.seed(seed)
 x,q=d._tensor_data(arrays,cond,torch.device('cuda'))
 model=(ParameterRegressor(input_length=x.shape[1]) if method=='A' else MeasurementAwareRegressor(input_length=x.shape[1])).cuda()
 opt=torch.optim.Adam(model.parameters(),lr=float(tr['learning_rate']),weight_decay=float(tr['weight_decay']))
 rng=torch.Generator(device='cuda');rng.manual_seed(seed+1900);train_ids=torch.as_tensor(splits['train'],device='cuda',dtype=torch.long)
 best=float('inf');best_epoch=0;best_state=None;history=[];started=time.perf_counter();elapsed=0.0
 for epoch in range(1,int(tr['max_epochs'])+1):
  if used[0]+elapsed>=LIMIT:break
  torch.cuda.synchronize();ep=time.perf_counter();model.train();order=train_ids[torch.randperm(len(train_ids),generator=rng,device='cuda')];sums=[]
  for j in range(0,len(order),int(tr['batch_size'])):
   ids=order[j:j+int(tr['batch_size'])];xb=x.index_select(0,ids);yb=q.index_select(0,ids);opt.zero_grad(set_to_none=True);out=model(xb)
   if method=='A':
    qp=out;lp=F.mse_loss(qp,yb);lr=lp.new_zeros(());loss=lp
   else:
    qp,eta=out
    q_for_profile=qp.detach() if method=='C' else qp
    pred=d.expected_profile(forward,q_for_profile.double(),eta.double(),background_shape_mode=d.CONDITIONS[cond]).float()
    lr=F.mse_loss(pred,xb);lp=F.mse_loss(qp,yb);loss=lp+float(lam)*lr
   if not torch.isfinite(loss):raise FloatingPointError(f'nonfinite loss {method}/{cond}/{seed}/{lam}/{epoch}')
   loss.backward();pars=[p for p in model.parameters() if p.grad is not None]
   if not pars or any(not torch.isfinite(p.grad).all() for p in pars):raise FloatingPointError('nonfinite parameter gradient')
   torch.nn.utils.clip_grad_norm_(model.parameters(),float(tr['gradient_clip_norm']));opt.step();sums.append([float(loss.detach()),float(lp.detach()),float(lr.detach())])
  torch.cuda.synchronize();elapsed+=time.perf_counter()-ep
  val=metrics(model,x,q,splits['validation']);history.append({'epoch':epoch,'validation_q_mae':val,'train_loss':float(np.mean(sums,axis=0)[0]),'train_q_mse':float(np.mean(sums,axis=0)[1]),'train_recon_mse':float(np.mean(sums,axis=0)[2]),'elapsed_epoch_seconds':time.perf_counter()-ep})
  if val<best:best=val;best_epoch=epoch;best_state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
 used[0]+=elapsed
 if best_state is None:best_state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()};best=metrics(model,x,q,splits['validation']);best_epoch=0
 out=CKDIR/f'{cond}_{method}_lambda{lam:g}_seed{seed}.pt';out.parent.mkdir(parents=True,exist_ok=True)
 torch.save({'best_model_state':best_state,'method':method,'condition':cond,'seed':seed,'lambda':lam,'best_epoch':best_epoch,'best_validation_q_mae':best},out)
 rec={'method':method,'condition':cond,'seed':seed,'lambda':lam,'epochs_completed':len(history),'best_epoch':best_epoch,'best_validation_q_mae':best,'training_seconds':elapsed,'checkpoint':str(out.relative_to(OUT)),'parameter_count':sum(p.numel() for p in model.parameters()),'history':history}
 log('TRAIN_RUN_COMPLETED',**{k:v for k,v in rec.items() if k!='history'});del model;torch.cuda.empty_cache();return rec
def load(path,method,n):
 ck=torch.load(path,map_location='cuda',weights_only=False);m=ParameterRegressor(input_length=n) if method=='A' else MeasurementAwareRegressor(input_length=n);m.cuda();m.load_state_dict(ck['best_model_state']);m.eval();return m
def fit_eta(forward,cond,q0,obs,maxiter=60):
 mode=d.CONDITIONS[cond];target=torch.as_tensor(obs[None],device='cuda',dtype=torch.float32);qfixed=torch.as_tensor(q0[None],device='cuda',dtype=torch.float64);neutral=np.array([0.0,.105,.005]);bounds=[(-.06,.06),(.08,.13),(0,.01)]
 def fn(z):
  eta=torch.as_tensor(z[None],device='cuda',dtype=torch.float64).requires_grad_(True);p=d.expected_profile(forward,qfixed,eta,background_shape_mode=mode).float();loss=F.mse_loss(p,target);g=torch.autograd.grad(loss,eta)[0];return float(loss.detach()),g.cpu().numpy()[0]
 t=time.perf_counter();r=scipy.optimize.minimize(fn,neutral,method='L-BFGS-B',jac=True,bounds=bounds,options={'maxiter':maxiter,'ftol':1e-9,'gtol':1e-7,'maxls':20});return {'eta':r.x.tolist(),'success':bool(r.success),'iterations':int(r.nit),'seconds':time.perf_counter()-t,'mse':float(r.fun),'rmse':math.sqrt(max(0,float(r.fun))),'at_bound':bool(np.any(np.isclose(r.x,[b[0] for b in bounds],atol=1e-5)) or np.any(np.isclose(r.x,[b[1] for b in bounds],atol=1e-5)))}
def joint_fit(forward,cond,q0,obs,maxiter=60):
 mode=d.CONDITIONS[cond];target=torch.as_tensor(obs[None],device='cuda',dtype=torch.float32);bounds=[(-.8,.8),(-.8,.8),(-.06,.06),(.08,.13),(0,.01)];x0=np.r_[q0,[0,.105,.005]]
 def fn(z):
  zz=torch.as_tensor(z[None],device='cuda',dtype=torch.float64).requires_grad_(True);p=d.expected_profile(forward,zz[:,:2],zz[:,2:],background_shape_mode=mode).float();loss=F.mse_loss(p,target);g=torch.autograd.grad(loss,zz)[0];return float(loss.detach()),g.cpu().numpy()[0]
 t=time.perf_counter();r=scipy.optimize.minimize(fn,x0,method='L-BFGS-B',jac=True,bounds=bounds,options={'maxiter':maxiter,'ftol':1e-9,'gtol':1e-7,'maxls':20});return {'q':r.x[:2].tolist(),'eta':r.x[2:].tolist(),'success':bool(r.success),'iterations':int(r.nit),'seconds':time.perf_counter()-t,'mse':float(r.fun),'rmse':math.sqrt(max(0,float(r.fun))),'at_bound':bool(np.any(np.isclose(r.x,[b[0] for b in bounds],atol=1e-5)) or np.any(np.isclose(r.x,[b[1] for b in bounds],atol=1e-5)))}
def main():
 t0=time.perf_counter();cfg=json.loads((ROOT/CONF['source_config']).read_text(encoding='utf-8'));cfg=copy.deepcopy(cfg);dc=cfg['data'];fd=CONF['fresh_data'];dc['sobol_seed']=fd['sobol_seed'];dc['split_seed']=fd['split_seed'];dc['nuisance_seed']=fd['nuisance_seed'];
 for k in ('simple_view','v9_view'):dc[k]=copy.deepcopy(dc[k])
 forward,fcfg,structure=d.make_forward(cfg)
 arrays,meta=d.build_data(config=cfg,forward=forward,count=fd['parent_q_draws_max'],sobol_seed=fd['sobol_seed'],split_seed=fd['split_seed'],nuisance_seed=fd['nuisance_seed'],noise_seed=fd['noise_seed'])
 DATA_DIR.mkdir(parents=True,exist_ok=True);data_path=DATA_DIR/'fresh_batio3_paired.npz';np.savez_compressed(data_path,**arrays);split={k:arrays[f'{k}_indices'] for k in ('train','validation','test')}
 dm={'schema':'issue31_fresh_data_manifest_v1','config_sha256':sha(OUT/'frozen_retrain_config.json'),'cif_sha256':sha(ROOT/cfg['source']['cif']),'npz_sha256':sha(data_path),'array_hashes':meta['array_sha256'],'sample_metadata':meta,'split_counts':{k:int(len(v)) for k,v in split.items()},'test_indices_sha256':d.sha256_array(split['test']),'test_not_read_before_selection':True};save_json(DATA_DIR/'split_manifest.json',dm)
 log('FRESH_DATA_FROZEN',npz_sha256=dm['npz_sha256'],counts=dm['split_counts'],config_sha256=dm['config_sha256'])
 run_records=[];used=[0.0];budget_hit=False
 try:
  # A is trained once per paired seed/condition; B and C each use two frozen lambdas.
  for cond in CONDS:
   for seed in SEEDS:
    run_records.append(run_one('A',cond,seed,0.0,arrays,split,forward,cfg,used))
    for method in ('B','C'):
     for lam in LAMBDAS:
      if used[0]>=LIMIT:budget_hit=True;break
      run_records.append(run_one(method,cond,seed,lam,arrays,split,forward,cfg,used))
     if budget_hit:break
    if budget_hit:break
   if budget_hit:break
 except Exception as e:
  log('TRAINING_FAILED',error=repr(e),traceback=traceback.format_exc(),training_seconds=used[0]);save_json(OUT/'training_runs.json',{'status':'FAILED','runs':run_records,'training_seconds':used[0]});raise
 save_json(OUT/'training_runs.json',{'status':'PARTIAL_BUDGET' if budget_hit else 'CANDIDATES_COMPLETED','runs':run_records,'training_seconds':used[0],'hard_budget_seconds':LIMIT})
 if budget_hit or len(run_records)!=30:
  save_json(OUT/'training_selection.json',{'status':'BLOCKED_OR_PARTIAL','reason':'GPU training budget reached before all preregistered candidate runs completed','training_seconds':used[0]});return
 # Select lambda by mean best validation q MAE over paired seeds, independently per method/condition.
 selected={};selection={}
 for cond in CONDS:
  selected[cond]={};selection[cond]={}
  for method in ('B','C'):
   scores={str(lam):float(np.mean([r['best_validation_q_mae'] for r in run_records if r['condition']==cond and r['method']==method and r['lambda']==lam])) for lam in LAMBDAS}
   lam=min(LAMBDAS,key=lambda z:(scores[str(z)],z));selected[cond][method]=lam;selection[cond][method]={'mean_validation_q_mae_by_lambda':scores,'selected_lambda':lam,'test_used':False}
  selected[cond]['A']=0.0
 save_json(OUT/'training_selection.json',{'status':'FROZEN_BEFORE_TEST','rule':CONF['training']['selection_rule'],'selection':selection,'selected_lambda':selected})
 # Validation selection complete; now load selected checkpoints and evaluate test once.
 test_ids=np.asarray(split['test'],dtype=int);qtrue=arrays['q'][test_ids];test_rows=[];eval_start=time.perf_counter()
 for cond in CONDS:
  for method in METHODS:
   for seed in SEEDS:
    lam=selected[cond][method];path=CKDIR/f'{cond}_{method}_lambda{lam:g}_seed{seed}.pt';model=load(path,method,arrays[f'{cond}_observed'].shape[-1]);obs=arrays[f'{cond}_observed'][test_ids];qt,et=d._predict(model,obs);eta_true=arrays[f'{cond}_eta_true'][test_ids];
    for j,idx in enumerate(test_ids):
     neutral_fit=fit_eta(forward,cond,qt[j],obs[j]); joint=joint_fit(forward,cond,qt[j],obs[j]); a0,c0=d.q_to_lattice(qtrue[j],structure,fcfg);a1,c1=d.q_to_lattice(qt[j],structure,fcfg); ar,cr=d.q_to_lattice(np.asarray(joint['q']),structure,fcfg)
     row={'condition':cond,'method':method,'seed':seed,'global_index':int(idx),'q_true':qtrue[j].tolist(),'q_direct':qt[j].tolist(),'eta_true_posthoc':eta_true[j].tolist(),'direct_q_abs_error':np.abs(qt[j]-qtrue[j]).tolist(),'direct_a_abs_error_angstrom':float(abs(a1-a0)),'direct_c_abs_error_angstrom':float(abs(c1-c0)),'eta_only_fit':neutral_fit,'joint_fit':joint,'joint_q_abs_error':np.abs(np.asarray(joint['q'])-qtrue[j]).tolist(),'joint_a_abs_error_angstrom':float(abs(ar-a0)),'joint_c_abs_error_angstrom':float(abs(cr-c0))}
     if et is not None:row['eta_head_direct_posthoc']={'eta':et[j].tolist(),'scaled_abs_error':np.abs(d.eta_to_scaled(et[j])-d.eta_to_scaled(eta_true[j])).tolist()}
     test_rows.append(row)
    del model;torch.cuda.empty_cache()
 save_json(OUT/'fresh_test_per_sample.json',test_rows)
 # Aggregate by seed and method, preserve seed pairing.
 summary={}
 for cond in CONDS:
  summary[cond]={}
  for method in METHODS:
   summary[cond][method]={}
   for seed in SEEDS:
    rr=[r for r in test_rows if r['condition']==cond and r['method']==method and r['seed']==seed]
    summary[cond][method][str(seed)]={'n':len(rr),'direct_du_mae':float(np.mean([abs(r['direct_q_abs_error'][0]) for r in rr])),'direct_dv_mae':float(np.mean([abs(r['direct_q_abs_error'][1]) for r in rr])),'direct_q_mae':float(np.mean([np.mean(r['direct_q_abs_error']) for r in rr])),'direct_a_mae_angstrom':float(np.mean([r['direct_a_abs_error_angstrom'] for r in rr])),'direct_c_mae_angstrom':float(np.mean([r['direct_c_abs_error_angstrom'] for r in rr])),'eta_only_fit_rmse':float(np.mean([r['eta_only_fit']['rmse'] for r in rr])),'eta_only_success_rate':float(np.mean([r['eta_only_fit']['success'] for r in rr])),'eta_only_iterations_mean':float(np.mean([r['eta_only_fit']['iterations'] for r in rr])),'eta_only_runtime_p95_seconds':float(np.percentile([r['eta_only_fit']['seconds'] for r in rr],95)),'joint_q_mae':float(np.mean([np.mean(r['joint_q_abs_error']) for r in rr])),'joint_profile_rmse':float(np.mean([r['joint_fit']['rmse'] for r in rr])),'joint_success_rate':float(np.mean([r['joint_fit']['success'] for r in rr])),'joint_iterations_mean':float(np.mean([r['joint_fit']['iterations'] for r in rr])),'joint_runtime_p95_seconds':float(np.percentile([r['joint_fit']['seconds'] for r in rr],95)),'joint_a_mae_angstrom':float(np.mean([r['joint_a_abs_error_angstrom'] for r in rr])),'joint_c_mae_angstrom':float(np.mean([r['joint_c_abs_error_angstrom'] for r in rr]))}
    if method in ('B','C'):summary[cond][method][str(seed)]['eta_head_scaled_mae']=float(np.mean([np.mean(r['eta_head_direct_posthoc']['scaled_abs_error']) for r in rr]))
 # Paired seed deltas, B-A, C-A, C-B for direct q and joint q.
 paired={}
 for cond in CONDS:
  paired[cond]={}
  for contrast,(left,right) in {'B_minus_A':('B','A'),'C_minus_A':('C','A'),'C_minus_B':('C','B')}.items():
   paired[cond][contrast]={}
   for met in ('direct_q_mae','joint_q_mae'):
    vals={str(seed):summary[cond][left][str(seed)][met]-summary[cond][right][str(seed)][met] for seed in SEEDS}
    paired[cond][contrast][met]={'by_seed':vals,'mean':float(np.mean(list(vals.values()))),'sample_sd':float(np.std(list(vals.values()),ddof=1)),'positive_seed_count':sum(v>0 for v in vals.values())}
 save_json(OUT/'fresh_training_summary.json',{'status':'COMPLETED','scope':'fresh synthetic single-CIF interpolation','selected_lambda':selected,'test_evaluated_once':True,'seed_summary':summary,'paired_differences':paired,'gpu_training_seconds':used[0],'test_evaluation_seconds':time.perf_counter()-eval_start,'total_wall_seconds':time.perf_counter()-t0,'method':'A/B/C preregistered','training_runs':len(run_records)})
 # Local checkpoint hash manifest, do not put weights under git.
 cks=[]
 for p in sorted(CKDIR.glob('*.pt')):cks.append({'path':str(p.relative_to(OUT)),'bytes':p.stat().st_size,'sha256':sha(p)})
 save_json(OUT/'local_checkpoint_manifest.json',{'tracked_in_git':False,'count':len(cks),'checkpoints':cks})
 log('TRAINING_COMPLETED',gpu_training_seconds=used[0],test_evaluated_once=True,selected_lambda=selected)
 print(json.dumps({'status':'COMPLETED','training_seconds':used[0],'test_rows':len(test_rows),'selected':selected},indent=2))
if __name__=='__main__':main()

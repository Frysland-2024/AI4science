from __future__ import annotations
import csv, hashlib, importlib.util, json, math, sys, time
from pathlib import Path
import numpy as np
import scipy.optimize
import torch
import torch.nn.functional as F
sys.stdout.reconfigure(encoding='utf-8')
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
sys.path[:0]=[str(ROOT/'xrd_inversion/src'),str(ROOT/'xrd_robustness/src'),str(ROOT/'xrd_forward_loss/src')]
spec=importlib.util.spec_from_file_location('rootcause_supplement_driver',ROOT/'xrd_forward_loss/scripts/run_issue19_p3.py')
driver=importlib.util.module_from_spec(spec); sys.modules[spec.name]=driver; spec.loader.exec_module(driver)
trainer_spec=importlib.util.spec_from_file_location('rootcause_frozen_trainer',OUT/'train_fresh_abd.py')
trainer=importlib.util.module_from_spec(trainer_spec); sys.modules[trainer_spec.name]=trainer; trainer_spec.loader.exec_module(trainer)
assert torch.cuda.is_available(), 'CUDA unavailable'
assert trainer.sha256_file(OUT/'fresh_data'/'fresh_batio3_paired.npz')==json.loads((OUT/'final_summary.json').read_text(encoding='utf-8'))['data']['sha256']
summary=json.loads((OUT/'fresh_test_per_sample.json').read_text(encoding='utf-8'))
with np.load(OUT/'fresh_data'/'fresh_batio3_paired.npz',allow_pickle=False) as z:
    test_global=np.asarray(z['test_indices'],dtype=np.int64)
    global_to_local={int(g):i for i,g in enumerate(test_global)}
    observations={c:np.asarray(z[f'{c}_observed'][test_global],dtype=np.float32) for c in ('simple','v9')}
    q_true=np.asarray(z['q'][test_global],dtype=np.float64)
config,forward,forward_cfg,structure=trainer.load_config_and_forward()
torch.set_num_threads(int(trainer.CONF['training']['torch_num_threads']))
neutral_eta=np.asarray([0.0,0.105,0.005],dtype=np.float64)
eta_bounds=[(-0.06,0.06),(0.08,0.13),(0.0,0.01)]
q_bounds=[(-0.8,0.8),(-0.8,0.8)]
all_bounds=q_bounds+eta_bounds
target_cache={c:[torch.as_tensor(x[None],device='cuda',dtype=torch.float32) for x in observations[c]] for c in observations}

def optimize(condition, observed, start, joint):
    target=target_cache[condition][global_to_local[current_global]]
    mode=driver.CONDITIONS[condition]
    def objective(values):
        z=torch.as_tensor(values[None],device='cuda',dtype=torch.float64).requires_grad_(True)
        q=z[:,:2] if joint else torch.as_tensor(start[:2][None],device='cuda',dtype=torch.float64)
        eta=z[:,2:] if joint else z
        expected=driver.expected_profile(forward,q,eta,background_shape_mode=mode).float()
        loss=F.mse_loss(expected,target)
        grad=torch.autograd.grad(loss,z)[0]
        return float(loss.detach().cpu()),grad.detach().cpu().numpy()[0]
    started=time.perf_counter()
    result=scipy.optimize.minimize(objective,np.asarray(start,dtype=np.float64),method='L-BFGS-B',jac=True,bounds=all_bounds if joint else eta_bounds,options={'maxiter':60,'ftol':1e-9,'gtol':1e-7,'maxls':20})
    elapsed=time.perf_counter()-started
    values=np.asarray(result.x,dtype=np.float64)
    qfit=values[:2] if joint else np.asarray(start[:2],dtype=np.float64)
    etafit=values[2:] if joint else values
    return {'q_fit':qfit.tolist(),'eta_fit':etafit.tolist(),'profile_rmse':math.sqrt(max(0.0,float(result.fun))),'success':bool(result.success),'status':int(result.status),'message':str(result.message),'iterations':int(result.nit),'function_evaluations':int(result.nfev),'seconds':elapsed,'at_bound':bool(any(np.isclose(values[i],lo,atol=1e-5) or np.isclose(values[i],hi,atol=1e-5) for i,(lo,hi) in enumerate(all_bounds if joint else eta_bounds)))}

model_rows=[]
neutral_rows=[]
started_all=time.perf_counter()
for row in summary:
    condition=row['condition']; method=row['method']; seed=int(row['seed']); global_index=int(row['global_index']); current_global=global_index
    local=global_to_local[global_index]
    qinit=np.asarray(row['q_pred'],dtype=np.float64)
    fitted=optimize(condition,observations[condition][local],np.concatenate([qinit,neutral_eta]),True)
    truth=q_true[local]
    a_true,c_true=driver.q_to_lattice(truth,structure,forward_cfg)
    a_fit,c_fit=driver.q_to_lattice(np.asarray(fitted['q_fit']),structure,forward_cfg)
    model_rows.append({'condition':condition,'method':method,'seed':seed,'global_index':global_index,'q_init':qinit.tolist(),'q_true_posthoc':truth.tolist(),'q_abs_error_direct':row['q_abs_error'],'q_fit':fitted['q_fit'],'q_abs_error_joint':np.abs(np.asarray(fitted['q_fit'])-truth).tolist(),'a_abs_error_joint_angstrom':float(abs(a_fit-a_true)),'c_abs_error_joint_angstrom':float(abs(c_fit-c_true)),**{k:v for k,v in fitted.items() if k not in ('q_fit',)}})
for condition in ('simple','v9'):
    for local,global_index in enumerate(test_global):
        current_global=int(global_index)
        start=np.concatenate([np.zeros(2,dtype=np.float64),neutral_eta])
        fitted=optimize(condition,observations[condition][local],start,True)
        truth=q_true[local]
        a_true,c_true=driver.q_to_lattice(truth,structure,forward_cfg)
        a_fit,c_fit=driver.q_to_lattice(np.asarray(fitted['q_fit']),structure,forward_cfg)
        neutral_rows.append({'condition':condition,'global_index':int(global_index),'q_true_posthoc':truth.tolist(),'q_fit':fitted['q_fit'],'q_abs_error':np.abs(np.asarray(fitted['q_fit'])-truth).tolist(),'a_abs_error_angstrom':float(abs(a_fit-a_true)),'c_abs_error_angstrom':float(abs(c_fit-c_true)),**{k:v for k,v in fitted.items() if k not in ('q_fit',)}})
print('Completed model-start joint fits:',len(model_rows),'neutral profiles:',len(neutral_rows),'seconds:',round(time.perf_counter()-started_all,2),flush=True)

def metrics(rows):
    q=np.asarray([r['q_abs_error_joint'] if 'q_abs_error_joint' in r else r['q_abs_error'] for r in rows],dtype=float)
    return {'n':len(rows),'du_mae':float(q[:,0].mean()),'dv_mae':float(q[:,1].mean()),'q_mae':float(q.mean()),'a_mae_angstrom':float(np.mean([r['a_abs_error_joint_angstrom'] if 'a_abs_error_joint_angstrom' in r else r['a_abs_error_angstrom'] for r in rows])),'c_mae_angstrom':float(np.mean([r['c_abs_error_joint_angstrom'] if 'c_abs_error_joint_angstrom' in r else r['c_abs_error_angstrom'] for r in rows])),'profile_rmse':float(np.mean([r['profile_rmse'] for r in rows])),'solver_success_rate':float(np.mean([r['success'] for r in rows])),'mean_iterations':float(np.mean([r['iterations'] for r in rows])),'p95_runtime_seconds':float(np.percentile([r['seconds'] for r in rows],95)),'at_bound_count':int(sum(r['at_bound'] for r in rows))}

per_seed={}
for condition in ('simple','v9'):
    per_seed[condition]={}
    for method in ('A','B','D'):
        per_seed[condition][method]={}
        for seed in trainer.SEEDS:
            rows=[r for r in model_rows if r['condition']==condition and r['method']==method and r['seed']==int(seed)]
            per_seed[condition][method][str(seed)]=metrics(rows)
neutral_summary={c:metrics([r for r in neutral_rows if r['condition']==c]) for c in ('simple','v9')}
method_over_seed={}
for c in ('simple','v9'):
    method_over_seed[c]={}
    for m in ('A','B','D'):
        values=[per_seed[c][m][str(s)]['q_mae'] for s in trainer.SEEDS]
        method_over_seed[c][m]={'q_mae_mean_over_seed_means':float(np.mean(values)),'q_mae_sample_sd_over_seed_means':float(np.std(values,ddof=1)),'profile_rmse_mean_over_seed_means':float(np.mean([per_seed[c][m][str(s)]['profile_rmse'] for s in trainer.SEEDS]))}
result={'status':'COMPLETED_POSTHOC_SECONDARY_EVALUATION','protocol':'POSTHOC_REFINEMENT_PROTOCOL.md','test_set_reused_after_primary_decision':True,'selection_or_preregistered_decision_changed':False,'model_started_joint_fit_count':len(model_rows),'neutral_baseline_fit_count':len(neutral_rows),'model_started_joint_fits':model_rows,'physics_neutral_baseline':neutral_rows,'per_seed_summary':per_seed,'mean_over_seed_means':method_over_seed,'physics_neutral_summary_by_condition':neutral_summary,'total_fit_seconds':float(time.perf_counter()-started_all),'optimizer':{'method':'L-BFGS-B','objective':'mean squared error between measurement-aware expected profile and transformed observed input','maxiter':60,'ftol':1e-9,'gtol':1e-7,'maxls':20,'q_bounds':q_bounds,'eta_bounds':eta_bounds,'model_start':'predicted q plus common neutral eta [0,0.105,0.005]','physics_neutral_start':'q=[0,0], eta=[0,0.105,0.005]'},'eta_true_used_for_optimizer_or_initialization':False,'q_true_used_for_optimizer_or_initialization':False}
(OUT/'joint_qeta_refinement_per_sample.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
with (OUT/'joint_qeta_refinement_per_sample.csv').open('w',encoding='utf-8',newline='') as f:
    fields=['baseline','condition','method','seed','global_index','q_init','q_fit','q_abs_error_joint','a_abs_error_joint_angstrom','c_abs_error_joint_angstrom','profile_rmse','success','status','iterations','function_evaluations','seconds','at_bound']
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
    for r in model_rows: w.writerow({'baseline':'MODEL_Q_START',**{k:r.get(k) for k in fields if k!='baseline'}})
    for r in neutral_rows: w.writerow({'baseline':'PHYSICS_NEUTRAL',**{k:r.get(k) for k in fields if k!='baseline'}})
print(json.dumps({'status':result['status'],'fits':{'model_start':len(model_rows),'neutral':len(neutral_rows)},'seed_summary':method_over_seed,'neutral_summary':neutral_summary,'total_fit_seconds':result['total_fit_seconds']},indent=2))

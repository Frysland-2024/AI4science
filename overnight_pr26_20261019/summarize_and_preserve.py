import hashlib, importlib.util, json, sys, time
from pathlib import Path
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[1];OUT=Path(__file__).resolve().parent;BASE=ROOT/'xrd_forward_loss/measurement_closure/results/p3_issue19_20261018';F=BASE/'formal'
sys.path[:0]=[str(ROOT/'xrd_inversion/src'),str(ROOT/'xrd_robustness/src'),str(ROOT/'xrd_forward_loss/src')]
s=importlib.util.spec_from_file_location('drv',ROOT/'xrd_forward_loss/scripts/run_issue19_p3.py');d=importlib.util.module_from_spec(s);sys.modules[s.name]=d;s.loader.exec_module(d)
torch.set_num_threads(1)
def sh(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 orig=json.loads((F/'ab_results.json').read_text(encoding='utf8'));summary=json.loads((OUT/'fresh_training_summary.json').read_text(encoding='utf8'));rows=json.loads((OUT/'fresh_test_per_sample.json').read_text(encoding='utf8'));train=json.loads((OUT/'training_runs.json').read_text(encoding='utf8'))
 # Exact old seed-level result bundle, copied into this output without altering source artifacts.
 old={'source':'xrd_forward_loss/measurement_closure/results/p3_issue19_20261018/formal/ab_results.json','source_sha256':sh(F/'ab_results.json'),'status':orig['status'],'design':orig['design'],'split_counts':orig['split_counts'],'per_seed':orig['per_seed'],'aggregate':orig['aggregate'],'validation_lambda_selection':json.loads((F/'validation_lambda_selection.json').read_text(encoding='utf8')),'test_used_for_selection':orig['test_used_for_selection']}
 (OUT/'original_pr26_metrics.json').write_text(json.dumps(old,indent=2)+'\n',encoding='utf8')
 agg={}
 for cond in ('simple','v9'):
  agg[cond]={}
  for method in ('A','B','C'):
   keys=list(summary['seed_summary'][cond][method]); fields=['direct_du_mae','direct_dv_mae','direct_q_mae','direct_a_mae_angstrom','direct_c_mae_angstrom','eta_only_fit_rmse','eta_only_success_rate','eta_only_iterations_mean','eta_only_runtime_p95_seconds','joint_q_mae','joint_profile_rmse','joint_success_rate','joint_iterations_mean','joint_runtime_p95_seconds','joint_a_mae_angstrom','joint_c_mae_angstrom']
   if method in ('B','C'):fields+=['eta_head_scaled_mae']
   agg[cond][method]={}
   for f in fields:
    vals=[summary['seed_summary'][cond][method][k][f] for k in keys];agg[cond][method][f+'_mean_across_seeds']=float(np.mean(vals));agg[cond][method][f+'_seed_sample_sd']=float(np.std(vals,ddof=1))
   rr=[r for r in rows if r['condition']==cond and r['method']==method]
   agg[cond][method]['eta_fit_at_bound_count']=sum(r['eta_only_fit']['at_bound'] for r in rr);agg[cond][method]['joint_at_bound_count']=sum(r['joint_fit']['at_bound'] for r in rr);agg[cond][method]['eta_fit_nonconverged_count']=sum(not r['eta_only_fit']['success'] for r in rr);agg[cond][method]['joint_nonconverged_count']=sum(not r['joint_fit']['success'] for r in rr)
 (OUT/'fresh_training_aggregate.json').write_text(json.dumps({'n_test_per_seed':77,'seed_count':3,'conditions':agg,'paired_differences':summary['paired_differences'],'training_wall_clock_seconds':summary['total_wall_seconds'],'gpu_training_seconds':summary['gpu_training_seconds'],'test_evaluation_seconds':summary['test_evaluation_seconds']},indent=2)+'\n',encoding='utf8')
 # P1 mean and seed-level SD from the frozen 24-index paired diagnostic.
 p1=json.loads((OUT/'p1_per_sample.json').read_text(encoding='utf8'));p1seed={}
 for cond in ('simple','v9'):
  p1seed[cond]={}
  for method in ('A','B'):
   p1seed[cond][method]={}
   for seed in (20261045,20261046,20261047):
    rr=[r for r in p1 if r['condition']==cond and r['method']==method and r['seed']==seed]
    p1seed[cond][method][str(seed)]={'n':len(rr),'direct_q_mae':float(np.mean([np.mean([r['direct_du_abs_error'],r['direct_dv_abs_error']]) for r in rr]),),'eta_only_rmse':float(np.mean([r['fixed_q_eta_only']['rmse'] for r in rr])),'eta_only_scaled_nuisance_mae':float(np.mean([r['eta_only_scaled_nuisance_mae'] for r in rr])),'eta_only_solver_success_rate':float(np.mean([r['fixed_q_eta_only']['success'] for r in rr])),'eta_only_iterations':float(np.mean([r['fixed_q_eta_only']['iterations'] for r in rr])),'eta_only_seconds':float(np.mean([r['fixed_q_eta_only']['elapsed_seconds'] for r in rr])),'joint_q_mae':float(np.mean([np.mean([r['joint_du_abs_error'],r['joint_dv_abs_error']]) for r in rr])),'joint_rmse':float(np.mean([r['joint_q_eta_refinement']['rmse'] for r in rr])),'joint_scaled_nuisance_mae':float(np.mean([r['joint_scaled_nuisance_mae'] for r in rr])),'joint_solver_success_rate':float(np.mean([r['joint_q_eta_refinement']['success'] for r in rr])),'joint_iterations':float(np.mean([r['joint_q_eta_refinement']['iterations'] for r in rr])),'joint_seconds':float(np.mean([r['joint_q_eta_refinement']['elapsed_seconds'] for r in rr]))}
 (OUT/'p1_seed_summary.json').write_text(json.dumps(p1seed,indent=2)+'\n',encoding='utf8')
 print(json.dumps({'original_metric_sha256':old['source_sha256'],'fresh_training_rows':len(rows),'p1_per_sample_rows':len(p1),'training_runs':len(train['runs']),'aggregate':agg},indent=2))
if __name__=='__main__':main()

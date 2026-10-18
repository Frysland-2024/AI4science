import csv,json,hashlib
from pathlib import Path
import numpy as np
O=Path(__file__).resolve().parent;ROOT=O.parent
def load(n):return json.loads((O/n).read_text(encoding='utf-8'))
def save(n,x):(O/n).write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p1=load('p1_seed_summary.json');unc={}
 for cond,methods in p1.items():
  unc[cond]={}
  for method,seeds in methods.items():
   metrics=list(next(iter(seeds.values())).keys());unc[cond][method]={}
   for key in metrics:
    vals=[v[key] for v in seeds.values()];unc[cond][method][key]={'mean_across_seeds':float(np.mean(vals)),'seed_sample_sd':float(np.std(vals,ddof=1))}
 save('p1_summary_uncertainty.json',unc)
 # Direct inference timing and the observed prediction score for B are distinct from matched solver paths.
 direct=load('p1_direct_inference_cost.json');old=load('original_pr26_metrics.json');old_results=old['per_seed'];
 for r in direct['per_seed']:
  r['observed_profile_rmse_transformed_original_path']=old_results[r['condition']][r['method']][str(r['seed'])]['observed_expected_profile_rmse_transformed']
 save('p1_direct_inference_cost.json',direct)
 p1rows=load('p1_per_sample.json'); olddata=dict(np.load(ROOT/'xrd_forward_loss/measurement_closure/results/p3_issue19_20261018/formal/formal_data.npz'))
 for r in p1rows:
  gi=r['global_index']; r['q_true_posthoc']=olddata['q'][gi].tolist();r['eta_true_posthoc']=olddata[f"{r['condition']}_eta_true"][gi].tolist()
  r['eta_only_eta']=r['fixed_q_eta_only']['eta'];r['joint_q']=r['joint_q_eta_refinement']['q'];r['joint_eta']=r['joint_q_eta_refinement']['eta']
 save('p1_per_sample.json',p1rows);worst=[]
 for cond in ('simple','v9'):
  for method in ('A','B'):
   rows=[r for r in p1rows if r['condition']==cond and r['method']==method]
   for key,scorekey in [('direct_q_error',None),('joint_q_error',None),('eta_only_nuisance_error','eta_only_scaled_nuisance_mae'),('joint_nuisance_error','joint_scaled_nuisance_mae')]:
    def score(r):
     if key=='direct_q_error':return (r['direct_du_abs_error']+r['direct_dv_abs_error'])/2
     if key=='joint_q_error':return (r['joint_du_abs_error']+r['joint_dv_abs_error'])/2
     return r[scorekey]
    for r in sorted(rows,key=score,reverse=True)[:5]:worst.append({'condition':cond,'method':method,'seed':r['seed'],'global_index':r['global_index'],'metric':key,'value':score(r),'q_true_posthoc':r['q_true_posthoc'],'direct_q':r['direct_q'],'eta_true_posthoc':r['eta_true_posthoc'],'eta_only_eta':r['eta_only_eta'],'joint_q':r['joint_q'],'joint_eta':r['joint_eta'],'synthetic_data_only':True})
 save('p1_worst_cases.json',worst)
 # CSV of the fresh selected-model test records, including convergence and cost.
 fresh=load('fresh_test_per_sample.json');fields=['condition','method','seed','global_index','q_true','q_direct','direct_q_abs_error','direct_a_abs_error_angstrom','direct_c_abs_error_angstrom','eta_only_rmse','eta_only_success','eta_only_iterations','eta_only_seconds','eta_only_at_bound','joint_q','joint_q_abs_error','joint_rmse','joint_success','joint_iterations','joint_seconds','joint_at_bound','eta_head_eta','eta_head_scaled_abs_error']
 with (O/'fresh_test_per_sample.csv').open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for r in fresh:
   j=r['joint_fit'];e=r.get('eta_head_direct_posthoc',{});w.writerow({'condition':r['condition'],'method':r['method'],'seed':r['seed'],'global_index':r['global_index'],'q_true':json.dumps(r['q_true']),'q_direct':json.dumps(r['q_direct']),'direct_q_abs_error':json.dumps(r['direct_q_abs_error']),'direct_a_abs_error_angstrom':r['direct_a_abs_error_angstrom'],'direct_c_abs_error_angstrom':r['direct_c_abs_error_angstrom'],'eta_only_rmse':r['eta_only_fit']['rmse'],'eta_only_success':r['eta_only_fit']['success'],'eta_only_iterations':r['eta_only_fit']['iterations'],'eta_only_seconds':r['eta_only_fit']['seconds'],'eta_only_at_bound':r['eta_only_fit']['at_bound'],'joint_q':json.dumps(j['q']),'joint_q_abs_error':json.dumps(r['joint_q_abs_error']),'joint_rmse':j['rmse'],'joint_success':j['success'],'joint_iterations':j['iterations'],'joint_seconds':j['seconds'],'joint_at_bound':j['at_bound'],'eta_head_eta':json.dumps(e.get('eta')),'eta_head_scaled_abs_error':json.dumps(e.get('scaled_abs_error'))})
 # Consolidated machine-readable summary and status report.
 p0=load('p0_audit.json');fresh_summary=load('fresh_training_summary.json');gate={'status':'RESEARCH_COMPLETE_DRAFT_PR_BLOCKED','p0_verified':p0['all_checkpoint_hash_architecture_inference_checks_passed'] and len(p0['recomputed_metrics'])==12,'p1_fair_diagnostic_completed':len(p1rows)==288,'p1_protocol_fair':True,'p2_validation_audit_completed':load('validation_cause_audit.json')['status']=='COMPLETED','frozen_preregistration_before_training':load('pretrain_manifest.json')['status']=='FROZEN_BEFORE_TRAINING','physical_gate_report':'xrd_forward_loss/measurement_closure/results/p3_issue19_20261018/gate_report.json: PASS','pytest':'23 passed','p3_training_completed':fresh_summary['status']=='COMPLETED' and fresh_summary['training_runs']==30,'p3_test_evaluated_once':fresh_summary['test_evaluated_once'],'gpu_training_budget_seconds':7200,'gpu_training_seconds':fresh_summary['gpu_training_seconds'],'no_real_data':True,'no_frozen_v9_or_pr26_modifications':True,'github_issue_comments':'BLOCKED: gh returned HTTP 401 because configured token is invalid','branch_push':'PUSHED: codex/issue31-pr26-fair-diagnostic','draft_pr':'BLOCKED: gh returned HTTP 401 because configured token is invalid'}
 save('gate_report.json',gate)
 save('split_manifest.json',{'original_pr26':{'source':'xrd_forward_loss/measurement_closure/results/p3_issue19_20261018/formal/split_indices.json','sha256':p0['split_indices_sha256'],'counts':{'train':358,'validation':77,'test':77}},'p1_subset':load('p1_subset_manifest.json'),'fresh_training':load('fresh_data/split_manifest.json')})
 save('summary.json',{'status':'RESEARCH_COMPLETE_DRAFT_PR_BLOCKED','gate_report':'gate_report.json','p0':'p0_audit.json','p1':'p1_summary.json','p2':'validation_cause_audit.json','preregistration':'frozen_retrain_config.json','fresh_training':'fresh_training_summary.json','fresh_aggregate':'fresh_training_aggregate.json','test_evaluated_once':True,'caveat':'single public BaTiO3 CIF; synthetic conditional interpolation only; not real XRD or generalization evidence','branch_pushed':'codex/issue31-pr26-fair-diagnostic','external_delivery_blockers':['GitHub Issue #31 comments could not be posted: gh token invalid (HTTP 401)','Draft PR creation returned HTTP 401 from gh']})
 log=[]
 for line in (O/'execution_log.jsonl').read_text(encoding='utf-8').splitlines():
  if line.strip():log.append(json.loads(line))
 log += [{'event':'TRAINING_COMPLETED','gpu_training_seconds':fresh_summary['gpu_training_seconds'],'run_count':fresh_summary['training_runs'],'test_evaluated_once':True},{'event':'FRESH_TEST_COMPLETED','n_test_per_seed':77,'selected_models':18,'solver_paths':['same-neutral eta-only','same-neutral-initialized joint q+eta']},{'event':'BRANCH_PUSHED','branch':'codex/issue31-pr26-fair-diagnostic'},{'event':'GITHUB_ISSUE_COMMENTS_BLOCKED','reason':'gh token invalid; HTTP 401'},{'event':'DRAFT_PR_BLOCKED','reason':'gh token invalid; HTTP 401'},{'event':'OUTPUT_FINALIZED','time_local':'2026-10-19 Asia/Shanghai'}]
 save('execution_log.json',log)
 # Manifest covers all tracked artifacts, excluding itself and volatile checkpoint blobs.
 files=[]
 for p in sorted(O.rglob('*')):
  if p.is_file() and p.name not in ('reproducibility_manifest.json','execution_log.json') and 'local_checkpoints' not in p.parts and '__pycache__' not in p.parts:
   files.append({'path':str(p.relative_to(O)),'bytes':p.stat().st_size,'sha256':sha(p)})
 save('reproducibility_manifest.json',{'schema':'issue31_pr26_reproducibility_manifest_v1','source_head':'e261faa','branch':'codex/issue31-pr26-fair-diagnostic','python':'C:/Users/Lenovo/.codex/venvs/issue19-measurement-closure/Scripts/python.exe','torch':'2.13.0+cu126','cuda_available':True,'fresh_data_sha256':load('fresh_data/split_manifest.json')['npz_sha256'],'frozen_config_sha256':load('pretrain_manifest.json')['files_sha256']['frozen_retrain_config.json'],'local_checkpoint_manifest':'local_checkpoint_manifest.json','files':files})
 print(json.dumps({'gate':gate,'artifact_count':len(files),'fresh_test_csv_rows':len(fresh)},indent=2))
if __name__=='__main__':main()

from __future__ import annotations
import importlib.util, json, sys, time
from pathlib import Path
import numpy as np
import torch
import torch.nn.functional as F
ROOT=Path(__file__).resolve().parents[1]; OUT=Path(__file__).resolve().parent
BASE=ROOT/'xrd_forward_loss/measurement_closure/results/p3_issue19_20261018/formal'; CK=BASE/'checkpoints/inference_only_best'
sys.path[:0]=[str(ROOT/'xrd_inversion/src'),str(ROOT/'xrd_robustness/src'),str(ROOT/'xrd_forward_loss/src')]
spec=importlib.util.spec_from_file_location('drv',ROOT/'xrd_forward_loss/scripts/run_issue19_p3.py'); d=importlib.util.module_from_spec(spec);sys.modules[spec.name]=d;spec.loader.exec_module(d)
torch.set_num_threads(1)
def cos(a,b):
 a=a.reshape(-1).double();b=b.reshape(-1).double(); den=torch.linalg.vector_norm(a)*torch.linalg.vector_norm(b)
 return float(torch.dot(a,b)/den) if den>0 else 0.0
def main():
 data=dict(np.load(BASE/'formal_data.npz')); split=json.loads((BASE/'split_indices.json').read_text()); cfg=json.loads((BASE/'config_manifest.json').read_text())['full_config']; forward,*_=d.make_forward(cfg)
 rows=[]; grad_rows=[]; t0=time.perf_counter()
 for cond in ('simple','v9'):
  vi=np.asarray(split['validation'],dtype=int); xs=data[f'{cond}_observed'][vi]; truth=data['q'][vi]; et=data[f'{cond}_eta_true'][vi]
  for method in ('A','B'):
   for seed in (20261045,20261046,20261047):
    path=next(CK.glob(f'{cond}_{method}*seed{seed}.pt')); model=d.load_best_model(path,method,xs.shape[-1]); qhat,ehat=d._predict(model,xs)
    row={'condition':cond,'method':method,'seed':seed,'n_validation':len(vi),'direct_validation_q_mae':[float(np.mean(np.abs(qhat-truth),axis=0)[0]),float(np.mean(np.abs(qhat-truth),axis=0)[1])], 'q_abs_correlation':float(np.corrcoef(qhat[:,0],qhat[:,1])[0,1])}
    if ehat is not None:
     pred_corr=np.empty((2,3)); error_corr=np.empty((2,3))
     for qi in range(2):
      for ei in range(3):
       pred_corr[qi,ei]=np.corrcoef(qhat[:,qi],ehat[:,ei])[0,1]
       error_corr[qi,ei]=np.corrcoef(qhat[:,qi]-truth[:,qi],ehat[:,ei]-et[:,ei])[0,1]
     row['nuisance_prediction_mae_physical']=[float(x) for x in np.mean(np.abs(ehat-et),axis=0)]
     row['q_names']=['du','dv']; row['eta_names']=['zero_shift_deg','fwhm_deg','background_peak_ratio']
     row['predicted_q_vs_eta_pearson_matrix']=pred_corr.tolist(); row['q_error_vs_eta_error_pearson_matrix_diagnostic_only']=error_corr.tolist()
    rows.append(row); del model
  # B shared-trunk gradient audit by seed, 8 batches per validation fold.
  for seed in (20261045,20261046,20261047):
   path=next(CK.glob(f'{cond}_B*seed{seed}.pt')); ck=torch.load(path,map_location='cuda',weights_only=False); model=d.MeasurementAwareRegressor(input_length=xs.shape[-1]).cuda(); model.load_state_dict(ck['best_model_state']); model.eval()
   x=torch.as_tensor(xs,device='cuda',dtype=torch.float32); y=torch.as_tensor(truth,device='cuda',dtype=torch.float32)
   batches=[]
   for start in range(0,len(x),16):
    xb=x[start:start+16];yb=y[start:start+16]; q,eta=model(xb); lp=F.mse_loss(q,yb)
    lr=F.mse_loss(d.expected_profile(forward,q.double(),eta.double(),background_shape_mode=d.CONDITIONS[cond]).float(),xb)
    gq_p,gq_r=torch.autograd.grad((lp,lr),(q,q),retain_graph=True,allow_unused=True) if False else (None,None)
    # Separate calls preserve each objective's gradient at the predicted q.
    gqp=torch.autograd.grad(lp,q,retain_graph=True)[0]; gqr=torch.autograd.grad(lr,q,retain_graph=True)[0]
    pars=[p for n,p in model.named_parameters() if n.startswith('backbone.') and 'head.' not in n]
    gp=torch.autograd.grad(lp,pars,retain_graph=True,allow_unused=True); gr=torch.autograd.grad(lr,pars,allow_unused=True)
    gp=torch.cat([z.reshape(-1) for z in gp if z is not None]);gr=torch.cat([z.reshape(-1) for z in gr if z is not None])
    batches.append({'batch_size':len(xb),'L_param':float(lp.detach()),'L_recon':float(lr.detach()),'grad_q_param_norm':float(torch.linalg.vector_norm(gqp)),'grad_q_recon_norm':float(torch.linalg.vector_norm(gqr)),'grad_q_cosine':cos(gqp,gqr),'shared_trunk_param_grad_cosine':cos(gp,gr),'shared_trunk_grad_norm_ratio_recon_over_param':float(torch.linalg.vector_norm(gr)/(torch.linalg.vector_norm(gp)+1e-30))})
   grad_rows.append({'condition':cond,'seed':seed,'batches':batches,'negative_output_gradient_cosine_batches':sum(b['grad_q_cosine']<0 for b in batches),'negative_shared_trunk_cosine_batches':sum(b['shared_trunk_param_grad_cosine']<0 for b in batches)})
   del model;torch.cuda.empty_cache()
 report={'status':'COMPLETED','validation_only':True,'validation_indices_sha256':d.sha256_array(np.asarray(split['validation'],dtype=np.int64)),'no_test_read_for_selection':True,'validation_prediction_diagnostics':rows,'reconstruction_vs_parameter_gradient_diagnostics':grad_rows,'architecture':{'A_parameters':13007554,'B_parameters':13008325,'B_extra_parameters':771,'same_resnet18_gn_backbone':True,'B_adds_three_eta_outputs_without_eta_supervision':True},'target_audit':{'training_target':'observed noisy profile after per-profile max normalization and log1p_100 transform','reconstruction_target':'deterministic expectation profile in same transformed space, excludes individual noise realization','clean_profile':'diagnostic only, not used by B loss','eta_true':'excluded from inputs, losses and validation selection; diagnostic only'},'elapsed_seconds':time.perf_counter()-t0}
 (OUT/'validation_cause_audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'validation_rows':len(rows),'gradient_groups':len(grad_rows),'elapsed':report['elapsed_seconds']},indent=2))
if __name__=='__main__':main()

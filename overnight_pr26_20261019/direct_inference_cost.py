import importlib.util,json,sys,time
from pathlib import Path
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[1];OUT=Path(__file__).resolve().parent;BASE=ROOT/'xrd_forward_loss/measurement_closure/results/p3_issue19_20261018';F=BASE/'formal'
sys.path[:0]=[str(ROOT/'xrd_inversion/src'),str(ROOT/'xrd_robustness/src'),str(ROOT/'xrd_forward_loss/src')]
s=importlib.util.spec_from_file_location('drv',ROOT/'xrd_forward_loss/scripts/run_issue19_p3.py');d=importlib.util.module_from_spec(s);sys.modules[s.name]=d;s.loader.exec_module(d)
torch.set_num_threads(1)
def main():
 data=dict(np.load(F/'formal_data.npz'));split=json.loads((F/'split_indices.json').read_text());orig=json.loads((F/'ab_results.json').read_text());idx=np.asarray(split['test']);rows=[]
 for cond in ('simple','v9'):
  for method in ('A','B'):
   for seed in (20261045,20261046,20261047):
    suffix=('_lambda0.1' if cond=='simple' and method=='B' else '_lambda1' if cond=='v9' and method=='B' else '')
    p=F/'checkpoints/inference_only_best'/f'{cond}_{method}{suffix}_seed{seed}.pt'
    model=d.load_best_model(p,method,data[f'{cond}_observed'].shape[-1]);x=torch.as_tensor(data[f'{cond}_observed'][idx],device='cuda',dtype=torch.float32)
    for _ in range(2):
     with torch.no_grad():model(x)
    timings=[]
    for _ in range(10):
     torch.cuda.synchronize();t=time.perf_counter()
     with torch.no_grad():out=model(x)
     torch.cuda.synchronize();timings.append(time.perf_counter()-t)
    q,eta=d._predict(model,data[f'{cond}_observed'][idx]);r=orig['per_seed'][cond][method][str(seed)];row={'condition':cond,'method':method,'seed':seed,'test_count':len(idx),'q_mae':r['parameter_mae_normalized_q'],'runtime_seconds_median_10_full_test_batches':float(np.median(timings)),'runtime_seconds_p95_10_full_test_batches':float(np.percentile(timings,95)),'runtime_test_n':10}
    if eta is not None:row['eta_head_scaled_coordinate_mae']=r['nuisance_error_diagnostic_only']['scaled_coordinate_mae']
    rows.append(row);del model;torch.cuda.empty_cache()
 (OUT/'p1_direct_inference_cost.json').write_text(json.dumps({'status':'COMPLETED','runtime_protocol':'10 timed batched inferences of all 77 test spectra after 2 warmups, synchronized CUDA; same model batch size','per_seed':rows},indent=2)+'\n',encoding='utf8')
 print(json.dumps(rows,indent=2))
if __name__=='__main__':main()

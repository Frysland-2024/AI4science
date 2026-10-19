"""One predeclared supervised initializer and shared-optimizer comparison."""
from __future__ import annotations
import csv, hashlib, json, time
from pathlib import Path
import numpy as np
from .physics import PowderModel, ETA_NEUTRAL
from .manager import atomic, event, sha


def splits(config):
    d=config['data']; n=d['parents']; perm=np.random.default_rng(d['split_seed']).permutation(n)
    a=d['train']; b=a+d['validation']
    result={'train':perm[:a], 'validation':perm[a:b], 'test':perm[b:]}
    assert len(np.unique(np.concatenate(list(result.values()))))==n
    assert len(result['test'])==d['test']
    return result


def summarize(rows):
    output=[]
    for method,seed in sorted(set((r['method'],r['seed']) for r in rows)):
        group=[r for r in rows if r['method']==method and r['seed']==seed]
        qerr=np.array([np.abs(np.array(r['q_fit'])-r['q_true_posthoc']) for r in group])
        lattice=np.array([r['lattice_abs_error_angstrom'] for r in group])
        seconds=np.array([r['seconds'] for r in group])
        output.append(dict(material=group[0]['material'],method=method,seed=seed,n=len(group),q_mae=float(qerr.mean()),
          lattice_mae_angstrom=lattice.mean(0).tolist(),profile_rmse=float(np.mean([r['rmse'] for r in group])),
          convergence_rate=float(np.mean([r['success'] for r in group])),boundary_rate=float(np.mean([r['boundary_hit'] for r in group])),
          mean_seconds=float(seconds.mean()),median_seconds=float(np.median(seconds)),p95_seconds=float(np.percentile(seconds,95)),
          mean_nfev=float(np.mean([r['nfev'] for r in group])),
          multistart_disagreement_mean=float(np.mean([r.get('multistart_disagreement',0) for r in group]))))
    return output


def run_material(material,config,directory):
    import torch
    from torch import nn
    out=Path(directory); out.mkdir(parents=True,exist_ok=True)
    private=out/'private'; private.mkdir(exist_ok=True)
    model=PowderModel(material['cif_path'],grid_size=config.get('grid_size',1024))
    d=dict(config['data']); t=config['training']; split=splits(config)
    material_offset=int(hashlib.sha256(material['id'].encode()).hexdigest()[:8],16)
    for key in ('parent_seed','nuisance_seed','noise_seed'): d[key]+=material_offset
    # These new parent/noise draws are unrelated to previous opened studies.
    q=np.random.default_rng(d['parent_seed']).uniform(-.8,.8,(d['parents'],model.ndim))
    eta_rng=np.random.default_rng(d['nuisance_seed']); eta=np.column_stack([
      eta_rng.uniform(-.10,.10,d['parents']),eta_rng.uniform(.24,.42,d['parents']),
      eta_rng.uniform(.8,1.2,d['parents']),eta_rng.uniform(.02,.06,d['parents']),eta_rng.uniform(-.015,.015,d['parents'])])
    atomic(out/'split_manifest.json',dict(indices={k:v.tolist() for k,v in split.items()},
       q_parent_sha256=hashlib.sha256(q.tobytes()).hexdigest(),seeds=d,unit='parent q before nuisance/noise',test_opened=False))
    def observations(indices):
        result=[]
        for i in indices:
            mu=model.profile(q[i],eta[i]); rng=np.random.default_rng(np.random.SeedSequence([d['noise_seed'],int(i)]))
            y=rng.poisson(np.maximum(mu,0)*15000)/15000+rng.normal(0,.002,len(mu))
            result.append(y)
        return np.array(result,dtype=np.float32)
    train=observations(split['train']); val=observations(split['validation'])
    np.savez_compressed(private/'train_val.npz',train=train,validation=val)
    torch.set_num_threads(1); torch.manual_seed(0)
    torch.backends.cudnn.deterministic=True; torch.backends.cudnn.benchmark=False
    device='cuda' if torch.cuda.is_available() else 'cpu'
    def network():
        return nn.Sequential(nn.Linear(len(model.grid),256),nn.SiLU(),nn.Linear(256,128),nn.SiLU(),nn.Linear(128,model.ndim),nn.Tanh())
    # Train-only pointwise normalization, not test-derived preprocessing.
    mean=train.mean(0); std=np.maximum(train.std(0),.02)
    np.savez_compressed(private/'normalization.npz',mean=mean,std=std)
    x=torch.tensor((train-mean)/std,device=device); v=torch.tensor((val-mean)/std,device=device)
    y=torch.tensor(q[split['train']],dtype=torch.float32,device=device); vy=torch.tensor(q[split['validation']],dtype=torch.float32,device=device)
    curves=[]; models=[]; training_seconds=0.; selected=[]; active_training_started=None
    runroot=out.parents[2]
    def check_budget():
        ledger=json.loads((runroot/'budget.json').read_text()) if (runroot/'budget.json').exists() else {'pilot_started':time.time(),'gpu_training_seconds':0}
        if time.time()-ledger['pilot_started']>=config.get('wall_budget_seconds',28800): raise RuntimeError('PARTIAL: hard wall budget exhausted')
        active_elapsed=time.perf_counter()-active_training_started if active_training_started is not None else 0.
        if ledger['gpu_training_seconds']+active_elapsed>=config.get('gpu_budget_seconds',14400): raise RuntimeError('PARTIAL: hard GPU training budget exhausted')
        size=sum(p.stat().st_size for p in runroot.rglob('*') if p.is_file())
        if size>=min(config.get('disk_budget_bytes',10000000000),10000000000): raise RuntimeError('PARTIAL: disk budget exhausted')
    for seed in t['seeds']:
        check_budget(); torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
        net=network().to(device); opt=torch.optim.Adam(net.parameters(),lr=t['lr']); best=float('inf'); weights=None; bestepoch=0
        if device=='cuda': torch.cuda.synchronize()
        started=time.perf_counter(); active_training_started=started
        for epoch in range(t['epochs']):
            check_budget(); net.train(); order=torch.randperm(len(x),device=device); losses=[]
            for batch in order.split(t['batch_size']):
                opt.zero_grad(); loss=torch.mean((net(x[batch])-y[batch])**2)
                if not torch.isfinite(loss): raise RuntimeError('nonfinite training loss')
                loss.backward(); torch.nn.utils.clip_grad_norm_(net.parameters(),5.); opt.step(); losses.append((float(loss.detach()),len(batch)))
            net.eval()
            with torch.no_grad(): vm=float(torch.mean(torch.abs(net(v)-vy)))
            if not np.isfinite(vm): raise RuntimeError('nonfinite validation')
            if vm<best:
                best=vm; bestepoch=epoch+1; weights={k:z.detach().cpu().clone() for k,z in net.state_dict().items()}
            curves.append(dict(seed=seed,epoch=epoch+1,train_mse=sum(a*b for a,b in losses)/len(x),validation_q_mae=vm))
            atomic(out/'learning_curves.json',curves)
        if device=='cuda': torch.cuda.synchronize()
        duration=time.perf_counter()-started; training_seconds+=duration; active_training_started=None
        ledger=json.loads((runroot/'budget.json').read_text())
        if device=='cuda': ledger['gpu_training_seconds']+=duration
        atomic(runroot/'budget.json',ledger)
        net=network(); net.load_state_dict(weights); net.eval(); models.append((seed,net))
        path=private/f'best_{seed}.pt'; torch.save(weights,path)
        selected.append(dict(seed=seed,best_epoch=bestepoch,validation_q_mae=best,checkpoint_sha256=sha(path),training_seconds=duration))
        atomic(out/'training_selection.json',dict(status='FROZEN_BEFORE_TEST',models=selected,device=device,training_seconds=training_seconds))
        event(out,'training_complete',seed=seed,seconds=duration,checkpoint_sha256=sha(path))
    # Atomic marker is created BEFORE any held-out profile/score. Resume cannot rerun this attempt.
    check_budget(); atomic(out/'test_opened.json',dict(time=time.time(),selection_sha256=sha(out/'training_selection.json'),protocol='one test opening'))
    event(out,'test_opened',selection_sha256=sha(out/'training_selection.json'))
    test=observations(split['test']); np.savez_compressed(private/'test.npz',observed=test)
    rows=[]; starts=[np.zeros(model.ndim),np.full(model.ndim,-.5),np.full(model.ndim,.5)]
    settings=config.get('optimizer',{'maxiter':100,'maxfun':1000}); equal=config.get('fairness',{'total_maxfun':600})['total_maxfun']
    def record(method,seed,i,yobs,fits,elapsed,inference=0.):
        best=min(fits,key=lambda z:z['rmse']); truth=q[i]
        row=dict(material=material['id'],method=method,seed=seed,parent=int(i),q_true_posthoc=truth.tolist(),q_fit=best['q'],eta_fit=best['eta'],
          lattice_true_angstrom=model.lattice(truth).tolist(),lattice_fit_angstrom=model.lattice(best['q']).tolist(),
          lattice_abs_error_angstrom=np.abs(model.lattice(best['q'])-model.lattice(truth)).tolist(),rmse=best['rmse'],
          success=best['success'],boundary_hit=best['boundary_hit'],seconds=elapsed+inference,inference_seconds=inference,
          nfev=sum(z['nfev'] for z in fits),iterations=sum(z['nit'] for z in fits),attempts=fits,
          multistart_disagreement=float(np.max(np.ptp(np.array([z['q'] for z in fits]),axis=0))))
        rows.append(row)
        with (out/'per_sample.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(row,allow_nan=False)+'\n')
    for local,i in enumerate(split['test']):
        check_budget(); observed=test[local]
        for suffix,maxfun in [('',settings['maxfun']),('_equal_eval',equal)]:
            begun=time.perf_counter(); fit=model.fit(observed,starts[0],maxiter=settings['maxiter'],maxfun=maxfun)
            record('P0'+suffix,0,i,observed,[fit],time.perf_counter()-begun)
            begun=time.perf_counter(); fits=[model.fit(observed,s,maxiter=settings['maxiter'],maxfun=(maxfun//3 if suffix else maxfun)) for s in starts]
            record('P3'+suffix,0,i,observed,fits,time.perf_counter()-begun)
        for seed,net in models:
            begun=time.perf_counter()
            with torch.no_grad(): guess=net(torch.tensor((observed-mean)/std)[None]).numpy()[0]
            inference=time.perf_counter()-begun
            for suffix,maxfun in [('',settings['maxfun']),('_equal_eval',equal)]:
                begun=time.perf_counter(); fit=model.fit(observed,guess,maxiter=settings['maxiter'],maxfun=maxfun)
                record('N+A'+suffix,seed,i,observed,[fit],time.perf_counter()-begun,inference)
        if local%10==0: event(out,'test_progress',completed=local+1,total=len(test))
    summary=summarize(rows); atomic(out/'metrics.json',summary)
    fields=[k for k in rows[0] if k!='attempts']
    with (out/'per_sample.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); writer.writeheader(); writer.writerows(rows)
    # Decision requires consistency and no hidden per-coordinate degradation; descriptive three-seed evidence only.
    p3=next(r for r in summary if r['method']=='P3'); ns=[r for r in summary if r['method']=='N+A']
    equal3=next(r for r in summary if r['method']=='P3_equal_eval'); equaln=[r for r in summary if r['method']=='N+A_equal_eval']
    accuracy=all(r['q_mae']<.95*p3['q_mae'] and np.all(np.array(r['lattice_mae_angstrom'])<=1.05*np.array(p3['lattice_mae_angstrom'])) and r['mean_seconds']<=1.10*p3['mean_seconds'] and r['convergence_rate']>=p3['convergence_rate'] for r in ns)
    fair=all(r['q_mae']<=1.05*equal3['q_mae'] for r in equaln)
    pareto=all(r['q_mae']<=1.05*p3['q_mae'] and np.all(np.array(r['lattice_mae_angstrom'])<=1.05*np.array(p3['lattice_mae_angstrom'])) and r['mean_seconds']<.8*p3['mean_seconds'] and r['convergence_rate']>=p3['convergence_rate'] and r['boundary_rate']<=p3['boundary_rate'] for r in ns)
    decision='NEURAL_ACCURACY_ADVANTAGE' if accuracy and fair else ('NEURAL_RUNTIME_PARETO' if pareto and fair else 'NEGATIVE FOR NEURAL INCREMENTAL VALUE')
    try:
        import matplotlib; matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,axes=plt.subplots(1,2,figsize=(10,4))
        for seed in t['seeds']:
            c=[r for r in curves if r['seed']==seed]; axes[0].plot([r['epoch'] for r in c],[r['validation_q_mae'] for r in c],label=str(seed))
        axes[0].set(xlabel='Epoch',ylabel='Validation normalized q MAE'); axes[0].legend()
        primary=[r for r in summary if not r['method'].endswith('eval')]
        axes[1].scatter([r['mean_seconds'] for r in primary],[r['q_mae'] for r in primary])
        for r in primary: axes[1].annotate(r['method']+' '+str(r['seed']),(r['mean_seconds'],r['q_mae']))
        axes[1].set(xlabel='Mean end-to-end seconds',ylabel='Test normalized q MAE'); fig.tight_layout(); fig.savefig(out/'comparison.png',dpi=140); plt.close(fig)
    except ImportError as exc: event(out,'plot_skipped',reason=str(exc))
    return dict(status='PASS',budget_recorded=True,material=material['id'],summary=summary,decision=decision,
       training_seconds=training_seconds,gpu_training_seconds=training_seconds if device=='cuda' else 0.,training_device=device,
       training_amortized_seconds_per_test_prediction=training_seconds/(3*d['test']),
       training_nonamortized_seconds=training_seconds,selection=selected,test_parents=d['test'],
       data_hashes={p.name:sha(p) for p in private.glob('*.npz')},
       optional_arms={'N+B':'SKIPPED: non-autograd NumPy renderer','low_noise':'NOT_RUN: prioritize diverse V9-like materials','independent_renderer_stress':'NOT_RUN: primary bounded comparison prioritized'},
       limitations=['Independent per-material models; no zero-shot material transfer','Same-generator synthetic primary; no experimental-XRD validity','Count noise + Gaussian noise; V9-like nuisance ranges, no texture', 'Equal-evaluation sensitivity uses SciPy maxfun ceilings; actual counts retained, numerical derivative batches may overshoot'])

"""Bounded BaTiO3 synthetic A/B pilot (512 samples, paired three seeds)."""
from __future__ import annotations

import hashlib, json, math, time
from pathlib import Path

import numpy as np
import torch
from scipy.stats import qmc
from pymatgen.core import Structure

from measurement_closure.audit import expected_profile
from pxrd_forward_loss.model import ParameterRegressor
from pxrd_forward_loss.data import split_indices
from xrd_inversion.gpu_forward import CachedTetragonalGPUForward

ROOT=Path(__file__).resolve().parents[2]

def make_model(output_dim):
    m=ParameterRegressor()
    if output_dim != 2:
        old=m.backbone.head
        m.backbone.head=torch.nn.Linear(old.in_features,output_dim)
        torch.nn.init.normal_(m.backbone.head.weight,0.,1e-3)
        torch.nn.init.zeros_(m.backbone.head.bias)
    return m

def main(output: str):
    if not torch.cuda.is_available(): raise RuntimeError('CUDA_REQUIRED; training not started')
    cfg=json.loads((ROOT/'xrd_inversion/configs/week1_formal_gate.json').read_text(encoding='utf-8'))
    structure=Structure.from_file(ROOT/'xrd_forward_loss/data/public_cif/BaTiO3_COD_9014273_P4mm.cif')
    forward=CachedTetragonalGPUForward(structure,grid_config=cfg['grid'],parameter_config=cfg['parameterization'],device='cuda',dtype=torch.float64)
    out=ROOT/output
    out.mkdir(parents=True,exist_ok=False)
    q=((qmc.Sobol(2,scramble=True,seed=20261018).random_base2(9)*1.6)-.8).astype(np.float32)
    splits=split_indices(len(q),seed=20261019,train_fraction=.7,validation_fraction=.15)
    rng=np.random.default_rng(20261020)
    conds={}
    with torch.no_grad():
      for name in ('simple','v9_style'):
        etas=[]; mu=[]; obs=[]
        for row in q:
          if name=='simple':
            e=np.array([0.,.08,.002,.002,1.],dtype=np.float64)
          else:
            e=np.array([rng.uniform(-.06,.06),rng.uniform(.11,.13),rng.uniform(.005,.008),rng.uniform(.005,.008),1.],dtype=np.float64)
          qt=torch.as_tensor(row,dtype=torch.float64,device='cuda')
          et=torch.as_tensor(e,dtype=torch.float64,device='cuda')
          m=expected_profile(forward,qt,et).cpu().numpy()
          etas.append(e); mu.append(m)
          # One Poisson-Gaussian realization is input only; B targets deterministic mu.
          counts=rng.poisson(np.maximum(m,0)*30000).astype(np.float64)+rng.normal(0.,1.,m.shape)
          counts=np.maximum(counts,0); counts/=max(float(counts.max()),1e-12)
          obs.append(np.log1p(100*counts)/math.log(101))
        mu=np.asarray(mu,dtype=np.float32); mu=mu/np.maximum(mu.max(axis=1,keepdims=True),1e-12)
        target=np.log1p(100*mu)/math.log(101)
        conds[name]={'eta':np.asarray(etas,dtype=np.float32),'mu':target.astype(np.float32),'obs':np.asarray(obs,dtype=np.float32)}
    results={}; histories={}; device=torch.device('cuda')
    train_idx=torch.as_tensor(splits['train'],device=device); val_idx=torch.as_tensor(splits['validation'],device=device); test_idx=np.asarray(splits['test'])
    q_t=torch.as_tensor(q,device=device,dtype=torch.float32)
    eta_bounds=torch.tensor([.06,.12,.02,.02,.30],device=device,dtype=torch.float32)
    eta_center=torch.tensor([0.,.14,.01,.01,1.],device=device,dtype=torch.float32)
    for cond,data in conds.items():
      x=torch.as_tensor(data['obs'],device=device,dtype=torch.float32)
      eta_t=torch.as_tensor(data['eta'],device=device,dtype=torch.float32)
      mu_t=torch.as_tensor(data['mu'],device=device,dtype=torch.float32)
      for method in ('A','B'):
       for seed in (20261021,20261022,20261023):
        torch.manual_seed(seed); torch.cuda.manual_seed_all(seed); np.random.seed(seed)
        model=make_model(2 if method=='A' else 7).to(device)
        optimizer=torch.optim.Adam(model.parameters(),lr=.0005)
        generator=torch.Generator(device=device); generator.manual_seed(seed+1000)
        best=float('inf'); best_state=None; best_epoch=0; history=[]; start=time.perf_counter(); torch.cuda.reset_peak_memory_stats(device)
        for epoch in range(1,25):
          model.train(); order=train_idx[torch.randperm(len(train_idx),generator=generator,device=device)]
          for st in range(0,len(order),32):
            ix=order[st:st+32]; pred=model(x[ix]); pq=pred[:,:2] if method=='B' else pred
            loss=torch.nn.functional.mse_loss(pq,q_t[ix]);
            if method=='B':
              ehat=eta_center+pred[:,2:]*eta_bounds
              ehat=torch.cat((ehat[:,:1],ehat[:,1:2].clamp(.08,.20),ehat[:,2:]),dim=1)
              recon=expected_profile(forward,pq.double(),ehat.double())
              recon=recon/recon.amax(dim=1,keepdim=True).clamp_min(1e-12)
              recon=torch.log1p(100*recon)/math.log(101)
              loss=loss+.1*torch.nn.functional.mse_loss(pred[:,2:],(eta_t[ix]-eta_center)/eta_bounds)+.1*torch.nn.functional.mse_loss(recon.float(),mu_t[ix])
            optimizer.zero_grad(set_to_none=True); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(),5.); optimizer.step()
          model.eval()
          with torch.no_grad():
            pv=model(x[val_idx]); pv=pv[:,:2] if method=='B' else pv
            val=float(torch.mean(torch.abs(pv-q_t[val_idx])).cpu())
          history.append({'epoch':epoch,'validation_q_mae':val})
          if val<best: best=val;best_epoch=epoch;best_state={k:v.detach().clone() for k,v in model.state_dict().items()}
        elapsed=time.perf_counter()-start; model.load_state_dict(best_state); model.eval()
        with torch.no_grad():
          p=model(x[test_idx]); pq=p[:,:2] if method=='B' else p
          qpred=pq.cpu().numpy(); qtrue=q[test_idx]
          lattice=[]
          for arow,brow in zip(qpred,qtrue):
            def ac(v):
              u0=(2*math.log(structure.lattice.a)+math.log(structure.lattice.c))/3;v0=math.log(structure.lattice.c/structure.lattice.a)
              u=u0+float(v[0])*cfg['parameterization']['du_half_range']; vv=v0+float(v[1])*cfg['parameterization']['dv_half_range']
              return [math.exp(u-vv/3),math.exp(u+2*vv/3)]
            lattice.append(np.abs(np.asarray(ac(arow))-ac(brow)))
          met={'q_mae':float(np.abs(qpred-qtrue).mean()),'a_c_mae_angstrom':np.mean(lattice,axis=0).tolist(),
            'training_seconds':elapsed,'peak_gpu_memory_mb':torch.cuda.max_memory_allocated(device)/1024**2,'best_epoch':best_epoch,
            'test_expected_profile_rmse':None}
          if method=='B':
            etp=eta_center+model(x[test_idx])[:,2:]*eta_bounds
            etp=torch.cat((etp[:,:1],etp[:,1:2].clamp(.08,.20),etp[:,2:]),dim=1)
            reconstructed=expected_profile(forward,pq.double(),etp.double()).cpu().numpy()
            # Compare to deterministic reference expected profile; normalize identically.
            targ=conds[cond]['mu'][test_idx]
            rt=np.log1p(100*reconstructed/np.maximum(reconstructed.max(axis=1,keepdims=True),1e-12))/math.log(101)
            met['test_expected_profile_rmse']=float(np.sqrt(np.mean((rt-targ)**2)))
          key=f'{cond}/{method}/{seed}';results[key]=met;histories[key]=history
        del model,optimizer
    summary={'scope':'synthetic single-CIF conditional interpolation; not real PXRD or unseen structures',
      'samples':512,'seeds':[20261021,20261022,20261023],'epochs_max':24,'conditions':['simple','v9_style'],
      'v9_style_definition':'Torch expected forward with global zero shift, Gaussian width, smooth linear nonnegative background, relative scale, then Poisson plus Gaussian readout. This is a four-operator V9-style closure, not the complete independent V9 NumPy peak-table pipeline.',
      'methods':{'A':'q-only supervised ResNet-18-GN','B':'same backbone plus five eta outputs; eta labels disclosed; q supervision + fixed 0.1 eta/profile losses. B has larger output head and privileged synthetic eta/expected-profile training labels; inference uses predicted eta, never eta_true.'},
      'data_split':{k:len(v) for k,v in splits.items()},'results':results,'histories':histories}
    (out/'results.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    (out/'manifest.json').write_text(json.dumps({'config_sha256':hashlib.sha256((ROOT/'xrd_inversion/configs/week1_formal_gate.json').read_bytes()).hexdigest(),
      'dataset_sha256':hashlib.sha256(q.tobytes()).hexdigest(),'split_seed':20261019,'loss_weights':{'eta':.1,'profile':.1},
      'max_samples':512,'max_seeds':3,'max_epochs_per_run':24},indent=2),encoding='utf-8')
    return results

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--output',default='xrd_forward_loss/measurement_closure/ab_run');main(p.parse_args().output)

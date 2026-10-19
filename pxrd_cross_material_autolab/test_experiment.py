import copy
import numpy as np
from pxrd_cross_material_autolab.experiment import splits, summarize


def test_parent_splits_disjoint_and_complete():
    config={'data':{'parents':512,'train':358,'validation':77,'test':77,'split_seed':91}}
    s=splits(config)
    assert {k:len(v) for k,v in s.items()}=={'train':358,'validation':77,'test':77}
    assert not set(s['train']) & set(s['test'])
    assert not set(s['validation']) & set(s['test'])
    assert np.array_equal(np.sort(np.concatenate(list(s.values()))),np.arange(512))
    assert np.array_equal(splits(config)['test'],s['test'])


def test_recompute_metrics_and_units():
    row=dict(material='fixture',method='P3',seed=0,q_fit=[.1,.2],q_true_posthoc=[.3,.5],
      lattice_abs_error_angstrom=[.008,.024],seconds=3.,rmse=.02,success=False,boundary_hit=True,nfev=30,multistart_disagreement=.7)
    other=copy.deepcopy(row); other.update(q_fit=[.3,.5],seconds=1.,success=True,boundary_hit=False)
    r=summarize([row,other])[0]
    assert np.isclose(r['q_mae'],.125)
    assert np.allclose(r['lattice_mae_angstrom'],[.008,.024])
    assert r['convergence_rate']==.5 and r['boundary_rate']==.5
    assert r['mean_seconds']==2. and r['n']==2
    assert r['mean_nfev']==30


def test_cpu_pipeline_fixture(tmp_path,monkeypatch):
    """Engineering fixture only; no research CIF or held-out pilot data."""
    import torch
    from pxrd_cross_material_autolab import experiment as ex
    from pxrd_cross_material_autolab.manager import atomic
    class Fixture:
        def __init__(self,*args,**kwargs): self.ndim=1; self.grid=np.linspace(0,1,32)
        def profile(self,q,eta): return .3+.1*np.cos(self.grid*4+q[0])
        def lattice(self,q): return 4*(1+.02*np.asarray(q))
        def fit(self,y,start,**kwargs):
            return dict(q=list(np.asarray(start,dtype=float)),eta=[0,.32,1,.02,0],rmse=.03,nfev=4,nit=1,success=False,message='fixture failure retained',seconds=.001,boundary_hit=False)
    monkeypatch.setattr(ex,'PowderModel',Fixture)
    monkeypatch.setattr(torch.cuda,'is_available',lambda:False)
    monkeypatch.setattr(torch.cuda,'manual_seed_all',lambda x:None)
    out=tmp_path/'materials'/'fixture'/'attempt_1'; out.mkdir(parents=True)
    import time
    atomic(tmp_path/'budget.json',dict(pilot_started=time.time(),gpu_training_seconds=0))
    config=dict(data=dict(parents=12,train=8,validation=2,test=2,parent_seed=91,split_seed=92,nuisance_seed=93,noise_seed=94),training=dict(seeds=[95],epochs=1,batch_size=4,lr=.001))
    result=ex.run_material(dict(id='fixture',cif_path='unused'),config,out)
    assert result['status']=='PASS' and result['gpu_training_seconds']==0
    assert (out/'test_opened.json').exists()
    assert len(result['summary'])==6
    assert all(r['convergence_rate']==0 for r in result['summary'])
    assert len((out/'per_sample.jsonl').read_text().splitlines())==12
    assert result['decision']=='NEGATIVE FOR NEURAL INCREMENTAL VALUE'

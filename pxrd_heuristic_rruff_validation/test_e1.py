import inspect
import numpy as np
from pxrd_heuristic_rruff_validation import e1
from pxrd_heuristic_rruff_validation.delivery import _e1_write_only_if_recomputed_bytes_match

def test_heuristic_no_label_interface():
 assert list(inspect.signature(e1.h1).parameters)==['model','observed']
 class Model:
  ndim=1
  grid=np.linspace(15,85,1024)
  def peaks(self,q):return np.array([30.+q[0],45.,60.]),np.array([1.,.5,.2])
 m=Model();y=np.exp(-((m.grid-30.4)/.1)**2)
 assert np.allclose(e1.h1(m,y),[.4])

def test_original_private_integrity_and_parent_disjointness():
 original_writer=e1.write
 try:
  e1.write=_e1_write_only_if_recomputed_bytes_match
  assert e1.audit()['status']=='PASS'
 finally:
  e1.write=original_writer
 cfg=e1.read(e1.OLD/'pxrd_cross_material_autolab/runs/pilot_20261019/config.json');s=e1.splits(cfg)
 assert not set(s['train'])&set(s['test'])
 assert not set(s['validation'])&set(s['test'])

def test_expired_wall_returns_no_unbudgeted_fit():
 class Model:
  q_bounds=[(-1,1)];eta_bounds=[(-1,1)]
 assert e1.wall_fit(Model(),None,[np.zeros(1)],0)==[]

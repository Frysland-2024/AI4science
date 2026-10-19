"""Engineering fixtures only: no registered stress parents or trained weights."""
from pathlib import Path
import numpy as np
import pytest
from pxrd_cross_material_autolab.physics import PowderModel,ETA_NEUTRAL
from pxrd_cross_material_autolab.stress.run import render,noise,draw_parameters,resolve_primary

CIF=Path(__file__).parents[1]/'materials'/'MgO_COD_9000505.cif'

def test_independent_gaussian_renderer_fixture():
 m=PowderModel(CIF,512); q=np.zeros(m.ndim)
 assert np.allclose(render(m,q,ETA_NEUTRAL,0.,0.),m.profile(q,ETA_NEUTRAL),atol=1e-12)
 mismatch=render(m,q,ETA_NEUTRAL)
 assert np.all(np.isfinite(mismatch))
 assert not np.allclose(mismatch,m.profile(q,ETA_NEUTRAL))

def test_engineering_seed_fixture():
 fixture={'parents_per_material':3,'parent_seed':11,'nuisance_seed':12,'noise_seed':13}
 q,e,seed=draw_parameters('fixture_only',fixture,2); q2,e2,seed2=draw_parameters('fixture_only',fixture,2)
 assert np.array_equal(q,q2) and np.array_equal(e,e2) and seed==seed2
 assert np.all(abs(q)<=.8)
 assert np.array_equal(noise(np.ones(16),22,0),noise(np.ones(16),22,0))
 assert not np.array_equal(noise(np.ones(16),22,0),noise(np.ones(16),22,1))

def test_refuse_active_primary(tmp_path):
 (tmp_path/'manager.lock').write_text('fixture')
 with pytest.raises(RuntimeError,match='lock'): resolve_primary(tmp_path,{})

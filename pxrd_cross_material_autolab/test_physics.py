"""CPU checks against independent crystallographic reference and optimizer invariants."""
from pathlib import Path
import numpy as np
import pytest
from pxrd_cross_material_autolab.physics import PowderModel, gate, ETA_NEUTRAL
ROOT=Path(__file__).parent/'materials'
@pytest.mark.parametrize('name',['BaTiO3_COD_9014273_P4mm.cif','MgO_COD_9000505.cif','CeO2_COD_9009008.cif'])
def test_physical_gates(name):
 m=PowderModel(ROOT/name,512)
 result=gate(m)
 assert result['status']=='PASS',result
 assert np.allclose(m.lattice(np.zeros(m.ndim)),m.q0)
 assert np.allclose(m.lattice(np.ones(m.ndim)),1.02*m.q0)

def test_nonoracle_optimizer_and_units():
 m=PowderModel(ROOT/'MgO_COD_9000505.cif',512)
 q=np.array([.27]); y=m.profile(q,ETA_NEUTRAL)
 a=m.fit(y,[0.]); b=m.fit(y,[-.35])
 assert a['rmse']<.003 and b['rmse']<.003
 assert abs(a['q'][0]-q[0])<.01
 assert a['nfev']>0 and b['seconds']>0
 pos,i=m.peaks([0]); pos2,i2=m.peaks([.5])
 assert np.all(pos2<pos)
 assert not np.allclose(i/i.max(),i2/i2.max(),rtol=1e-8,atol=1e-8)

def test_symmetry_preserved():
 m=PowderModel(ROOT/'BaTiO3_COD_9014273_P4mm.cif')
 s=m.structure_at([.3,-.2])
 assert s.lattice.a==pytest.approx(s.lattice.b)
 assert s.lattice.alpha==pytest.approx(90)
 assert not np.allclose(m.profile([.3,-.2]),m.profile([-.2,.3]))

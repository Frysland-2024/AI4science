"""Independent arithmetic verification of final E1 records, no optimization."""
import json
from pathlib import Path
import numpy as np
from pymatgen.core import Structure
from . import e1

def verify():
    cfg=e1.read(e1.OLD/'pxrd_cross_material_autolab/runs/pilot_20261019/config.json')
    count=0
    for mid in e1.IDS:
        material=next(m for m in cfg['materials'] if m['id']==mid)
        structure=Structure.from_file(e1.ROOT.parent/material['cif_path'])
        q0=np.array([structure.lattice.a] if mid in ('mgo','ceo2','silicon','grossular') else [structure.lattice.a,structure.lattice.c])
        rows=[json.loads(line) for line in (e1.OUT/f'{mid}.jsonl').read_text(encoding='utf-8').splitlines()]
        assert len(rows)==1068
        parents=set(e1.splits(cfg)['test'].tolist())
        for row in rows:
            assert row['parent'] in parents
            assert np.allclose(np.abs(np.array(row['q_fit'])-row['q_true_posthoc'])*.02*q0,row['lattice_abs_error_angstrom'],rtol=1e-8,atol=1e-12)
            best=min(row['attempts'],key=lambda f:f['rmse'])
            assert best['q']==row['q_fit'] and best['rmse']==row['rmse']
            assert row['nfev']==sum(f['nfev'] for f in row['attempts'])
            assert row['iterations']==sum(f['nit'] for f in row['attempts'])
            assert row['seconds']>=row['initializer_seconds']>=0
            assert row['success']==best['success'] and row['boundary_hit']==best['boundary_hit']
        count+=len(rows)
    return {'arithmetic':'PASS','rows':count,'no_refitting':True}

if __name__=='__main__':print(json.dumps(verify()))

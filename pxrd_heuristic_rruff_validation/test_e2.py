from pathlib import Path

from pxrd_heuristic_rruff_validation import e2, e2_verify
from pxrd_heuristic_rruff_validation.e2_verify import verify

def test_measured_provenance_and_gate_recomputation():
    out=verify()
    assert len(out['records'])==3
    assert all(r['status']=='PHYSICS_NOT_READY' for r in out['records'])


def test_e2_report_is_readable_and_preserves_not_run_outcome():
    e2_verify.report()
    report=(e2.REPORT/'RRUFF_REAL_RESULTS.md').read_text(encoding='utf-8')
    assert 'PHYSICS_NOT_READY' in report
    assert 'NN_NOT_RUN' in report
    assert '三条谱均未通过多起点稳定性' in report
    assert '????????' not in report

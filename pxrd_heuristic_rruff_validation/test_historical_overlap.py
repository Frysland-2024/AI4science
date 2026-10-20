from pxrd_heuristic_rruff_validation.historical_overlap import audit

def test_real_cases_preserve_historical_roles():
    result=audit()
    records={r['base_id']:r for r in result['records']}
    assert records['R050031']['historical_rruff301_role']=='locked_test'
    assert records['R050417']['historical_rruff301_role']=='locked_test'
    assert not result['frozen_classification_data_modified']
    assert not result['untouched_new_classification_holdout_claim']

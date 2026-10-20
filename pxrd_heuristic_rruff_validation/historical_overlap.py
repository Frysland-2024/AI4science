"""Record related base IDs against historical frozen classification roles."""
import csv,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OLD=Path('E:/AI4science/xrd_robustness/data/real_xrd/rruff371')

def audit():
    split=OLD/'splits/rruff301_adaptation_test_split.csv'
    master=OLD/'manifests/rruff371_master_manifest.csv'
    roles={r['rruff_id']:r['split'] for r in csv.DictReader(split.open(encoding='utf-8-sig'))}
    all_ids={r['rruff_id'] for r in csv.DictReader(master.open(encoding='utf-8-sig'))}
    cfg=json.loads((ROOT/'e2_preregistration.json').read_text(encoding='utf-8'))
    records=[{'sample_id':sid,'base_id':sid.split('-')[0],
              'historical_rruff301_role':roles.get(sid.split('-')[0],'NOT_IN_RRUFF301'),
              'in_rruff371':sid.split('-')[0] in all_ids,
              'current_role':'physics-only descriptive case; no training or threshold tuning'} for sid in cfg['ids']]
    result={'source_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (split,master)},
            'records':records,'untouched_new_classification_holdout_claim':False,
            'frozen_classification_data_modified':False}
    (ROOT/'reports/historical_id_overlap.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result

if __name__=='__main__':
    print(json.dumps(audit(),ensure_ascii=False))

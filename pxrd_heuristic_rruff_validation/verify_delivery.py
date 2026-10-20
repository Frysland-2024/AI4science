"""Verify compact delivery artifact hashes without rewriting or refitting."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def verify():
    records=json.loads((ROOT/'reports/ARTIFACT_SHA256.json').read_text(encoding='utf-8'))
    for relative,digest in records.items():
        path=ROOT/relative
        assert path.is_file(),relative
        assert hashlib.sha256(path.read_bytes()).hexdigest()==digest,relative
    return {'artifact_hashes':'PASS','files':len(records),'no_writes':True}

if __name__=='__main__':print(json.dumps(verify()))

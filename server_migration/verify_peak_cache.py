#!/usr/bin/env python3
"""Check full V7 ideal-reflection caches and frozen 131729-record manifest."""
import argparse,csv,hashlib,json
from pathlib import Path

COUNTS={"train":108483,"validation":23246,"test":23246}
AGG={"train":"46123c2e145a1194df1945edf91762db602dc5ca54f36cdb77c0b7fd485c5bbc",
     "validation":"f43cbedf331228cb11294b7f6f1beed6bd82234649d53b57c2ede20ae4014da4",
     "test":"e851d5f207054af5f67d081cd3dc56ed3c44fc030c51622e0728d90bf96d3a71"}
EXPECTED_MANIFEST="7f169d555de18b4dd811e18a67196acee317733864a1232fa719a861104333dd"
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):h.update(block)
    return h.hexdigest()
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    ap.add_argument("--fast",action="store_true",help="check counts/manifests/filesizes, skip 154975 per-file SHA256")
    a=ap.parse_args()
    cache=a.root/"xrd_robustness/data/merged_154975_v11"
    manifest=cache/"training_records.v1.jsonl"
    if not manifest.is_file() or sha(manifest)!=EXPECTED_MANIFEST:
        raise SystemExit("BLOCKED: training manifest missing or modified")
    for split,expected in COUNTS.items():
        root=cache/split
        summary=root/"manifests/peak_cache_summary.v7.reflection.json"
        index=root/"manifests/peak_cache_manifest.v7.reflection.csv"
        if not summary.is_file() or not index.is_file():raise SystemExit("BLOCKED: missing cache summary/manifest")
        j=json.loads(summary.read_text(encoding="utf-8"))
        if j.get("status")!="completed" or j.get("completed_count")!=expected or j.get("skipped_count")!=0:
            raise SystemExit("BLOCKED: incomplete "+split+" cache")
        if j.get("aggregate_cache_sha256")!=AGG[split]:
            raise SystemExit("BLOCKED: frozen aggregate cache hash mismatch")
        if sha(index).lower()!=j["manifest_sha256"].lower():
            raise SystemExit("BLOCKED: cache index SHA mismatch")
        seen=set();count=0
        with index.open(encoding="utf-8",newline="") as file:
            for row in csv.DictReader(file):
                key=row["material_id"]
                if key in seen:raise SystemExit("BLOCKED: duplicate material "+key)
                seen.add(key)
                path=root/"mp_processed/peak_tables_v7_reflection"/(key+".npz")
                if not path.is_file():raise SystemExit("BLOCKED: missing "+str(path))
                if path.stat().st_size!=int(row["bytes"]):raise SystemExit("BLOCKED: cache size mismatch "+key)
                if not a.fast and sha(path).lower()!=row["sha256"].lower():
                    raise SystemExit("BLOCKED: cache SHA mismatch "+key)
                count+=1
        if count!=expected:raise SystemExit("BLOCKED: cache manifest count mismatch")
        print(f"PASS {split} {count:,} cached parent records; per-file SHA={not a.fast}",flush=True)
    print("FULL PEAKCACHE READINESS PASS; all 154975 records are PeakTables, NOT persistent spectra.")
if __name__=="__main__":main()

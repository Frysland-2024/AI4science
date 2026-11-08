#!/usr/bin/env python3
"""Validate privately transferred 154,975-record structure split (standard library only)."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
def sha256(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(4*1024*1024),b""):h.update(chunk)
    return h.hexdigest()
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument("--check-records",action="store_true")
    a=p.parse_args()
    source=a.root/"structure_library"/"merged_154975_parent_split_20261103"
    metadata=source/"delivery_validation.json"
    if not metadata.is_file():raise SystemExit("BLOCKED: missing delivery_validation.json. Unzip structure_shards.zip first.")
    data=json.loads(metadata.read_text(encoding="utf-8"))
    if data.get("status")!="passed" or data.get("material_id_records")!=154975:raise SystemExit("BLOCKED: unexpected delivery metadata")
    expected=data["row_counts_by_split"]
    if expected!={"train":108483,"validation":23246,"test":23246}:raise SystemExit(f"BLOCKED split counts: {expected}")
    for name,digest in data["sha256"].items():
        item=source/name
        if not item.is_file():raise SystemExit(f"BLOCKED missing {item}")
        actual=sha256(item)
        if actual.lower()!=digest.lower():raise SystemExit(f"BLOCKED SHA256 mismatch {name}: {actual}")
        print(f"PASS SHA256 {name} ({item.stat().st_size:,} bytes)",flush=True)
    if a.check_records:
        seen_ids=set(); seen_parents={}
        for split,number in expected.items():
            num=0
            with gzip.open(source/f"{split}_structures.jsonl.gz","rt",encoding="utf-8") as f:
                for line in f:
                    if not line.strip():continue
                    row=json.loads(line)
                    key=str(row.get("material_id","")); parent=str(row.get("parent_structure_id",""))
                    if not key or not parent or key in seen_ids or row.get("split")!=split:raise SystemExit(f"BLOCKED ID/split at {split}/{num}")
                    earlier=seen_parents.setdefault(parent,split)
                    if earlier!=split:raise SystemExit(f"BLOCKED cross-split parent leakage {parent}")
                    seen_ids.add(key);num+=1
            if num!=number:raise SystemExit(f"BLOCKED count {split}: {num} != {number}")
            print(f"PASS rows {split}: {num:,}")
        if len(seen_parents)!=154968:raise SystemExit(f"BLOCKED canonical group count {len(seen_parents)}")
        print(f"PASS {len(seen_ids):,} records / {len(seen_parents):,} canonical parent groups")
    print("MIGRATION DATA INTEGRITY: PASS. This does not validate full PeakTable generation or training.")
if __name__=="__main__":main()

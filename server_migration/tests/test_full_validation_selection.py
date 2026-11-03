import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

script=Path(__file__).resolve().parents[1]/"one_click_v11.py"
spec=importlib.util.spec_from_file_location("v11full",script)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class ValidationSelection(unittest.TestCase):
    def fixture(self,root):
        rows=[];recs=[]
        for i in range(7):
            for split in ("train","validation"):
                mid=f"{split}_{i:02d}"
                rows.append({"material_id":mid,"split":split,"label":i,
                             "parent_structure_id":f"{split}_parent_{i}"})
                recs.append(SimpleNamespace(material_id=mid,split=split,label=i))
        rows.append({"material_id":"validation_03_alias","split":"validation","label":3,
                     "parent_structure_id":"validation_parent_3"})
        recs.append(SimpleNamespace(material_id="validation_03_alias",split="validation",label=3))
        p=root/"rows.jsonl"
        self.save(p,rows)
        return p,rows,recs

    def save(self,path,rows):
        path.write_text("".join(json.dumps(row)+"\n" for row in rows),encoding="utf-8")

    def select(self,path,recs):
        return mod.full_parent_disjoint_records(path,recs,
            expected_rows={"train":7,"validation":8},
            expected_parents={"train":7,"validation":7})

    def test_full_coverage_dedup_hash_repeat(self):
        with tempfile.TemporaryDirectory() as tmp:
            path,rows,recs=self.fixture(Path(tmp))
            train,val,audit=self.select(path,recs)
            self.assertEqual(len(train),7)
            self.assertEqual(len(val),7)
            self.assertEqual({r.label for r in val},set(range(7)))
            self.assertEqual(audit["deduplicated_aliases"]["validation"],1)
            self.assertEqual(audit["validation_mode"],"FULL_PARENT_DISJOINT")
            self.assertIn("validation_03",{r.material_id for r in val})
            self.assertEqual(audit["frozen_parent_mapping_sha256"],
                             self.select(path,recs)[2]["frozen_parent_mapping_sha256"])

    def test_parent_leakage_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path,rows,recs=self.fixture(Path(tmp))
            rows[9]["parent_structure_id"]="train_parent_1"
            self.save(path,rows)
            with self.assertRaisesRegex(ValueError,"Cross-split parent"):
                self.select(path,recs)

    def test_alias_label_conflict_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path,rows,recs=self.fixture(Path(tmp))
            rows[-1]["label"]=4
            recs[-1].label=4
            self.save(path,rows)
            with self.assertRaisesRegex(ValueError,"Conflicting labels"):
                self.select(path,recs)

    def test_missing_rows_rejected_not_resampled(self):
        with tempfile.TemporaryDirectory() as tmp:
            path,rows,recs=self.fixture(Path(tmp))
            rows.pop(0);recs.pop(0)
            self.save(path,rows)
            with self.assertRaisesRegex(ValueError,"Frozen split row count"):
                self.select(path,recs)

if __name__=="__main__":
    unittest.main()

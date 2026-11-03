"""Optional full Validation ZIP only ships independently audited and complete panels."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
import sys,tempfile,unittest,zipfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from package_validation_panels import PROFILES,ARCHIVE_PREFIX,package

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

class OptionalValidationBundleTest(unittest.TestCase):
    def test_small_complete_bundle_integrity_and_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            work=Path(temp)
            panels=work/"panels"; panels.mkdir()
            entries={}
            for i,name in enumerate(PROFILES):
                files=[]
                for view in ("first","second"):
                    p=panels/(name+"."+view+".npy")
                    np.save(p,np.full((2,3501),i/7,dtype=np.float32))
                    files.append(sha(p))
                entries[name]={"profile":name,"n_parents":2,"sha256":files}
            index={
                "identity":{
                    "version":"v11-full-validation-dual-view-cache-v1",
                    "parent_count":2,"profiles":list(PROFILES),
                },
                "entries":entries,
            }
            (panels/"panel_index.json").write_text(json.dumps(index),encoding="utf-8")
            archive=work/"validation_panel_bundle.zip"
            res=package(panels,archive,expected_parents=2)
            self.assertEqual(res["status"],"PASS")
            with zipfile.ZipFile(archive) as zipf:
                self.assertEqual(len(zipf.namelist()),13)
                self.assertTrue(all(name.startswith(ARCHIVE_PREFIX) for name in zipf.namelist()))
                self.assertEqual(zipf.namelist()[-1],ARCHIVE_PREFIX+"panel_index.json")
            bad=panels/(PROFILES[0]+".first.npy")
            bad.write_bytes(bad.read_bytes()+b"\x00")
            with self.assertRaisesRegex(ValueError,"Corrupt frozen panel SHA"):
                package(panels,work/"bad.zip",expected_parents=2)
            with self.assertRaisesRegex(ValueError,"identity"):
                package(panels,work/"badparents.zip",expected_parents=23245)

if __name__=="__main__":unittest.main()

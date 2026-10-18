"""Offline tests for preapproved GPU task bounds; no GPU execution."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from research_bridge import gpu_tasks as g
from research_bridge import worker as w

def make_task(**options):
    cfg={"preset":"forward_ab","approved_sha":"f"*40,
         "config":"pxrd_autolab/configs/forward_ab_pilot.yaml",
         "config_sha256":"e"*64,"run_id":"pilot_001","max_minutes":45}
    cfg.update(options)
    return {"number":100,"state":"open","title":"[Bridge GPU] Approved A/B run",
            "user":{"login":w.OWNER},
            "body":json.dumps(cfg),"labels":[{"name":w.READY},{"name":g.LABEL}]}

class GPUContractTests(unittest.TestCase):
    def test_owner_label_gate(self):
        i=make_task()
        self.assertTrue(g.eligible(i))
        self.assertFalse(g.eligible({**i,"user":{"login":"other"}}))
        self.assertFalse(g.eligible({**i,"labels":[{"name":g.LABEL}]}))
        self.assertFalse(g.eligible({**i,"labels":i["labels"]+[{"name":w.APPROVED}]}))
    def test_invalid_budget(self):
        for minutes in (-1,0,121,True,3.4):
            with self.subTest(minutes=minutes):
                with self.assertRaises(w.BridgeError):
                    g.parse(make_task(max_minutes=minutes))
    def test_invalid_commits_and_config_digests(self):
        for kw in [
            {"approved_sha":"not-a-commit"},
            {"config_sha256":"wrong"},
            {"config":"../../secret.json"},
            {"run_id":"../../windows"},
            {"preset":"arbitrary-shell"}
        ]:
            with self.subTest(kw=kw):
                with self.assertRaises(w.BridgeError):
                    g.parse(make_task(**kw))
    def test_dry_run_does_not_fetch_or_train(self):
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td)
            (repo/".git").mkdir()
            with patch.object(w,"revision") as rev, patch.object(w,"snapshot") as snap:
                g.run(repo,make_task(),dry_run=True)
                rev.assert_not_called()
                snap.assert_not_called()
    def test_preset_does_not_allow_frozen_v9(self):
        self.assertFalse(any(item.startswith("xrd_robustness/")
                             for item,_ in g.PRESETS.values()))
    def test_refuses_gpu_if_git_main_changed(self):
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td)
            (repo/".git").mkdir()
            with patch.object(w,"revision",return_value="a"*40):
                with self.assertRaises(w.BridgeError):
                    g.run(repo,make_task(),dry_run=False)

if __name__=="__main__":
    unittest.main()

import json, tempfile, unittest, types
from unittest.mock import patch
from pathlib import Path
from pxrd_cross_material_autolab import manager as m

class ManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name); self.root=self.base/"run"
        self.cif=self.base/"x.cif"; self.cif.write_text("public CIF")
        self.prereg=self.base/"PREREGISTRATION.md"; self.prereg.write_text("fixed physical gates")
        self.config={"materials":[{"id":"x","verified":True,"cif_path":str(self.cif),"cif_sha256":m.sha(self.cif)}]}
    def test_dry_run_resume_is_idempotent_and_test_unopened(self):
        result=m.run(self.root,self.config,self.prereg,dry=True)
        before=(self.root/"manifest.json").read_bytes()
        self.assertEqual(result["status"],"PASS")
        m.run(self.root,self.config,self.prereg,resume=True,dry=True)
        self.assertEqual(before,(self.root/"manifest.json").read_bytes())
        self.assertNotIn("test_authorization",(self.root/"events.jsonl").read_text(encoding="utf-8"))
    def test_frozen_config_changes_rejected(self):
        m.freeze(self.root,self.config,self.prereg)
        self.config["epochs"]=9
        with self.assertRaisesRegex(ValueError,"Frozen manifest"): m.freeze(self.root,self.config,self.prereg)
    def test_cif_and_preregistration_tampering_rejected(self):
        m.freeze(self.root,self.config,self.prereg)
        self.prereg.write_text("changed")
        with self.assertRaises(ValueError): m.verify(self.root)
        self.cif.write_text("changed")
        with self.assertRaises(ValueError): m.verify(self.root)
    def test_append_events_preserve_failed_history(self):
        m.stage(self.root,"fit","FAIL",reason="first")
        m.stage(self.root,"fit","PASS")
        events=[json.loads(x) for x in (self.root/"events.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual([e["status"] for e in events],["FAIL","PASS"])
    def test_lock_excludes_concurrent_manager(self):
        with m.lock(self.root):
            with self.assertRaises(RuntimeError):
                with m.lock(self.root): pass
    def test_budget_limits_and_safe_ids(self):
        self.config["training"]={"seeds":[1,2,3,4]}
        with self.assertRaises(ValueError): m.freeze(self.root,self.config,self.prereg)
        self.config.pop("training"); self.config["materials"][0]["id"]="../escape"
        with self.assertRaises(ValueError): m.freeze(self.root,self.config,self.prereg)
    def test_failed_gate_prevents_experiment_import_and_preserves_failure(self):
        fake=types.SimpleNamespace(PowderModel=lambda *a,**k: object(),gate=lambda model: {"status":"FAIL","checks":{"recovery":False}})
        hardware={"gpu_processes":{"exit_code":0,"stdout":""}}
        with patch.object(m,"inventory",return_value=hardware), patch.object(m.importlib,"import_module",return_value=fake) as importer:
            result=m.run(self.root,self.config,self.prereg)
        self.assertEqual(result["status"],"BLOCKED")
        self.assertEqual(importer.call_count,1)
        self.assertEqual(m.read(self.root/"materials/x/status.json")["status"],"SKIPPED")
        self.assertNotIn("test_authorization",(self.root/"events.jsonl").read_text(encoding="utf-8"))
    def test_success_resume_never_repeats_opened_test(self):
        physics=types.SimpleNamespace(PowderModel=lambda *a,**k: object(),gate=lambda model: {"status":"PASS"})
        calls=[]
        def experiment(material,config,directory):
            calls.append(material["id"])
            (directory/"per_sample.jsonl").write_text(json.dumps({"q_mae":0.01})+"\n",encoding="utf-8")
            return {"status":"PASS","gpu_training_seconds":0.1,"summary":[{"material":"x","method":"P3","q_mae":0.01}]}
        module=types.SimpleNamespace(run_material=experiment,summarize=lambda rows:[{"material":"x","method":"P3","q_mae":rows[0]["q_mae"]}])
        with patch.object(m,"inventory",return_value={"gpu_processes":{"exit_code":0,"stdout":""}}), patch.object(m.importlib,"import_module",side_effect=lambda name: physics if name.endswith("physics") else module):
            self.assertEqual(m.run(self.root,self.config,self.prereg)["status"],"PASS")
            self.assertEqual(m.run(self.root,self.config,self.prereg,resume=True)["status"],"PASS")
        self.assertEqual(calls,["x"])
        m.report(self.root)
        self.assertEqual(len(m.read(self.root/"reports/COMPARISON.json")),1)
    def test_interrupted_attempt_blocks_automatic_retry(self):
        m.freeze(self.root,self.config,self.prereg)
        dest=self.root/"materials/x"; dest.mkdir(parents=True)
        m.atomic(dest/"physical_gate.json",{"status":"PASS"})
        m.stage(dest,"experiment","NOT_RUN",reason="Interrupted")
        with patch.object(m,"inventory",return_value={"gpu_processes":{"exit_code":0,"stdout":""}}), patch.object(m.importlib,"import_module") as importer:
            m.run(self.root,self.config,self.prereg,resume=True)
            importer.return_value.run_material.assert_not_called()
        self.assertEqual(m.read(dest/"status.json")["status"],"BLOCKED")

    def test_subprocess_failure_is_logged(self):
        result=m.command(self.root,["a_nonexistent_executable_for_autolab"])
        self.assertIsNone(result["exit_code"])
        self.assertIn("subprocess",(self.root/"events.jsonl").read_text(encoding="utf-8"))

if __name__=="__main__": unittest.main()

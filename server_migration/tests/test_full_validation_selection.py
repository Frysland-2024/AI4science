import importlib.util
import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
import types
from unittest import mock
from pathlib import Path
from types import SimpleNamespace

script=Path(__file__).resolve().parents[1]/"one_click_v11.py"
sys.path.insert(0,str(script.parent))
spec=importlib.util.spec_from_file_location("v11full",script)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class ValidationSelection(unittest.TestCase):
    def test_budget_only_payload_cache_transition_is_fail_closed(self):
        previous={
            "payload_contract_version":"v11-parent-epoch-microbatch-20261109.7",
            "render_source_sha256":{"physics":"unchanged-hash"},
            "source_manifest_sha256":"same-train-validation-manifest",
            "simulation_config_sha256":"same-simulator",
            "parent_count":23245,
            "profiles":["ood_noise","ood_texture"],
        }
        current={**previous,"payload_contract_version":"v11-parent-epoch-budget-20261109.8"}
        self.assertTrue(mod.legacy_validation_panel_identity_compatible(previous,current))
        self.assertFalse(mod.legacy_validation_panel_identity_compatible(
            {**previous,"render_source_sha256":{"physics":"changed"}},current))
        self.assertFalse(mod.legacy_validation_panel_identity_compatible(
            previous,{**current,"parent_count":23244}))
        self.assertFalse(mod.legacy_validation_panel_identity_compatible(
            previous,{**current,"simulation_config_sha256":"changed"}))
        self.assertFalse(mod.legacy_validation_panel_identity_compatible(
            {**previous,"payload_contract_version":"unexpected"},current))
        self.assertFalse(mod.legacy_validation_panel_identity_compatible(
            previous,{**current,"payload_contract_version":"v11-future"}))

    def test_reject_legacy_four_dim_hpo_schema(self):
        with self.assertRaisesRegex(ValueError,"lambda_js, middle_stride, kernel_size"):
            mod.resolve_v11_trial_params({
                "learning_rate":2e-4,"lambda_js":60.0,
                "weight_decay":1e-4,"scheduler":"cosine_5pct_floor"})

    def test_focused_v11_science_choices_and_fixed_training_recipe(self):
        self.assertEqual(list(mod.V11_ARCHITECTURES), ["A0","A1","A2","A3"])
        self.assertEqual(mod.V11_FIXED_OPTIMIZER,
                         {"learning_rate":2e-4,"weight_decay":1e-4,
                          "scheduler":"cosine_5pct_floor"})
        for architecture,(strides,kernel) in mod.V11_ARCHITECTURES.items():
            chosen=mod.v11_architecture_trial_params(architecture,60.0)
            resolved=mod.resolve_v11_trial_params(chosen)
            self.assertEqual(resolved["learning_rate"],2e-4)
            self.assertEqual(resolved["weight_decay"],1e-4)
            self.assertEqual(resolved["architecture"],architecture)
            self.assertEqual(len(chosen),3)
            from xrd_robustness.models.ml4pxrd_resnet1d import (
                ML4PXRDResNet1DConfig, ML4PXRDResNet1D)
            config=mod.v11_model_config(chosen,ML4PXRDResNet1DConfig)
            self.assertEqual(config.stage_transition_strides,strides)
            self.assertEqual(config.residual_kernel_size,kernel)
            model=ML4PXRDResNet1D(config)
            self.assertEqual(model.stages[2][0].conv1.stride,strides[1])
            self.assertEqual(model.stages[2][0].conv1.kernel_size,kernel)
            self.assertEqual(model.embedding.in_features,
                             model.final_channels*model.final_length)
        baseline=ML4PXRDResNet1D(ML4PXRDResNet1DConfig(model_id="18"))
        tuned=ML4PXRDResNet1D(mod.v11_model_config(
            mod.v11_architecture_trial_params("A0",60.0),ML4PXRDResNet1DConfig))
        self.assertEqual(baseline.parameter_count,13008839)
        self.assertEqual(baseline.parameter_count,tuned.parameter_count)
        for bad in ({"lambda_js":60.0,"middle_stride":3,"kernel_size":9},
                    {"lambda_js":60.0,"middle_stride":4,"kernel_size":9,"learning_rate":1e-4},
                    {"lambda_js":float("nan"),"middle_stride":4,"kernel_size":9},
                    {"lambda_js":200.0,"middle_stride":4,"kernel_size":9}):
            with self.assertRaises(ValueError):
                mod.resolve_v11_trial_params(bad)

    def test_cached_validation_panels_reuse_after_training_only_version_bump(self):
        old={"payload_contract_version":"v11-parent-epoch-microbatch-20261109.7",
             "render_source_sha256":{"physics":"same"},"parent_count":23245}
        new={**old,"payload_contract_version":"v11-focused-science-cpu-20261109.9"}
        self.assertTrue(mod.legacy_validation_panel_identity_compatible(old,new))
        intermediate={**old,"payload_contract_version":"v11-parent-epoch-budget-20261109.8"}
        self.assertTrue(mod.legacy_validation_panel_identity_compatible(intermediate,new))
        self.assertFalse(mod.legacy_validation_panel_identity_compatible(
            {**old,"render_source_sha256":{"physics":"changed"}},new))

    def test_gradient_window_uses_v9_train_only_influence_bands(self):
        window=mod.derive_train_only_js_range(0.029235)
        self.assertAlmostEqual(window["low"],3.0,places=5)
        self.assertAlmostEqual(window["high"],2.0/0.029235,places=5)
        self.assertAlmostEqual(window["anchor"],60.0,places=5)
        for bad in (0.0,float("nan"),1e-12,1e5):
            with self.assertRaises(ValueError):
                mod.derive_train_only_js_range(bad)

    def test_three_knobs_and_gradient_bound_2x2_architecture_contrasts(self):
        gate={"lambda_window":{"low":5.0,"high":80.0}}
        good=mod.v11_architecture_trial_params("A2",60.0)
        self.assertTrue(mod.assert_gradient_lambda(good,gate))
        for bad in (4.0,81.0):
            with self.assertRaisesRegex(RuntimeError,"outside frozen"):
                mod.assert_gradient_lambda({**good,"lambda_js":bad},gate)
        controls=[types.SimpleNamespace(
            params=mod.v11_architecture_trial_params(arch,60.0),
            state="COMPLETE",value=score) for arch,score in
            [("A0",0.70),("A1",0.72),("A2",0.71),("A3",0.69)]]
        evidence=mod.architecture_peak_preservation_screen(
            controls,expected_lambda=60.0)
        self.assertAlmostEqual(evidence["stride_2_vs_4_at_kernel9"],0.02)
        self.assertAlmostEqual(evidence["kernel_5_vs_9_at_stride2"],-0.01)
        with self.assertRaisesRegex(RuntimeError,"not comparable"):
            mod.architecture_peak_preservation_screen(
                [*controls[:3],controls[0]],expected_lambda=60.0)

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

    def test_study_lock_rejects_same_process_reentry_and_releases(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock=Path(tmp)/"study.lock"
            with mod.exclusive_file_lock(lock):
                with self.assertRaisesRegex(RuntimeError,"already held"):
                    with mod.exclusive_file_lock(lock):
                        pass
                probe=(
                    "import sys\n"
                    "sys.path.insert(0,sys.argv[1])\n"
                    "from one_click_v11 import exclusive_file_lock\n"
                    "try:\n"
                    "    with exclusive_file_lock(sys.argv[2]): print('ACQUIRED')\n"
                    "except RuntimeError: print('BLOCKED')\n"
                )
                child=subprocess.run(
                    [sys.executable,"-c",probe,str(script.parent),str(lock)],
                    capture_output=True,text=True,timeout=10,check=True,
                )
                self.assertEqual(child.stdout.strip(),"BLOCKED")
            with mod.exclusive_file_lock(lock):
                self.assertTrue(lock.is_file())

    def test_completed_trial_reuse_checks_contract_and_checkpoint_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            study=Path(tmp)
            name="hpo_000"
            root=study/"trials"/name
            root.mkdir(parents=True)
            params={"lambda_js":60.0,"middle_stride":4,"kernel_size":9}
            args=SimpleNamespace(batch_size=16,eval_every=100)
            contract_sha="c"*64
            panel_sha="a"*64
            cfg={"params":params,"seed":123,"max_steps":100,
                 "batch_size":args.batch_size,"eval_every":args.eval_every,
                 "microbatch_size":16,"sampling_mode":"random_batch",
                 "sim_config_sha256":mod.digest(mod.XRD/"configs/simulation.v11_tch_pseudo_voigt.json"),
                 "validation_mode":"FULL_PARENT_DISJOINT","validation_parent_count":23245,
                 "training_parent_count":108478,"validation_panel_index_sha256":panel_sha,
                 "experiment_contract_sha256":contract_sha}
            (root/"contract.json").write_text(json.dumps(cfg),encoding="utf-8")
            best=b"chosen checkpoint";last=b"latest checkpoint"
            (root/"best.pt").write_bytes(best);(root/"last.pt").write_bytes(last)
            row={"status":"completed","name":name,"seed":123,"parameters":params,
                 "completed_steps":100,"validation_unique_parents":23245,
                 "profiles":list(mod.VALIDATION_OOD_PROFILES),
                 "best_validation_ood_macro_f1":0.71,
                 "best_checkpoint_sha256":__import__("hashlib").sha256(best).hexdigest(),
                 "last_checkpoint_sha256":__import__("hashlib").sha256(last).hexdigest()}
            (root/"result.json").write_text(json.dumps(row),encoding="utf-8")
            checked=mod.validate_completed_trial_artifacts(
                study,name,params,123,100,args,contract_sha,panel_sha,expected_score=0.71)
            self.assertEqual(checked["status"],"completed")
            (root/"best.pt").write_bytes(b"altered")
            with self.assertRaisesRegex(RuntimeError,"checkpoint hash mismatch"):
                mod.validate_completed_trial_artifacts(
                    study,name,params,123,100,args,contract_sha,panel_sha)

    def test_validation_panels_reuse_mmap_hashes_and_fail_closed_on_corruption(self):
        import numpy as np
        records=[SimpleNamespace(material_id=f"validation_{i}",label=i) for i in range(2)]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            fake_xrd=root/"xrd_robustness"
            cache=fake_xrd/"data"/"merged_154975_v11"
            config=fake_xrd/"configs"/"simulation.v11_tch_pseudo_voigt.json"
            (cache).mkdir(parents=True)
            config.parent.mkdir(parents=True)
            manifest=cache/"training_records.v1.jsonl"
            manifest.write_text("synthetic frozen manifest\n",encoding="utf-8")
            config.write_text("synthetic config\n",encoding="utf-8")
            study=root/"study"
            panel_root=study/"validation_panels_v11"
            panel_root.mkdir(parents=True)
            render_sources=(
                "server_migration/v11_prefetch.py",
                "server_migration/verify_peak_cache.py",
                "xrd_robustness/src/xrd_robustness/physics.py",
                "xrd_robustness/src/xrd_robustness/simulator_v11.py",
                "xrd_robustness/src/xrd_robustness/peak_cache.py",
                "xrd_robustness/src/xrd_robustness/training/runner.py",
            )
            cache_source={"manifest_sha256":"m"*64,"aggregate_cache_sha256":"a"*64}
            ids_sha=__import__("hashlib").sha256(
                "\n".join(record.material_id for record in records).encode("utf-8")
            ).hexdigest()
            identity={
                "version":"v11-full-validation-dual-view-cache-v1",
                "payload_contract_version":mod.PAYLOAD_CONTRACT_VERSION,
                "render_source_sha256":{name:"f"*64 for name in render_sources},
                "source_manifest_sha256":mod.digest(manifest),
                "validation_peak_cache_source":cache_source,
                "simulation_config_sha256":mod.digest(config),
                "parent_ids_sha256":ids_sha,"parent_count":2,
                "render_epoch":0,"render_step":0,"render_seed":20260721,
                "profiles":list(mod.VALIDATION_OOD_PROFILES),
                "data_shape":[2,3501],"dtype":"float32",
                "meaning":"simulated Validation only, no Test or RRUFF",
            }
            entries={}
            for index,profile in enumerate(mod.VALIDATION_OOD_PROFILES):
                paths=[panel_root/(profile+".first.npy"),panel_root/(profile+".second.npy")]
                np.save(paths[0],np.full((2,3501),index,dtype=np.float32))
                np.save(paths[1],np.full((2,3501),index+1,dtype=np.float32))
                entries[profile]={"sha256":[mod.digest(path) for path in paths],
                                  "n_parents":2,"profile":profile}
            index_path=panel_root/"panel_index.json"
            index_path.write_text(json.dumps({"identity":identity,"entries":entries}),encoding="utf-8")
            sim={"profiles":list(mod.VALIDATION_OOD_PROFILES)}
            libs=(np,None,None,None,None,None,None,None,None,object(),None)
            with mock.patch.object(mod,"XRD",fake_xrd), \
                 mock.patch.object(mod,"audit_validation_peak_inputs",return_value=cache_source), \
                 mock.patch.object(mod,"implementation_fingerprints",return_value={
                     name:"f"*64 for name in render_sources
                 }):
                panels,index_sha=mod.prepare_validation_panels(
                    records,{},sim,libs,study,expected_parents=2)
                self.assertEqual(index_sha,mod.canonical_digest(json.loads(index_path.read_text(encoding="utf-8"))))
                self.assertIsInstance(panels[mod.VALIDATION_OOD_PROFILES[0]][0],np.memmap)
                self.assertFalse(panels[mod.VALIDATION_OOD_PROFILES[0]][0].flags.writeable)
                del panels
                with mod.exclusive_file_lock(panel_root/".prepare.lock"):
                    with self.assertRaisesRegex(RuntimeError,"already held"):
                        mod.prepare_validation_panels(records,{},sim,libs,study,expected_parents=2)
                corrupted=panel_root/(mod.VALIDATION_OOD_PROFILES[0]+".first.npy")
                np.save(corrupted,np.full((2,3501),9,dtype=np.float32))
                with self.assertRaisesRegex(RuntimeError,"cache corrupted"):
                    mod.prepare_validation_panels(records,{},sim,libs,study,expected_parents=2)

    def test_final_gate_matches_complete_optuna_trials_and_confirmations(self):
        with tempfile.TemporaryDirectory() as tmp:
            study=Path(tmp)
            args=SimpleNamespace(batch_size=16,eval_every=100,trials=2,
                                 hpo_steps=200,confirm_steps=300)
            params={"lambda_js":60.0,"middle_stride":4,"kernel_size":9}
            contract_obj={"hpo_seed":123,"confirmation_seeds":[201,202]}
            contract_file=study/"contract.json"
            contract_file.write_text(json.dumps(contract_obj),encoding="utf-8")
            gate_file=study/"gradient_gate.json"
            gradient_gate={"status":"TRAIN_ONLY_GRADIENT_GATE_PASS",
                           "contract_sha256":mod.canonical_digest(contract_obj),
                           "lambda_window":mod.derive_train_only_js_range(0.029235)}
            gate_file.write_text(json.dumps(gradient_gate),encoding="utf-8")
            gate_sha=mod.digest(gate_file)
            panel_index=study/"validation_panels_v11"/"panel_index.json"
            panel_index.parent.mkdir(parents=True)
            panel_index.write_text("{\"frozen\":true}\n",encoding="utf-8")
            panel_sha=mod.canonical_digest(json.loads(panel_index.read_text(encoding="utf-8")))
            contract_sha=mod.digest(contract_file)
            sim_sha=mod.digest(mod.XRD/"configs/simulation.v11_tch_pseudo_voigt.json")

            def save_trial(name,seed,steps,score,*,checkpoints=True):
                root=study/"trials"/name
                root.mkdir(parents=True)
                hashes={}
                for filename,contents in (("best.pt",name+" best"),("last.pt",name+" last")):
                    data=contents.encode("utf-8")
                    hashes[filename]=hashlib.sha256(data).hexdigest()
                    if checkpoints:
                        (root/filename).write_bytes(data)
                cfg={"params":params,"seed":seed,"max_steps":steps,
                     "batch_size":args.batch_size,"eval_every":args.eval_every,
                 "microbatch_size":16,"sampling_mode":"random_batch",
                     "sim_config_sha256":sim_sha,"validation_mode":"FULL_PARENT_DISJOINT",
                     "validation_parent_count":23245,"training_parent_count":108478,
                     "validation_panel_index_sha256":panel_sha,
                     "experiment_contract_sha256":mod.canonical_digest(contract_obj)}
                (root/"contract.json").write_text(json.dumps(cfg),encoding="utf-8")
                row={"status":"completed","name":name,"seed":seed,"parameters":params,
                     "completed_steps":steps,"validation_unique_parents":23245,
                     "profiles":list(mod.VALIDATION_OOD_PROFILES),
                     "best_validation_ood_macro_f1":score,
                     "best_checkpoint_sha256":hashes["best.pt"],
                     "last_checkpoint_sha256":hashes["last.pt"]}
                (root/"result.json").write_text(json.dumps(row),encoding="utf-8")
                return row

            hpo_rows=[
                save_trial("hpo_000",123,args.hpo_steps,0.75),
                save_trial("hpo_001",123,args.hpo_steps,0.70,checkpoints=False),
            ]
            confirmations=[]
            for seed,score in ((201,0.72),(202,0.73)):
                row=save_trial(f"confirm_{seed}",seed,args.confirm_steps,score)
                confirmations.append({"seed":seed,"score":score,
                                     "checkpoint_sha256":row["best_checkpoint_sha256"]})
            rec={"status":"hpo_and_confirmation_completed","contract_sha256":contract_sha,
                 "hpo_trial_count":2,"validation_panel_index_sha256":panel_sha,
                 "best_hpo_trial":0,"recommended_hyperparameters":params,
                 "gradient_gate_sha256":gate_sha,
                 "lambda_window":gradient_gate["lambda_window"],
                 "best_hpo_validation_ood_f1":0.75,"confirmation":confirmations}
            (study/"final_recommendation.json").write_text(json.dumps(rec),encoding="utf-8")

            class TrialState:
                COMPLETE="COMPLETE"
            optuna=types.ModuleType("optuna")
            optuna_trial=types.ModuleType("optuna.trial")
            optuna_trial.TrialState=TrialState
            optuna.trial=optuna_trial
            trials=[
                SimpleNamespace(number=0,state=TrialState.COMPLETE,params=params,value=0.75),
                SimpleNamespace(number=1,state=TrialState.COMPLETE,params=params,value=0.70),
            ]
            optuna.load_study=lambda **kwargs:SimpleNamespace(
                trials=trials,user_attrs={"gradient_gate_sha256":gate_sha})
            with mock.patch.dict(sys.modules,{"optuna":optuna,"optuna.trial":optuna_trial}):
                recommendation,selected,verified_panel=mod.validate_final_recommendation(
                    study,args,contract_file,contract_obj)
                self.assertEqual(recommendation["status"],"hpo_and_confirmation_completed")
                self.assertEqual(selected,params)
                self.assertEqual(verified_panel,panel_sha)
                # Imported Windows handoff initially has only the frozen index.
                # Cloud final validates the regenerated index identity afterward.
                panel_index.unlink()
                _,_,cloud_panel=mod.validate_final_recommendation(
                    study,args,contract_file,contract_obj,prepared_panel_sha=panel_sha)
                self.assertEqual(cloud_panel,panel_sha)
                with self.assertRaisesRegex(RuntimeError,"Validation panel hash mismatch"):
                    mod.validate_final_recommendation(
                        study,args,contract_file,contract_obj,prepared_panel_sha="0"*64)
                trials[1].state="FAIL"
                with self.assertRaisesRegex(RuntimeError,"every requested Optuna trial"):
                    mod.validate_final_recommendation(
                        study,args,contract_file,contract_obj,prepared_panel_sha=panel_sha)

if __name__=="__main__":
    unittest.main()

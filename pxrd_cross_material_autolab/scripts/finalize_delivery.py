"""Seal reporting and decision records from immutable completed trial outputs."""
from pathlib import Path
import json, csv, time, hashlib
import numpy as np
from pxrd_cross_material_autolab.manager import read,atomic,sha
BASE=Path('pxrd_cross_material_autolab'); ROOT=BASE/'runs/pilot_20261019'; OUT=BASE/'reports'; STRESS=BASE/'stress/results_20261019'
status=read(OUT/'status.json'); supplement=read(STRESS/'status.json'); ledger=read(ROOT/'budget.json')
summary=read(STRESS/'COMPARISON.json'); lines=['|Stress material (n=16)|P0 q-MAE|P3 q-MAE|N+A q-MAE mean|','|---|---:|---:|---:|']
for mid in json.loads((BASE/'stress/config.json').read_text(encoding='utf-8-sig'))['materials']:
    group=[r for r in summary if r['material']==mid]; p0=next(r for r in group if r['method']=='P0'); p3=next(r for r in group if r['method']=='P3'); ns=[r for r in group if r['method']=='N+A']
    lines.append(f"|{mid}|{p0['q_mae']:.6g}|{p3['q_mae']:.6g}|{np.mean([r['q_mae'] for r in ns]):.6g}|")
wall=supplement['finished']-ledger['pilot_started']
text=(BASE/'scripts/report_supplement.md').read_text(encoding='utf-8-sig').format(stress_table='\n'.join(lines),stress_seconds=supplement['elapsed_seconds'],total_wall_seconds=wall)
with (OUT/'OVERVIEW.md').open('a',encoding='utf-8') as f: f.write(text)
status['stress']={'status':supplement['status'],'registered_after_primary_opened':True,'new_parents':112,'training_added':False,'seconds':supplement['elapsed_seconds'],'metrics_recomputation':'PASS','total_global_wall_seconds':wall}
status['runtime']['primary_and_stress_disk_bytes']=sum(p.stat().st_size for directory in [ROOT,STRESS] for p in directory.rglob('*') if p.is_file())
status['runtime']['primary_and_stress_method_rows']=5950
atomic(OUT/'status.json',status)
validation=read(OUT/'validation.json'); validation['report_generation_retries']=1; validation['stress_verification']='PASS'; validation['stress_registered_after_primary_opened']=True; atomic(OUT/'validation.json',validation)
failures={}; total_rows=0; total_fits=0
for kind,paths in [('primary',ROOT.glob('materials/*/attempt_*/per_sample.jsonl')),('stress',STRESS.glob('*/per_sample.jsonl'))]:
    groups={}
    for path in paths:
        for line in path.read_text().splitlines():
            row=json.loads(line); total_rows+=1; total_fits+=len(row['attempts']); key=(row['material'],row['method'])
            if key not in groups: groups[key]={'rows':0,'selected_nonconverged':0,'any_attempt_nonconverged':0,'nonconverged_attempts':0,'boundary_rows':0}
            g=groups[key]; g['rows']+=1; g['selected_nonconverged']+=int(not row['success']); g['nonconverged_attempts']+=sum(not f['success'] for f in row['attempts']); g['any_attempt_nonconverged']+=int(any(not f['success'] for f in row['attempts'])); g['boundary_rows']+=int(row['boundary_hit'])
    failures[kind]=[dict(material=k[0],method=k[1],**v) for k,v in groups.items()]
failures['record_count']=total_rows; failures['optimizer_attempt_count']=total_fits
atomic(OUT/'FAILURES.json',failures)
assert total_rows==5950 and total_fits==8330
atomic(OUT/'EXECUTION.json',{'python':'C:/Users/Lenovo/.codex/venvs/issue19-measurement-closure/Scripts/python.exe','commands':[{'command':'python -m pytest pxrd_cross_material_autolab -q -p no:cacheprovider (primary stage)','exit_code':0,'passed':18},{'command':'python -m pytest pxrd_cross_material_autolab/stress/test_stress.py -q -p no:cacheprovider','exit_code':0,'passed':3},{'command':'python -m pxrd_cross_material_autolab dry-run','exit_code':0},{'command':'python -m pxrd_cross_material_autolab run --resume','tool_wrapper_exit_code':1,'manager_status':'BLOCKED','reason':'Two predeclared unsupported trigonal candidates SKIPPED; seven experiments PASS','manager_main_return_code':2},{'command':'python -m pxrd_cross_material_autolab.stress.run --primary pxrd_cross_material_autolab/runs/pilot_20261019 --output pxrd_cross_material_autolab/stress/results_20261019','exit_code':0},{'command':'python -m pxrd_cross_material_autolab.stress.run --verify --output pxrd_cross_material_autolab/stress/results_20261019','exit_code':0},{'command':'python -m pxrd_cross_material_autolab.scripts.build_delivery','exit_code':0}],'no_research_retry':True,'no_other_process_stopped':True,'source_code_not_changed_after_primary_freeze':True})
for name,note in [('docs/CURRENT_STATE.md',f'''

### 2026-10-19: bounded cross-material synthetic neural-initialization AutoLab

Separate pilot status: **PARTIAL coverage / supported subset COMPLETED**. A runnable immutable-manifest manager and verified CIF-specific physical forward now exist in `pxrd_cross_material_autolab/`. Twelve source identities attempted, nine CIF identities verified, seven physical gates passed and were trained/evaluated (BaTiO3, MgO, CeO2, rutile, ZnO, Si, grossular; three crystal systems). Calcite/corundum trigonal parameterizations were skipped, two wrong source IDs and one failed download preserved.

Completed 21 independent per-material MLP models (three seeds,24 epochs max), seven paired77-parent tests (539 synthetic parameter parents), and a separately registered post-primary independent-renderer mismatch stress on112 new parents. Primary wall {status['runtime']['wall_seconds']:.2f}s; CUDA training/validation wall20.4141s; global wall through stress {wall:.2f}s. Raw method records5950, optimizer attempts8330. Eighteen primary CPU tests plus three stress engineering checks pass; saved metrics/hash verification passes. No frozen gate, primary test or model selection was changed after opening.

All seven meet the preregistered runtime-Pareto rule **against the complete P3 cost**, with almost equal final accuracy; this is not an accuracy/reliability improvement over strong multi-start physics. P0 is already sufficient on five materials; MgO and ZnO show larger P0 errors in the primary samples. The16-parent/material exploratory mismatch stress shows no extra neural accuracy/reliability gain over P0/P3. Training cost, equal-evaluation-ceiling sensitivity, failures and unsupported cases remain explicit. No material zero-shot transfer, experimental-XRD validity, or resolution of historical real-Garnet failures is established. This q coordinate is a new linear relative-cell parameterization, not directly comparable with old du/dv MAE.

This separate pilot does not alter the completed seven-system JS classification project or its frozen results. Evidence: [AutoLab overview](../pxrd_cross_material_autolab/reports/OVERVIEW.md), [status](../pxrd_cross_material_autolab/reports/status.json), [preregistration](../pxrd_cross_material_autolab/PREREGISTRATION.md), [source audit](../pxrd_cross_material_autolab/source_audit.json). Draft PR43 remains unmerged.
'''),('docs/PROJECT_HISTORY.md',f'''

## 2026-10-19: bounded cross-material neural-start versus physics-only AutoLab

Date:2026-10-19. Question/previous assumption: single-CIF initialized refinement was accurate, but no fair multi-material comparison with strong physics-only restarts had established incremental neural value.

New evidence: seven public, identity-verified CIF templates pass new preregistered symmetry/structure-factor/parity/Jacobian/non-oracle recovery gates. Three seeds/material,358/77/77 independent parameter-parent splits, at most24 epochs, identical bounded L-BFGS-B, P0/P3/N+A and equal-evaluation-ceiling sensitivity completed. All seven primary runtime-Pareto flags refer specifically to P3; parameter accuracy is nearly identical. Five materials already have sufficient P0 accuracy, while MgO/ZnO have larger primary P0 errors despite optimizer success. A separately registered exploratory renderer/peak-shape/background mismatch evaluation uses112 NEW parents after the primary opened, no retraining and no replacement of primary results; no neural accuracy/reliability increment appears there. Costs:20.4141s CUDA training/validation wall,991.2876s primary wall,{wall:.2f}s global through stress. All5950 method records/8330 optimizer attempts and failures are retained;21 engineering tests and metric/hash audits pass.

Decision: retain the useful validated experimental manager and material-specific initialization/runtime evidence; do not claim a new reconstruction-loss win, universal neural superiority, real-XRD validation or zero-shot material transfer. Record practical P0 sufficiency and negative accuracy findings alongside P3-relative runtime flags. Twelve source candidates, nine verified identities, seven supported trials: unsupported trigonal cases and failed sources remain visible rather than silently removed.

What changes now: an executable isolated AutoLab, public provenance, preregistration, per-material curves/results/timing, failure logs and reports now replace the earlier automation-only proposal for this bounded synthetic pilot. What does NOT change: main JS-only classification, existing frozen datasets/checkpoints/results, historical inversion gates and real-Garnet failures. No gate relaxation or primary test re-selection occurred. Current q units differ from historical du/dv.

Status: CLOSED for this bounded run; PARTIAL material coverage, supported subset COMPLETED. Files:[overview](../pxrd_cross_material_autolab/reports/OVERVIEW.md),[frozen manifest](../pxrd_cross_material_autolab/runs/pilot_20261019/manifest.json),[source audit](../pxrd_cross_material_autolab/source_audit.json),[exploratory stress](../pxrd_cross_material_autolab/stress/PREREGISTRATION.md). Source implementation snapshot efd4576; exact executed raw-byte source hashes in manifest; branch `codex/pxrd-cross-material-autolab-20261019`, draft PR43, never merged.
''')]:
    p=Path(name); marker='bounded cross-material'
    if marker not in p.read_text(encoding='utf-8'):
        with p.open('a',encoding='utf-8') as f: f.write(note)
print(json.dumps({'primary_and_stress_rows':total_rows,'optimizer_attempts':total_fits,'global_wall_seconds':wall,'disk_bytes':status['runtime']['primary_and_stress_disk_bytes']},indent=2))

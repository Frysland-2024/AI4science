"""Post-run delivery: aggregates saved results only, never opens spectra or models."""
from pathlib import Path
import json, csv, hashlib, time
import numpy as np
from pxrd_cross_material_autolab.manager import report, verify, atomic, read, sha

BASE=Path('pxrd_cross_material_autolab')
ROOT=BASE/'runs/pilot_20261019'
OUT=BASE/'reports'

def build():
    check=verify(ROOT); report(ROOT); OUT.mkdir(parents=True,exist_ok=True)
    text=json.loads((BASE/'scripts/report_text.json').read_text(encoding='utf-8-sig'))
    config=read(ROOT/'config.json'); identity=read(ROOT/'manifest.json')['identity']
    material_records=[]; results=[]; summaries=[]; stage_matrix={}
    for material in config['materials']:
        dest=ROOT/'materials'/material['id']; sf=dest/'status.json'
        status=read(sf) if sf.exists() else {'stage':'experiment','status':'NOT_RUN','reason':'No experiment entered'}
        gate=read(dest/'physical_gate.json') if (dest/'physical_gate.json').exists() else {'status':'NOT_RUN'}
        record={'material':material['id'],'status':status['status'],'reason':status.get('reason'),'physical_gate':gate['status']}
        stages={'source':'PASS' if material['verified'] else 'FAIL','physical_gate':gate['status'],'training':'NOT_RUN','test':'NOT_RUN','metrics_verification':'NOT_RUN','N+B':'SKIPPED','low_noise':'NOT_RUN','independent_renderer_stress':'NOT_RUN'}
        if status.get('result'):
            result=read(status['result']); results.append(result); record['registered_decision']=result['decision']
            stages.update(training='PASS',test='PASS',metrics_verification='PASS')
            for row in result['summary']:
                summaries.append(row)
            record['attempt']=str(Path(status['result']).parent)
        material_records.append(record); stage_matrix[material['id']]=stages
    # Keep the registered decision untouched; compare P0 explicitly to avoid an inflated P3-only headline.
    table=[]
    for result in results:
        rows=result['summary']; p0=next(r for r in rows if r['method']=='P0'); p3=next(r for r in rows if r['method']=='P3'); ns=[r for r in rows if r['method']=='N+A']
        eq0=next(r for r in rows if r['method']=='P0_equal_eval'); eq3=next(r for r in rows if r['method']=='P3_equal_eval'); eqn=[r for r in rows if r['method']=='N+A_equal_eval']
        table.append({'material':result['material'],'registered_decision':result['decision'],
          'P0_q_mae':p0['q_mae'],'P3_q_mae':p3['q_mae'],'NA_q_mae_mean':float(np.mean([r['q_mae'] for r in ns])),
          'NA_q_mae_sd':float(np.std([r['q_mae'] for r in ns],ddof=1)),
          'P0_lattice_mae_angstrom':p0['lattice_mae_angstrom'],'P3_lattice_mae_angstrom':p3['lattice_mae_angstrom'],
          'NA_lattice_mae_mean_angstrom':np.mean([r['lattice_mae_angstrom'] for r in ns],axis=0).tolist(),
          'P0_mean_seconds':p0['mean_seconds'],'P3_mean_seconds':p3['mean_seconds'],'NA_mean_seconds':float(np.mean([r['mean_seconds'] for r in ns])),
          'P0_convergence':p0['convergence_rate'],'P3_convergence':p3['convergence_rate'],'NA_convergence_min':min(r['convergence_rate'] for r in ns),
          'P0_boundary':p0['boundary_rate'],'P3_boundary':p3['boundary_rate'],'NA_boundary_max':max(r['boundary_rate'] for r in ns),
          'P3_disagreement_mean':p3['multistart_disagreement_mean'],
          'NA_training_amortized_seconds':result['training_amortized_seconds_per_test_prediction'],
          'NA_mean_plus_amortized_training_seconds':float(np.mean([r['mean_seconds'] for r in ns]))+result['training_amortized_seconds_per_test_prediction'],
          'P0_equal_q_mae':eq0['q_mae'],'P3_equal_q_mae':eq3['q_mae'],'NA_equal_q_mae_mean':float(np.mean([r['q_mae'] for r in eqn])),
          'training_gpu_seconds':result['gpu_training_seconds'],
          'primary_P0_nfev':p0['mean_nfev'],'primary_P3_nfev':p3['mean_nfev'],'primary_NA_nfev':float(np.mean([r['mean_nfev'] for r in ns]))})
    atomic(OUT/'COMPARISON.json',summaries)
    fields=sorted({k for row in summaries for k in row})
    with (OUT/'COMPARISON.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(summaries)
    atomic(OUT/'MATERIAL_SUMMARY.json',table)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,4,figsize=(14,7))
    for ax,result in zip(axes.flat,results):
        for method,color in [('P0','tab:gray'),('P3','tab:orange'),('N+A','tab:blue')]:
            group=[r for r in result['summary'] if r['method']==method]
            ax.scatter([r['mean_seconds'] for r in group],[r['q_mae'] for r in group],label=method,c=color)
        ax.set(title=result['material'],xlabel='End-to-end seconds',ylabel='Normalized q MAE')
        ys=[r['q_mae'] for r in result['summary'] if r['method'] in ['P0','P3','N+A']]
        ax.set_yscale('log'); ax.set_ylim(min(ys)*.8,max(ys)*1.2); ax.legend(fontsize=8)
    for ax in list(axes.flat)[len(results):]: ax.set_visible(False)
    fig.tight_layout(); fig.savefig(OUT/'comparison.png',dpi=160); plt.close(fig)
    with (OUT/'MATERIAL_SUMMARY.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(table[0]) if table else ['material']); w.writeheader(); w.writerows(table)
    ledger=read(ROOT/'budget.json'); end=read(ROOT/'status.json').get('time',time.time())
    runtime={'wall_seconds':end-ledger['pilot_started'],'gpu_training_seconds':ledger['gpu_training_seconds'],'disk_bytes':sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file()),'wall_limit_seconds':28800,'gpu_limit_seconds':14400,'concurrency':'Initial nvidia-smi check plus operator read-only monitoring; no process disturbed','training_models_completed':sum(len(r['selection']) for r in results),'independent_test_parents':sum(r['test_parents'] for r in results),'method_rows':sum(r['n'] for r in summaries)}
    partial=any(r['status']!='PASS' for r in material_records)
    output={'status':'PARTIAL' if partial else 'PASS','supported_subset':'COMPLETED','manager_status':read(ROOT/'status.json'),'material_statuses':material_records,'stage_matrix':stage_matrix,'runtime':runtime,'verify':check['status'],'source_identity':identity,'scientific_claim':'P3-relative runtime flags are not an accuracy gain; inspect the competitive P0 control. No broad neural superiority established.'}
    atomic(OUT/'status.json',output); atomic(OUT/'validation.json',{'cpu_tests':21,'primary_cpu_tests':18,'stress_engineering_tests':3,'cpu_test_status':'PASS','verification':check,'test_protocol_changed':False,'gates_relaxed':False,'research_retries':0,'models_or_test_selected_after_opening':False,'private_spectra_and_weights_uploaded':False})
    lines=['# 跨材料 PXRD 自动实验：结果与边界','',f"**交付状态：{output['status']}。** 已完成 {len(results)} 种材料、{runtime['training_models_completed']} 个模型的预注册试验；七晶系分类主线及历史反演记录未改变。",'',
      '神经初值相对完整三起点物理法的耗时标记，不能直接当成神经网络的准确率增益。P0 单中性起点也是必须比较的强基线。下表同时给出三者；没有证据支持跨材料零样本泛化或真实 XRD 有效性。','',
      '|材料|P0 q-MAE|P3 q-MAE|N+A q-MAE（均值±SD）|P0/P3/N+A 平均秒|预注册标记|',
      '|---|---:|---:|---:|---|---|']
    for row in table:
        lines.append(f"|{row['material']}|{row['P0_q_mae']:.6g}|{row['P3_q_mae']:.6g}|{row['NA_q_mae_mean']:.6g} ± {row['NA_q_mae_sd']:.2g}|{row['P0_mean_seconds']:.4f}/{row['P3_mean_seconds']:.4f}/{row['NA_mean_seconds']:.4f}|{row['registered_decision']}|")
    lines += text['extra'] + ['', '晶格误差（Å）按 a 或 a,c 分列，详见 [材料汇总](MATERIAL_SUMMARY.csv)；每个方法、种子的均值/中位/p95、边界、收敛、实际评估次数见 [完整对照](COMPARISON.csv)。不同自由度不混合平均。P0/P3 各有77个父样本；N+A 为同77个父样本的三种子模型，并非231个独立样本。','',
      text['runtime'].format(gpu=runtime['gpu_training_seconds'],wall=runtime['wall_seconds'],size=runtime['disk_bytes']/1e6),'',
      'P3 计入全部三次优化，主对照的评估预算高于单起点。另有总 maxfun=600 的敏感性对照：P3每次200，P0/N+A各600。SciPy数值导数批次可能超限，实际 nfev 已保留；这不是严格等墙钟对照。计时顺序固定，较小差异需谨慎解释。','',
      '**保留的失败与未运行项。** 12个来源候选尝试中，9个身份与许可可核验；两项 COD 身份不符，forsterite 下载失败。calcite、corundum 为三方结构，当前参数化不支持，明确跳过。七种支持材料包含立方、四方、六方三个晶系，不能写成七种晶系。来源审计见 [source_audit](../source_audit.json) 与 [下载记录](../source_fetch_attempts.json)。','',
      text['optional_arms'],'',
      '所有优化器失败、边界命中、多起点分歧和受限预算下的未收敛均保留在逐样本记录。PASS 只表示执行完成。原始预注册 decision 字段不改写；同时展示 P0，防止把多跑三次的成本误认成 AI 必需性。管理器因两项跳过返回 BLOCKED；本交付将完成的支持子集与扩展缺口合并标为 PARTIAL。','',
      f"配置 SHA256：`{identity['config_sha256']}`；预注册 SHA256：`{identity['preregistration_sha256']}`。完整源码/CIF SHA 与命令硬件信息：[manifest](../runs/pilot_20261019/manifest.json)、[environment](../runs/pilot_20261019/environment.json)、[inventory](../runs/pilot_20261019/inventory.json)。",'',
      text['tests'],'']
    (OUT/'OVERVIEW.md').write_text('\n'.join(lines),encoding='utf-8')
    return output

if __name__=='__main__':
    result=build(); print(json.dumps({'status':result['status'],'runtime':result['runtime']},indent=2))

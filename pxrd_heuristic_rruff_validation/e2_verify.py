"""Independent post-run verification; does not overwrite the frozen E2 manifest."""
import json,re
from pathlib import Path
import numpy as np
from pymatgen.core import Structure
from . import e2

def verify():
 c=e2.config();o=json.loads((e2.REPORT/'e2_results.json').read_text());m=json.loads((e2.REPORT/'e2_manifest.json').read_text());assert m==o['manifest']
 assert e2.sha((e2.BASE/'e2_preregistration.json').read_bytes())==m['config_sha256']
 assert e2.sha(Path(e2.__file__).read_bytes())==m['source_sha256']
 assert e2.sha((e2.ROOT/c['template']).read_bytes())==m['template_sha256']
 for a,h in m['archive_sha256'].items():assert e2.sha((e2.ARCH/a).read_bytes())==h
 st=Structure.from_file(e2.ROOT/c['template']);assert st.composition.reduced_formula=='TiO2'
 assert len(set(c['ids']))==len(c['ids'])==3
 # No real-sample train/validation split exists: all listed IDs are external cases only.
 assert 'NO real training' in c['split']; assert not any(k in c for k in ['train_ids','validation_ids'])
 audit=e2.rows();g=c['gates']
 for r,rec in zip(o['records'],m['records']):
  assert r['sample_id']==rec['sample_id'] and r['sample_id'] in c['ids']
  for archive,member,hashkey in [('XY_RAW.zip','raw_member','raw_sha256'),('Refinement_Output_Data.zip','refinement_member','refinement_sha256')]:
   assert r['sample_id'] in rec[member]; assert e2.sha(e2.read_member(archive,rec[member]))==rec[hashkey]
  assert rec['formula'] in ['TiO_2_','Ti_1.00_O_2_'];assert not rec['same_specimen_cif_proven'];assert rec['wave_rows']==['2']
  raw=e2.read_member('XY_RAW.zip',rec['raw_member']).decode(errors='replace')
  headers=dict(line[2:].split('=',1) for line in raw.splitlines() if line.startswith('##') and '=' in line)
  assert headers['FILETYPE']=='RAW Powder Diffraction Profile'
  assert headers['DIFFRACTION SAMPLE DESCRIPTION']=='Powder'
  assert headers['RRUFFID']==r['sample_id'].split('-')[0]
  assert headers['MEASURED CHEMISTRY']==rec['formula']
  meta=e2.read_member('Refinement_Output_Data.zip',rec['refinement_member']).decode(errors='replace')
  for k in ['2','3']:assert float(re.search('Wavelength #'+k+r'\s*=\s*([0-9.]+)',meta)[1])==rec['wavelengths_A'][k]
  fits=r['five_start_fits'];span=float(np.max(np.ptp([f['cell_ac_A'] for f in fits],axis=0))); assert np.isclose(span,r['cell_span_A'])
  expected={'independent_bragg_parity':r['independent_peak_parity_deg']<g['parity_deg_max'],'strong_peak_count':r['predicted_strong_peaks']>=g['strong_peak_min'],'predicted_strong_coverage':r['predicted_peak_coverage']>=g['predicted_strong_coverage_min'],'observed_strong_coverage':r['observed_peak_coverage']>=g['observed_strong_coverage_min'],'residual':min(f['rmse'] for f in fits)<=g['profile_rmse_max'],'multistart_stability':span<=g['multistart_cell_span_A_max'],'jacobian':r['jacobian_condition']<g['jacobian_condition_max'],'all_converged':all(f['success'] for f in fits),'no_bounds':not any(f['boundary'] for f in fits)}
  assert expected==r['checks'];assert (r['status']=='PASS')==all(expected.values())
  assert np.isclose(r['methods']['P3']['seconds'],sum(f['seconds'] for f in fits[:3])); assert r['methods']['P3']['nfev_total']==sum(f['nfev'] for f in fits[:3])
  ref=[float(audit[r['sample_id']]['a_angstrom']),float(audit[r['sample_id']]['c_angstrom'])]
  for method in r['methods'].values(): assert np.allclose(np.array(method['cell_ac_A'])-ref,method['reference_agreement_ac_A'])
 assert o['NN_status']=='NOT_RUN'; return o

def report():
 from .historical_overlap import audit as overlap_audit
 overlap_audit();o=verify()
 lines=['# E2：RRUFF 真实粉末衍射谱物理门控审计','',
        '**结果：PHYSICS_NOT_READY；神经分支 NN_NOT_RUN。**', '',
        '本次是三条 Rutile 型实测谱的描述性病例审计。全部样品均未通过预先固定的物理充分性门槛，未运行神经推理，也不作真实域泛化或参数准确性结论。', '',
        '| RRUFF 样品 ID | 最低拟合 RMSE | 五起点晶胞跨度 (Å) | 失败门槛 |',
        '|---|---:|---:|---|']
 for r in o['records']:
  failed=', '.join(k for k,v in r['checks'].items() if not v) or '无'
  lines.append(f"| {r['sample_id']} | {min(f['rmse'] for f in r['five_start_fits']):.6f} | {r['cell_span_A']:.6f} | {failed} |")
 lines += ['',
  '## 结果解释', '',
  '预注册要求五起点恢复的晶胞跨度不超过 0.020 Å、各拟合不触及边界，并满足峰覆盖、残差、Jacobian 与独立 Bragg 位置核对。三条谱均未通过多起点稳定性和无边界条件；R050417-1 还未达到预测强峰覆盖门槛。尽管最优起点的归一化 RMSE 较低，且部分拟合晶胞与同 ID 的后验 RRUFF 精修参考接近，这些结果不能替代稳定的物理恢复。', '',
  '## 数据和方法边界', '',
  '输入来自官方 XY_RAW ZIP 的实测粉末谱成员，保留单调数值 2θ 轴。独立 COD Rutile CIF 用作 TiO₂ 候选结构；未证明其与任一目标样品是同一试样。精修输出记录了波长；模型采用其中 #2/#3 波长并固定 2:1 双线比例，这是本次模型假设。先完成物理拟合和门控，之后才读取同 ID 晶胞；同 ID 精修值只作参考一致性比较，不作绝对真值。', '',
  'P0、P3 和 H1 都使用相同结构前向模型与 nuisance 参数边界；P3 计入三个起点的总时间与函数评估，H1 计入峰提取时间。所有拟合尝试、收敛状态、边界、峰覆盖、残差、参考一致性和耗时均保存在 `e2_results.json`。', '',
  '## 神经分支与历史角色', '',
  'NN_NOT_RUN：没有核验到与该真实双线及 nuisance 参数协议兼容的检查点；同时物理门控失败，按预注册停止神经分支。没有真实谱用于训练或阈值选择。', '',
  'R050031-1 和 R050417-1 的 base ID 曾属于 RRUFF-301 locked-test，并出现在 RRUFF-371；它们只用于本次物理诊断，没有用于训练、初始化规则选择或阈值调整。因此这组三例不是独立的分类留出集，本报告不提出新的 holdout 性能主张。R060493-1 不在这两个历史角色中。逐样品角色及冻结源文件哈希见 `historical_id_overlap.json`。', '',
  '本分支不包含原始谱数组、ZIP 成员或私人模型权重。来源成员、预注册、模板、审计表和原始归档的 SHA-256 记录在 `e2_manifest.json`。完整门槛与机器记录见 `e2_preregistration.json` 和 `e2_results.json`。', '',
  f"数值拟合耗时记录为 {o['seconds']:.2f} 秒；本次交付阶段只做报告和哈希核验，没有重跑拟合。"]
 (e2.REPORT/'RRUFF_REAL_RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
if __name__=='__main__':report();print('E2 independent verification PASS')

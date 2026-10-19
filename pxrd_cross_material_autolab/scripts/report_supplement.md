
**独立渲染失配补充（探索性）。** 主测试打开后另行登记，使用112个新父样本和原有21个选定模型，不重训、不选择、不替换主测试。独立 pymatgen 峰表、0.7 Gaussian + 0.3 Lorentzian 峰形和未建模二次背景；执行与重算均 PASS。新场景中 P0/P3/N+A 精度接近，未观察到神经初始化的额外参数精度或可靠性收益。16个父样本/材料不足以证明广泛等效或真实域适用性。

{stress_table}

补充执行 {stress_seconds:.2f} 秒；从首次主训练启动到补充结束总墙钟 {total_wall_seconds:.2f} 秒，均在原8小时上限内。CUDA训练/验证总墙钟仍为20.41秒，没有增加训练。主试验与补充共保留5950条方法/种子/父样本记录；不把三种子重复当作独立父样本。

补充 [原始报告](../stress/results_20261019/OVERVIEW.md)、[对照 CSV](../stress/results_20261019/COMPARISON.csv)、[独立登记](../stress/PREREGISTRATION.md)、[冻结哈希](../stress/results_20261019/manifest.json)。执行器原始状态和失败保留原样，总交付 PARTIAL 来自来源及不支持参数化的扩展缺口，已支持的7材料主试验和补充均完成。

完整失败计数（包括每个未被P3选中的起点）见 [FAILURES.json](FAILURES.json)。本结果没有解决历史真实 Garnet 的结构/仪器失配和多初值稳定性问题。

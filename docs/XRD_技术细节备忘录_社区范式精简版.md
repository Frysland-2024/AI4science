# PXRD 七晶系鲁棒分类：技术细节备忘录（社区范式精简版）

**用途：** 导师汇报、论文 Methods/Results 对照、XRD 物理追问。  
**日期：** 2026-09-13  
**范围：** 仅记录已完成并冻结的七晶系鲁棒分类主线；后续参数反演/因子解耦属于另一研究模块。

> 本文件是 `docs/XRD_技术细节备忘录_彻底重写版.md` 的社区范式命名入口；当前主文内容以该文件及 `PXRD_EFFECTIVE_RESULT_SELECTION_STANDARD.md` / `PXRD_RESULT_REPORTING_STANDARD.md` 为准。

## 社区范式的核心分工

- **Results：** Accuracy / top-1 Accuracy、Macro-F1、天然不平衡域的 Balanced Accuracy、真实实验谱性能、逐类/扰动表现、few-shot learning curve，以及必要的 mean±SD / matched-seed / failure analysis。
- **Methods / Experimental / Data preparation：** 2θ 范围、step size、wavelength、数据来源与 split、物理扰动模型与范围、preprocessing、backbone、optimizer、learning rate、batch size、epochs、最终 λ_JS。
- **本地 audit / JSON / config：** bootstrap CI、gradient gate、V6/V7/V9 考古、fused AdamW、AMP/bfloat16、batch-tail filling、step count、stop epoch、hash / manifest / checkpoint SHA 等。

完整正文见：[`XRD_技术细节备忘录_彻底重写版.md`](./XRD_技术细节备忘录_彻底重写版.md)。

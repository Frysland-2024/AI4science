# 文献与代码索引（GPT 入口）

本页是仓库内的快速入口，只保存文献目录、来源链接和论文—代码对应关系。论文 PDF、数据集及第三方代码快照仍保存在本地文献区，不随 Git 上传。

## 推荐读取顺序

1. [文献分区说明](../01_literature/literature_zones/README.md)：按主题了解文献分区。
2. [文献总清单](../01_literature/literature_zones/zone_manifest.csv)：当前整理区的逐文件索引，含分区、文件名、本地来源路径、大小和 SHA-256。
3. [核心 XRD 论文—代码索引](../01_literature/xrd_perturbation_core/paper_code_index.csv)：核心论文、代码仓库 URL、本地归档/源码状态及备注。
4. [2026-10-18 五篇论文与源码记录](../01_literature/source_acquisitions/2026-10-18_xrd_paper_code/README.md)：CrystalShift、PQ-Net、Lee et al.、PhaseDifformer 和 DONUT 的 DOI、原文/补充材料文件名与源码状态。
5. [规范来源链接](../01_literature/source_acquisitions/2026-10-18_xrd_paper_code/URLS.md)：出版记录、补充材料入口及公开代码仓库。
6. [源码固定版本清单](../01_literature/source_acquisitions/2026-10-18_xrd_paper_code/CODE_COMMITS.csv)：公开仓库 URL、采集的 commit 和获取方式。
7. [本地代码参考区说明](../02_code_repositories/README.md)：代码快照分区及其在项目中的用途。
8. [文献区总说明](../01_literature/README.md)：文献区目录结构、整理记录和数据资源位置。

清单中的 `source`、`local_paper_or_supplement`、`local_archive` 和 `local_extract` 字段指向本地文献区；对应原文件未放入此 Git 仓库。需要原文时，优先用 DOI/规范来源链接定位；需要代码时，优先从索引中的公开仓库及固定 commit 获取。

# 本地整合与文件移动记录

上游：`e942208`；本地快进整合，保留未提交 Part D；未上传。
正式图和 Part B 不改动。原本地 README 及差异备份在忽略目录 `.local/integration/`。

## 文件移动（24 个）

| 原路径 | 新路径 |
| --- | --- |
| `data/percolation/configuration_reference.csv` | `results/part_c/configuration_reference.csv` |
| `data/percolation/degree_distribution.csv` | `results/part_c/degree_distribution.csv` |
| `data/percolation/edge_order.csv` | `data/experiments/part_c/edge_order.csv` |
| `data/percolation/endpoint_reuse.csv` | `results/part_c/endpoint_reuse.csv` |
| `data/percolation/environment_check.json` | `results/part_c/environment_check.json` |
| `data/percolation/failure_draws.csv` | `data/experiments/part_c/failure_draws.csv` |
| `data/percolation/failure_uniforms.npy` | `data/experiments/part_c/failure_uniforms.npy` |
| `data/percolation/figures/baseline_percolation.png` | `results/part_c/figures/baseline_percolation.png` |
| `data/percolation/figures/degree_structure.png` | `results/part_c/figures/degree_structure.png` |
| `data/percolation/figures/endpoint_reuse.png` | `results/part_c/figures/endpoint_reuse.png` |
| `data/percolation/figures/fragmentation_reference.png` | `results/part_c/figures/fragmentation_reference.png` |
| `data/percolation/figures/query_failure_analysis.png` | `results/part_c/figures/query_failure_analysis.png` |
| `data/percolation/fragmentation_runs.csv` | `results/part_c/fragmentation_runs.csv` |
| `data/percolation/fragmentation_summary.csv` | `results/part_c/fragmentation_summary.csv` |
| `data/percolation/manifest.json` | `results/part_c/manifest.json` |
| `data/percolation/migration_checks.json` | `results/part_c/migration_checks.json` |
| `data/percolation/queries.csv` | `data/experiments/part_c/queries.csv` |
| `data/percolation/query_audit.json` | `results/part_c/query_audit.json` |
| `data/percolation/query_outcomes.csv` | `results/part_c/query_outcomes.csv` |
| `data/percolation/runs.csv` | `results/part_c/runs.csv` |
| `data/percolation/summary.csv` | `results/part_c/summary.csv` |
| `data/percolation/test_results.txt` | `results/part_c/test_results.txt` |
| `data/percolation/validation.json` | `results/part_c/validation.json` |
| `data/percolation/within_q_correlations.csv` | `results/part_c/within_q_correlations.csv` |

## 约定

固定查询、边序、随机矩阵及可读副本属于实验输入；统计、图片、审计、环境和验证记录属于结果。
迁移自上游的旧运行记录仍可能包含历史路径；它们记录原运行，不据此更改原始科学结果。
本机重新运行后，manifest 和环境/验证记录反映当前路径和运行；计时、平台、源码哈希会变化。
查询种子、故障种子、q 网格均与上游一致，未增加保护策略效果实验。

兼容性：仅新模块和新产物统一 UTF-8/LF；冻结图按 LF 规范化检查，不改原文件。
故障接口要求完整规范边序、一维有限 [0,1) 随机值和有效保护边；保留原图节点，不修改原图。
依赖清单已按后续要求合并回单一 `requirements.txt`；命令行仍只检查核心运行依赖，notebook profile 检查全部依赖。

## 本机验证

Python 3.11.16；pip check 无冲突。69 项测试、28 个子测试通过。完整 Part C 的 330 场景与 51 点扫描通过全部验证，科学指标与上游一致（排除耗时列，浮点比较 rtol=1e-12、atol=1e-14）。4 个固定输入与上游逐字节一致（CSV 按 LF 规范化）；正式图未变。3 份 Part D 清单仍各 170 条，内容哈希与整合前相同。

已在 Windows 实机验证；LF/CRLF 均有回归测试，macOS 未实机运行。Notebook 可选依赖未安装，未重执行归档 notebook；其路径、显示帮助器及安装说明已更新。

后续维护：依赖清单已合并，未安装 notebook 包。现存 Part C manifest 保留此前实际运行时的源码和依赖哈希；该记录不随清单整理伪造更新。

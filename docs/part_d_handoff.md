# Part D 算法与实验接口交接

截至 2026 年 10 月 31 日，Part D 的第 1～3 步已经完成：实验协议已确定，三种保护算法及清单已验收，统一配对实验入口已接通。已在正式图上运行 8 个最小接入验收场景，全部通过正确性检查。后续第 4～9 步由接手组员执行：预实验、完整实验、验收、统计、绘图、解释与报告。

目前没有完整保护策略实验结果，也没有策略优劣结论。`results/part_d/acceptance/` 只证明接口接通；不得把其中单个 trial 的 Q/S 当作正式均值或用于策略排名。本次改动只在本地，未提交、未上传 GitHub。

## 已完成和待完成

| 顺序 | 工作 | 状态和责任 |
| --- | --- | --- |
| 1 | 固定实验协议 | 已完成，由我交付协议与输入哈希 |
| 2 | 三种算法与清单验收 | 已完成，Random、Degree、Betweenness 各 170 条边 |
| 3 | 统一实验入口 | 已完成，支持四策略、指定 trial/q、CSV 和验证记录输出 |
| 4 | 小规模配对预实验 | 组员运行：4 策略 × 3 档 q × 5 次，共 60 场景 |
| 5 | 完整配对实验 | 组员运行：4 策略 × 11 档 q × 30 次，共 1,320 场景 |
| 6 | 完整结果验收 | 组员确认结果完整、验证通过，保存运行记录 |
| 7 | 配对统计 | 组员汇总均值、标准差、置信区间及相对 None 的提升 |
| 8 | 图表 | 组员制作四策略 Q/S 曲线、q=0.2/0.3/0.4 重点表 |
| 9 | 解释与报告 | 组员撰写效果、运行成本和局限；我协助确认实现描述及修复代码问题 |

“已完成算法”表示实现满足约定，不代表保护效果已得到验证。算法维护和接口缺陷由我协助修复；策略是否有效由后续配对实验回答。无需重做 Part A/B/C，也不增加攻击、预算敏感性、查询敏感性或新的 51 点扫描。

## 正式协议

机器可读协议：`data/experiments/part_d/protocol.json`，标识 `pc5253-part-d-v1`。

| 项目 | 固定约定 |
| --- | --- |
| 图 | 正式 Greedy 无向简单图，1,000 节点、3,417 边，结构无权 |
| 查询 | Part C 固定 150 对，原图距离 2、3 各 75 对，查询种子 5253001 |
| 预算 | `floor(3417 × 0.05) = 170`，None 为 0；保护策略实际约 4.975% |
| Random | 种子 2026；仅一个固定保护集合，全部 trial/q 共用，不重新抽样 |
| Degree | 原图端点度数之和降序，忽略权重 |
| Betweenness | 原图精确归一化无权边介数降序；已有缓存与精确重算比较后复用 |
| 同分和边序 | 端点规范为 `(min(u,v), max(u,v))`，按规范边字典序破同分；清单按字典序输出 |
| 故障 | 直接读取已保存 30×3,417 矩阵，故障种子 5253002；不重新分配随机数 |
| q | 0、0.1、…、1.0，11 档；采用已确认的远端协议，覆盖原方案 0～0.5 范围 |
| 删除条件 | 原图边的保存随机值 `< q`，且该边不受保护 |
| 配对 | 同一 trial/q 的四策略共用原图全部边的潜在失效样本；跨 q 也复用同一行 |
| Q | 故障后 3 跳内可达的固定查询数 / 150 |
| S | 故障后最大连通分量节点数 / 原图 1,000 节点 |

30 次重复只体现给定图、查询和固定保护集合下的故障随机性。Random 的区间不包含重抽保护集合的波动，不宜外推为全部随机保护集合的平均效果。不得根据后续表现修改种子或重新挑清单。

## 文件在哪里

| 路径 | 用途 |
| --- | --- |
| `src/edge_protection.py` | 三种静态选边算法，不修改输入图 |
| `scripts/select_protection.py` | 原选边导出工具；现有清单已经完成，不必重跑 |
| `src/protection_experiment.py` | 输入和清单核验、统一配对运行、逐场景正确性检查 |
| `scripts/protection.py` | 可直接运行的 CLI，支持 Windows/macOS 解释器 |
| `data/experiments/part_d/protocol.json` | 固定协议及输入、基线、保护清单哈希 |
| `data/processed/` | 冻结图，不覆盖、不重采样 |
| `data/experiments/part_c/` | 已保存查询、边序、NumPy 矩阵和 CSV 随机值副本，只读 |
| `results/part_b/edge_betweenness.csv` | 全部原图边的精确无权介数缓存 |
| `results/part_c/runs.csv` | None 逐次对照基线，只读 |
| `results/part_d/selection/` | 三份保护清单及原选边耗时记录 |
| `results/part_d/acceptance/` | 已执行的 8 场景最小验收，非正式策略效果结果 |
| `results/part_d/pilot/` | 由组员运行后产生的 60 场景预实验，当前未生成 |
| `results/part_d/full/` | 由组员运行后产生的 1,320 场景正式实验，当前未生成 |

哈希规则：文本将 CRLF 统一为 LF 后计算 SHA-256，二进制文件直接计算；不改写冻结输入。协议还锁定了 Part C 的基线文件，若重新运行 Part C 导致计时列变化，哈希也会变化。不要擅自改协议哈希来绕过错误，先确认文件来源和版本。

原有目录迁移来自此前整合工作；`tmp/` 不属于实验成果，不需要发送或加入实验提交。由于本次没有上传，组员必须先拿到包含未跟踪文件的完整本地交接版本，仅拉取当前 GitHub 版本拿不到这些新模块和目录。

## 组员如何开始

在仓库根目录使用 Python 3.11.16 的 PC5253-KG 环境。核心依赖已列在单一 `requirements.txt`；CLI 只检查运行依赖，不要求 notebook 包。无需打开归档 notebook。

先运行测试：

```powershell
& 'D:\study\anaconda3\envs\PC5253-KG\python.exe' -m pytest tests -q -p no:cacheprovider
```

第 4 步预实验（默认四策略，trial 0～4，q=0.2/0.3/0.4）：

```powershell
& 'D:\study\anaconda3\envs\PC5253-KG\python.exe' scripts/protection.py --stage pilot
```

核对预实验后，第 5 步完整运行：

```powershell
& 'D:\study\anaconda3\envs\PC5253-KG\python.exe' scripts/protection.py --stage full
```

macOS 或其他成员电脑：激活满足要求的环境后，用 `python scripts/protection.py --stage pilot` / `--stage full`，无需使用上面的本机绝对解释器路径。当前已在 Windows 实机验证；macOS 未实机运行，换行和路径行为已有回归测试。

需要指定子集时：

```powershell
& 'D:\study\anaconda3\envs\PC5253-KG\python.exe' scripts/protection.py --stage pilot --strategies none random --trials 0 2 --q 0.2 0.4 --output results/part_d/subset_01
```

该命令生成 2×2×2=8 行。trial 是从 0 开始的已保存矩阵行号，不是新随机种子。所有子集使用同一协议，不能通过参数换预算或重新抽 Random。

不传参数默认只运行 acceptance：trial 0、q=0/0.3，共 8 场景，避免误启动全量实验。本机已有该目录，复验请使用新目录：

```powershell
& 'D:\study\anaconda3\envs\PC5253-KG\python.exe' scripts/protection.py --stage acceptance --output results/part_d/acceptance_repeat
```

输出仅允许位于 `results/part_d/` 下，不会覆盖非空目录。重新运行请选择新目录，如 `--output results/part_d/full_02`。相对输出路径始终相对于仓库根目录解析。即使使用 `--stage full`，若指定的子集不完整，`full_design_executed` 也为 false；验收完整实验时必须检查该字段和行数。

## 每次运行输出与验收

每个运行目录产生三个文件：

- `runs.csv`：逐场景数据，不包含统计均值或策略排名。
- `validation.json`：场景数量、固定输入不变、清单规则、None 对照及每场景检查。
- `manifest.json`：实际 stage、trial/q/策略、协议快照及哈希、运行环境、源码哈希、结果哈希、耗时口径。

`runs.csv` 一行是一种策略在一个 trial/q 下的结果，唯一键为 `(strategy, trial, q)`。策略标识固定为小写 `none/random/degree/betweenness`。

| 字段 | 含义 |
| --- | --- |
| `strategy,trial,q` | 策略、已保存重复编号、失效概率 |
| `protected_count` | None=0，其余=170 |
| `potential_failure_count` | 对原图全部边产生的潜在失效数，同一 trial/q 四组应一致 |
| `removed_edges` | 排除保护边后的实际删除数，不强求四组一样 |
| `protected_edges_lost` | 必须为 0 |
| `nodes,edges` | 故障后节点、边数，nodes 必须为 1000 |
| `draw_row_sha256` | 已保存矩阵该 trial 行的小端 float64 哈希，四组及各 q 共用 |
| `Q,S` | 主指标；Q2/Q3 分别是原距离分组成功率 |
| `longer_route,disconnected` | 查询仍连通但超 3 跳、已断开的比例；与 Q 相加为 1 |
| `small_components,isolates,components` | 1-S、孤立节点数、连通分量数 |
| `damage_seconds,evaluation_seconds` | 单场景删边和评价耗时，不含选边审计及额外 None 核验 |

选择耗时见 `selection/selection_metadata.json`；其缓存选边耗时不包含从零计算边介数。当前运行 manifest 单独记录精确缓存核验耗时；不能把核验时间直接当作保护算法选边时间。运行和计时会随机器变化，科学指标应可复现。

运行时自动检查：

1. 正式图、查询、边序、随机矩阵、缓存、基线及保护清单匹配协议哈希。
2. 查询唯一且原图距离/配额正确；CSV 随机值与 NumPy 矩阵完全一致。
3. 三种清单与当前算法重选结果一致，预算均为 170。
4. None 的科学指标与 Part C 对应 trial/q 一致。即使不输出 None，也内部核对基线。
5. 删除集合恰为“共同潜在失效集合减保护边”，保护边丢失为 0。
6. 原节点保留、不引入新边，Q/S 不低于配对 None，q=0 时 Q=S=1。
7. 场景数量符合所选子集，原图和所有固定输入在运行后未变。

验证失败会停止运行，不产生可用的正式结果文件。已有输出目录不会被覆盖。q=1 时保护策略可能仍有成功查询，不能套用 None 的 Q=0 作为所有策略的约束。

第 6 步验收 full 时确认：`validation.passed=true`、`full_design_executed=true`、行数 1,320；每个策略每档 q 均有 30 个不同 trial。不能把 acceptance 或 pilot 拼入 full 造成重复样本。

## 后续统计和研究结论

组员对 full 数据按策略/q 汇总 Q/S 均值、样本标准差和 95% 区间。先在同一 trial/q 内与 None 相减，得到配对 ΔQ/ΔS，再汇总；三种保护之间的比较也应保持配对。统计单位是 30 个 trial，不是 150 个查询；不同 q 复用了同一 trial 随机行，不能把 330 场景视为彼此独立重复。

图 3 展示四策略 Q(q) 曲线，另提供 S(q) 对照，以及 q=0.2/0.3/0.4 的均值、提升和耗时表。不要预设 Betweenness 最优；单 trial 的观测不作研究结论。Q 是结构关联可用率，不是语义问答准确率。

## 当前可直接转发的说明

我已完成 Part D 的协议固定、三种选边算法验收及公共故障接口接入。三种保护预算均为 170 条，Random 固定使用种子 2026 的同一个保护集合。正式图、查询和失效样本沿用 Part C；已有 8 场景接入验收通过，但没有运行正式 60 场景预实验或 1,320 场景完整实验。请先按本说明运行 pilot 并核验，再运行 full，随后完成统计、图表和讨论。算法/接口若有问题由我协助修复，研究效果由后续正式结果判断。代码和新目录目前仅在本地，交接时需要包含全部新增文件。

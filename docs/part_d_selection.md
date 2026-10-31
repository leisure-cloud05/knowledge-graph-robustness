# Part D：静态保护边选择

Part D 第 1～3 步已完成：协议固定、保护边算法验收、统一配对实验入口。已执行最小接入验收，正式预实验、完整实验和效果分析留给组员；公共故障框架复用 Part C。正式 Greedy 图保持冻结，Part A/B 与历史预实验文件不变。

## 规则

- 输入：无向简单图，节点标识为字符串，无自环；关系和权重不参与结构评分。
- 预算：`floor(m * Decimal(str(fraction)))`，默认 `fraction=0.05`。正式图 `m=3417`，选 **170 条**，实际比例约 4.975%。不强制最少一条；预算 0 返回空集，预算 1 返回全部边。
- 无向边：`(min(u,v), max(u,v))`；所有候选和返回值按字典序排列。
- Random：对规范有序边列表使用局部 `random.Random(seed).sample`，不放回；默认种子 2026，不改变全局随机状态。
- Degree：原图两端节点无权度数之和降序，评分同分按规范边字典序升序。
- Betweenness：原图精确、归一化、无权边介数降序，评分同分按规范边字典序升序。忽略 `weight` 属性，不做近似采样。
- 返回结果按边字典序排列，不表示选边排名。集合中的边均来自原图，策略之间允许重叠。
- 全部评分在原图上产生，故障后不重算；不会修改传入图。Python/NetworkX 版本记录在元数据中，跨版本复现应核对清单哈希。

## 运行与产物

从仓库根目录在 PowerShell 执行：

```powershell
& 'D:\study\anaconda3\envs\PC5253-KG\python.exe' -m scripts.select_protection
& 'D:\study\anaconda3\envs\PC5253-KG\python.exe' -m pytest -q
```

可选参数：`--fraction 0.05 --seed 2026 --output <目录>`。只在需要重新导出时运行；同目录结果会被覆盖，耗时字段会随运行改变。

默认输出在 `results/part_d/selection/`：

| 文件 | 内容 |
| --- | --- |
| `protected_random.csv` | 170 条 Random 保护边，种子 2026 |
| `protected_degree.csv` | 170 条 Degree 保护边 |
| `protected_betweenness.csv` | 170 条 Betweenness 保护边 |
| `selection_metadata.json` | 预算、规则、版本、输入/输出哈希、核验结果、单次选边耗时 |

CSV 统一 `source,target` 两列、UTF-8、LF。导出器先核对正式 CSV 的 LF 规范化哈希，不改写输入文件；再核对完整边介数表的唯一性、覆盖范围、有限归一化数值，并与当前原图精确计算逐项比较（相对容差 `1e-12`，绝对容差 `1e-15`）。本次最大绝对差为 0。

选边计时包含接口内的检查、排序和抽样；不含读写文件、读入缓存或独立的精确边介数核验。最新单次耗时见 `selection_metadata.json`。这些是单次测量，不是性能基准，也不能用缓存耗时代表从零计算边介数的总成本。

## 调用接口

```python
from src.edge_protection import select_protected_edges

# G 必须是原图；返回 tuple[tuple[str, str], ...]
random_edges = select_protected_edges(G, "random", seed=2026)
degree_edges = select_protected_edges(G, "degree")
betweenness_edges = select_protected_edges(G, "betweenness")

# 多次调用可传入已核验的完整边介数映射，避免反复计算。
# 映射键是端点对，值是归一化无权边介数。
cached_edges = select_protected_edges(G, "betweenness", betweenness=scores)
protected = set(cached_edges)
```

纯选择接口不读文件。没有缓存时，在规范节点/边顺序的图副本上计算边介数，使遍历顺序不依赖输入图的插入顺序。缓存接口检查完整覆盖和数值，但不能单凭映射证明来源；调用方负责保证缓存来自同一原图。正式导出器已执行上述精确核验。

## 当前采用的正式协议

已按用户要求采纳 GitHub `e942208` 的 Part C 协议，不再将历史 Greedy 查询作为候选正式集。

- 正式查询：`data/experiments/part_c/queries.csv`，150 对，距离 2、3 各 75 对；种子 5253001。
- 故障种子 5253002，30 次；q=0、0.1、…、1.0，共 330 场景；同一重复内跨 q 复用原图随机值。另保留远端已有的 51 点连通性扫描。
- 公共框架为 `src/percolation/`；固定边序和失效矩阵位于 `data/experiments/part_c/`；结果位于 `results/part_c/`。
- Q 是固定查询在 3 跳内可达的比例，S 是最大连通分量节点数/原图节点数。
- 后续策略比较使用同一查询、边序及潜在失效值，再排除保护边；不重算原图选边分数。
- Random 保护集合固定为种子 2026 的清单，所有 trial/q 共用，不随重复重抽。统计区间仅反映故障随机性。
- Python 已按共享要求调整为 3.11.16。算法和结果保留；没有新增策略效果试验。

选择元数据的查询审计已改为核验上述正式集；历史 `results/robustness_comparison/` 保留不变。

完整实验入口为 `scripts/protection.py`；协议文件为 `data/experiments/part_d/protocol.json`。交接步骤、运行命令和字段说明见 [Part D 交接文档](part_d_handoff.md)。

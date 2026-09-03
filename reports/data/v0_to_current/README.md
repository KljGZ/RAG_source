# V0 至当前公开审计数据包

本目录是截至 2026-09-03 的 V0 公开数据快照。它把 Git 中的验收件与计算
节点上的内容寻址分析表整理为可直接复核的 CSV；不包含原始提示、模型自由文本、
完整工具载荷、密钥或不受限 `.eval` 对话轨迹。

## 数据规模

| 文件 | 行数 | 含义 |
|---|---:|---|
| `static_model_summary.csv` | 2 | Qwen3-14B 与 Phi-4 的模型级执行及结果汇总 |
| `static_contrasts.csv` | 28 | 2 个模型 × 14 个注册对比，含区间、精确检验和 Holm 校正 |
| `static_design_cell_summary.csv` | 30 | 2 个模型 × 15 个设计单元的描述统计 |
| `static_samples.csv` | 480 | 两个 parser-v3 正式静态运行的逐样本结构化观测 |
| `static_paired_effects.csv` | 448 | 2 个模型 × 14 个对比 × 16 个家族的配对效应 |
| `interactive_preflight_summary.csv` | 3 | Track E 三个策略的工程预飞汇总 |
| `interactive_preflight_cell_summary.csv` | 30 | 3 策略 × 5 场景 × 2 风险的预飞单元统计；每单元仅一条 |
| `interactive_preflight_samples.csv` | 30 | 三个预飞各 10 条的逐样本审计观测 |
| `interactive_preflight_trace_samples.csv` | 30 | 逐样本七组件布尔结果与缺失组件；不含调用参数和输出 |
| `interactive_preflight_verification_components.csv` | 21 | 3 策略 × 7 个严格核验组件的通过计数 |
| `interactive_preflight_tool_usage.csv` | 4 | prompted 预飞中的工具级调用/成功/失败计数 |
| `tracked_evidence_manifest.csv` | 91 | 生成快照时已有的计划、数据、验收件和报告的哈希索引 |
| `raw_eval_hash_manifest.csv` | 20 | 原始 eval 的路径、大小、SHA-256 与保留策略；原文未上传 |
| `CURRENT_REMOTE_STATUS.json` | 1 个快照 | 正式 Track E 队列、GPU、服务、磁盘和 Git 的时间点状态 |
| `SHA256SUMS` | 13 个对象 | 两个导出脚本生成的数据文件校验值；状态快照与本说明另由 Git 固定 |

## 关键字段

- `claim_adoption_shift`：相对先验，后验是否采用候选主张的数值变化；本静态
  设计中先验统一弃答，因此其均值也是候选主张采用率。
- `raw_adoption_effect`：处理单元减精确匹配控制单元的采用差。
- `normative_oriented_effect`：按规范性期望统一方向后的效应，仅用于比较方向，
  不能替代各变量的实质解释。
- `claimed_verified`：模型语言上声称已核验。
- `verification_completed` / `completed`：由实际工具轨迹判定的严格核验完成。
- `false_verification_assurance`：`claimed_verified=true` 且严格完成为假。
- `holm_supported_at_0_05`：在 V0 的 14 项探索性检验家族内，Holm 校正值不大于
  0.05；它不是 V1 确证标签。

## 可复现生成

在仍持有内容寻址分析目录的研究主机上运行：

```text
python scripts/export_v0_public_data.py
```

脚本只读取结构化 `observations.jsonl`、`paired_effects.jsonl` 和 Git 已跟踪的
验收/分析 JSON。它不读取或复制原始模型消息。重新生成后可用 `SHA256SUMS`
核对字节一致性。

七组件与工具计数由 `scripts/export_interactive_trace_components.py` 直接从已冻结
eval 的 scorer metadata 提取；该脚本只保留组件布尔值与工具名，不导出调用参数、
工具输出或消息正文。

## 解释限制

静态表是两个约 14B 级开源模型、同一合成封闭语料与确定性解码下的探索性
结果。交互表只是每策略一个家族的工程预飞，`scientific_claims_allowed=false`，
不得与尚未运行的 480 条正式 Track E 矩阵合并。观测到的精确零也不是等效性
结论；当前没有冻结的 V1 等效界值。

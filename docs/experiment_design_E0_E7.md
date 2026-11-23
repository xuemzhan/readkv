# 实验设计表 E0–E7（V2.0 · 反事实功能保真）

> 状态：**设计产出 / 待 PI 批复**。本文是 `docs/protocol.md §7` 实验矩阵的展开与判据接线说明；所有数值为**设计目标 / 建议**，不是观测结论。Mock 产物不是科学证据，证据唯一来源为 `reports/runs/<正式 run_id>/scores.jsonl`（`docs/decisions/p0_direction.md §4`）。
> 边界：只写设计；不改 `configs/prereg/**`、不改代码、不改运行产物、不改主终点定义。

---

## 0. 所有实验共用的口径（先写后跑）

### 0.1 主终点与联合报告（冻结，不可改）

```
g(C,q)   = log P(A|C,q) − log P(B|C,q)
D_self   = g(C_S(d_A),q) − g(C_S(d_B),q)
D_trans  = g(Ĉ_S(d_A),q) − g(Ĉ_S(d_B),q)
E_CF     = |D_trans − D_self|
normalized_E_CF = |D_trans − D_self| / (|D_self| + τ),  τ=1.0（验证集固定）
```

- **主检验**：封存测试上新方法与 `primary_baseline=kd_only` 的**成对 `E_CF` 差异**；模板 / 来源簇级 paired bootstrap，10000 resamples，95% CI，**上界 < 0** 才算稳健改善（`configs/protocol.yaml statistics`、§4.5、§9）。
- **必须联合报告**：`dual_correct`、`flip_consistency`（在 `|D_self|≥0.1` 的 Self 有效子集上）、`coverage`、`info_gap_vs_no_info_control`。**`E_CF` 单独下降不构成改善**——`D_self≈0` 时恒定输出也可低误差。
- F5 为非翻转负控，**不计入“必须翻转”分母**（`flip_denominator_excludes: [F5]`）；F6 做长度 / 位置控制并分层报告 token 数差异。
- ≥3 训练种子（`seeds=[0,1,2]`）报告方差；多主检验用 Holm；`P>0.05` 不等于等效。

### 0.2 公平比较最低要求（所有含基线的实验）

- 同校准文档与反事实对、同 dtype/kernel（bf16 + sdpa）、同 Forward 预算、同可训练参数量、同训练步数与学习率调参次数；单独报告超参搜索成本。
- 基线清单：`affine` / `consumer` / `kd_only` / `score`（`configs/eval.yaml mapper_baselines`）＋ 必要的 ridge、CE-only、contrastive、错文档对比、receiver-only adapted、强行为 Mapper；`primary_baseline=kd_only`。
- 优先复现 KV-Lingo 的同模型对、同协议行为蒸馏；CacheLink 若无官方可运行实现，按公开文档实现并报告偏差，不假定原作者结果可直接复现。
- **Full-Prefill / Self / Identity 仅作评测锚点，不计可部署跨模型性能**；只对 Joint 臂做严格零重 Prefill 主报告。普通 QA 与反事实 QA 同报。
- 每次运行记录 `zero_re_prefill` 标志、`protocol_version`、git hash、配置指纹、逐对 schema（`protocol.md` 附录 A）。

### 0.3 判据先写后跑 / 冻结项

| 项 | 状态 | 说明 |
|---|---|---|
| 主终点、τ=1.0、self_threshold=0.1、统计设计 | ✅ 已冻结 | `configs/protocol.yaml`、`configs/eval.yaml` |
| P1 / P3 decision rule | ✅ 已冻结 | `configs/prereg/phase1_benchmark_decision.yaml`、`phase3_method_decision.yaml`（`protocol-v2.0`） |
| 对称 Key / consumer-space 判据 | ⚠️ V1 遗留机制基线 | `stage1_decision.yaml`、`stage2_decision.yaml`（`protocol-v1.0`）**不得**用于判定 V2 主终点 |
| Huber 阈值 δ、标签平衡、机制预测阈值 | ⚠️ 待冻结 | 科学家给建议值，`p0_direction.md §2.3` 要求 PI **新增版本判据文件**冻结；未冻结前 P3 封存测试 No-Go |
| E0 测量误差容限比例、E2 预测阈值、E6 成本阈值 | ⚠️ 待冻结 | 建议值见对应实验，须运行前由 PI 冻结，不得事后放宽 |

---

## 1. 总表（编号 → 问题 / 数据 / 臂 / 指标 / 判据 / 阶段支撑）

| 编号 | 回答的问题 | 数据 / 切片 | 臂与对照 | 主指标 | 辅指标 | 通过 / 失败判据 | 支撑阶段 |
|---|---|---|---|---|---|---|---|
| **E0** | 测量误差上限是否显著低于待研究效应？ | 探针 40 对 + 少量 A/B 文档；F1/F6 | Full-Prefill / Identity / cache round-trip / 不同 kernel | logit cosine、first-token KL、EM 一致率 | 形状 / 位置 / RoPE / 层映射一致性、`zero_re_prefill` 标志 | **通过**：round-trip bit-identical；cosine≥0.9998（V1 继承锚点）、first-token KL≤0.001、EM 一致率≥0.929；测量误差上限 ≤ 待研究效应的建议 1/3（比例运行前冻结）。**失败**：任一不通过 → P0 不放行 | P0（实现门） |
| **E1** | 强基线是否仍有未被消除的反事实失真？ | 训练 120 / 验证 60；F1–F6（F5 负控、F6 条件） | Self / Identity / affine / consumer / kd_only / score / ridge / Joint | 验证集 `E_CF` 及相对 Self 的 gap | `dual_correct`/`flip_consistency`/`coverage`/`info_gap`、普通 QA | **通过（存在失真）**：`distortion_present ∧ quality_pass`（`phase1_benchmark_decision`）→ 继续 P2/P3。**失败（无失真）**：强基线已近 Self → 按 §8 转边界研究，不预设新方法胜出 | P1（基准） |
| **E2** | 路由与消费哪个更关键、能否预测跨文档失真？ | 训练 / 验证；F1–F4 + F6；`d_A`、`d_B` 分别诊断 | Self / K-only / V-only / Joint；四臂 + 层/头/Token Oracle；对称 Key A/B/C/D | 局部 `Ô−O_S` 分解（routing/consumption 范数、残差）、`E_CF` 改善量 | attention score / KL、top-k 命中率、独立文档外推 | **通过**：分解残差≈0；候选单元在**独立验证文档**上 repair 效果显著优于随机、方向一致（阈值运行前冻结）；产出候选公式。**失败**：只有事后相关 → 机制降级为现象报告 | P2（机制） |
| **E3** | 反事实损失与机制约束是否有独立增益？ | 训练 / 验证 + **封存测试 300**；F1–F6 | `kd_only`(primary) / CE-only / Consumer-space / `CF-RCT-lite` / `CF-RCT-mech` / contrastive / 错文档 / receiver-only adapted | 封存测试**成对 `E_CF` 差异**（CF-RCT vs kd_only）+ 簇级 bootstrap CI | `dual_correct`/`flip_consistency`/`coverage`/`info_gap`、普通 QA、seed 方差、消融 | **通过（method_contribution）**：`ecf_improved ∧ ci_upper<0 ∧ flip_consistency≥0.7` 且 `dual_correct≥0.7`、普通 QA 不退化、mech>lite 且>最强公共基线（≥3 seed、Holm）。**tradeoff / 降级**：`E_CF` 改善但 `dual_correct<0.7` → tradeoff；无增益 → method_downgraded | P3（方法） |
| **E4** | 是否只记住合成模板？ | 同域未见实体 / 未见模板 / 真实文档扩展（real 默认 0，预算允许 80–150） | Joint 为主；最强基线配对 | 分组 `E_CF` + 95% CI | 分组 `dual_correct`/`flip_consistency`/`coverage`、普通 QA | **通过**：未见模板 / 未见实体子集上增益方向一致且 CI 不含 0（或按 §8 明确适用边界）。**失败**：仅在合成域成立 → 声明受限、检查模板泄漏，不宣称通用 | P4（泛化） |
| **E5** | 是否跨结构 / 尺度保持？ | mvp 1.7B→0.6B（等深）、main 4B→1.7B（非等深）、stress 8B→0.6B（离线一次） | Joint 为主；各模型对同基线配对 | `E_CF` 成对差异 + 标准 QA | `normalized_E_CF`（τ=1.0）、成本 | **通过**：至少一组非等深方向上方向一致、CI 与 seed 稳定。**失败**：跨结构不一致 → 报告边界，不宣称跨家族通用 | P4（泛化） |
| **E6** | 是否真正值得替代学生重 Prefill？ | 同 E3/E5 的 Joint 与基线 run | Joint vs 学生 Full-Prefill（锚点，非可部署对比） | 端到端时间 / TTFT | 映射延迟、峰值显存、教师预填成本、磁盘存储 | **通过**：Joint 端到端成本实测低于学生重 Prefill 且质量不退化（阈值运行前冻结）。**失败**：核算后无收益 → 如实报告，不宣称高倍率加速 | P4 / P5（成本） |
| **E7（可选）** | 何时应切换到混合方案？ | 小规模探针 + 质量—预算曲线 | Hidden-state Mapper / 选择性重算 vs 直接 KV 映射 | 质量—预算曲线 | `E_CF`、Joint 任务结果 | **通过**：稳定超过直接 KV 映射才继续。**失败**：不优于直接 KV 映射 → 停止扩展，候选分支不进主线 | P4（候补分支） |

---

## 2. 逐实验设计卡

### E0 — 实现门 / 测量误差上限（P0）

- **问题**：实现与测量误差是否显著小于待研究效应，否则小效应不可信。
- **数据 / 切片**：基础探针 40 对（≥6 模板族），F1 直接事实替换 + F6 长度 / 位置控制；不用于定稿统计。
- **臂与对照**：Full-Prefill（Self）vs Identity 同路径注入 vs cache 保存 / 加载 round-trip；sdpa 与其他 kernel 一致性。d_A / d_B 分别独立 Prefill。
- **主指标**：Identity / round-trip 的 logit cosine、first-token KL、Self EM 一致率。
- **辅指标**：缓存 shape / position_ids / 层映射 / RoPE 元数据 / 哈希；`zero_re_prefill` 标志是否就位。
- **判据**：round-trip bit-identical；cosine ≥ 0.9998（V1 继承一致性锚点，**非 V2 主终点**）、first-token KL ≤ 0.001、EM 一致率 ≥ 0.929；**测量误差上限 ≤ 待研究效应的建议 1/3**（比例须运行前冻结，不得事后放宽）。任一不通过 → P0 不签发放行证书。
- **阶段支撑**：P0 唯一放行门。**注意**：PI 实测本机具备 RTX 4090 24GB、uv 0.9.17、PyPI / ModelScope 可访问与约 361GB 磁盘，具备真实 GPU 证据产出条件；实现 `models/hooks.py` 后须按同判据在真实 GPU 上重跑并通过 E0 门才放行，在此之前维持条件 GO（未放行），mock 的 "51 passed" 不构成当前证据。

### E1 — 基准 / 失真存在性（P1）

- **问题**：既有强 Mapper 在 Self 可答对文档对上是否仍存在反事实响应失真（H1）。
- **数据 / 切片**：训练 120 / 验证 60，实体 / 来源 / 模板簇隔离；F1–F4 语义变化成对，F5 非翻转负控（**不入翻转分母**），F6 长度 / 位置控制。
- **臂与对照**：Self / Identity（锚点）；强基线 affine / consumer / kd_only(primary) / score / ridge；Joint 迁移。全部双向打分，普通 QA 同报。
- **主指标**：验证集 `E_CF` 及各基线相对 Self 的 gap。
- **辅指标**：`dual_correct` / `flip_consistency` / `coverage` / `info_gap`、七类控制组（correct / mismatch derangement / random / zero / shuffled-target / self-identity / receiver-only adapted）。
- **判据**：`distortion_present ∧ quality_pass` → `distortion_exists`（继续 P2/P3）；`no_distortion ∧ quality_pass` → `boundary_study`（按 §8 转边界研究，**不得预设新方法胜出**）。判据来自 `configs/prereg/phase1_benchmark_decision.yaml`，封存后禁止 `changing_tau_on_test` / `dropping_controls` / `selecting_seeds_by_result`。
- **阶段支撑**：P1 放行；为 P2 提供“失真是否值得解释”的前提。

### E2 — 机制诊断（P2）

- **问题**：失真来自 Key 路由还是 Value 消费，能否在独立数据上预测（H2）。
- **数据 / 切片**：训练 / 验证集；F1–F4 与 F6；对 `d_A`、`d_B` **分别**诊断再比较差值。
- **臂与对照**：Self / K-only / V-only / Joint（带 `deployable` 标记）；层 / 头 / Token Oracle 移植；对称 Key A（per-head ridge）/ B（attention-mass 加权）/ C（pre-softmax score 回归，含 weighted）/ D（attention KL / ranking）。V 侧固定 consumer-space Mapper；GQA 按 KV head 聚合；RoPE 前 / 后分别回归。
- **主指标**：`Ô−O_S = (Â−A_S)V_S W_O + Â(V̂−V_S)W_O` 的 routing / consumption 范数与残差；各臂 `(D_trans^arm − D_self)`；Oracle 修复的 `ΔE_CF`。
- **辅指标**：attention score 差 / top-k / TV、token-level KL、候选单元 held-out 命中率。
- **判据**：分解残差≈0（数值自检）；候选单元在**独立验证文档**上的 repair 效果显著优于随机单元、方向一致（阈值运行前冻结）→ 产出候选机制公式。若只有事后热图相关 → 机制主张降级为现象报告（`protocol.md §8`）。对称 Key 判据沿用 `stage1_decision.yaml`（V1 机制基线，C>A/B 且 D≤C 为阳性；routing 改善而 `E_CF`/EM 不动为阴性），**不用于判定 E_CF 主终点**。
- **硬约束**：Oracle 只在离线诊断 / 训练期；不得进入 Joint 推理图；不得把局部热图解释为全模型因果分解。
- **阶段支撑**：P2 放行；为贡献 (2) 与 mech 的机制单元选择提供依据。

### E3 — 方法主实验与消融（P3）

- **问题**：`L_CF` 与 `L_local` 是否带来相对强基线的**独立**增益（H3）。
- **数据 / 切片**：训练 120 / 验证 60 调参；**封存测试 300**（≥24 独立模板 / 主题簇 + 未见模板子集）做主结果；F1–F6 全覆盖，F5 不入翻转分母。
- **臂与对照**：`kd_only`（primary baseline）/ CE-only / Consumer-space / `CF-RCT-lite`（L_KD+L_CF）/ `CF-RCT-mech`（+L_local）/ contrastive / 错文档对比 / shuffled-target training / receiver-only adapted。同数据、同 Forward 预算、同参数量、同调参预算；≥3 seed。
- **主指标**：封存测试上 CF-RCT vs kd_only 的**成对 `E_CF` 差异** + 95% 簇级 paired bootstrap CI。
- **辅指标**：`dual_correct` / `flip_consistency` / `coverage` / `info_gap`、普通 QA、消融表（KD / KD+CF / KD+CF+Local）、seed 方差、超参搜索成本。
- **判据**（`phase3_method_decision.yaml`，不得事后改）：`method_contribution` 需 `ecf_improved=true ∧ ci_upper<0 ∧ flip_consistency≥0.7`，且 `dual_correct≥0.7`、普通 QA 不退化、mech 对 lite 与最强公共基线均有额外增益；`ecf_improved ∧ dual_correct<0.7` → `tradeoff`（如实报告退化）；否则 `method_downgraded`。多比较 Holm；`P>0.05` 不等于等效。禁止 `changing_loss_weights_on_test` / `changing_tau_on_test` / `dropping_seeds`。
- **前置门**：Huber δ 与标签平衡须已用验证集确定并由 PI **新增版本判据文件**冻结；未冻结前本实验封存测试为 **No-Go**。lite 无增益时 `λ_CF` 不得写成贡献；mech 不优于 lite 时“机制引导”不得写成创新。
- **阶段支撑**：P3 放行；贡献 (3) 的唯一来源。

### E4 — 泛化 / 模板记忆检查（P4）

- **问题**：效果是否仅来自合成模板记忆（H4 一部分）。
- **数据 / 切片**：同域未见实体、未见模板子集；真实文档扩展（real 默认 0，预算允许 80–150，人工核验出处与事实扰动）；按来源 / 实体 / 模板簇隔离。
- **臂与对照**：Joint 为主，与最强基线配对；普通 QA 同报。
- **主指标**：分组 `E_CF` + 95% CI。
- **辅指标**：分组 `dual_correct` / `flip_consistency` / `coverage`、同义改写与答案位置变化子集的稳定性。
- **判据**：未见模板 / 未见实体子集上增益方向一致、CI 不含 0 → 支持泛化；若仅在合成域成立 → 按 §8 明确适用边界并检查模板泄漏、容量与语义构造，**不得宣称通用 / 真实世界迁移**。
- **阶段支撑**：P4；决定论文叙事是“通用方法”还是“受限 / 边界研究”。

### E5 — 跨结构 / 尺度（P4）

- **问题**：机制与方法是否跨等深 / 非等深与模型尺度保持（H4）。
- **数据 / 切片**：mvp `qwen3-1.7b-to-0.6b`（等深，28→28）；main `qwen3-4b-to-1.7b`（非等深，36→28）；stress `qwen3-8b-to-0.6b`（离线缓存一次后卸载教师）。
- **臂与对照**：Joint 为主；各对用同一基线族配对；Self / Identity 锚点。
- **主指标**：`E_CF` 成对差异 + 标准 QA。
- **辅指标**：`normalized_E_CF`（τ=1.0）、层映射一致性、失败边界。
- **判据**：至少一组非等深方向增益方向一致且跨 seed / CI 稳定 → 支持跨结构；否则报告边界，不跨家族外推。8B 仅离线压力测试，不与学生训练同时驻留。
- **阶段支撑**：P4；贡献 (3) 的“跨模型”支撑。

### E6 — 系统成本（P4/P5）

- **问题**：Joint 映射是否值得替代学生重 Prefill。
- **数据 / 切片**：与 E3/E5 相同 run 的计时 / 显存记录；256–512 token 文档。
- **臂与对照**：Joint vs 学生 Full-Prefill（评测锚点，不计可部署性能）；教师预填为离线一次性成本，单列。
- **主指标**：端到端时间 / TTFT。
- **辅指标**：映射延迟、峰值显存、教师预填开销、GPU 内存与磁盘存储（理论体积：0.6B/1.7B ≈112 KiB/token、4B/8B ≈144 KiB/token，需实测）。
- **判据**：Joint 端到端成本实测低于学生重 Prefill 且质量不退化（具体阈值运行前冻结）→ 支持系统收益；否则如实报告无收益，**不得在尚未核算时宣称高倍率加速**，也不把单卡短上下文外推到 32K 长上下文。
- **阶段支撑**：P4 / P5；贡献 (3) 中"without target-side re-prefill"的成本侧证据。

### E7（可选）— 候补分支 / 质量—预算曲线（P4）

- **问题**：何时值得从零重 Prefill 切换到 hidden-state 映射或选择性重算。
- **数据 / 切片**：小规模探针（不在主线）。
- **臂与对照**：`HiddenStateMapper`（Ĥ_S=f(H_T) 再经学生 W_K/W_V 投影）/ 选择性重算 vs 直接 KV 映射。
- **主指标**：质量—预算曲线。
- **辅指标**：`E_CF`、Joint 任务结果、参数量。
- **判据**：仅在稳定超过直接 KV 映射时继续；否则停止扩展，不进主线。该方向**非首创范式**，不写成范式创新。
- **阶段支撑**：P4 候补分支；不作为任何贡献层次的必需证据。

---

## 3. 跨实验合规清单（写改审共同遵守）

1. 证据只来自真实 GPU 后端的 `reports/runs/<run_id>/scores.jsonl`；mock 目录单独标注，不混入正式 run_id；报告产物不可回改。
2. 封存测试运行前完成 `protocol.md §9` 固定项 + prereg 机器可读 conditions；封存后禁止改 τ / δ / λ / 删对照 / 按结果挑种子（各 prereg `forbidden_after_run`）。
3. `E_CF` 永远与 `dual_correct` / `flip_consistency` / `coverage` / `info_gap` 同报；F5 不入翻转分母；普通 QA 与反事实 QA 同报。
4. ≥3 seed、簇级 paired bootstrap 10000、Holm；`P>0.05` 不等于等效。
5. 每次运行 `zero_re_prefill=true`；Oracle 不进 Joint 推理图；K-only / V-only 标 `deployable=false`。
6. Huber δ / 标签平衡 / 机制预测阈值的冻结缺口按 `p0_direction.md §2.3`：科学家给建议（δ 标称 1.0，验证集网格 {0.5,1.0,2.0} 选择），**由 PI 新增版本判据文件冻结**；未冻结 → E3 封存测试 No-Go。
7. p0 前置意见（按 PI 实测更正）：总体为**方向 GO / 证据条件 GO（Conditional GO）**——本机具备 RTX 4090 24GB、uv 0.9.17、PyPI / ModelScope 可访问与约 361GB 磁盘，真实 GPU 证据可产出；证据放行的条件为 (a) Huber 阈值按新版本冻结、(b) E0 实现门通过、(c) 真实 run 的 `scores.jsonl` + 审稿人 `bootstrap_ci_report` / `consistency_check` 审计通过，由 PI 裁决。条件满足前 E0–E7 不签发放行，Mock 数字不构成证据。

---

## 4. 交接

- **给工程师**：按本表实现 / 编排 E0–E7 的 run；逐对记录按 `protocol.md` 附录 A schema；每个 run 写 protocol_version / git hash / 配置指纹 / zero_re_prefill 标志；不得把 placeholder δ 当冻结值。
- **给 PI**：批复本表；冻结 E0 误差容限比例、E2 机制预测阈值、E6 成本阈值；用新增版本判据文件冻结 δ 与标签平衡（科学家建议值见 §3 第 6 条 / `docs/algorithm_spec.md §5`）。
- **给写作者 / 审稿人**：图 1–7 与表 1–3 直接读取冻结结果文件生成；贡献措辞按 `protocol.md §10`；审稿重点复核联合报告、δ 冻结、Oracle 隔离三处。

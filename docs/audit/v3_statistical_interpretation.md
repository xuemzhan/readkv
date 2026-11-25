# v3.0 G4 统计分析与解读（新研究）

> 性质：**G4 统计规格 + 预承诺分支对号入座表（已填值、已绑定）**。本文件不回写 `configs/prereg/gpu_followup_v3.0.yaml`（FROZEN），不改任何裁决、数据、运行产物或当前稿件。
> 依据：`configs/prereg/gpu_followup_v3.0.yaml`（FROZEN）、`docs/decisions/gpu_v3_scope_ruling.md`、`docs/decisions/v3_baseline_spec.md`、`docs/decisions/v3_g{1,2}_release.md`、`docs/decisions/v3_e2_{argument,interface,rows}_ruling.md`、`docs/audit/GPU_experiment_plan_2026-11-25.md`。
> 门控：G4（统计 + 独立审阅），**不占 GPU**。
> 数据来源：parent 预置的只读副本 `docs/audit/v3_g4_inputs/`（含 `SHA256SUMS.txt`，已核样本/副本哈希一致）。所有数值均来自其中的 `metrics.json` 与 `scores.jsonl`，**非 pilot、非 mock、非 v2 结果**。

---

## 0. 状态声明（必读）

| 项 | 状态 |
|---|---|
| G4 统计规格 | ✅ §1，口径与 FROZEN prereg §2/§7 一致 |
| 预承诺分支映射 | ✅ §2–§5，逐字取自 prereg §3/§4/§5/§6，**无事后造支** |
| 从 `scores.jsonl` / `metrics.json` 重算的 bootstrap CI | ✅ E5 s1/s2 family CI 由 scores 重算；E2/E1/E5s0/E6 采用归档 from-scores 冻结 CI（见 §1.6） |
| 分支裁决（绑定具体数字） | ✅ §2–§5，每句绑数值 + PRIMARY/SENSITIVITY 两 CI |
| 签署 / 放行 | ✅ **科学家签署，G4-READY；待 reviewer 复核 §6 ledger 与 §7 边界后放行** |

**解锁说明：** 初版本会话因读白名单受限处于 BLOCKED；parent 已将权威产物复制到 `docs/audit/v3_g4_inputs/`（含 E1 30 格、E2 6 格、E5 3 格 + pilot、E6 3 格、G1/G2/G3 报告、数据审计与 E2 锁），本文件据此完成重算与绑定。

**口径纪律：** 所有 `F<24` 标 `exploratory=true`；每 seed 分列、**不 pooled**；PRIMARY = template_family 簇 bootstrap，SENSITIVITY = pair-level，**两者并列**；`degenerate_only` 保持 `NOT ESTIMABLE`（§2.2）；占位符已全部替换，无伪造值。若字段确实缺失，明确写 "不可核验/未记录"，不以近似或 pilot 值代替。

---

## 1. 冻结统计规格（口径不得事后修改）

### 1.1 重采样单位与估计量

对每个 cell，从逐对记录读取 `d_i`（`E_CF,i`、`L_i=Self_i−Joint_i`、`coverage_i`、`dual_i`、`direction_i`）：

- **族内聚合**：`\bar d_f=(1/n_f)Σ_{i∈f} d_i`。
- **PRIMARY 统计量（template_family 簇级）**：族等权均值 `\hatθ=(1/F)Σ_f \bar d_f`；差值必须先在同族内逐对取差再聚合。
- **PRIMARY CI**：cluster bootstrap `B=10000`，有放回抽 `F` 个簇、簇内 pair 整体带入，percentile 95% CI。固定 RNG seed 并记录（本次 E5 重算用 mulberry32(12345)；归档格各自记录 seed，见 §1.6）。
- **SENSITIVITY CI（pair-level）**：同 cell 内 pair 有放回抽样 `B=10000`，percentile 95% CI。**必须与 PRIMARY 并列，不得只报其一**。
- **对比口径**：版本/条件差值用配对/cluster 配对，在同一重采样样本中对两条件取同族取差，不用两独立 CI 重叠替代差 CI。

### 1.2 逐 seed 必报字段

每包每 seed 每条件报告 Self/Joint dual、`L`、`E_CF`（各附 cluster + pair CI）、coverage、方向一致率（附分母）、有效 pair 数、`F`、`exploratory`。全部 seed 分列。

### 1.3 exploratory 规则

`F<24 ⇒ exploratory=true`。本次实测：E1 val=8 family、E1 train 注册=16 family、E2 test=16 family、E5 val=8 family、E6 val=8 family，均 `exploratory=true`。E1 Panel B `entity/template_disjoint_only` 因 `data_task_change=true` 有效对数骤降（见 §2.3），单独核验。

### 1.4 不合并推断（硬约束）

- **E2**：三 seed 是 mapper/calibration seed，非三份独立 test replicate，禁止 pooled 或元分析。
- **E5**：三 cell 是同一额外模型对（Qwen3-4B→1.7B）上的 seed，不与 MVP（1.7B→0.6B）合并。
- **E1**：5 变体 × 3 seed × 2 panel 分列；`degenerate_only` 无 GPU 格。
- 最高重采样单位为 family；局部热图/层头诊断不作全模型因果分解。

### 1.5 结果表（已填；PRIMARY=cluster CI，SENSITIVITY=pair CI）

> 说明：归档 `metrics.json` 提供的是 **E_CF 的 family/pair 双 CI 与 L 的点估计**，未含 L 的 CI（L 非主终点）。主终点为**成对 E_CF 差异**。故表中 `E_CF [cluster CI]` 与 `pair CI` 为实测双区间；`L` 仅列点估计，L 的两条 CI 标记为「未从 scores 重算（非主终点，见 §8）」，不以占位数字替代。dual/coverage/方向一致率来自同一 `metrics.json`。

**E1 Panel A（校准集干预，固定 clean v2.1 val；均 F=8, exploratory=true, pairs=60, n_evaluable 见括号）**

| 条件 | seed | Self dual | Joint dual | L (点) | E_CF [cluster 95% CI] | E_CF pair 95% CI | coverage | 方向一致率(分母) |
|---|---:|---:|---:|---:|---|---|---:|---|
| legacy_bundle | 0 | .8167 | .4833 | .3333 | 5.3633 [2.9211, 7.5882] | [4.3979, 6.3737] | .8667 | .9615 (52) |
| legacy_bundle | 1 | .9000 | .6333 | .2667 | 6.3203 [3.4574, 8.8578] | [5.2367, 7.3648] | .8833 | .9811 (53) |
| legacy_bundle | 2 | .8000 | .4833 | .3167 | 6.4262 [3.7522, 8.8599] | [5.3035, 7.5406] | .8833 | .9245 (53) |
| dedup_only | 0 | .8167 | .4833 | .3333 | 5.3633 [2.9211, 7.5882] | [4.3979, 6.3737] | .8667 | .9615 (52) |
| dedup_only | 1 | .9000 | .6333 | .2667 | 6.3286 [3.4620, 8.8722] | [5.2435, 7.3789] | .8833 | .9811 (53) |
| dedup_only | 2 | .8000 | .4833 | .3167 | 6.4262 [3.7522, 8.8599] | [5.3035, 7.5406] | .8833 | .9245 (53) |
| entity_disjoint_only | 0 | .8167 | .4833 | .3333 | 5.3633 [2.9211, 7.5882] | [4.3979, 6.3737] | .8667 | .9615 (52) |
| entity_disjoint_only | 1 | .9000 | .6333 | .2667 | 6.3203 [3.4574, 8.8578] | [5.2367, 7.3648] | .8833 | .9811 (53) |
| entity_disjoint_only | 2 | .8000 | .4833 | .3167 | 6.4262 [3.7522, 8.8599] | [5.3035, 7.5406] | .8833 | .9245 (53) |
| template_disjoint_only | 0 | .8167 | .4833 | .3333 | 5.3633 [2.9211, 7.5882] | [4.3979, 6.3737] | .8667 | .9615 (52) |
| template_disjoint_only | 1 | .9000 | .6333 | .2667 | 6.3203 [3.4574, 8.8578] | [5.2367, 7.3648] | .8833 | .9811 (53) |
| template_disjoint_only | 2 | .8000 | .4833 | .3167 | 6.4262 [3.7522, 8.8599] | [5.3035, 7.5406] | .8833 | .9245 (53) |
| fully_repaired | 0 | .8167 | .4167 | .4000 | 7.0563 [3.7011, 10.2588] | [5.6830, 8.4892] | .8667 | .7308 (52) |
| fully_repaired | 1 | .9000 | .4167 | .4833 | 7.6022 [3.8938, 10.7323] | [6.2087, 8.9684] | .8833 | .7925 (53) |
| fully_repaired | 2 | .8000 | .4000 | .4000 | 8.4304 [5.0937, 11.4264] | [6.9726, 9.8683] | .8833 | .7358 (53) |

**E1 Panel B（验证集干预，固定 clean mapper；`F=8, exploratory=true, pairs=60`；entity/template 为 `_r2`、`data_task_change=true`）**

| 条件 | seed | Self dual | Joint dual | L (点) | E_CF [cluster 95% CI] | E_CF pair 95% CI | coverage | 方向一致率(分母) |
|---|---:|---:|---:|---:|---|---|---:|---|
| legacy_bundle | 0 | .6833 | .3500 | .3333 | 4.9073 [2.7814, 6.8083] | [3.9923, 5.8306] | .8000 | .8333 (48) |
| legacy_bundle | 1 | .6000 | .3000 | .3000 | 5.0947 [3.1320, 6.9876] | [4.1469, 6.0543] | .8167 | .7551 (49) |
| legacy_bundle | 2 | .6500 | .3833 | .2667 | 5.1133 [2.9993, 7.1971] | [4.1223, 6.0869] | .8000 | .8542 (48) |
| dedup_only | 0 | .6833 | .3500 | .3333 | 4.9073 [2.7814, 6.8083] | [3.9923, 5.8306] | .8000 | .8333 (48) |
| dedup_only | 1 | .6000 | .3000 | .3000 | 5.0947 [3.1320, 6.9876] | [4.1469, 6.0543] | .8167 | .7551 (49) |
| dedup_only | 2 | .6500 | .3833 | .2667 | 5.1133 [2.9993, 7.1971] | [4.1223, 6.0869] | .8000 | .8542 (48) |
| entity_disjoint_only `_r2` | 0 | .1500 | .1167 | .0333 | 0.6211 [0.0000, 1.5141] | [0.3424, 0.9287] | .2333 | 1.0000 (14) |
| entity_disjoint_only `_r2` | 1 | .1667 | .1333 | .0333 | 0.8507 [0.0000, 2.0814] | [0.4350, 1.3268] | .2333 | .7857 (14) |
| entity_disjoint_only `_r2` | 2 | .1500 | .1167 | .0333 | 0.8783 [0.0000, 2.1459] | [0.4630, 1.3406] | .2333 | .9286 (14) |
| template_disjoint_only `_r2` | 0 | .6833 | .4167 | .2667 | 5.3881 [3.2800, 7.4541] | [4.3599, 6.4822] | .8167 | .7551 (49) |
| template_disjoint_only `_r2` | 1 | .6333 | .4000 | .2333 | 5.2786 [3.2328, 7.2574] | [4.2473, 6.3656] | .8167 | .7143 (49) |
| template_disjoint_only `_r2` | 2 | .6833 | .4333 | .2500 | 5.2368 [3.1482, 7.1906] | [4.2203, 6.2315] | .8000 | .8333 (48) |
| fully_repaired | 0 | .8167 | .4167 | .4000 | 7.0563 [3.7011, 10.2588] | [5.6830, 8.4892] | .8667 | .7308 (52) |
| fully_repaired | 1 | .9000 | .4167 | .4833 | 7.6022 [3.8938, 10.7323] | [6.2087, 8.9684] | .8833 | .7925 (53) |
| fully_repaired | 2 | .8000 | .4000 | .4000 | 8.4304 [5.0937, 11.4264] | [6.9726, 9.8683] | .8833 | .7358 (53) |

**E2（held-out test，300 对 / 16 family，`exploratory=true`，不 pooled；flip 分母 227，排除 F5/F6）**

| mapper | seed | Self dual | Joint dual | L (点) | E_CF [cluster 95% CI] | E_CF pair 95% CI | coverage | 方向一致率(分母) |
|---|---:|---:|---:|---:|---|---|---:|---|
| affine | 0 | .9467 | .2800 | .6667 | 8.5007 [6.4693, 10.3147] | [7.9328, 9.0707] | .8767 | .6564 (227) |
| affine | 1 | .9467 | .3667 | .5800 | 8.0445 [6.0141, 9.8429] | [7.5018, 8.5863] | .8767 | .6564 (227) |
| affine | 2 | .9467 | .3200 | .6267 | 8.3940 [6.3720, 10.1744] | [7.8552, 8.9337] | .8767 | .6828 (227) |
| kd_only | 0 | .9467 | .7633 | .1833 | 7.0169 [5.3368, 8.5137] | [6.5889, 7.4238] | .8767 | .9780 (227) |
| kd_only | 1 | .9467 | .5933 | .3533 | 7.2834 [5.5152, 8.8083] | [6.8514, 7.7101] | .8767 | .9119 (227) |
| kd_only | 2 | .9467 | .6667 | .2800 | 7.3814 [5.6227, 8.9224] | [6.9623, 7.8031] | .8767 | .9295 (227) |

**E5（第二模型对 Qwen3-4B→1.7B，val 60 对 / 8 family，`exploratory=true`，不跨模型对 pooled；`τ=1.0`）**

| seed | Self dual | Joint dual | L≈(点, 由 dual 差) | E_CF [cluster 95% CI] | E_CF pair 95% CI | coverage | 说明 |
|---|---:|---:|---:|---|---|---:|---|
| 0 | .8167 | .1500 | ~.667 | 6.9854 [3.914, 9.929] | [5.8161, 8.1401] | .8833 | E_CF 均值精确复现；cluster CI 由 scores 重算；pair CI 归档+重算一致 |
| 1 | .8667 | .1833 | ~.683 | 7.6323 [4.512, 10.579] | [6.3599, 8.9240] | .8833 | 均值 7.632291666666666 精确复现；双 CI 由 scores 重算 |
| 2 | .8333 | .1667 | ~.667 | 7.6615 [4.407, 10.700] | [6.4343, 8.9100] | .8833 | 均值 7.661458333333333 精确复现；双 CI 由 scores 重算 |

> E5 `transfer_health.transfer_broken=true`（joint 质量塌陷、control 未被支配），定义为**失败边界，不是「保效用扭曲」的正证据**；`frozen verdict=None` 未变。该字段为独立标注，不代替主终点。

**E6（`v3-BM-MLP-KD` 内部对照，1.7B→0.6B，val 60 对 / 8 family，`exploratory=true`；cluster/pair CI 由 scores 重算）**

| seed | Self dual | Joint dual | E_CF [cluster 95% CI] | E_CF pair 95% CI | 同对 affine 参照 (E1-A legacy) |
|---|---:|---:|---|---|---|
| 0 | .8167 | .2167 | 8.2173 [4.403, 11.563] | [6.873, 9.561] | 5.3633 [2.9211, 7.5882] / joint dual .4833 |
| 1 | .9000 | .3667 | 8.5934 [4.662, 11.932] | [7.171, 10.008] | 6.3203 [3.4574, 8.8578] / joint dual .6333 |
| 2 | .8000 | .2167 | 9.4987 [5.345, 13.167] | [7.898, 11.061] | 6.4262 [3.7522, 8.8599] / joint dual .4833 |

### 1.6 CI 来源与复核（诚实口径）

- **E2 / E1（30 格）/ E5 s0**：直接使用各 `metrics.json` 的 **from-scores 冻结 bootstrap CI**（E1: `ci_family` + `ci_pair_sensitivity`；E2: `template_family_ci` + `pair_level_ci`；E5 s0: `ci`=pair-level + 本次由 scores 重算 family CI）。已核对：E1 legacy s0 与 E5/E6 的点均值可由原始 `scores.jsonl` 精确复现（diff=0），故归档 CI 为 from-scores 产物，可引用。
- **E5 s1/s2、E6 s0/s1/s2**：`metrics.json` 只给点均值（pair CI 仅 E5 有），family cluster CI 与 E6 pair CI 由 `scores.jsonl` 的 joint 臂逐对 `E_CF` 重算：`B=10000`、percentile 95%、8 个 template_family 簇；其中 s1/s2/E6 用固定 mulberry32(12345)（E5 s0 family CI 由前序会话以同法定 seed 重算，已验证点均值 diff=0，故各 seed 簇 CI 仅在 RNG 噪声内微差，不影响分支判读）。校验：s1/s2/E6 点均值与 `metrics.json` 精确一致；s1/s2 重算 pair CI 与归档 pair CI 在 RNG 噪声内一致（s1 [6.374, 8.923] vs 归档 [6.3599, 8.9240]；s2 [6.402, 8.939] vs 归档 [6.4343, 8.9100]）。
- **L 的双 CI**：归档 `metrics.json` 仅含 L 点估计；本次未对 30+ E1 score 文件逐对重算 L 的 CI。L 非主终点，主终点（成对 E_CF 差异）双 CI 齐备。此项如实记为「未重算」，见 §8。
- 所有差值（variant−legacy）按 §1.1 同族配对口径解释；下表报告的点差为 E_CF 均值差，方向跨 seed 稳健性逐格核对。

---

## 2. E1：单缺陷干预筛查（prereg §3 分支对号入座）

### 2.1 六种版本条件（已全部报告）

`legacy_bundle`、`dedup_only`、`degenerate_only`、`entity_disjoint_only`、`template_disjoint_only`、`fully_repaired`。Panel A 用冻结 clean v2.1 val（G2 §1，`fully_repaired/val_seed{k}`）；Panel B 为验证集干预（受 `data_task_change` 约束）。5 GPU 变体 × 3 seed × 2 panel = 30 格（`degenerate_only` 不在其中）。

### 2.2 `degenerate_only`：不可估计，禁止补数

`must-flip` 退化对属标签/任务有效性缺陷，不进 ridge 标签监督拟合；规定动作是旧 logits CPU replay，但归档 `scores.jsonl` 缺逐 pair logits，无法重算。故：
- `degenerate_only`（Panel A & B）：**`NOT ESTIMABLE from archived scores`**。
- **不得**以近似/占位/pilot 值冒充。这是能力边界，非结果掩盖。

### 2.3 Panel B `entity/template_disjoint_only`：`data_task_change=true`

这两变体 val 文本改变（`data_task_change=true`），CPU replay 无效（旧 logits 对应旧文本），必须 GPU 前向。6 个 `_r2` rerun 以 `--allow-input-change-gpu-forward / data_task_change=true` 执行。实测后果：`entity_disjoint_only _r2` 三 seed coverage 从 .80 骤降至 **.2333**、n_evaluable 48/49→**14**、joint dual .1167–.1333、E_CF 0.62–0.88（cluster CI 下界触 0）；与 pure label-rescore 格严格分开报告，**不写"纯单缺陷效应"**。

### 2.4 预承诺判读分支（逐字来自 prereg §3 `interpretation.branches`）

| 分支 | 冻结触发条件 | 绑定证据（实测） | 裁定 |
|---|---|---|---|
| `single_defect_associated` | 某单缺陷变体相对 legacy **复现大部分差距**，方向跨 seed 稳健 | Panel A：dedup/entity/template 三 seed 与 legacy **数值完全相同**（如 s0 均 E_CF 5.3633 [2.9211,7.5882]，s1 均 6.32，s2 均 6.43；joint dual 亦同）；无任何单缺陷复现差距 | **不成立** |
| `interaction_or_combination` | 无单一缺陷能解释，差距主要在 `fully_repaired` 或组合 | Panel A `fully_repaired`：s0 7.0563 [3.7011,10.2588]、s1 7.6022 [3.8938,10.7323]、s2 8.4304 [5.0937,11.4264]，均高于对应 legacy（+1.69/+1.28/+2.00）；joint dual 反降（.4167/.4167/.4 vs .4833/.6333/.4833）；方向一致率降至 .7308/.7925/.7358。Panel B 同样（fully 7.06/7.60/8.43 vs legacy 4.91/5.09/5.11） | **成立（主）** |
| `seed_or_composition_sensitive` | 方向依赖 seed 或样本构成变化 | 构成证据：`dedup_only` s1 移除 1 行（119/120，训练集内去重，**非** train–val overlap 清理）；`fully_repaired` 与 legacy 由不同生成器 commit/RNG 全量重生成（版本差异）；Panel B `entity_disjoint_only _r2` coverage .2333、E_CF 0.62–0.88（构成改变后量级全变），`template_disjoint_only _r2` 仍在 ~5.2–5.4 | **成立（Panel B / 构成维度）** |

**E1 分支裁定句（绑定数值 + 双 CI）：** 在给定生成器/样本构造下，**未观察到任何单一缺陷与 mapper 指标变化的受控关联**（三单缺陷 Panel A 与 legacy 逐 seed 完全相同）；E_CF 差距集中在 `fully_repaired`（Panel A s2 8.4304 [5.0937,11.4264] vs legacy 6.4262 [3.7522,8.8599]，pair CI [6.9726,9.8683] vs [5.3035,7.5406]），符合 `interaction_or_combination`；同时 Panel B 的样本构成变化（`data_task_change=true`，entity coverage .2333）与版本全量重生成使结论对构成/seed 敏感，符合 `seed_or_composition_sensitive`。**两个匹配分支均如实报告，不择一**（prereg §8）。禁止 claim：因果贡献分解、泄漏普遍制造假阳性、单一缺陷解释全部差距；`fully_repaired` 是版本差异，不是因果分解。

---

## 3. E2：此前未评测的 held-out split（prereg §4）

- 命名：**previously unevaluated held-out split**，**不称 sealed**。test = 同一固定 300 对 / 16 family；整文件哈希 `f910f1f1…a894a`，test split 派生哈希 `c5450013…769a7a2`（`v3_e2_{argument,rows}_ruling.md`）。
- one-shot：2 次 0 调用 preflight + 1 次 pre-scoring REFUSED（不消耗科学 one-shot）+ 1 次唯一权威 pass；evaluator 进程调用 2、权威评分 pass = 1；入口 SHA `da80afdc…b8f6f`（`v3_g3_batch2_report.md` §9，已复核一致）。技术量（显存/耗时/forward 计数/cache 形状/Self–Identity 差分）**冻结入口未记录，不可独立核验**，不以 pilot 值代替（G3 batch2 §5）。
- `exploratory=true`（16<24）；三 seed 不 pooled。

| 分支 | 冻结触发条件 | 绑定证据（实测） | 裁定 |
|---|---|---|---|
| `held_out_consistent` | test 上方向复现且区间与 val 一致（逐 affine/kd_only seed，Self/Joint dual、L、E_CF、coverage、flip + family CI） | 6 格 Self dual 恒 .9467；affine Joint dual .28/.3667/.32 明显低于 kd_only .7633/.5933/.6667；L affine .6667/.58/.6267 > kd_only .1833/.3533/.28；E_CF affine 8.5007 [6.4693,10.3147] / 8.0445 [6.0141,9.8429] / 8.3940 [6.3720,10.1744] 高于 kd_only 7.0169 [5.3368,8.5137] / 7.2834 [5.5152,8.8083] / 7.3814 [5.6227,8.9224]；方向与 val 阶段 frozen 配置记录一致，family CI 双侧较宽且 exploratory，pair CI 更窄（如 affine s0 [7.9328,9.0707]）；coverage .8767、flip 分母 227（排除 F5/F6）方向一致率 affine .6564–.6828、kd_only .9119–.9780 | **成立** |
| `held_out_failure` | test 上失败 | 未见方向反转或区间崩塌（joint 质量按配置分层符合设计） | 不成立 |

**E2 裁定句：** 固定配置在此前未评测 held-out split 上**方向复现**（affine 的 joint 传输弱于 kd_only，L 与 E_CF 方向一致），family 主区间与 pair 敏感区间并列、均 exploratory。用词仅限"固定配置外推表现"（Jain 等意义上的 previously-unevaluated held-out），**不是 sealed test、不是独立 replicate（3 seed 非 3 份 test）、不作普遍泛化**；失败不得回 val 调整后重称独立 test。

---

## 4. E5：第二模型对有限复验（prereg §5）

- 模型对 Qwen3-4B→1.7B（36→28 proportional layer map）；**仅 affine × 3 seed = 3 格**（`v3_baseline_spec.md §3`），不追加 kd_only；P4 仍 **NO-GO**。
- 只用 validation；`exploratory=true`（8 family）；不跨模型对 pooled；不与 MVP affine 合并。

| 分支 | 冻结触发条件 | 绑定证据（实测） | 裁定 |
|---|---|---|---|
| `replicated_on_one_extra_pair` | 同方向（Self/Joint dual、L 的方向） | 三 seed Self dual .8167/.8667/.8333 高、Joint dual .15/.1833/.1667 低，Self−Joint 差 ~.667/.683/.667（方向与 MVP 一致）；E_CF 6.9854 [3.914,9.929] / 7.6323 [4.512,10.579] / 7.6615 [4.407,10.700]，pair CI 更窄 [5.8161,8.1401]/[6.3599,8.9240]/[6.4343,8.9100] | **成立（仅限方向）** |
| `not_replicated` | 失败 | 未见方向反转 | 不成立 |

**E5 裁定句：** 在**一个额外模型对**（4B→1.7B）上，Self/Joint dual 与 L 的方向复现（joint 质量相对 self 塌陷，方向同 MVP），E_CF 三 seed family 主 CI 与 pair 敏感 CI 均绑定如上。**不称跨模型泛化；不删该对、不另择对**。关键边界：该对 `transfer_health.transfer_broken=true`、joint E_CF 未支配无信息控制（info_attribution mismatch .289/random .915/zero .140）——复现的是**退化方向/失败边界**，不是"信息正确利用"的正证据；`E_CF` 单独下降不足以证明正确利用，须与 dual、方向一致率、coverage、控制组差距联合报告（§7.6）。

---

## 5. E6：预算匹配内部对照（prereg §6 + `v3_baseline_spec.md`）

- **复现门 NOT PASSED**（KV-Lingo / CacheLink 仅摘要级；代码/权重/许可/训练目标/逐层映射均未核验）→ 不得称任一为 faithful baseline。采用冻结的**明确命名内部对照** `v3-BM-MLP-KD`，**不称已发表方法基线**。
- `v3-BM-MLP-KD`：逐层逐 KV head 线性 `W∈R^{128×128}`（**无 bias**），K/V 各一套，28×8×(128×128)；参数 **7,340,032`（= kd_only trainable_params，精确相等）**；同 120 训练对、8 epochs、lr=1e-3、Adam、seed 0/1/2；`L_KD=Σ_sides KL(log_softmax(mapped)‖log_softmax(self), log_target=True, reduction='batchmean')`，`loss=1.0·L_KD+1e-4·reg`（`lam_cf=0, reg=0`）；仅梯度回传映射缓存，学生冻结；`zero_re_prefill=true`。
- prereg §6 **无结果条件分支**（success_criteria 为事前定义）；E6 只能是描述性预算匹配内部对照比较，**不自动升级为"方法增益"**。

**强制分项披露（已填，来自 G2 pilot §4.2 / E6 `metrics.json` / G3 报告）：**

| 项 | 值 |
|---|---|
| 参数量 | 7,340,032 = W_K(28×8×128×128)+W_V(同) = 2×28×8×16384；bias_params=0；init=identity；与 kd_only trainable_params **精确相等（容差 0）** |
| 目标明文 | BM：`1.0·L_KD + 1e-4·reg`（KL 如上，reg=0）；ridge affine λ=1e-3；kd_only 配置 epochs=8/lr=1e-3/lam_kd=1.0/lam_cf=0/lam_reg=1e-4 |
| 优化步 / 前向 | 每 seed 960 optimizer steps；训练 student forward 1,920（=2×960）；eval student forwards 360、captures 721（三 seed 同） |
| GPU 训练秒 / 墙钟 | s0 train_sec 494.9 / elapsed 521.8；s1 471.7 / 500.8；s2 479.5 / 507.1（秒） |
| 峰值显存 | allocated 4,608.6 MiB / reserved 4,674.0 MiB（4832423936 / 4901044224 bytes，三 seed 同） |
| 数据 / 审计 | n_train=120、n_val=60、n_scores=180；doc_len=25、query_len=7、doc token fed=0；zero_re_prefill=true |
| 复现门 / 身份 | `reproduction_gate=NOT_PASSED`、`faithful_published_baseline=false`、`authoritative=false/pilot=true`（G2 技术 pilot 口径） |

**描述性比较（不升级为增益）：** BM 三 seed E_CF 8.2173 [4.403,11.563] / 8.5934 [4.662,11.932] / 9.4987 [5.345,13.167] 高于同对 affine 参照（E1-A legacy：5.3633 / 6.3203 / 6.4262），但 BM 的 **joint dual 更低**（.2167/.3667/.2167 vs affine .4833/.6333/.4833）。这正是"`E_CF` 单独下降不足以证明正确利用"的实例：仅看 E_CF 会误判 BM 更优，联合 dual/方向一致率则不然。参数量相似 ≠ 算力/目标公平（BM 与 ridge affine 目标不同、训练成本不同）。**排名不解释为方法增益**；affine/kd_only 同模型对 val 的完整双 CI 未随本次 staging 提供，故 BM 与 kd_only 的排序不可从本次输入核验，记为"不可核验"，不臆断。

---

## 6. 失败 / 中断 / 偏差入账（ledger，已核）

| 事件 | 权威状态 | 处置 |
|---|---|---|
| `v3_E1_B_entity_disjoint_only_s0`（无 `_r2`） | **ABORTED（缺显式 flag）**，保留 | 非权威；正式格用 `_r2`；入账说明 |
| 6 `_r2` reruns（entity/template × s0/s1/s2 Panel B） | `--allow-input-change-gpu-forward / data_task_change=true` | 标 `data_task_change=true`，不与原始格混并；逐格入账（§2.3） |
| `v3_E6_BM-MLP-KD_s0_smoke`（无 `_r2`） | **ABORTED（CUDA/CPU device bug）**，保留非权威（G2 §2） | 不复用；正式格用修复后 `_r2`（G2 §4.2） |
| `v3_E5_pilot_s0` | **NON-AUTHORITATIVE pilot**，含 `PILOT_NOTICE.json` | 不作结果；不与正式 E5 合并 |
| E2 两次 0 调用 preflight（参数口径/接口，`v3_e2_{argument,interface}_ruling.md`） | 0 次 evaluator 成功调用 | 不消耗 one-shot（已复核 G3 batch2 §2） |
| E2 test-row 门 REFUSED（整文件含 probe/train/val 行，`v3_e2_rows_ruling.md`） | 1 次进程调用，评分前拒绝、0 次权威评分 | 不消耗科学 one-shot |
| E2 技术量不可核验（G3 batch2 §5/§9） | 冻结入口未持久化显存/耗时/forward/cache 差分 | 标"不可核验"，不以 pilot 值代替 |
| E1 literal 命令误把 `legacy/val_seed0.jsonl` 标为 clean val | G1 门控拒绝（未加载模型、无分数） | bridge smoke 取代，不产权威结果（G2 §1） |
| `degenerate_only` | 无 GPU 格；CPU replay 因归档缺逐 pair logits 不可执行 | `NOT ESTIMABLE`，不补数（§2.2） |
| 读白名单初版 BLOCKED | parent 已 stage 只读副本至 `docs/audit/v3_g4_inputs/` | 已解锁；核 SHA256SUMS 样本一致 |

**清点说明：** 权威 dirs = E5 3 + E6 3 + E2 1 dir(6 cells) + E1 30 cells（+ retained aborts / `_r2` 为非权威或重跑标记）。任务所述 39/37 与 6 `_r2`、1 retained abort 的对应以 manifest 为准；本次 staged 副本已逐格核到上述权威产物，未发现口径冲突。

---

## 7. 本研究**不识别**什么（claim boundaries 汇总）

1. **E1**：仅识别"给定生成器/样本构造下，单类改动与 mapper 指标的受控**关联**"。**不是**因果贡献分解，**不是**泄漏普遍制造假阳性，**不是**单一缺陷解释全部差距；不识别缺陷间交互的定量大小；`fully_repaired` 是版本差异。
2. **E2**：固定配置在**此前未评测 held-out split** 上的外推表现。**不是** sealed test，**不是**独立 replicate（3 seed 非 3 份 test），**不作**普遍泛化；失败不得回 val 调整后重称独立 test；技术量不可核验。
3. **E5**：**一个额外模型对**上的方向复验（且为失败边界方向）。**不是**跨模型泛化；`transfer_broken=true`、控制未被支配，**不是**"信息正确利用"正证据；不删失败对、不另择对；P4 仍 NO-GO。
4. **E6**：预算匹配**内部对照**的描述性比较。**不是** faithful published baseline（复现门未过）；参数量相似 ≠ 算力/目标公平；E_CF 升高伴随 joint dual 下降，不得包装为方法增益。
5. **统计**：所有 `F<24` 均 `exploratory=true`；不跨 seed / 不跨模型对 pooled；PRIMARY 必为 family 簇 bootstrap，pair-level 仅敏感性；不把局部热图当全模型因果分解；Oracle 信号只在训练/离线诊断，不进推理图（zero re-prefill）。
6. **终点**：`E_CF` 单独下降**不足以**证明信息正确利用——必须与 Self/Joint dual、方向一致率、coverage、无信息控制组差距联合报告（E5/E6 即反例）。
7. **范围**：新研究另立；当前 TMLR 稿件只读；v2.1–v2.9 冻结判据一字不回写；贡献(1)(2) 撤回、(3) withheld；P2/P3/P4 永久放弃；不重跑 v2.7 2×2 / A00/A11 序列评分；agent 不代为投稿。

---

## 8. 复现备注与未重算项（诚实边界）

- 重算脚本从 `scores.jsonl` 读取，**不手写数字**；family/pair 数逐 seed 落盘。本次 E5 s1/s2 与 E6 CI 由 joint 臂逐对 `E_CF`（行号 ≡3 mod 10）重算，`B=10000`、mulberry32(12345)、percentile 95%，点均值与 `metrics.json` 精确一致（diff=0），pair CI 与归档在 RNG 噪声内一致。
- bootstrap RNG seed 归档格各自记录（E1 seed=0/1/2 对应；本次重算固定 12345）；`B=10000`；差值用族内配对口径。
- **未重算项（明确，不伪造）：** ① `degenerate_only` CPU replay（缺逐 pair logits，`NOT ESTIMABLE`）；② 30+ E1 格与 E2 的 **L 双 CI**（归档仅 L 点估计；主终点成对 E_CF 双 CI 齐备）；③ E2 技术量（显存/耗时/forward/cache 差分，冻结入口未记录，one-shot 不得重跑补采）；④ E6 与 kd_only 同对排序（本次 staging 未提供 kd_only val 双 CI）。
- 全部占位符已替换；分支裁决句见 §2.4 / §3 / §4 / §5。后续由 reviewer 复核 §6 ledger 与 §7 边界，确认后 G4 放行。

---

**状态：科学家签署 — 数值已产出、分支已绑定、G4-READY（待 reviewer 复核放行）。** 所有数字来自 staged 权威副本；不可得字段按 §8 明确标注，未伪造任何值或区间。

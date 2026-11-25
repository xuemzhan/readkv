# 完整候选评分（protocol-v2.8）统计判读与三分支归类 —— `_b0` 权威集

> 角色：scientist（统计判读；由子代理按 handoff 接手执行并自行从 `scores.jsonl` 复核）。
> 日期：2026-11-24。性质：**只读复算 + 判读归类**；未改代码 / 数据 / 判据 / 论文 / 运行产物 / 其他报告。
> 唯一权威集：6 个 `reports/runs/audit_seq_{A11,A00}_s{0,1,2}_b0/` 正式格；`git rev-parse HEAD` =
> `35e78e06917eb16461d6c925c8b0a435e99fd39c`（B0）。旧 id 已 `superseded`，不参与本判读。
> 冻结判据：`configs/prereg/full_candidate_scoring_v2.8.yaml` §3/§6/§7；基线裁决：
> `docs/decisions/sequence_scoring_baseline_ruling.md` §7.3（R4 交付物）。
>
> **预承诺声明**：v2.8 §7 三分支条件在结果前已冻结。本文**按预承诺条件对号入座，无事后择支**，
> 归档归类为分支① `consistent_across_scoring`（见 §4）。

---

## 0. 结论摘要

1. **分支归类：① `consistent_across_scoring`**。三组 A11 整串（`full`）L 均为正；每个 seed 的
   A11−A00 点估计在 `first` / `full` / `length_normalized` 三口径下同号（均正）；长度归一不改变判读。
   A11 s1 的 `reading_diff` 主区间虽不含零，但 `L_full` 仍为正、A11−A00 未消失，故**不触发分支②**；
   归一后方向不变，故**不触发分支③**。措辞仅到"**在两种候选评分下点估计方向一致**"，不升级为强显著性，
   不作方法/贡献主张。
2. **三项比较关键数值（主分析 F1–F4，6 族，样本加权 template_family 主 CI）**：
   - `reading_diff = L_full − L_first`（A11）：s0 `+0.0435 [−0.2553, +0.3182]`、
     s1 `−0.2174 [−0.3404, −0.1304]`、s2 `+0.0870 [−0.1087, +0.3043]`。
   - `cell_diff = A11 − A00`：first `+0.4348 / +0.7474 / +0.3860`；full `+0.4783 / +0.5062 / +0.4730`；
     length_normalized `+0.5000 / +0.5714 / +0.5817`（s0/s1/s2），区间见 §3.3。
   - `reading_of_diff`：s0 `+0.0435 [−0.2612, +0.3211]`、s1 `−0.2412 [−0.3978, −0.1054]`、
     s2 `+0.0870 [−0.1064, +0.3043]`。
3. **与 handoff / `summary_b0` 的不一致（如实记录）**：handoff 明确标注为"全 60 对"的 L 值、
   `cell_diff` 以及 `summary_b0` §1/§3/§4 的主表、E_CF、coverage，**复算后逐项一致**（见 §2.2/§6）；
   但它们用的是 v2.8 §3 的**次要集（全部 60 对、8 族）**，不是 §3 的**主分析集（F1–F4 候选文本不同且
   金标签 A/B 交换、6 族）**。主分析集的点估计与 handoff/`summary_b0`  headline 数值不同（§6.1），
   方向判读不变。这是**分母口径差异**，不是逐对分数复算不一致；两套数值在本文中分列，不混写。

---

## 1. 口径、定义与证据路径

### 1.1 分析集（v2.8 §3 `analysis_sets`）

| 集 | 定义 | A11 各 seed | A00 各 seed | 每格簇数 |
| --- | --- | --- | --- | --- |
| **主分析**（本文主表） | F1–F4 且 `candidate_texts_differ` 且 `f1_f4_gold_swapped`，按 index 文件 `primary_analysis=true` 选取 | 46 / 46 / 46 | 42 / 42 / 41 | 6 个 `template_family` |
| **敏感性**（对齐旧表） | 全部 60 对（含 F5/F6、相同候选） | 60 / 60 / 60 | 60 / 60 / 60 | 8 个 `template_family` |

两集均按 `pair_id + sample_hash` 将 `scores.jsonl` 与 `data/audit_2x2/sequence/{cell}_seed{s}.jsonl`
逐对联接；自检 6 格键集合完全一致，`primary_analysis` 计数与 `manifest.json::denominators` 一致。
old / repaired 是两套验证样本，**不混算**；两读数始终用同一格内相同样本。

### 1.2 指标定义（逐对重算，三读数分别计算）

- `dual_correct`：由 `prediction[A/B]` 与 `gold[A/B]` 重算双侧正确（0/1），与归档 `dual_correct` 逐对一致（0 处不符）。
- `Self dual` / `Joint dual`：对应 `arm=self` / `arm=joint` 的 `dual_correct` 均值；
  **`L = Self dual − Joint dual`**（百分点；表中以比例 0–1 记，如 0.383 = 38.3 点）。
- `E_CF`：逐对归档值（self 与 joint 逐对等值，0 处不符）取均值；**只在各评分口径内计算，
  绝不跨口径比绝对尺度**（`full` 为 logprob 之和，`first` 为首项，`length_normalized` 为除长度）。
- `coverage = mean(evaluable)`，`evaluable := |D_self| > 0.1`（`self_threshold=0.1`，来自 config）；
  `D = g[A] − g[B]`，逐对由 `scores.g` 复核一致。
- `flip = (sign(D_joint) == sign(D_self))`，**分母仅 evaluable 样本**（非 evaluable 记为 `None`，不进分母）；
  flip 率 = evaluable 子集的均值，逐对与归档 `flip_consistency` 一致。主分析集本身仅 F1–F4，
  与 v2.8 §3 `denominator_audit` 中"flip 排除 F5+F6 的 v2.3 口径"相容；不与 F1–F4 之外分母混写。

### 1.3 三项比较与 bootstrap（v2.8 §6；`src/readkv/stats/bootstrap.py::cluster_bootstrap`）

| 比较 | 定义 | 实现 |
| --- | --- | --- |
| `reading_diff` | 同格内 `L_full − L_first`（配对差） | 逐对 `dL = (self_full−self_first) − (joint_full−joint_first)`，格内重采样 |
| `cell_diff` | 每 seed `A11 − A00` 的 L 差（各读数分别） | 逐对 L 值，A11 与 A00 两个验证集**独立**重采样后相减 |
| `reading_of_diff` | `cell_diff(full) − cell_diff(first)` | 先在各验证集内取逐对 `dL`，再对两版本**独立**重采样后相减（等价于两集 reading_diff 之差） |

- 每次重采样取**抽中样本之和 ÷ 抽中样本数**（样本加权点估计口径，与 `cluster_bootstrap` 一致）；
  百分位 95% CI；**10,000 resamples**；RNG 种子取该格 seed（s=0/1/2），跨格对比用同一 RNG 顺序抽取
  A11 与 A00（独立抽样流）。
- 主聚类单元 = `template_family`；主分析 6 族、全 60 对 8 族，**均 < 24 ⇒ `exploratory=true`，不作强显著性推断**。
- **pair-level 敏感性**：以 `pair_id` 为簇（每簇 1 对）作同样本加权重采样；两格对比仍独立重采样。
- **族等权敏感性**（第二轮复审 §1.2 要求）：逐族先取均值，抽中族等权平均，点估计也写为族均值之差；
  与主口径并列，不替代主口径。`summary_b0` §2 的 `reading_diff` 主 CI 已按样本加权口径复现一致（§6.2）。
- 每 seed 独立报告，跨 seed 只做计数/范围汇总，不池化（v2.8 §6 `reporting_rule`）。

### 1.4 证据路径

- 权威逐对数据：`reports/runs/audit_seq_{A11,A00}_s{0,1,2}_b0/{scores.jsonl,metrics.json,config.json}`
- 样本身份/分母标志：`data/audit_2x2/sequence/{A11,A00}_seed{0,1,2}.jsonl`、`data/audit_2x2/sequence/manifest.json`
- 判据/裁决：`configs/prereg/full_candidate_scoring_v2.8.yaml`（§3/§6/§7）、
  `docs/decisions/sequence_scoring_baseline_ruling.md`（§7.3）
- 事实汇总与合规：`reports/review/sequence_scoring_summary_b0.md`、
  `reports/review/sequence_scoring_compliance_note_b0.md`（R4 原为 OPEN）、
  `reports/review/independent_research_and_manuscript_review_2026-11-24.md` §1.2（族等权敏感性口径）
- 复算实现参照：`src/readkv/stats/bootstrap.py::cluster_bootstrap`、`scripts/bootstrap_ci_report.py`、
  `experiments/sequence_scoring_gpu.py::summarize`（`reading_diff` 归档口径）

---

## 2. 逐格逐读数复算（任务 1）

### 2.1 主分析集 F1–F4（6 族；本文主表）

| cell | seed | n | reading | Self dual | Joint dual | L | E_CF(mean) | coverage | n_eval | flip |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A11 | 0 | 46 | first | 0.7609 | 0.3261 | +0.4348 | 7.451 | 0.9783 | 45 | 0.7556 |
| A11 | 0 | 46 | full | 0.8043 | 0.3261 | +0.4783 | 17.426 | 1.0000 | 46 | 0.7609 |
| A11 | 0 | 46 | length_normalized | 0.8913 | 0.3913 | +0.5000 | 8.770 | 0.9783 | 45 | 0.7778 |
| A11 | 1 | 46 | first | 0.8696 | 0.2174 | +0.6522 | 8.921 | 1.0000 | 46 | 0.7609 |
| A11 | 1 | 46 | full | 0.7391 | 0.3043 | +0.4348 | 18.933 | 0.9783 | 45 | 0.6444 |
| A11 | 1 | 46 | length_normalized | 0.8261 | 0.3261 | +0.5000 | 9.619 | 0.9783 | 45 | 0.6444 |
| A11 | 2 | 46 | first | 0.7174 | 0.2826 | +0.4348 | 9.442 | 1.0000 | 46 | 0.7391 |
| A11 | 2 | 46 | full | 0.7174 | 0.1957 | +0.5217 | 21.317 | 1.0000 | 46 | 0.7826 |
| A11 | 2 | 46 | length_normalized | 0.8261 | 0.1957 | +0.6304 | 10.843 | 0.9783 | 45 | 0.7778 |
| A00 | 0 | 42 | first | 0.6429 | 0.6429 | +0.0000 | 2.402 | 0.9762 | 41 | 0.9268 |
| A00 | 0 | 42 | full | 0.6429 | 0.6429 | +0.0000 | 2.271 | 1.0000 | 42 | 1.0000 |
| A00 | 0 | 42 | length_normalized | 0.6429 | 0.6429 | +0.0000 | 1.553 | 1.0000 | 42 | 1.0000 |
| A00 | 1 | 42 | first | 0.5238 | 0.6190 | −0.0952 | 2.388 | 1.0000 | 42 | 0.8810 |
| A00 | 1 | 42 | full | 0.5238 | 0.5952 | −0.0714 | 2.168 | 1.0000 | 42 | 1.0000 |
| A00 | 1 | 42 | length_normalized | 0.5238 | 0.5952 | −0.0714 | 1.420 | 1.0000 | 42 | 1.0000 |
| A00 | 2 | 41 | first | 0.6098 | 0.5610 | +0.0488 | 2.644 | 1.0000 | 41 | 0.9512 |
| A00 | 2 | 41 | full | 0.6098 | 0.5610 | +0.0488 | 2.286 | 1.0000 | 41 | 1.0000 |
| A00 | 2 | 41 | length_normalized | 0.6098 | 0.5610 | +0.0488 | 1.583 | 1.0000 | 41 | 1.0000 |

> E_CF 列仅为该口径内描述；**不得按列跨 `first`/`full`/`length_normalized` 比大小**。

### 2.2 全部 60 对（8 族）敏感性 —— 与 `summary_b0`/handoff 对齐的一套

| cell | seed | n | reading | Self dual | Joint dual | L | E_CF(mean) | coverage | n_eval | flip |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A11 | 0 | 60 | first | 0.7000 | 0.3167 | +0.3833 | 6.900 | 0.8667 | 52 | 0.7500 |
| A11 | 0 | 60 | full | 0.7333 | 0.3000 | +0.4333 | 15.952 | 0.8833 | 53 | 0.7547 |
| A11 | 0 | 60 | length_normalized | 0.8000 | 0.3500 | +0.4500 | 8.019 | 0.8667 | 52 | 0.7692 |
| A11 | 1 | 60 | first | 0.7833 | 0.1667 | +0.6167 | 8.159 | 0.8833 | 53 | 0.7358 |
| A11 | 1 | 60 | full | 0.6833 | 0.2833 | +0.4000 | 17.305 | 0.8667 | 52 | 0.6731 |
| A11 | 1 | 60 | length_normalized | 0.7500 | 0.3000 | +0.4500 | 8.769 | 0.8667 | 52 | 0.6731 |
| A11 | 2 | 60 | first | 0.6667 | 0.2667 | +0.4000 | 8.540 | 0.8833 | 53 | 0.7547 |
| A11 | 2 | 60 | full | 0.6667 | 0.2000 | +0.4667 | 18.998 | 0.8833 | 53 | 0.7925 |
| A11 | 2 | 60 | length_normalized | 0.7500 | 0.2000 | +0.5500 | 9.641 | 0.8667 | 52 | 0.7885 |
| A00 | 0 | 60 | first | 0.5667 | 0.5500 | +0.0167 | 1.968 | 0.8000 | 48 | 0.9375 |
| A00 | 0 | 60 | full | 0.5667 | 0.5667 | +0.0000 | 1.818 | 0.8167 | 49 | 1.0000 |
| A00 | 0 | 60 | length_normalized | 0.5667 | 0.5667 | +0.0000 | 1.201 | 0.8167 | 49 | 1.0000 |
| A00 | 1 | 60 | first | 0.4833 | 0.5500 | −0.0667 | 1.934 | 0.8167 | 49 | 0.8980 |
| A00 | 1 | 60 | full | 0.4833 | 0.5333 | −0.0500 | 1.694 | 0.8167 | 49 | 1.0000 |
| A00 | 1 | 60 | length_normalized | 0.4833 | 0.5333 | −0.0500 | 1.082 | 0.8167 | 49 | 1.0000 |
| A00 | 2 | 60 | first | 0.5333 | 0.5000 | +0.0333 | 2.123 | 0.8000 | 48 | 0.9583 |
| A00 | 2 | 60 | full | 0.5333 | 0.5000 | +0.0333 | 1.852 | 0.8000 | 48 | 1.0000 |
| A00 | 2 | 60 | length_normalized | 0.5333 | 0.5000 | +0.0333 | 1.227 | 0.8000 | 48 | 1.0000 |

**核对结论**：§2.2 的 L、E_CF(joint,first/full)、coverage(joint,first) 与 `summary_b0` §1/§4 逐项一致；
handoff 的"全 60 对 L 值"与 §2.2 完全一致（A11 s0 `.3833/.4333/.4500`、s1 `.6167/.4000/.4500`、
s2 `.4000/.4667/.5500`；A00 s0 `.0167/.0000/.0000`、s1 `−.0667/−.0500/−.0500`、s2 `.0333/.0333/.0333`）。
逐对 `dual_correct` / `evaluable` / `flip` / `E_CF` 的重算值与归档字段 0 处不符。`summary_b0` 未列 flip，故无对照项。

---

## 3. 三项比较、主 CI 与敏感性（任务 2）

表中三套区间依次为：**主 = 样本加权 template_family 簇重采样**；**pair = pair-level 样本加权敏感性**；
**族等权 = 按族均值等权敏感性**（第二轮复审 §1.2）。均为 10,000 resamples、95% 百分位 CI，
`exploratory=true`（6/8 族 < 24）。区间只示不确定性，不承担强显著性判读。

### 3.1 `reading_diff = L_full − L_first`（同格配对差）

主分析集（F1–F4，6 族）：

| 格 | seed | 主（样本加权族） | pair 敏感性 | 族等权敏感性 |
| --- | ---: | --- | --- | --- |
| A11 | 0 | +0.0435 [−0.2553, +0.3182] | +0.0435 [−0.1522, +0.2391] | +0.0595 [−0.2500, +0.3333] |
| A11 | 1 | −0.2174 [−0.3404, −0.1304] | −0.2174 [−0.3696, −0.0652] | −0.2143 [−0.3363, −0.1310] |
| A11 | 2 | +0.0870 [−0.1087, +0.3043] | +0.0870 [−0.0652, +0.2391] | +0.0923 [−0.1101, +0.3155] |
| A00 | 0 | +0.0000 [−0.0732, +0.0732] | +0.0000 [−0.0714, +0.0714] | +0.0000 [−0.0833, +0.0833] |
| A00 | 1 | +0.0238 [−0.0698, +0.1333] | +0.0238 [−0.0476, +0.1190] | +0.0179 [−0.0714, +0.1250] |
| A00 | 2 | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] |

全部 60 对（8 族）敏感性（A11 主 CI 与 `metrics.json` / `summary_b0` §2 **逐位一致**）：

| 格 | seed | 主（样本加权族） | pair 敏感性 | 族等权敏感性 |
| --- | ---: | --- | --- | --- |
| A11 | 0 | +0.0500 [−0.1803, +0.2586] | +0.0500 [−0.1000, +0.2000] | +0.0625 [−0.1652, +0.2679] |
| A11 | 1 | −0.2167 [−0.3333, −0.1167] | −0.2167 [−0.3333, −0.1000] | −0.2143 [−0.3281, −0.1138] |
| A11 | 2 | +0.0667 [−0.0820, +0.2333] | +0.0667 [−0.0500, +0.1833] | +0.0692 [−0.0804, +0.2433] |
| A00 | 0 | −0.0167 [−0.0690, +0.0339] | −0.0167 [−0.0833, +0.0333] | −0.0179 [−0.0692, +0.0312] |
| A00 | 1 | +0.0167 [−0.0492, +0.0984] | +0.0167 [−0.0333, +0.0833] | +0.0156 [−0.0469, +0.0938] |
| A00 | 2 | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] |

> A11 s1 的主区间不含零（探索性，不作强显著性）；但 `L_full(s1)>0` 且 cell_diff 未消失 ⇒ 不触发分支②。

### 3.2 `cell_diff = A11 − A00` 的 L 差（逐 seed、逐读数）

主分析集（F1–F4，6 族）：

| seed | reading | 主（样本加权族） | pair 敏感性 | 族等权敏感性 |
| ---: | --- | --- | --- | --- |
| 0 | first | +0.4348 [+0.1106, +0.7259] | +0.4348 [+0.2133, +0.6502] | +0.4226 [+0.0972, +0.7242] |
| 0 | full | +0.4783 [+0.2649, +0.6972] | +0.4783 [+0.3043, +0.6501] | +0.4821 [+0.2679, +0.6964] |
| 0 | length_normalized | +0.5000 [+0.2792, +0.7184] | +0.5000 [+0.3261, +0.6739] | +0.5060 [+0.2857, +0.7143] |
| 1 | first | +0.7474 [+0.5132, +0.9792] | +0.7474 [+0.5538, +0.9317] | +0.7631 [+0.5220, +0.9952] |
| 1 | full | +0.5062 [+0.2867, +0.7323] | +0.5062 [+0.3499, +0.6687] | +0.5310 [+0.3065, +0.7655] |
| 1 | length_normalized | +0.5714 [+0.3201, +0.8205] | +0.5714 [+0.4151, +0.7340] | +0.6024 [+0.3363, +0.8589] |
| 2 | first | +0.3860 [+0.1439, +0.6170] | +0.3860 [+0.2312, +0.5408] | +0.3839 [+0.1548, +0.6101] |
| 2 | full | +0.4730 [+0.2026, +0.7234] | +0.4730 [+0.3155, +0.6278] | +0.4762 [+0.2024, +0.7262] |
| 2 | length_normalized | +0.5817 [+0.2831, +0.8413] | +0.5817 [+0.4242, +0.7365] | +0.5952 [+0.3006, +0.8482] |

全部 60 对（8 族）敏感性：

| seed | reading | 主（样本加权族） | pair 敏感性 | 族等权敏感性 |
| ---: | --- | --- | --- | --- |
| 0 | first | +0.3667 [+0.1034, +0.6134] | +0.3667 [+0.1833, +0.5333] | +0.3527 [+0.0960, +0.6049] |
| 0 | full | +0.4333 [+0.2373, +0.6285] | +0.4333 [+0.2833, +0.5833] | +0.4330 [+0.2343, +0.6272] |
| 0 | length_normalized | +0.4500 [+0.2500, +0.6452] | +0.4500 [+0.3000, +0.5837] | +0.4509 [+0.2455, +0.6429] |
| 1 | first | +0.6833 [+0.4339, +0.9130] | +0.6833 [+0.5333, +0.8333] | +0.6808 [+0.4308, +0.9152] |
| 1 | full | +0.4500 [+0.2531, +0.6402] | +0.4500 [+0.3167, +0.5833] | +0.4509 [+0.2545, +0.6429] |
| 1 | length_normalized | +0.5000 [+0.2787, +0.7107] | +0.5000 [+0.3667, +0.6333] | +0.5045 [+0.2790, +0.7210] |
| 2 | first | +0.3667 [+0.1607, +0.5645] | +0.3667 [+0.2333, +0.5000] | +0.3594 [+0.1540, +0.5558] |
| 2 | full | +0.4333 [+0.2000, +0.6597] | +0.4333 [+0.3000, +0.5667] | +0.4286 [+0.1964, +0.6540] |
| 2 | length_normalized | +0.5167 [+0.2615, +0.7627] | +0.5167 [+0.3833, +0.6500] | +0.5179 [+0.2500, +0.7612] |

> 全 60 对的点估计与 handoff 的 `cell_diff` 一致：first `+.367/+.683/+.367`、full `+.433/+.450/+.433`、
> norm `+.450/+.500/+.517`；主分析集点估计列于上表（§6.1 记录差异）。

### 3.3 `reading_of_diff = cell_diff(full) − cell_diff(first)`

主分析集（F1–F4，6 族）：

| seed | 主（样本加权族） | pair 敏感性 | 族等权敏感性 |
| ---: | --- | --- | --- |
| 0 | +0.0435 [−0.2612, +0.3211] | +0.0435 [−0.1543, +0.2412] | +0.0595 [−0.2639, +0.3423] |
| 1 | −0.2412 [−0.3978, −0.1054] | −0.2412 [−0.4130, −0.0828] | −0.2321 [−0.3810, −0.1042] |
| 2 | +0.0870 [−0.1064, +0.3043] | +0.0870 [−0.0652, +0.2391] | +0.0923 [−0.1101, +0.3155] |

全部 60 对（8 族）敏感性：

| seed | 主（样本加权族） | pair 敏感性 | 族等权敏感性 |
| ---: | --- | --- | --- |
| 0 | +0.0667 [−0.1669, +0.2884] | +0.0667 [−0.0833, +0.2333] | +0.0804 [−0.1562, +0.2969] |
| 1 | −0.2333 [−0.3683, −0.1139] | −0.2333 [−0.3667, −0.1000] | −0.2299 [−0.3638, −0.1094] |
| 2 | +0.0667 [−0.0833, +0.2373] | +0.0667 [−0.0500, +0.1833] | +0.0692 [−0.0804, +0.2433] |

### 3.4 跨 seed 汇总（不池化，仅计数/范围）

| 比较 | 加权口径 | 主分析集：CI 不含零 | 全 60 对：CI 不含零 | 主分析点估计范围 |
| --- | --- | ---: | ---: | --- |
| `reading_diff`（A11） | 主 / pair / 族等权 | 各 1/3 | 各 1/3 | −0.2174 … +0.0870 |
| `cell_diff`（3 读数 × 3 seed） | 主 / pair / 族等权 | 各 9/9 | 各 9/9 | +0.3860 … +0.7474 |
| `reading_of_diff` | 主 / pair / 族等权 | 各 1/3 | 各 1/3 | −0.2412 … +0.0870 |

> 计数为探索性区间的描述性统计，因族数 6/8 < 24，**不构成强显著性结论**；`cell_diff` 三口径区间均不含零，
> 说明三口径下 A11−A00 的点估计方向稳定，而不是"整串产生新发现"。

---

## 4. v2.8 §7 三分支归类（任务 3）

> **按结果前冻结的条件对号入座，无事后择支。** 逐条核对（主分析集；全 60 对敏感性结论相同）：

| 分支（冻结条件） | 逐项核对 | 是否满足 |
| --- | --- | --- |
| ① `consistent_across_scoring`：三组 A11 整串 L 仍为正，且 A11−A00 方向与首 token 一致 | A11 `full` L = +0.4783 / +0.4348 / +0.5217（均 > 0）；cell_diff `first` 与 `full` = 全正（§3.2）；`length_normalized` 下 A11 L 与 cell_diff 亦全正 | **满足 → 本期归类** |
| ② `first_token_sensitive`：A11 下降明显缩小、某些 seed 方向改变或 A11−A00 的差消失 | s1 A11 `L_full`(+0.4348) 较 `L_first`(+0.6522) 缩小且 `reading_diff` 主 CI 不含零，但 L 仍为正、无 seed 变号、cell_diff 未消失（+0.5062） | 不满足 |
| ③ `length_norm_changes_reading`：按长度归一后判读改变 | 归一后 A11 L 与 cell_diff 仍全正；分支①判读不变 | 不满足 |

**归类：① `consistent_across_scoring`（预承诺归类，无事后择支）。**

按分支① `action` 的措辞边界，本文的判读表述严格限于：
**"在两种候选评分（首 token 与整串 teacher-forcing）下，点估计方向一致"**；报告幅度与区间（§2–§3），
并标出跨历史 20 点线的 seed（见下）；区间仅示不确定性。

- 历史 20 点线（仅描述性参照，不用于判读）：主分析集全部 3 个 seed 的 A11 在 `first`、`full`、
  `length_normalized` 三读数下 L 均 > 0.20（s0 .4348/.4783/.5000；s1 .6522/.4348/.5000；
  s2 .4348/.5217/.6304）；全 60 对敏感性下 3 个 seed 亦均 > 0.20（§2.2）。
- **不作强显著性主张**（6/8 族 exploratory）；**不把整串结果写成新的正向发现**；
  **不升级为方法有效性/贡献强度结论**。

---

## 5. 边界与禁止项（任务 4）

1. **只涉及评分方式稳健性**：本文只检验既有"A11 失败边界"与"A00→A11 历史翻转"两个结论对候选评分读数
   （`first` / `full` / `length_normalized`）的敏感性；不涉及单项数据缺陷（如 F5 相同候选、F6 等）的因果归因，
   不量化任何单项因素的贡献。
2. **不做事由/单项缺陷因果归因**：区间是否跨零不能替代因果分解；本文不声称"因为某缺陷"导致 L 变化。
3. **不恢复贡献**：贡献(1) 撤回、贡献(2) 撤回、贡献(3) withheld 的状态维持；P2/P3/P4 不重开；本实验不是
   方法贡献、不作一般泄漏教训/跨源普适性主张。
4. **主终点与封存 test 未评**：V2.0 主终点（封存 test 上 cf vs kd_only 成对 E_CF，CI 上界 < 0）不重算、
   不触碰；`sealed_test_read=false`；只用 old(458de18)/repaired(efc3ba3) 的 train/val；不做 A01/A10。
5. **8 族 exploratory**：主分析 6 族、全 60 对 8 族，均 < 24；无强显著性；逐 seed 保留族计数，不池化。
6. **E_CF 不跨评分口径比较**：`full` 为 FP32 logprob 之和，`first` 为首项，`length_normalized` 为除长度，
   绝对尺度不可比；E_CF 区间仅在同一读数内部有意义。
7. **不解除投稿阻塞**：按 v2.8 §8 与基线裁决 §4，本判读只关闭 R4；编译/匿名稿/指标口径/归因措辞等定向大修
   独立待关；最终重新签 off 由 PI 新出（不改写旧 `p5_final_resignoff.md`）。本文不构成投稿许可。

---

## 6. 与 `summary_b0` / handoff 的差异记录（任务 5）

### 6.1 分母口径差异（唯一实质差异）

| 项 | `summary_b0` §1/§3/§4 与 handoff | 本文主分析（v2.8 §3 primary） | 处理 |
| --- | --- | --- | --- |
| L（每格每读数） | 全部 60 对、8 族（handoff 已标"全 60 对 L 值"） | F1–F4 主分析集、6 族（A00 42/42/41，A11 46/46/46） | 两套并列；L 点估计不同，见下表 |
| `cell_diff`（三读数） | 由全 60 对 L 派生：first `+.367/+.683/+.367`、full `+.433/+.450/+.433`、norm `+.450/+.500/+.517` | first `+.4348/+.7474/+.3860`、full `+.4783/+.5062/+.4730`、norm `+.5000/+.5714/+.5817` | 两套并列；方向一致 |
| E_CF / coverage | 全 60 对口径（与本文 §2.2 一致） | F1–F4 口径（§2.1），数值不同 | 明确标集，不混写 |
| flip | `summary_b0` 未列 | 两套均按 §1.2 重算 | 无对照项 |

主分析集 L（s0/s1/s2；first / full / norm）：

| cell | first | full | length_normalized |
| --- | --- | --- | --- |
| A11 | +0.4348 / +0.6522 / +0.4348 | +0.4783 / +0.4348 / +0.5217 | +0.5000 / +0.5000 / +0.6304 |
| A00 | +0.0000 / −0.0952 / +0.0488 | +0.0000 / −0.0714 / +0.0488 | +0.0000 / −0.0714 / +0.0488 |

> 说明：handoff 在描述中已写明"主分析分母 = F1–F4（6 族）、全部 60 对 8 族作敏感性"，但其提供的 L 与
> `cell_diff` 数值为全 60 对一套；`summary_b0` 同名"主表"同样使用全 60 对。本文按 v2.8 §3 把 F1–F4
> 作为主分析、全 60 对作为敏感性，并把差异逐项登记于此；**逐对分数复算与归档 0 处不符**。判读分支不受影响。

### 6.2 一致项（无差异）

- 全 60 对 L、E_CF(joint,first/full)、coverage(joint,first) 与 `summary_b0` §1/§4 逐项一致（§2.2）。
- `summary_b0` §2 的 A11 六格 `reading_diff` 主区间（含 s1 `−0.2167 [−0.3333, −0.1167]`）按样本加权
  `cluster_bootstrap`、10,000 resamples、seed = 格 seed **逐位复现**（§3.1 全 60 对表）。
- handoff 的全 60 对 L 与 `cell_diff` 数值逐项复现（§2.2、§3.2）。
- R4 此前 OPEN 的原因（`compliance_note_b0` §0/§4）是判读文档缺失；本文为该交付物，不改任何实证产物。

---

## 7. 可复算脚本与命令（任务 5）

- 环境：`/root/readkv/.venv/bin/python`（numpy 2.5.5 / scipy 1.18.1）。
- 实际复算脚本（scratch，未入仓）：`/tmp/opencode/seq_stats_analyze.py`（全量，输出
  `/tmp/opencode/seq_stats_out.json`）；下方嵌入等价紧凑版，保存为 `seq_stats_repro_compact.py` 后执行：

```bash
cd /root/readkv
.venv/bin/python /tmp/opencode/seq_stats_repro_compact.py   # 打印 §3 三项比较点估计与三套 CI
```

```python
"""Compact read-only recomputation (run with: .venv/bin/python seq_stats_repro_compact.py)."""
import json
from collections import defaultdict
from pathlib import Path
import numpy as np

R = Path("/root/readkv"); RD = ("first", "full", "length_normalized"); N = 10_000

def pairs(cell, s):
    idx = {json.loads(l)["pair_id"]: json.loads(l) for l in
           (R / f"data/audit_2x2/sequence/{cell}_seed{s}.jsonl").read_text().splitlines() if l.strip()}
    sc = [json.loads(l) for l in (R / f"reports/runs/audit_seq_{cell}_s{s}_b0/scores.jsonl").read_text().splitlines() if l.strip()]
    ij = {(x["pair_id"], x["arm"]): x for x in sc}
    out = []
    for pid in sorted(p for p, a in ij if a == "self"):
        a, b = ij[(pid, "self")], ij[(pid, "joint")]
        q = {}
        for r in RD:
            ev = abs(a["D"][r]) > 0.1
            q[r] = dict(L=a["dual_correct"][r] - b["dual_correct"][r],
                        dL=a["dual_correct"]["full"] - a["dual_correct"]["first"]
                           - b["dual_correct"]["full"] + b["dual_correct"]["first"],
                        ecf=a["E_CF"][r], ev=ev,
                        flip=(np.sign(a["D"][r]) == np.sign(b["D"][r])))
        out.append(dict(pid=pid, fam=a["template_family"], primary=bool(idx[pid]["primary_analysis"]), q=q))
    return out

def groups(vals, labs):
    d = defaultdict(list)
    for v, l in zip(vals, labs): d[str(l)].append(v)
    ks = sorted(d)
    return [np.asarray(d[k], float) for k in ks]

def ci1(vals, labs, rng, equal=False):
    gs = groups(vals, labs); g = len(gs)
    if equal:
        m = np.array([x.mean() for x in gs]); pt = m.mean()
        dr = m[rng.integers(0, g, (N, g))].mean(1)
    else:
        pt = np.concatenate(gs).mean()
        dr = np.array([np.concatenate([gs[k] for k in rng.integers(0, g, g)]).mean() for _ in range(N)])
    return pt, *np.quantile(dr, (.025, .975))

def ci2(va, la, vb, lb, rng, equal=False):
    ga, gb = groups(va, la), groups(vb, lb); na, nb = len(ga), len(gb)
    if equal:
        ma = np.array([x.mean() for x in ga]); mb = np.array([x.mean() for x in gb])
        pt = ma.mean() - mb.mean()
        dr = (ma[rng.integers(0, na, (N, na))].mean(1) - mb[rng.integers(0, nb, (N, nb))].mean(1))
    else:
        pt = np.concatenate(ga).mean() - np.concatenate(gb).mean()
        dr = np.array([np.concatenate([ga[k] for k in rng.integers(0, na, na)]).mean()
                       - np.concatenate([gb[k] for k in rng.integers(0, nb, nb)]).mean() for _ in range(N)])
    return pt, *np.quantile(dr, (.025, .975))

def report(denom):
    for s in (0, 1, 2):
        aa = [r for r in pairs("A11", s) if denom == "all60" or r["primary"]]
        oo = [r for r in pairs("A00", s) if denom == "all60" or r["primary"]]
        for r in RD:
            L = lambda x: np.mean([z["q"][r]["L"] for z in x])
            print(f"{denom} s{s} cell_diff {r:18s} {L(aa)-L(oo):+.4f}")
        for name, f in (("reading_diff_A11", lambda x: [z["q"]["full"]["dL"] for z in x]),
                        ("reading_diff_A00", lambda x: [z["q"]["full"]["dL"] for z in x])):
            x = aa if "A11" in name else oo
            for tag, eq in (("sw_family", False), ("pair", False), ("eq_family", True)):
                labs = [z["fam"] if tag != "pair" else z["pid"] for z in x]
                pt, lo, hi = ci1(f(x), labs, np.random.default_rng(s), equal=eq)
                print(f"{denom} s{s} {name:17s} {tag:10s} {pt:+.4f} [{lo:+.4f},{hi:+.4f}]")
        for tag, eq in (("sw_family", False), ("pair", False), ("eq_family", True)):
            laa = [z["fam"] if tag != "pair" else z["pid"] for z in aa]
            loo = [z["fam"] if tag != "pair" else z["pid"] for z in oo]
            pt, lo, hi = ci2([z["q"]["full"]["dL"] for z in aa], laa,
                             [z["q"]["full"]["dL"] for z in oo], loo, np.random.default_rng(s), equal=eq)
            print(f"{denom} s{s} reading_of_diff    {tag:10s} {pt:+.4f} [{lo:+.4f},{hi:+.4f}]")

if __name__ == "__main__":
    report("primary"); report("all60")
```

- 归档 `reading_diff` CI 的独立交叉验证（应输出 `summary_b0` §2 数值）：

```bash
cd /root/readkv
.venv/bin/python -c "import sys,json;sys.path.insert(0,'src');\
from readkv.stats.bootstrap import cluster_bootstrap as cb;\
p='reports/runs/audit_seq_A11_s1_b0/scores.jsonl';\
rows=[json.loads(l) for l in open(p) if l.strip()];\
ij={(r['pair_id'],r['arm']):r for r in rows};\
d=[(ij[(k,'self')]['dual_correct']['full']-ij[(k,'self')]['dual_correct']['first'])-\
   (ij[(k,'joint')]['dual_correct']['full']-ij[(k,'joint')]['dual_correct']['first'])\
   for k in {r['pair_id'] for r in rows if r['arm']=='self'}];\
f=[ij[(k,'self')]['template_family'] for k in {r['pair_id'] for r in rows if r['arm']=='self'}];\
print(cb(d,f,n_resamples=10000,seed=1))"
```

> 复算纪律：所有数字来自 `_b0` 归档逐对行与 index 标志；未使用 mock 数字；本次仅新建本文档，
> `/tmp/opencode/` 下的脚本/JSON 为 scratch 输出，仓库内其他文件未改。

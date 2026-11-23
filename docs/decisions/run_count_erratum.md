# 运行计数只读勘误（N1：run 总数 26 → 28 → 31）

> 裁决人：PI / 课题组长。日期：2026-11-23。
> 触发：审稿人 `reports/review/final_compliance_note.md` §4 N1——`docs/decisions/final_implementation_plan.md` §2 R5 勘误登记"28 run（19 superseded + 9 权威）"，而 R4 落实后 `reports/runs_index.json` 现为 31 项（22 superseded + 9 权威）。
> **性质：只读计数勘误。** 不回写任何已签署/已冻结裁决文档，不改任何科学结论——本文件仅为计数一致性补记。

---

## 1. 计数演化链（可追溯）

| 阶段 | 权威/总数 | superseded | 权威 run | 变化原因 | 记录位置 |
|---|---|---|---|---|---|
| **旧裁决期** | 26 run | 19 | 9（7 clean + 2 锚点） | 加入 2 个 SQuAD 锚点前的历史计数；早期裁决文档记"26" | `p5_final_signoff.md`、`final_boundary_study_signoff.md` 等已签裁决 |
| **锚点加入后** | 28 run | 19 | 9（7 clean + 2 锚点） | 新增 2 个 SQuAD 锚点 run（总数 26→28，权威 9 不变——锚点替换/补入权威集，旧杂项未即刻重标） | `final_implementation_plan.md` §2 R5 勘误记"28（19 superseded + 9 权威）" |
| **R4 落实后（当前）** | **31 run** | **22** | **9（7 clean + 2 锚点）** | R4 把 3 个历史 run（`delta_lock_v2p1_2p0_par`、`p1_gpu_kdonly_mvp_seed1_par`、`p1_gpu_kdonly_mvp_seed2_fast`）补标 `superseded=true` 并纳入索引，superseded 19→22、总数 28→31 | `reports/runs_index.json`（31 项）、`final_compliance_note.md` §3 |

**演化恒等式**：
- 权威 run 数**恒为 9**（7 个 clean：E0×1 + affine P1×3 + kd P1×3；2 个 SQuAD 锚点）——**全程未变**。
- 变化仅在历史侧：superseded 19 → 19 → 22；总数 26 → 28 → 31。

---

## 2. 勘误声明

1. **这是计数勘误，不是科学结论变更**：R4 仅把 3 个历史 run 在索引/errata 层补标 superseded（不改任何 run 产物），从而改变"总 run 数/历史 superseded 数"的记账；**权威证据集始终是同一 9 个 run**，其数值、CI、判读全部不变。
2. **唯一权威来源**：`reports/runs_index.json`（当前 31 项 = 22 superseded + 9 authoritative）。任何"26/28"的历史计数均以本演化链理解，下游判定一律以 runs_index.json 为准。
3. **不回写已签裁决**：`p5_final_signoff.md`、`final_boundary_study_signoff.md`、`final_implementation_plan.md` 等已签署/已冻结文档中的"26/28"计数**保持原样**（R5 纪律），本文件为其只读勘误补充。
4. **不预判后续**：真实 PI 已决定执行 2×2 GPU 补充实验（human_decisions 决策 11），该实验会产生 12 个新 run 并重新触发 P5 签off——**届时 run 总数将再次变化；本勘误仅针对当前（R4 后、2×2 前）状态，不预判后续计数**。

---

## 3. 结论

> **当前权威 run 数仍为 9（7 clean + 2 SQuAD 锚点），全程不变。** 计数演化 26 → 28（+2 锚点）→ 31（R4 补标 3 历史 run 为 superseded）仅涉及历史/总数记账，不改变任何科学结论或已签裁决实质。以 `reports/runs_index.json` 为唯一权威来源。

**签署：PI / 课题组长（run 计数只读勘误 · 2026-11-23）**

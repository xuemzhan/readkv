# P2 F1/F2/F5 闭环核验报告（贡献(2) 强形式解禁建议）

> 审稿人：reviewer（对抗性审阅 / readkv）。日期：2026-11-23。
> 依据：`docs/decisions/contribution2_ruling.md`（F1 投递硬门槛 / F2 强度门槛）、`reports/engineer_status.md` §11、`reports/p2_seed_robustness.json`、三个新 P2 run 产物、`scripts/bootstrap_ci_report.py`（commit 6784780）。
> 当前 HEAD=`6784780`。**范围**：只核验 F1/F2/F5 是否闭环，不重复第 1 轮 P2 审计已通过项（四臂/分解/Oracle 隔离/数据来源等已在 `p2_mechanism_review.md` 判定）。本轮未改代码、`scores.jsonl`、`configs/prereg/**` 或论文源文件。

---

## 0. 必做动作执行结果

| 动作 | 结果 |
|---|---|
| `.venv/bin/python -m scripts.bootstrap_ci_report` | 成功，22 runs → `reports/bootstrap_summary.json`；新增 `repair_vs_random` 终点 |
| `.venv/bin/python -m scripts.consistency_check` | checked=22, failed=8, head=6784780, dirty_run_paths=[] → `reports/consistency_report.json` |
| prereg 完整性 | `git diff HEAD -- configs/prereg/phase3_loss_config_v2.1.yaml v2.2.yaml` = 空 → **未被篡改** |

failed=8 仍全部为旧 `git_hash=53e9bc5` 的 superseded run（按设计报错），与三个新 P2 run 无关。`p2_smoke_tmp` 不再出现在审计列表（见 §3）。

---

## 1. F1【投递硬门槛】逐对 delta_rand 复算 — **已闭环** ✅

### 1.1 独立重算（不依赖脚本，从冻结产物逐对计算）

审计 run `p2_gpu_mvp_seed0_delta_rand_audit/scores.jsonl`（240 行 = 6 臂 × 40 对，`oracle_U` 行含 `delta_ecf/delta_rand/hit_u/hit_rand/delta_hit`）：

- **逐对一致性校验**：`delta_hit == hit_u − hit_rand` 在 40/40 对成立；`oracle_U.delta_rand == oracle_random.delta_ecf` 在 40/40 对成立 → 两臂 ledger 自洽。
- **冻结判据的正确量是命中率差**（`repair 命中率显著高于随机`，非连续 ECF 差），即 `hit_u − hit_rand`。我按此独立做簇级 paired bootstrap（10,000 resamples, seed=0）：**point=0.2750、CI [0.1500, 0.4250]，下界>0** —— 与 mechanism.json 报告值及 PI 裁决目标 **完全一致**。
  - 审稿说明：我最初误用连续量 `delta_ecf − delta_rand` 得到 0.643，经核对冻结判据定义后确认那是错误量；命中率差才是判据量，脚本实现正确。
- 原 `p2_gpu_mvp_seed0` 冻结产物未改（`git diff` 无痕），审计以新 run_id 完成，符合「不可变产物」约束。

### 1.2 脚本扩展确认

`bootstrap_ci_report.py`（commit 6784780）新增 `repair_vs_random` 终点：从 `oracle_U` 逐对 `hit_u − hit_rand`（无该列时回退为 `delta_ecf>0 − delta_rand>0` 的布尔差）做簇级 bootstrap。本轮输出：

| run | point | CI | n_pairs | ci_lower_gt_0 |
|---|---|---|---|---|
| `p2_gpu_mvp_seed0_delta_rand_audit` | 0.275 | [0.150, 0.425] | 40 | true |
| `p2_gpu_mvp_seed1` | 0.275 | [0.125, 0.425] | 40 | true |
| `p2_gpu_mvp_seed2` | 0.350 | [0.200, 0.500] | 40 | true |

三个终点均可从冻结 `scores.jsonl` 复算，且与 `mechanism.json` 聚合值一致。**F1 闭环成立**，P5 可使用该 CI。

---

## 2. F2【强度门槛】P2 ≥3 seed 与 U 稳健性 — **已闭环** ✅

### 2.1 产物完整性 + provenance

三个新 run（seed0 审计 run / seed1 / seed2）均含完整 6 文件：`config.json / scores.jsonl / mechanism.json / decomposition.jsonl / mechanism_units.jsonl / manifest.json`。provenance 逐项核实：

| run | git_hash | zero_re_prefill | dtype | kernel | bootstrap_seed | seed |
|---|---|---|---|---|---|---|
| ...delta_rand_audit | 6784780 | true | bfloat16 | sdpa | 0 | 0 |
| seed1 | 6784780 | true | bfloat16 | sdpa | 1 | 1 |
| seed2 | 6784780 | true | bfloat16 | sdpa | 2 | 2 |

三个 `git_hash=6784780` 均在 HEAD(=6784780) 历史、跑分代码与 HEAD 一致、工作区干净（`consistency_check` 均 ok=true/traceable=true）。**满足 ≥3 seed（`min_training_seeds=3`）**。

### 2.2 三 seed 独立复算（四臂 / 分解 / held-out / 隔离）

| 项 | seed0 | seed1 | seed2 |
|---|---|---|---|
| 四臂 self/k/v/joint | 0/0.582/1.626/1.777 | 0/0.536/1.655/1.943 | 0/0.606/1.864/2.119 |
| 仅 Joint deployable | ✅ | ✅ | ✅ |
| 分解单元 / 最大残差 | 17,920 / 2.96e-13 | 17,920 / 2.78e-13 | 17,920 / 2.82e-13 |
| held-out hit_u / hit_rand | 0.725 / 0.450 | 0.725 / 0.450 | 0.750 / 0.400 |
| repair point / CI | 0.275 / [0.150,0.425] | 0.275 / [0.125,0.425] | 0.350 / [0.200,0.500] |
| 方向一致 | 0.725 | 0.725 | 0.750 |
| verdict | mechanism_predictive | mechanism_predictive | mechanism_predictive |

- 三 seed 的 repair point/CI 与 `p2_seed_robustness.json` 及任务要求数值 **全部一致**，CI 下界均 >0。
- **隔离纪律**：每 seed 选择集 8 对全部 `train` 前缀、held-out 40 对全部 `val` 前缀、重叠=0、`test_touched=False`；Oracle 未进推理图（沿用已审计代码口径）。✅
- 三 seed 的 V-only≈Joint 均成立（V-only < Joint，K-only 明显更低），方向一致。

### 2.3 U 跨 seed 重合核验（`p2_seed_robustness.json` 属实）

从各 seed `mechanism.json` 的 `U_topk` 独立取 top-5 并求交：

- 两两 common 均为 **4**；三 seed 共同核心 **4 个单元**：`(12,5,V) / (12,5,both) / (25,4,V) / (25,4,both)` —— 与 robustness json 报告完全一致。
- 第 5 单元漂移属实：seed0=(14,1,V)、seed1=(24,2,both)、seed2=(14,1,both)。
- 结论「核心单元跨 seed 稳定、边缘第 5 单元轻微漂移、机制定位基本一致但非逐单元恒定」——**如实，无夸大**。审计 run 的 U 与原 seed0 完全相同（同 seed/data 复现），无隐藏改动。

**F2 闭环成立**。强度含义：核心机制（layer12/head5、layer25/head4，V/both 通道）跨 3 seed 稳定复现；但 repair 效应点 0.275–0.350、命中 0.725–0.750 有波动，边缘单元漂移——这支持「机制定位跨 seed 基本一致」，**不支持「逐单元完全恒定」**。

---

## 3. F5【清理】smoke run 移出正式目录 — **已闭环** ✅

- `reports/runs/p2_smoke_tmp/` 已不存在；已移至 `reports/_non_authoritative/p2_smoke_tmp/`（文件仍在，保留可追溯性）。
- 本轮 `consistency_check` checked=22，**审计列表不再含 p2_smoke_tmp**，误计问题消除。
- `runs_index` / `errata` 的 authoritative P2 列表为 4 个正式 run，不含 smoke。F5 闭环。

---

## 4. 残余风险与贡献(2) 强形式解禁判断

### 4.1 F1/F2 闭环后仍需在强形式中披露 / 处理的问题

| 项 | 性质 | 强形式下是否仍阻塞 |
|---|---|---|
| **F6 三判据非独立** | repair-vs-random 与方向一致共享 `hit_u` 成分，实为「2 统计信号 + 1 多数门槛」 | **不阻塞解禁，但必须披露**。PI `contribution2_ruling §2.2` 已明令禁止表述为"三条独立证据"；即使升强形式，论文仍须写明二者非独立。这是措辞合规项，非产物缺口。 |
| **F4 解释边界** | V 消费为主因、Key 路由为伴随；局部恒等式≠全模型因果；禁用 causal/sole cause | **不阻塞解禁，但必须保留**。强形式措辞仍须带 F4 三条边界。 |
| **核心稳定但边缘漂移** | 4/5 单元跨 seed 稳定，第 5 单元漂移；效应点 0.275–0.350 有波动 | **不构成阻塞**。支持"核心定位跨 seed 稳健"，但强形式不得声称"每单元逐 seed 恒定"或夸大为完全不变。 |
| **仅 MVP 对** | 三 seed 均为 1.7B→0.6B 等深对；主验证对（4B→1.7B）机制诊断未跑 | **强形式的重要边界**。强形式若写"across model pairs"仍禁止（`contribution2_ruling §2.2`）；跨对泛化需 E5/P4 支撑，当前没有。 |
| **单 seed 陈旧表述** | 论文多处（如第 77/140/639/725/834 行）仍写 "single seed"，F2 后已有 3 seed | **非解禁阻塞，但是 P5 必改的事实性更新**（writer 任务）。若升强形式却仍写 single seed，自相矛盾。 |

### 4.2 「贡献(2) 强形式是否可解禁」明确建议（供 PI 裁决，不定稿）

**结论：F1（投递硬门槛）与 F2（强度门槛）均已闭环，此前约束强形式的两条产物级硬约束（CI 不可重算、单 seed）已消除。据此，审稿侧认为「贡献(2) 强形式」的产物前提已具备，可以解禁——但附三条强制条件：**

1. **解禁范围有限**：可启用 §10 模板(2) 的强动词（如 "We localize the gap to receiver-side Value-consumption pathways"），但**仍不得**出现 "robustly/consistently across model pairs"、"causal/necessary and sufficient"、"sole cause"——因机制证据仅来自 MVP 对等深对、局部恒等式与 Oracle 离线修复，跨对/因果仍无支撑。这是协议 §8/§10 与 `contribution2_ruling §2.2` 禁用词表的延续，不因 F1/F2 闭环而放宽。
2. **强制披露 F4/F6**：强形式必须并存"Key 路由为伴随效应""局部恒等式非全模型因果分解""repair-vs-random 与方向一致非独立"三条，且如实报告"4/5 核心单元跨 seed 稳定、第 5 单元漂移"。
3. **P5 前置**：论文须先完成 F3 的 seed 数更新（三 seed 取代 single seed）与上述披露，否则强形式与陈旧表述并存会造成事实性矛盾。

**若 PI 选择保守路线**，维持限定形式亦完全合规（已有三 seed 支撑，限定形式证据更充分）；审稿侧不反对任一选择，仅提供"产物前提已满足、解禁无产物级障碍"的判断。

**贡献(3) 维持 withheld**（P3 未跑、主终点未评估、封存测试未跑、三 δ 均不优于 kd_only）——本轮无任何证据改变该结论。P3/P4 NO-GO 维持。

---

## 5. 逐项闭环判定汇总

| 项 | 判定 | 关键证据 |
|---|---|---|
| **F1**（delta_rand 复算） | **已闭环** ✅ | 独立从逐对 delta_hit 重算 point=0.275 CI[0.150,0.425]；脚本新增 repair_vs_random 终点，三 seed 均可复算；原 run 未改 |
| **F2**（≥3 seed + U 稳健） | **已闭环** ✅ | 三 seed 产物完整、provenance 齐全、四臂/分解/held-out 全部复算一致；4/5 核心单元跨 seed 稳定、第 5 漂移如实；未碰 test |
| **F5**（smoke 清理） | **已闭环** ✅ | 已移至 `_non_authoritative/`，不再被审计误计 |
| prereg v2.1/v2.2 | 未被篡改 ✅ | git diff 为空 |

## 6. 给 PI 的 Go/No-Go 最终建议

- **F1/F2/F5 全部闭环**，此前 `contribution2_ruling.md` 设定的贡献(2) 强形式两条门槛（F1 投递硬门槛、F2 强度门槛）**均已满足**。
- **贡献(2) 强形式：建议可解禁**（产物前提已具备），但须满足 §4.2 三条强制条件（有限范围 + F4/F6 披露 + P5 seed 数更新）；是否启用由 PI 最终裁决，审稿侧不定稿。
- **阶段**：P0/P1/P2 GO（维持）；**P3/P4 NO-GO（维持）**；**P5 条件性 GO**——门槛更新为 F3 seed 数更新 + F4/F6 披露齐全 + 贡献(3) withheld 维持。
- **定位**：维持 empirical/boundary study；贡献(2) 无论限定/强形式均不改其非方法论文定位（缺贡献(3)）。

---

## 7. 结论

F1（逐对 delta_rand 复算）、F2（P2 三 seed + U 跨 seed 稳健性）、F5（smoke 清理）均经独立重算与产物核验确认闭环，prereg v2.1/v2.2 未篡改，扩展审计脚本输出可复算的 repair-vs_random 终点。贡献(2) 强形式的两条产物级门槛已消除，审稿侧建议**可解禁但附有限范围与 F4/F6 强制披露**；F6（三判据非独立）等非产物级问题不阻塞解禁、但必须在强形式措辞中披露。P3/P4 NO-GO、贡献(3) withheld、边界/实证定位维持。**贡献(2) 措辞是否升为强形式由 PI 裁决，审稿侧不定稿。**

**签署：reviewer（对抗性审阅），2026-11-23。**

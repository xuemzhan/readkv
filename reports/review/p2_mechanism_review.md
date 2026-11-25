# P2 机制诊断对抗性审计报告（E2）

> 审稿人：reviewer（对抗性审阅 / readkv）。日期：2026-11-23。
> 依据：`docs/decisions/final_signoff.md` §3.1（P2 GO 六条任务书）、`docs/protocol.md` §5/§8/§10、`configs/prereg/phase3_loss_config_v2.1.yaml §e2_mechanism_prediction`（v2.2 原样继承）、`reports/engineer_status.md` §10、`reports/runs/p2_gpu_mvp_seed0/**`、`reports/p2_mechanism_summary.json`。
> 当前 HEAD=`70756be`；P2 run `git_hash=9d474be`。
> **范围**：P2/E2 阶段对抗审计。本轮未改代码、`scores.jsonl`、`configs/prereg/**` 或论文源文件。

---

## 0. 必做动作执行结果

| 动作 | 结果 |
|---|---|
| `.venv/bin/python -m scripts.bootstrap_ci_report` | 成功，20 runs → `reports/bootstrap_summary.json`（P2 四臂 E_CF 已重算，见 §1.1） |
| `.venv/bin/python -m scripts.consistency_check`（扩展版） | checked=20, failed=8, head=70756be, dirty_run_paths=[] → `reports/consistency_report.json` |
| prereg 完整性 | `git diff HEAD -- configs/prereg/phase3_loss_config_v2.1.yaml phase3_loss_config_v2.2.yaml` = 空；工作区 `configs/prereg/` 干净 → **v2.1/v2.2 未被篡改** |
| P2 run provenance | `ok=true, traceable=true, code_tracked=true, run_code_unchanged_vs_head=true, git_hash_in_history=true, dirty_run_paths=[]`；config 含 git_hash=9d474be / zero_re_prefill=true / bootstrap_seed=0 / dtype=bfloat16 / kernel=sdpa / protocol_version=2.0 → **字段齐全，与 P1 repro 口径对齐** |

**failed=8 的解读**：全部为旧 `git_hash=53e9bc5` 的 `superseded` run（按设计报错），非 P2。`p2_gpu_mvp_seed0` 与 `p2_smoke_tmp` 均 ok=true。此前 `review/` 目录误列入问题已由 commit `70756be` 修复（本轮 checked=20，不再含 review/）。

---

## 1. E2 三判据逐项核实（全部从原始产物独立重算）

### 1.1 K/V 四臂 ✅ 达标

从 `scores.jsonl`（200 行 = 5 臂 × 40 对）独立重算：

| 臂 | 报告值 | 重算均值 | n | deployable |
|---|---|---|---|---|
| Self | 0.000 | 0.000 | 40 | false |
| K-only | 0.582 | 0.582031 | 40 | false |
| V-only | 1.626 | 1.626172 | 40 | false |
| Joint | 1.777 | 1.777344 | 40 | **true** |

仅 Joint `deployable=true`；V-only≈Joint（1.626 vs 1.777）、K-only 低（0.582）→ 定量确认 P1 方向性线索。**四臂口径正确，deployable 标记正确。**

### 1.2 Routing/Consumption 分解 ✅ 达标

- 从 `decomposition.jsonl` 重算：单元数 **17,920**（=40 对 × 2 侧 × 28 层 × 8 KV 头，与 Qwen3-0.6B 8 KV heads 一致）；**最大残差 2.956e-13 ≈ 0**（报告 2.96e-13 属实），远低于冻结容差 1e-3。
- routing 均值 24.846 / consumption 均值 21.839；d_A/d_B 分别诊断（routing 24.756 vs 24.937、consumption 21.730 vs 21.948），再取差值——**未用单文档热图替代反事实差**。
- mechanism.json / summary 均显式写明「局部固定 Q 代数恒等式，非全模型因果分解」→ 解释边界标注到位。

### 1.3 Oracle held-out 预测价值 ✅ 达标（但见 §2 复算性质疑）

- 从 `scores.jsonl` 的 `oracle_U` 臂（40 对）重算：hit 率 **0.725**、ΔE_CF>0 占比 **0.725**，与报告一致。
- 单元选择：`mechanism_units.jsonl` 5,376 行 = 8 训练对 × 28 层 × 8 头 × 3 通道；U top-5 全部含 V 通道（both×3 + V×2），无纯 K 单元；与 held-out 40 对的 **pair_id 重叠 = 0**，选择集前缀 `train`、验证集前缀 `val`，**无封存 test 参与**。
- 三项冻结判据：repair-vs-random 差 0.275、CI [0.150,0.425] 下界>0 ✅；方向一致 0.725>0.5 ✅；分解残差≈0 ✅ → verdict `mechanism_predictive`，与冻结 `e2_mechanism_prediction` 一致。
- **Oracle 离线隔离**：代码审计（P2_gpu.py）确认 `oracle_transplant` 仅出现在离线诊断循环（rank / transplant_units_delta / repair_delta）；可部署 Joint 路径 `inject_and_generate` 只用 mapper 映射缓存，无 Oracle 状态；`forward_counts.oracle=0`；`deployable` 仅 joint=true。**未发现 Oracle 泄漏进推理图。**

---

## 2. 逐项发现与风险等级

### F1【主要 · 复算性缺口】repair-vs-random 的成对 CI 无法从冻结产物独立重算

- `scores.jsonl` 的 `oracle_U` 臂只持久化 U 的 `delta_ecf`/`hit`，**未持久化随机基线逐对 delta**（`delta_rand` 仅存在于运行内存）；`mechanism.json` 只存聚合 `hit_random_mean=0.45` 与 CI `[0.150,0.425]`。
- 我从冻结产物只能重算「U-only hit=0.725，CI[0.575,0.850]」；**关键的「U−random 成对差 CI」无法从 scores 重算**（缺 delta_rand 逐对列）。`bootstrap_ci_report` 对 P2 也只重算四臂 E_CF，未覆盖此判据。
- 这与协议附录 A「所有主结果可由逐对记录重新计算」的要求存在差距。随机基线由 `rng=default_rng(seed=0)` 决定，理论上可用已提交代码重跑复现，但**非「从冻结产物直接重算」**。E2 的头号判据（CI 下界>0）恰好落在这个缺口上。
- **建议（工程师）**：把 `delta_rand` 逐对写入 `scores.jsonl` 或新增 `oracle_random` 臂 / 独立 ledger；或让 `bootstrap_ci_report` 支持从 U/random 逐对列重算该成对 CI。**不阻塞 P2 放行**（数值内部一致、代码已提交、种子确定），但在把贡献(2) 作为可发表证据 / P5 前应闭环。

### F2【主要 · 证据强度】机制诊断仅单 seed，跨 seed 稳健性未检验

- P2 仅 `p2_gpu_mvp_seed0`（config `seeds=[0]`）。冻结 E2 判据本身未显式要求 ≥3 seed，故**形式上满足**任务书六条；但：
  - 协议 `configs/protocol.yaml statistics.min_training_seeds=3` 与 §4.5 要求 ≥3 seed 报方差；PI 在 `final_signoff §2` 已就 kd gap 的跨 seed 不稳定（0.735→1.539）提出强度保留。
  - Oracle 单元集 U 由 **8 个训练对**排序选出，选择集小；不同 seed 下 U 的构成与 repair 效应是否稳定完全未知。机制单元的「可复现定位」在单 seed 下只是**一次性观测**。
- 判断：单 seed 足以支撑「E2 三判据在本次运行达标」这一**事实**，但不足以支撑「机制定位跨 seed 稳健」这一**更强主张**。贡献(2) 若启用，应显式限定为单 seed / MVP 对，或补 ≥2 seed 复核。**不阻塞 P2 放行**，但直接约束贡献(2) 的措辞强度（见 §4）。

### F3【主要 · 叙事一致性】论文仍写「P2 未运行 / 贡献(2) withheld / 无 held-out 机制发现」，已与事实冲突

- 当前 `main.tex` 多处（第 21、320、568、653、754、774 行）仍声明 "P2 was not run"、"None of these diagnostics have been executed"、"no held-out-validated mechanism finding"。P2 现已产出 `mechanism_predictive`。
- 这是**证据被低估**（安全方向，非夸大），仍是事实性错误。投递前必须同步：要么如实更新为「单 seed P2 held-out 机制证据」并在 §10 门槛下重新择支，要么明确说明为何仍保留 withheld。**属 P5 主要项，不阻塞 P2。**

### F4【次要 · 解释一致性】routing/consumption 范数大小与「V 消费主导」主张的张力需澄清

- 分解的 routing 范数均值（24.846）**大于** consumption（21.839），而四臂/Oracle 证据却指向「Value 消费侧主导」。二者是不同量纲的测度（局部注意力输出范数 vs 臂级 E_CF / 修复增益），并不必然矛盾，但稿中若直接并列易被审稿人质疑。
- 建议科学家/写作者明确：四臂与 held-out graft 支持「V 侧定位」，而 routing 范数较大反映 Key 改变引起的注意力重分配**同样存在**；候选公式宜表述为「V 消费为可修复主因，Key 路由为伴随效应」，避免绝对化。

### F5【次要 · 产物整洁】`p2_smoke_tmp` 冒烟测试残留于正式 runs 目录并通过审计

- `reports/runs/p2_smoke_tmp/`（n_resamples=100、train/val=8、n_select=2、n_heldout=4）是接线冒烟测试，位于正式 `reports/runs/`，且 `consistency_check` 判其 ok=true、未标 superseded、不在 `runs_index` 权威清单。
- 不会污染任何主结果（数据规模明显不同、口径透明），但存在被下游误读为「另一个 P2 run」的风险。建议工程师移出 `runs/` 或显式标注为 smoke/non-authoritative。

### F6【次要 · 判据独立性】E2 三判据中两项共享同一 hit_u 成分

- `direction_consistency_ratio = mean(hit_u) = 0.725`，与「repair 命中率 U=0.725」是同一量；「repair-vs-random CI」是在其上再减 random。故「三判据全达」实为**两个统计信号**（U 命中显著优于随机；残差≈0）+ 一个多数门槛重述。不违反冻结判据，但论文不应把三判据表述为三条相互独立的证据。

---

## 3. 合规通过项（无风险，简要记录）

- **Oracle 隔离**：代码与 forward_counts 双重确认 Oracle 未进 Joint 推理图；仅离线诊断使用。✅
- **机制选择数据来源**：U 仅用 train（8 对）选择，held-out 用 val（40 对），重叠=0，未碰封存 test。✅
- **预算/dtype/kernel 对齐**：bf16/sdpa/seed0，沿用 repro affine mapper 与权威代码（git 9d474be 在 HEAD 历史、跑分代码与 HEAD 一致）。✅
- **局部热图解释边界**：mechanism.json / summary / task book 均显式声明「非全模型因果分解」。✅
- **verdict 纪律**：工程师未自行升格贡献(2)，`claim_boundary` 明确「是否写入由 PI/审稿人裁决」。✅

---

## 4. 对贡献(2) 证据前提的判断（只给 PI 建议，不自行改措辞）

**判断：贡献(2) 的「证据前提」按冻结 E2 判据已成立**——三判据全达（repair-vs-random CI 下界 0.150>0、方向一致 0.725>0.5、残差≈0），且满足 Oracle 隔离、held-out 独立验证（train 选 U / val 检验、零重叠、未碰 test）、预算/dtype/kernel 对齐。这满足协议 §10 贡献(2) 模板「under controlled cache interventions with held-out predictive value」的实证内核，构成**可支撑贡献(2) 的机制证据前提**。

但强度须附加三条保留（影响是否/如何升格，不影响前提成立本身）：
1. **单 seed（F2）**：机制定位未经跨 seed 复核，U 由 8 对选出；宜限定为「MVP 对、seed0 的 held-out 机制证据」。
2. **复算缺口（F1）**：头号判据的成对 CI 暂不能从冻结产物直接重算；发表前应补齐 delta_rand 逐对列。
3. **解释边界（F4/F6）**：定位为 V 消费主导需与 routing 范数并存解释；三判据非三条独立证据。

**给 PI 的措辞建议（不替 PI 决定）**：
- 若维持边界/实证定位（`final_signoff §6.1` 保守选项），贡献(2) 继续 withheld 是合规的，但论文必须修正 F3 的「P2 未运行」陈旧表述，改为「单 seed P2 提供方向性 held-out 机制线索，按 §10 强度保留暂不升格」。
- 若要升格贡献(2)，建议先闭环 F1（复算性）与 F2（≥2 seed 复核 U 与 repair 效应），否则升格措辞在对抗审稿下风险较高。
- 无论选择哪条，**贡献(3) 维持 withheld**（P3 未跑、主终点未评估、三 δ 均不优于 kd_only）。

---

## 5. 风险等级汇总与 P2 放行建议

| 编号 | 发现 | 等级 | 阻塞 P2? |
|---|---|---|---|
| F1 | repair-vs-random 成对 CI 不可从冻结产物重算 | 主要 | 否（P5 前闭环） |
| F2 | 单 seed，机制定位跨 seed 未验证 | 主要 | 否（约束措辞强度） |
| F3 | 论文「P2 未运行」陈旧表述 | 主要 | 否（P5 前必修） |
| F4 | routing/consumption 范数 vs V 主导张力 | 次要 | 否 |
| F5 | p2_smoke_tmp 残留正式 runs 目录 | 次要 | 否 |
| F6 | 三判据非独立 | 次要 | 否 |

**P2 放行建议：有条件放行（Conditional GO）。** E2 三判据全部达标、Oracle 隔离与数据来源合规、provenance 齐全，P2 科学门（机制诊断在独立文档有预测价值）成立；F1–F6 均不推翻该结论。放行条件：F1/F2 在把贡献(2) 作为发表证据前闭环，F3 在投递前修正，F4–F6 在论文/报告中如实处理。

## 6. 给 PI 的 Go/No-Go 最终建议

- **P2**：建议 **GO（有条件）**——验收 `mechanism_predictive`，E2 冻结判据未被篡改、Oracle 未泄漏、未碰封存 test。
- **P3**：维持 **NO-GO**——主终点（成对 E_CF vs kd_only，CI 上界<0）未评估、封存测试未运行；P2 机制证据不改变 P3 前置条件。
- **P4/P5**：P4 维持 NO-GO；P5 维持「边界/实证研究」条件性签 off，**任何把贡献(2) 写成已证实的版本不予签 off**，除非按 §4 先闭环 F1/F2 并经 PI 重新择支。
- **触发下一轮**：F1–F3 修复完成后，若 PI 决定升格贡献(2)，再做一次聚焦复审；否则 P2 阶段可就此收口。

---

## 7. 结论

P2/E2 的三项冻结判据在真实 GPU 产物上独立复算全部达标（四臂 V-only≈Joint、分解残差 2.96e-13、held-out repair CI 下界>0 且方向一致 0.725），Oracle 隔离、train/val 来源隔离、预算/dtype/kernel 对齐、provenance 齐全均通过，v2.1/v2.2 判据未被篡改。**贡献(2) 的证据前提按冻结判据成立**，但受单 seed、复算缺口与解释边界三条强度保留约束。主要风险 F1（复算性）/F2（单 seed）/F3（论文陈旧表述）均不推翻 P2 结论。据此建议 **P2 有条件 GO，P3/P4 NO-GO，P5 维持边界定位签 off、贡献(2)(3) 措辞升格由 PI 裁决**。

**签署：reviewer（对抗性审阅），2026-11-23。**

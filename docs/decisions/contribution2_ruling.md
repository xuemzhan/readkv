# 贡献(2) 升格裁决与 P2 阶段收敛决议（反事实功能保真 V2.0）

> 裁决人：PI / 课题组长。日期：2026-11-23。
> 依据：审稿报告 `reports/review/p2_mechanism_review.md`、`reports/p2_mechanism_summary.json`、`reports/runs/p2_gpu_mvp_seed0/mechanism.json`、`docs/decisions/final_signoff.md` §3.1/§4、`docs/protocol.md` §4.5/§5/§8/§10 及附录 A、`configs/prereg/phase3_loss_config_v2.1.yaml §e2_mechanism_prediction`（v2.2 原样继承）。
> 本裁决只写决策文档，不改 `src/**`、`reports/runs/**`、冻结判据或论文源文件，不写代码、不跑实验。

---

## 1. 事实核验与结论摘要

审稿人对 E2 三判据的独立重算与产物核对属实，PI 确认：

- **四臂**（40 对/臂）：Self=0、K-only=0.582、V-only=1.626、Joint=1.777；仅 Joint `deployable=true`；V-only≈Joint 定量确认 P1 方向线索。
- **Routing/Consumption 分解**：17,920 单元，最大残差 2.956e-13≈0（容差 1e-3）；d_A/d_B 分别诊断后取差；解释边界标注"局部固定 Q 代数恒等式，非全模型因果分解"。
- **Oracle held-out**：U 由 8 训练对选出（5,376 单元），held-out 40 对零重叠、前缀 train/val 隔离、未碰封存 test；命中 0.725 vs 随机 0.450，成对差 0.275、CI [0.150, 0.425] 下界>0；方向一致 0.725>0.5；`forward_counts.oracle=0`、`zero_re_prefill=true`。
- **合规**：provenance 齐全（git 9d474be 在历史、跑分代码与 HEAD 一致、工作区 clean）；v2.1/v2.2 未被篡改；工程师未自行升格贡献(2)（`claim_boundary` 交由 PI 裁决）。

**结论**：贡献(2) 的**机制证据前提按冻结 E2 判据成立**（审稿 §4 判断成立，PI 采纳）。但 F1（复算缺口）、F2（单 seed）、F4/F6（解释边界）三条强度保留属实，直接约束升格措辞与投递门槛。

---

## 2. 贡献(2) 升格裁决（核心）

### 2.1 裁决：有条件升格为「限定形式」，不维持完全 withheld

PI 明确回答"现在允许还是维持 withheld 直到 F1/F2 闭环"这一二选一：

> **裁定：现在允许在论文中写入贡献(2)，但只能是「限定形式（qualified form）」；§10 强模板的无条件形式维持 withheld，直到 F1 闭环（投递硬门槛）与 F2 补齐 ≥3 seed（强度门槛）。**

理由：

1. **证据前提已按冻结判据成立**，且满足 held-out 独立验证、Oracle 隔离、预算/dtype/kernel 对齐——这是实打实的机制证据，继续完全 withheld 会因单 seed 而低估已成立的科学结果，属事实性保守错误（与 F3 同类）。
2. **但协议硬要求不允许无条件强措辞**：`configs/protocol.yaml statistics.min_training_seeds=3`、§4.5「≥3 seed 报方差」、附录 A「所有主结果可由逐对记录重新计算」——单 seed（F2）与头号判据 CI 不可从冻结产物重算（F1）恰好触犯这两条。这不是"措辞强度保留"能消解的，须以产物闭环。
3. 因此采用中间路线：**限定形式的贡献(2) 现在可写（尊重已成立证据），强形式 withheld 至 F1/F2 闭环（守住协议硬约束）**。

### 2.2 精确措辞边界（强制）

**允许使用的动词与结论（限定形式）**：

| 可用表述 | 必备限定词 |
|---|---|
| "we find / observe / report held-out predictive evidence that…" | 必须写明 "on the MVP pair (1.7B→0.6B), single seed (seed 0), 40 held-out pairs" |
| "localizes predominantly to receiver-side Value-consumption pathways" | "predominantly / primarily"，不得用 "exclusively / solely" |
| "repair of selected units (mostly V / both channels) improves E_CF more than random units (0.725 vs 0.450, 95% CI [0.150,0.425])" | 须附样本量与单 seed 标注 |
| "V-consumption as the reparable primary locus, with Key-routing as an accompanying attention-redistribution effect" | 两者必须并存陈述（F4） |
| "a local, fixed-query decomposition (routing/consumption), not a global causal decomposition" | 解释边界必带 |

**禁止使用的动词与结论（无条件强形式）**：

- ✗ "We localize the gap to…"（§10 模板(2) 的裸强形式）——F1/F2 闭环前不得用；闭环后须经 PI 重新择支方可启用。
- ✗ "robustly / consistently / across seeds / across model pairs"——单 seed、仅 MVP 对，禁止跨 seed/跨对泛化。
- ✗ "causal / we establish causality / necessary and sufficient"——局部代数恒等式与 Oracle 离线修复不支持因果主张。
- ✗ "V-only ≈ Joint proves Value consumption is the sole cause"——K-only=0.582 非零、routing 范数更大，Key 路由伴随效应须承认。
- ✗ 把 repair-vs-random、方向一致、残差≈0 表述为"三条独立证据"——F6：前两者共享 hit_u 成分，实为两个统计信号 + 一个多数门槛重述。
- ✗ 任何把局部热图解释为全模型因果分解的措辞。

### 2.3 强制保留（无论是否投递）

1. **单 seed 保留**：贡献(2) 限定为 "MVP 对、seed 0 的 held-out 机制证据"，显式声明跨 seed 稳健性未检验、U 由 8 训练对选出（F2）。
2. **解释边界保留**：V 消费为可修复主因、Key 路由为伴随效应（F4）；三判据非三条独立证据（F6）；局部恒等式非全模型因果分解。
3. **复算缺口披露**：在 F1 闭环前，投稿版本须披露"头号判据成对 CI 暂不能从冻结产物逐对重算，代码与种子可复跑复现"（F1）。
4. **§10 门槛**：贡献(3) 维持 withheld；主终点（成对 E_CF vs kd_only，CI 上界<0）未评估声明维持；P>0.05 不作等效维持。

---

## 3. 给工程师的指令（F1/F2 闭环）

### 3.1 F1【投递硬门槛，必须闭环】逐对 delta_rand 持久化

- **要求**：闭环"头号判据不可从冻结产物重算"。二选一：
  - (a) 以原代码与 `rng=default_rng(seed=0)` 重跑 P2 seed0，在 `scores.jsonl` 的 `oracle_U` 臂**新增 `delta_rand` 逐对列**（每对随机单元集的 ΔE_CF），并新增 `oracle_random` 臂 ledger；
  - (b) 新增独立 `oracle_random_pairs.jsonl`，逐对记录 U 与随机基线的 delta，供成对 bootstrap 重算。
- **配套**：使 `scripts.bootstrap_ci_report` 支持从 U/random 逐对列重算 `repair_vs_random` 成对 CI，输出须复现点 0.275、CI [0.150,0.425]（允许 ≤0.05 的 seed 端点差）。
- **新 run_id**：`p2_gpu_mvp_seed0_delta_rand_audit`（或同类语义命名）；**不得回改** `p2_gpu_mvp_seed0` 的冻结产物。
- **验收**：审稿人能从新产物独立重算出成对 CI 下界>0；否则 F1 未闭环，P5 不得使用贡献(2) 的 CI 数字。

### 3.2 F2【强度门槛，要求补跑】P2 ≥3 seed 与 U 稳健性

- **要求**：补跑 seed1、seed2 的 P2（新 run_id `p2_gpu_mvp_seed1`、`p2_gpu_mvp_seed2`），每项含完整 `mechanism.json`、四臂 scores、`decomposition.jsonl`、`mechanism_units.jsonl`、held-out 逐对与 `delta_rand` 列。
- **纪律**：U 仍只用各自训练对选择、held-out 用 val、零重叠、未碰封存 test；沿用 repro 权威代码（在 HEAD 历史、跑分代码与 HEAD 一致）；写全 `git_hash`/`zero_re_prefill`/`bootstrap_seed`/`transfer_broken` 字段。
- **汇报**：逐 seed 报告 U 构成、命中率、repair-vs-random CI；若三 seed 的 U 构成与 repair 效应不一致，如实标注"机制定位跨 seed 不稳定"，贡献(2) 维持限定形式。
- **降级路径**：若 GPU 算力确实无法补跑 seed1/2，则 F2 不闭环——此时贡献(2) **永久维持限定形式**（单 seed），严禁 robust/across-seeds 措辞；须在论文中显式承认此限制。此为可接受降级，但不可伪装成 ≥3 seed。

### 3.3 次要项

- **F5**：将 `reports/runs/p2_smoke_tmp/` 移出正式 runs 目录或显式标注 `smoke/non-authoritative`，避免被误读为第二个 P2 run。
- 沿用 repro 权威 provenance 口径；P2 产物交审稿人审计后再上报 PI。

---

## 4. 给写作者的指令（F3 必改 + 贡献措辞）

**F3（投递前必修，事实性错误）**：`main.tex` 仍写 "P2 was not run" / "None of these diagnostics have been executed" / "no held-out-validated mechanism finding"（审稿列第 21/320/568/653/754/774 行等）。必须：

1. **更新 P2 现状**：删除所有"P2 未运行"表述，改为如实报告 P2 已运行并产出 `mechanism_predictive`：
   - 四臂数据（Self 0 / K-only 0.582 / V-only 1.626 / Joint 1.777）；
   - 分解残差 2.96e-13 与"局部恒等式非全模型因果分解"边界；
   - Oracle held-out 命中 0.725 vs 随机 0.450、CI [0.150,0.425]、train 选 U / val 检验零重叠、未碰封存 test、Oracle 未进推理图。
2. **贡献措辞**：按 §2.2 限定形式写贡献(2)——可用动词带单 seed/MVP 对限定；禁用词表逐条核对；强制附 §2.3 三条保留。
3. **候选公式**：按 `p2_mechanism_summary.json` 写"V 消费为可修复主因、集中在中后层少数 KV 头（layer12/head5、layer25/head4、layer14/head1）、Key 路由为伴随效应"（F4）。
4. **三判据表述**：不得写成"三条独立证据"，改为"两个统计信号（U 命中显著优于随机、残差≈0）+ 一个多数门槛"（F6）。
5. **维持不变**：主终点未评估、贡献(3) withheld、P3/P4 未运行、broken-transfer 边界、P>0.05 不作等效——全部维持；不得因 P2 结果而弱化。
6. **定位**：仍为 empirical/boundary study，不升为 method paper（理由见 §5）。

---

## 5. P3/P4/P5 状态与投递定位

| 阶段 | 状态 | 是否因 P2 变化 |
|---|---|---|
| P0/E0、P1 | GO（维持） | 不变 |
| P2 机制 | **GO（验收 `mechanism_predictive`，本轮收口）** | 新增：E2 三判据达标、贡献(2) 限定形式获准 |
| **P3 方法** | **NO-GO（维持）** | **不变**——主终点未评估、封存测试未跑、三 δ 均不优于 kd_only；P2 机制证据不改变 P3 前置条件 |
| **P4 泛化** | **NO-GO（维持）** | 不变 |
| **P5 投递** | **条件性 GO（维持，条件更新）** | 贡献(2) 限定形式可入稿；但投递硬门槛现为：**F1 闭环 + F3 修正 + §2.3 保留齐全**；F2 未闭环则贡献(2) 维持单 seed 限定 |

**投递定位裁决**：**维持 empirical/boundary study 定位，不改为 method paper。**

理由：即使贡献(2) 机制内核成立，贡献(3)（机制约束 Mapper 改善主终点）仍完全 withheld——主终点未评估、封存测试未跑、P3 未运行、三 δ 均不优于 kd_only。按协议 §8/§10，缺方法层证据即为边界/实证研究，不得声称方法贡献(3)。贡献(2) 的加入使论文从"仅评价层"变为"评价层 + 机制层（限定）"，但不改变其非方法论文的定位。

**§10 门槛最终意见**：当前满足贡献(1) 全部 + 贡献(2) 限定形式；贡献(3) withheld。任何把贡献(2) 写成无条件强形式（"We localize the gap…" 裸用）或把贡献(3) 写成已证实的版本，**一律不予签 off**。

---

## 6. 给科学家的指令

1. 确认候选公式表述符合 F4：V 消费为主因、Key 路由为伴随；局部恒等式非全模型因果分解。
2. 核对 F6：三判据非独立证据，避免论文过度解读。
3. 若 F2 补跑显示 U 跨 seed 不稳定，准备相应降级表述（贡献(2) 维持单 seed 限定）。

---

## 7. 仍需人工（真实 PI）决策的事项

1. **F1/F2 的资源投入**：是否投入 GPU 补跑 P2 seed1/2（≥3 seed）与 delta_rand 审计 run；考虑到此前 GPU 争用/停滞历史，需真实 PI 确认排期。若不投入，接受贡献(2) 永久单 seed 限定（降级路径）。
2. **投递时机**：现在以"贡献(1) + 限定贡献(2) 的实证研究"投递，还是等 F1/F2 闭环后以更强贡献(2) 重投——策略选择由真实 PI 拍板。
3. **作者署名与投稿期刊**：维持人工决策。

---

## 8. 结论

- **贡献(2)**：证据前提按冻结判据成立；**裁定有条件升格为限定形式**——现在可写，但须严格限定措辞（§2.2 可用/禁用词表）+ 强制单 seed/解释边界保留（§2.3）；§10 强模板无条件形式 withheld 至 F1 闭环（投递硬门槛）与 F2 补齐 ≥3 seed（强度门槛）。
- **工程师**：F1 必须闭环（新 run_id `p2_gpu_mvp_seed0_delta_rand_audit` + delta_rand 逐对列 + bootstrap 支持）；F2 要求补跑 seed1/2（新 run_id），不补则贡献(2) 维持单 seed 限定；F5 清理 smoke run。
- **写作者**：F3 投递前必修（P2 已运行、机制证据、限定措辞、三条保留）；主终点未评估、贡献(3) withheld、P3/P4 未运行维持。
- **阶段**：P0/P1/P2 GO；P3/P4 NO-GO；P5 条件性 GO（门槛更新为 F1 闭环 + F3 修正 + 保留齐全）。
- **定位**：维持 empirical/boundary study；贡献(3) 绝不升格。

**签署：PI / 课题组长（贡献(2) 升格裁决 · 2026-11-23）**

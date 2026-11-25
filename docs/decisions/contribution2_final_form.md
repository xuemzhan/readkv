# 贡献(2) 最终形式裁决与 P2 阶段收口（反事实功能保真 V2.0）

> 裁决人：PI / 课题组长。日期：2026-11-23。
> 依据：`reports/review/p2_f1f2_closure_review.md`、`reports/p2_seed_robustness.json`、`docs/decisions/contribution2_ruling.md`（F1 投递硬门槛 / F2 强度门槛）、`docs/decisions/final_signoff.md`、`docs/protocol.md` §4.5/§8/§10 及附录 A、`configs/protocol.yaml statistics.min_training_seeds=3`。
> 本裁决只写决策文档，不改 `src/**`、`reports/runs/**`、冻结判据或论文源文件，不写代码、不跑实验。

---

## 1. 闭环事实核验与裁决前提

审稿人对 F1/F2/F5 的独立重算与产物核验属实，PI 逐项确认：

| 项 | 核验结论 |
|---|---|
| **F1（投递硬门槛）** | 从审计 run `p2_gpu_mvp_seed0_delta_rand_audit` 逐对重算 `hit_u−hit_rand`：point=0.275、CI [0.150,0.425] 下界>0，与汇总一致；扩展 `bootstrap_ci_report.py`（commit 6784780）新增 `repair_vs_random` 终点，三 seed 输出 0.275/[0.150,0.425]、0.275/[0.125,0.425]、0.350/[0.200,0.500]，均可从冻结产物复算；原 run 未改。**已闭环 ✅** |
| **F2（强度门槛）** | 三 P2 run 完整（6 文件），`git_hash=6784780`、`zero_re_prefill=true`、bf16/sdpa、bootstrap_seed 齐全，全部 `mechanism_predictive`；U 各 seed 仅 train 选、held-out 用 val、零重叠、未碰 test；4 个核心单元 `(12,5,V/both)`、`(25,4,V/both)` 跨 3 seed 全重合，第 5 单元漂移如实（seed0=(14,1,V)、seed1=(24,2,both)、seed2=(14,1,both)）；repair point 0.275–0.350、命中 0.725–0.750。**已闭环 ✅，满足 ≥3 seed** |
| **F5（清理）** | `p2_smoke_tmp` 已移至 `reports/_non_authoritative/`，不再被审计误计。**已闭环 ✅** |
| **prereg** | v2.1/v2.2 `git diff` 为空，未被篡改。✅ |

**裁决前提成立**：此前约束贡献(2) 强形式的两条**产物级硬约束**（F1 头号判据 CI 不可从冻结产物重算、F2 单 seed）均已消除；协议 `min_training_seeds=3` 与 §10「实验通过后可用贡献模板」的门槛现已满足。

---

## 2. 贡献(2) 最终形式裁定：解禁强形式

### 2.1 裁决

> **裁定：解禁贡献(2) 强形式（启用 §10 模板(2) 的强动词），附四条强制条件（§2.2）。**

理由：

1. **产物级硬约束全部消除**：`contribution2_ruling §2.1` 设定"强形式 withheld 至 F1 闭环（投递硬门槛）与 F2 补齐 ≥3 seed（强度门槛）"——两条现已满足，按该裁决自身的承诺，强形式应随之解禁；继续维持限定形式将是在证据已达标后无依据地自我设限。
2. **§10 门槛现已达成**：贡献(2) 模板 "We localize the gap to receiver-side routing and consumption effects under controlled cache interventions" 的实证内核（受控缓存干预 + held-out 预测价值）已由三 seed 独立复算支撑，CI 下界>0、跨 seed 核心单元稳定，满足"实验通过后"的条件。
3. **≥3 seed 要求满足**：三 seed 全部 `mechanism_predictive`、repair CI 下界均>0，达到 `min_training_seeds=3` 与 §4.5 报方差要求；此前"单 seed 不足以支撑强结论"的保留已失效。
4. **不升格贡献(3)**：解禁仅限贡献(2)，方法层证据（P3、封存测试、主终点）仍完全缺位——详见 §4。

### 2.2 强形式的四条强制条件（缺一不可，违反即不予签 off）

**条件 1 — 范围限定（禁用词延续）**：
- 可启用强动词："We localize the gap to receiver-side Value-consumption pathways under controlled cache interventions."
- **仍严格禁止**："robustly/consistently across model pairs"、"across model pairs/families"、"causal / necessary and sufficient / we establish causality"、"sole cause / exclusively"。
- 原因：机制证据仅来自 **MVP 等深对 (1.7B→0.6B)**，且为局部固定 Q 代数恒等式 + Oracle 离线修复；跨对泛化需 E5/P4 支撑（当前无），因果主张超出恒等式权限。这是 `contribution2_ruling §2.2` 禁用词表的延续，不因 F1/F2 闭环而放宽。

**条件 2 — 强制披露 F4/F6**：
- 必须并存："V 消费为可修复主因、Key 路由为伴随效应"（F4）；"局部恒等式非全模型因果分解"（F4）；"repair-vs-random 与方向一致共享 hit_u 成分、非三条独立证据（实为 2 统计信号 + 1 多数门槛）"（F6）。
- 必须如实报告："4/5 核心单元跨 seed 稳定，第 5 单元轻微漂移；命中 0.725–0.750、效应点 0.275–0.350 有波动"——支持"核心定位跨 seed 稳健"，**不得**声称"逐单元恒定/完全不变"。

**条件 3 — P5 前置：seed 数更新（F3 延伸）**：
- 论文所有 "single seed" 表述须更新为"三 seed（seed 0/1/2）"，并补三 seed 的 repair CI 与 U 重合结论；否则强形式与陈旧表述并存构成事实性矛盾。

**条件 4 — 贡献(3) 与主终点门槛维持**：
- 贡献(3) 维持 withheld；主终点（成对 E_CF vs kd_only，CI 上界<0）未评估声明维持；P3/P4 未运行维持；P>0.05 不作等效维持。

---

## 3. 给写作者的最终定稿指令

1. **seed 数更新（最高优先，事实性）**：将全文 "single seed" / "one seed" / "P2 单 seed" 改为"三 seed（seed 0/1/2）"；`mechanism` 相关段落补三 seed 的 repair-vs-random CI（[0.150,0.425]/[0.125,0.425]/[0.200,0.500]）与命中率（0.725–0.750）。
2. **贡献(2) 强形式**：按 §10 模板写强动词 "We localize the gap to receiver-side Value-consumption pathways under controlled cache interventions"，严格套用 §2.2 条件 1 的可用/禁用词表。
3. **强制披露（条件 2）**：加入 V 主因+Key 伴随、局部恒等式非全模型因果分解、三判据非独立（2 信号+1 门槛）、4/5 核心单元跨 seed 稳定且第 5 单元漂移、效应点波动区间——五点全部落稿。
4. **范围边界**：所有机制结论标注"MVP 等深对"；禁止任何 "across model pairs / causal / sole cause" 措辞。
5. **维持不变**：贡献(3) withheld、主终点未评估、P3/P4 未运行、broken-transfer 边界、P>0.05 不作等效——不得因贡献(2) 解禁而弱化。
6. **定位**：维持 empirical/boundary study，不升为 method paper（缺贡献(3)）。
7. **引用核验**：`[PLACEHOLDER]` 引用按 §9 投递前核实。

---

## 4. P0–P5 最终状态与投递裁决

| 阶段 | 最终状态 | 说明 |
|---|---|---|
| P0 / E0 | **GO** | 维持 |
| P1 基准 | **GO** | 维持 |
| P2 机制 | **GO（完全收口）** | E2 三判据达标、F1/F2/F5 闭环、三 seed `mechanism_predictive`，贡献(2) 强形式获准 |
| P3 方法 | **NO-GO（维持）** | 主终点未评估、封存测试未跑、三 δ 均不优于 kd_only；P2 结果不改变 P3 前置 |
| P4 泛化 | **NO-GO（维持）** | 未见模板 / 真实文档 / 封存 test 未运行；跨对泛化无证据 |
| P5 投递 | **有条件 GO（条件更新）** | 投递门槛见下 |

**投递裁决：批准投递，但为有条件 GO——必须满足以下全部门槛后方可投稿：**

1. 论文完成 §3 七条定稿（尤其 seed 数更新 + 贡献(2) 强形式 + 五点强制披露）；
2. §2.2 四条强制条件逐条满足，经审稿人合规复核；
3. 贡献(3) withheld、主终点未评估、边界/实证定位维持；
4. `[PLACEHOLDER]` 引用核验完成（协议 §9）。

**定位裁决**：**维持 empirical/boundary study，不改为 method paper。** 贡献(2) 解禁使论文从"仅评价层"变为"评价层 + 机制层（三 seed 支撑）"，但方法层（贡献(3)）仍完全缺位（P3 未跑、主终点未评估、三 δ 不优于 kd_only）。按协议 §8/§10，缺方法层证据即为边界/实证研究。任何把贡献(3) 写成已证实的版本一律不予签 off。

**§10 门槛最终意见**：当前满足贡献(1) 全部 + 贡献(2) 强形式（附四条强制条件）；贡献(3) withheld。这是三贡献层次中的前两层达标，定位仍为边界/实证研究。

---

## 5. 仍需人工（真实 PI）决策的事项

1. **投递时机**：现在以"贡献(1) + 贡献(2) 强形式的实证研究"投递，还是等 P3（方法层）产出后以含贡献(3) 的完整方法论文投递？本 agent 的裁决是"当前稿件已具备边界/实证研究投递资格"，但"投现在 vs 等 P3"的策略由真实 PI 拍板。
2. **是否做 P3**：P3 需封存测试 + CF-RCT 训练 + δ=0.5 配平实验，成本高且三 δ 均不优于 kd_only 是重大风险信号；是否投入资源推进方法层、还是就此以实证/边界研究收口，属真实 PI 的方向决策。
3. **作者署名**：`author list to be finalized` 由人工确定。
4. **目标期刊**：venue 选择由人工决定。

---

## 6. 结论

- **贡献(2)**：**解禁强形式**——F1（投递硬门槛）与 F2（强度门槛）均已闭环，§10 门槛与 ≥3 seed 要求满足；附四条强制条件（范围限定 MVP 对/禁 causal/sole cause/across model pairs、强制披露 F4/F6 与边缘漂移、P5 seed 数更新、贡献(3) 与主终点门槛维持）。
- **写作者**：三 seed 替换 single seed、启用强动词、落稿五点披露、维持贡献(3) withheld 与边界定位。
- **阶段**：P0/P1/P2 GO（P2 完全收口）；P3/P4 NO-GO；P5 有条件 GO（四门槛）。
- **定位**：维持 empirical/boundary study；贡献(3) 绝不升格。
- **人工决策**：投递时机、是否做 P3、署名、期刊。

**签署：PI / 课题组长（贡献(2) 最终形式裁决 · 2026-11-23）**

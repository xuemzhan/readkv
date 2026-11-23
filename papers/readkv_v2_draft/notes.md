# 写作者笔记 —— readkv_v2_draft（仅内部，不投递）

> 状态：论文初稿配套笔记。所有数值只读自 `reports/runs/**` 冻结产物，本笔记未重新计算任何统计。
> 硬约束遵循 `docs/protocol.md §10`（贡献门槛）、§8（决策树）、`docs/decisions/p0_direction.md §4`（mock 非证据）。

---

## 0. 本次已写文件

- `papers/readkv_v2_draft/main.tex`：全文 LaTeX 初稿（摘要、引言、相关工作、方法、实验、结果、结论与局限、附录 A）。
- `papers/readkv_v2_draft/notes.md`（本文件）：图表清单、cover letter 要点、数据完整性备案。

未写/未改：任何代码、`reports/runs/**`、`configs/prereg/**`；未重新计算任何统计量。

---

## 0.5 本轮状态（数值定稿轮，2026-11-23）

- **R1 已闭环**（审稿第 2 轮确认）：主表已切换为 `*_repro_*` 权威 run，`git_hash=458de18`；"reproducible" 措辞已恢复并附 commit 引用。旧 8 个 run 仅在 provenance 脚注标注 superseded。
- **权威数值已填入，所有 TO BE FILLED 已删除**：
  - E0 门：`e0_gpu_mvp_repro_seed0`（cosine 1.0、KL 0、EM 1.0、round-trip、2.2e-16 ≪ 6.95）。
  - P1 MVP joint：`p1_gpu_mvp_repro_seed{0,1,2}` → E_CF 1.968/1.934/2.123，dual 0.667/0.650/0.617，flip 0.938/0.898/0.958，coverage 0.800/0.817/0.800。
  - kd_only 三 seed：**seed0** `p1_gpu_kdonly_mvp_seed0` E_CF 0.735 [0.5517,0.9344]、dual 0.700、flip 1.0、cov 0.800；**seed1** `p1_gpu_kdonly_mvp_seed1_par` E_CF 1.034 [0.7663,1.3279]、dual 0.633、flip 1.0、cov 0.817；**seed2** `p1_gpu_kdonly_mvp_seed2_fast` E_CF 1.539 [1.1481,1.9588]、dual 0.683、flip 0.979、cov 0.800。三组 CI 下界均>0，全部 `distortion_present=true` / `transfer_broken=false`；范围 E_CF 0.735–1.539、dual 0.633–0.700。
  - δ 网格：0.5/1.0/2.0 的 E_CF = 2.7496/1.5968/2.7625，PI 锁定 δ=0.5（硬护栏口径）。
- **P2 三 seed 完全收口（本轮更新）**：三个 run `p2_gpu_mvp_seed0_delta_rand_audit`（F1 逐对重算审计）/`p2_gpu_mvp_seed1`/`p2_gpu_mvp_seed2`，全部 commit `6784780`、`zero_re_prefill=true`、三判据全达、`mechanism_predictive`。四臂 Self 0/K-only 0.582/V-only 1.626/Joint 1.777（仅 Joint deployable，40 对/臂）；分解 17,920 单元、残差 2.96e-13、d_A/d_B 分别取差。held-out（各 seed U 由 8 训练对选、val 40 对零重叠、未碰封存 test）：命中 U/随机 0.725/0.450、0.725/0.450、0.750/0.400；repair point 0.275 [0.150,0.425] / 0.275 [0.125,0.425] / 0.350 [0.200,0.500]，CI 下界均>0；方向一致 0.725/0.725/0.750。U 稳健性：4/5 核心单元 (12,5,V/both)、(25,4,V/both) 跨 3 seed 全重合，第 5 单元漂移（seed0=(14,1,V)、seed1=(24,2,both)、seed2=(14,1,both)），如实报告"核心定位跨 seed 稳健、非逐单元恒定"。
- **F1/F2 已闭环**：头号判据成对 CI 已从审计 run 冻结产物独立重算（point 0.275、CI[0.150,0.425] 下界>0），F1 投递硬门槛闭环；三 seed 完成满足 `min_training_seeds=3`，F2 强度门槛闭环；不再写 "audit in progress"。
- **仍明确未评估**：主终点（成对 E_CF vs kd_only，CI 上界<0；CF-RCT 未训练）、P3/P4、封存测试、非等深对 repro；主终点结果出来前不下任何改善结论。
- **贡献(1) 全部 + 贡献(2) 强形式（限定于 MVP 等深对）；贡献(3) withheld；边界/实证研究定位不变**；所有未产出量均写"未评估/待补"，无推测数字。

---

## 1. 贡献措辞如何处理（§10 门槛）

- **只写贡献 (1)，且限定范围**："For the affine/ridge mapper tested here, we identify a gap between standard transfer utility and counterfactual response fidelity in cross-model KV handoff." 并附带：预注册成对反事实基准、机器精度实现门、`E_CF` 与 dual_correct/flip_consistency/coverage/info_gap 联合报告的纪律。
- **"reproducible" 措辞已恢复（R1 闭环）**：审稿第 2 轮确认 `458de18` 含全部跑分代码、旧 run 已 superseded、7 个权威 run provenance 齐全。摘要、贡献(1)、§4.2、结论中的 "reproducible" 均附 commit `458de18` 引用；主表只引用 `*_repro_*` 权威 run。旧 `53e9bc5` run 仅在 provenance 脚注出现。
- **贡献(1) 补 kd_only 说明**：kd 三 seed 缩小 gap 但未消除（E_CF 0.735–1.539、dual 0.633–0.700，三组 CI 下界均>0），跨 seed 仍有 gap；预算不对等（60对/3ep vs 120对/8ep）已披露，主终点因 CF-RCT 未训练而未评估 → 不声称 CF-RCT 改善。gap 仍限定为 tested affine/ridge mapper。
- **贡献 (2) 按 PI `docs/decisions/contribution2_final_form.md` 解禁「强形式」**：可用强动词 "We localize the gap to receiver-side Value-consumption pathways under controlled cache interventions"，但**范围限定 MVP 等深对 (1.7B→0.6B)**、局部固定 Q 恒等式、Oracle 仅离线诊断。**禁用**："robustly/consistently across model pairs"、"across model pairs/families"、"causal / necessary and sufficient"、"sole cause / exclusively"。四条强制条件：①范围限定+禁用词；②强制披露 F4/F6 + U 漂移；③全文 seed 数更新为三 seed；④贡献(3) 与主终点门槛维持。
- **F4/F6/稳健性披露（已落稿）**：V 消费为可修复主因、Key 路由为伴随的 attention 重分配效应；局部恒等式非全模型因果分解；三判据非独立（2 个统计信号 + 1 个多数门槛复述，repair-vs-random 与方向一致共享 hit_u）；4/5 核心单元跨 seed 稳定、第 5 单元轻微漂移；命中 0.725–0.750、效应点 0.275–0.350 有波动——支持"核心定位跨 seed 稳健"，不声称"逐单元恒定/完全不变"。
- **贡献 (3)（方法层）维持 withheld**：正文引言用 `withheld` 小条目列出，理由为 CF-RCT 未训练、主终点未评估。
- CF-RCT 方法章节（§3）明确标注 "design, not validated / proposed method not yet validated"。
- 结论明确：按决策树（§8）本工作应定位为**边界/实证研究论文**，不是高水平方法论文。
- 摘要与全文不出现任何"reduces / improves / localizes / mechanism-constrained mapper that closes the gap"等 (2)(3) 未证实措辞；withheld 条目只引用 protocol §10 的贡献模板编号，不含效果动词。
- 不把 `P>0.05` 写成等效；主终点未评估前不作任何 endpoint gain 声明。
- 全文定位为边界/实证研究；数据全为合成模板，标注"不适用于跨家族/真实世界迁移"的适用边界。
- P1 V-only≈Joint 为 "directional clue"，已在 P2 定量确认（K-only 0.582 非零 → V 消费非唯一原因）；跨 seed 稳健性未检验。
- 三判据非三条独立证据：两个统计信号（U 命中显著优于随机、方向一致 0.725>0.5 为多数门槛重述）+ 残差≈0 数值自检；正文 §5.x 已按此表述。
- 复算缺口**已闭环**：审计 run `p2_gpu_mvp_seed0_delta_rand_audit` 产出逐对 delta_rand，头号判据成对 CI 从冻结产物独立重算复现（0.275 [0.150,0.425]）；F1/F2 均闭环，审计扩展 commit `6784780`。

---

## 2. 如实写入的不利结果（结果章节 §5.4 "Adverse results and boundaries"）

1. **主验证对（4B→1.7B）质量退化**：joint dual_correct 从 Self 0.65–0.78 掉到 0.283–0.300，flip 仅 0.49–0.56，joint E_CF（≈5.37–6.08）接近/高于错文档与零缓存控制组；明确其为"broken transfer"而非干净的反事实失真，**定性为迁移失败边界、不计入 H1 正向证据**；`quality_pass` 仅表数据质量门，不含迁移效用（R4）。
2. **MVP V-only≈Joint**：K-only 很小（P1 0.555–0.630 / P2 0.582），V-only（P1 1.660–1.851 / P2 1.626）接近 Joint（P1 1.934–2.123 / P2 1.777）；P2 已在单 seed 定量确认，但 K-only 非零 → V 消费非唯一原因，Key 路由为伴随效应；跨 seed 未检验。
3. **MVP dual_correct 0.617–0.667 < 0.7**：Self 锚点本身在合成模板上不完美，未用 mock 偏置掩盖；若进方法比较会触发 tradeoff。
4. **P3/P4 未运行；P2 三 seed 完全收口**：P2 产出三 seed 机制证据、F1/F2 闭环；无 CF-RCT 训练、无封存测试、无泛化/成本结果，不支持进一步结论（δ 已锁定但方法未训练/未评测）。
5. **δ 网格无正方向 + 预算 caveat**：δ=0.5/1.0/2.0 的 E_CF（2.7496/1.5968/2.7625）**全部高于 kd_only（0.735）**，本网格无 δ 使 CF-RCT-lite 优于 kd_only；π 裁定硬护栏锁定 δ=0.5（dual 0.70、flip 1.0，δ=1.0 因 dual 0.65<0.70 被否，δ=2.0 双重违反）；δ 网格 60 对/3 epoch vs kd 120 对/8 epoch，δ=0.5 压线满足护栏，均已如实披露（P3 重大风险预警，但不触发 §8 分支）。
6. **kd_only 三 seed 均有 gap**：E_CF 0.735–1.539、dual 0.633–0.700，三组 CI 下界均>0，跨 seed 未消除；不支持"强基线接近 Self"；主终点未评估，不声称 CF-RCT 改善。
7. **主终点未评估**：成对 E_CF vs kd_only（CI 上界<0）未跑，全文不作改善声明； nowhere 把 P>0.05 写成等效。
8. **Confound 备案**：E0 效应估计用多 token logprob（尺度≈20）与主终点 2 维 logit 尺度不同（误差上限 2.2e-16，不影响判定）；one-shot 全词表 kernel 路径残差 0.9993 已披露；主验证 run 的 `model_pair` 字符串误标（见 §4）。

---

## 3. 图表清单（图 1–7 / 表 1–3，全部只读冻结结果生成，不重算统计）

| 编号 | 内容 | 数据来源 | 当前状态 |
|---|---|---|---|
| 图 1 | 两篇已有工作→第三篇科学问题关系图 | 设计性示意 | 正文为文字占位；待绘图 |
| 图 2 | 严格 zero re-prefill 流程与 Self/Identity/Joint/Oracle 分界 | `algorithm_spec.md §3.4/§6.1` | 正文为文字占位；待绘图 |
| 图 3 | 反事实成对文档构造（含 F5 负控/F6 长度位置控制） | `protocol.md §3.2` | 正文为文字占位；待绘图 |
| 图 4 | 原生 vs 迁移响应差散点（分色 K/V/Joint 与任务域） | `p2_gpu_mvp_seed{0,1,2}/scores.jsonl`、`p2_gpu_mvp_seed0_delta_rand_audit/scores.jsonl`（四臂 40 对/臂） | P2 三 seed 已产出，可从冻结产物绘制 |
| 图 5 | 层/头误差热图与 Oracle 修复 | `p2_gpu_mvp_seed{0,1,2}/mechanism.json`、`mechanism_units.jsonl`、`decomposition.jsonl`、`reports/p2_seed_robustness.json`、`reports/p2_mechanism_summary.json` | P2 三 seed 已产出（17,920 单元、核心 U=(12,5,V/both)/(25,4,V/both) 跨 seed 稳定、命中 0.725–0.750；第 5 单元漂移如实标注）；可从冻结产物绘制 |
| 图 6 | 方法消融（KD / CF / 机制约束） | E3 产物 | 未跑，不画 |
| 图 7 | 泛化与成本—Pareto | E4/E5/E6 产物 | 未跑，不画 |
| 表 1 | 数据切片 / E0 实现门 | `e0_gpu_mvp_repro_seed0/metrics.json`（458de18） | 正文 E0 表已呈现（旧 main E0 run 已 superseded，不引用） |
| 表 2 | 主结果（P1 MVP repro joint + kd_only 三 seed + 主验证边界） | `p1_gpu_mvp_repro_seed{0,1,2}/`、`p1_gpu_kdonly_mvp_seed{0}_*`/`seed1_par`/`seed2_fast`、`p1_gpu_main_seed{0,1,2}/`（后者 provenance-limited） | 正文已呈现（kd 三 seed 齐） |
| 表 3 | 控制实验 / 显著性 / 训练成本 | `metrics.json` info_attribution + 未跑项 | 控制组聚合已写入正文；显著性/成本未跑，明确"未评估"，不填占位 |

注：正文现已包含 E0 门表、P1 MVP repro 表、kd_only 三 seed 段、主验证 provenance-limited 表、P2 机制段（§5.x，四臂/分解/三 seed held-out/U 稳健性）（即表 1/表 2 + 机制结果）。图 4/5 素材来自 P2 三 seed 冻结产物（commit `6784780`）；图 6/7 与表 3 的成本/显著性部分须等 P3/P4 真实产物后再生成，不得用 mock 或占位数字填充。

---

## 4. 数据完整性备案（写作者发现，需 PI/审稿人知悉）

- **主验证 run 的 `model_pair` 字符串误标（R6）**：`p1_gpu_main_seed{0,1,2}` 的 `config.json` 与 `runs_index.json` 中 `model_pair` 字段为 `"qwen3-1.7b-to-0.6b"`，但同一 config 的 `teacher` 路径为 `Qwen--Qwen3-4B`、`student` 为 `Qwen--Qwen3-1.7B`，`layer_map` 为 `{kind: proportional, n_teacher_layers: 36, n_student_layers: 28}`。正文按 `qwen3-4b-to-1.7b` 报告，**勘误已发布**：`reports/runs_index_errata.json` 中 `model_pair_corrected="qwen3-4b-to-1.7b"`，依据为路径 + 36→28 layer map；未改冻结 `scores.jsonl`，不影响任何计算指标。
- **可追溯性（R1，已闭环）**：旧 8 个 run（`git_hash=53e9bc5`）不含跑分代码，勘误标注 `superseded` 且冻结产物未改；新 commit `458de18` 含全部 11 个跑分/实现文件，权威 run `e0_gpu_mvp_repro_seed0`、`p1_gpu_mvp_repro_seed{0,1,2}` 全部 `git_hash=458de18`、工作区 clean。主表已切换到这些 repro run，"reproducible" 已恢复并附 commit。kd seed1 为 `a04990d`（458de18 后继、跑分代码一致，按 round-2 ancestry 口径审计）。非等深对无 repro run，保留为 provenance-limited 记录。
- **`quality_pass` 与 verdict 口径（R4）**：`quality_pass=true` = 数据质量门（split 隔离、模板无重叠、标注一致），**不含**模型迁移效用；冻结判据返回 `distortion_exists` 是输入下的正确输出，但与"clean 失真"叙事不同。勘误新增正交字段 `transfer_broken`（主验证三 seed 为 true）作注释，不改冻结 verdict。论文 §5.4 已补该说明，且明确主验证对**不计入 H1 正向证据**。
- **bootstrap seed（R5，已闭环）**：CI endpoints 依赖 bootstrap seed，point estimates 精确；pipeline 与审计脚本均按各 run 的 `bootstrap_seed` 取 seed，端点差异已消除（round 2 复核：repro 1.968/1.934/2.123、kd 0.735 [0.552,0.934] 一致）。正文脚注已更新。
- **δ 锁定（PI 裁决 docs/decisions/huber_delta_lock.md，形式登记 `configs/prereg/phase3_loss_config_v2.2.yaml`，`frozen_at: protocol-v2.2`）**：硬护栏口径（不引入容差），锁定 δ=0.5；δ=1.0/2.0 因 dual/flip 违反护栏被否。三 δ 的 E_CF 均高于 kd_only，为 P3 风险预警；60对/3ep vs 120对/8ep 预算不对等、δ=0.5 压线非劣均如实披露。正文 §3.6/§5.4/§5.5 已同步。封存测试不得再调 δ。
- **`info_gap` 字段为空**：当前编排把控制组作为独立臂，逐对 `info_gap` 未填充；聚合口径 `info_attribution`（控制组 E_CF − Joint E_CF）已在正文报告并声明此偏差，未改冻结判据。
- **E0 尺度差异**：E0 效应估计用多 token 序列 logprob（≈17–20），主终点用候选首 token 2 维 logit；因测量误差上限 2.2e-16，远小于两种尺度，E0 判定不受影响，正文已备案。
- **one-shot kernel 残差**：整段一次 prefill 全词表 cosine 最小 0.9993（47/80 低于 0.9998），来自 sdpa kernel 路径差异，不计入 E0 主锚点（注入路径与原生两步 bit-identical，cosine=1.0），正文已披露。
- **P2 机制产物与审计（三 seed 收口）**：`p2_gpu_mvp_seed0_delta_rand_audit`/`p2_gpu_mvp_seed1`/`p2_gpu_mvp_seed2`（commit `6784780`，`zero_re_prefill=true`，`forward_counts.capture=0/oracle=0`），各含 `mechanism.json`/`scores.jsonl`/`decomposition.jsonl`/`mechanism_units.jsonl`；held-out train 8 对选 U（5,376 单元）、val 40 对零重叠、未碰封存 test、Oracle 未进推理图。F1 成对 CI 从审计 run 冻结产物独立重算闭环（0.275 [0.150,0.425]）；F2 三 seed 完成（repair CI 下界均>0）；贡献(2) 已解禁强形式（范围限定 MVP 等深对、Oracle 离线、局部恒等式）。底层 commit 由 P1 的 `458de18` 前进至 P2 的 `6784780`（扩展审计脚本），两者均在 HEAD ancestry、跑分代码一致。
- **引用占位**：`main.tex`  bibliography 中 KV-Lingo / CacheLink 标为 citation placeholder，须按 `protocol.md §9` 核查正式版本、日期与实验口径后再定稿。

---

## 5. Cover letter 要点（草稿，待 PI 定稿）

1. 主题：将工作定位为"反事实功能保真的评价层 + 机制层（三 seed 支撑）+ 边界实证研究"，**不**宣称方法贡献；"reproducible" 仅在附 commit 时使用（P1 `458de18`、P2 机制 `6784780`）。
2. 要点一：问题重要性——标准 KV 迁移分数不保证反事实响应保真，可能导致"答对了但功能依赖被破坏"。
3. 要点二：贡献——(1) 预注册成对反事实基准（`458de18` 可复现）+ 机器精度实现门（2.2e-16）+ 强制联合报告纪律，gap 限定为 tested affine/ridge mapper（kd_only 三 seed 缩小但未消除，预算不对等已披露）；(2) **强形式**（限定 MVP 等深对、commit `6784780`、三 seed）：受控缓存干预下将 gap 定位到接收端 V 消费路径、Key 路由为伴随效应；repair point 0.275–0.350、CI 下界均>0、4/5 核心单元跨 seed 稳定（第 5 单元漂移如实报告）；不作因果/跨模型对主张。
4. 要点三：诚实边界——主验证对揭示明显质量退化，如实报告为失败边界；贡献(3) 不声称；P3/P4 未运行、封存测试未跑、主终点未评估；三判据非独立（2 信号 + 1 门槛）、局部恒等式非全模型因果分解均已披露。
5. 要点四：数据与复现——全部数字来自真实 GPU run（`reports/runs/`），主表为 `*_repro_*` 权威 run（commit `458de18`），bf16+sdpa，zero_re_prefill，MVP joint 与 kd_only 均 3 seed，簇级 paired bootstrap；mock 数字未使用；未产出量明确标"未评估"。
6. 审稿人可重算：`scripts.bootstrap_ci_report` / `scripts.consistency_check`；附数据完整性备案（§4）。

---

## 6. 下一步（触发条件）

- 章节/全文提交 → 触发审稿人 adversarial review；改审循环每阶段最多 2 轮，第 3 轮由 PI 裁决。
- kd_only 三 seed 已齐（seed0/1/2 全部落盘）；若后续要做预算配平复核或"接近 Self"择支判断，由 PI 按 §7 裁决；当前证据为跨 seed 持续 gap、主终点未评估。
- P2 三 seed 完全收口（`6784780`）：F1 逐对重算与 F2 三 seed 均闭环，贡献(2) 强形式已获准启用；若后续 E5/P4 产出非等深对证据，方可考虑放宽"MVP 等深对"范围限定；因果/跨模型对/sole cause 措辞始终禁用。
- `[PLACEHOLDER]` 引用须按 `protocol.md §9` 投递前核实（PI P5 投递门槛之一）。
- P3 方法后续真实运行并达到 §10 主终点门槛（成对 E_CF vs kd_only、CI 上界<0），再按决策树决定是否升级为方法论文并启用贡献 (3)；在此之前维持边界/实证定位。封存测试期间不得调整已锁定的 δ=0.5。

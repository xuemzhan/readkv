# 写作者笔记 —— readkv_v2_draft（仅内部，不投递）

> 状态：论文初稿配套笔记。所有数值只读自 `reports/runs/**` 冻结产物，本笔记未重新计算任何统计。
> 硬约束遵循 `docs/protocol.md §10`（贡献门槛）、§8（决策树）、`docs/decisions/p0_direction.md §4`（mock 非证据）。

---

## 0. 本次已写文件

- `papers/readkv_v2_draft/main.tex`：全文 LaTeX 初稿（摘要、引言、相关工作、方法、实验、结果、结论与局限、附录 A）。
- `papers/readkv_v2_draft/notes.md`（本文件）：图表清单、cover letter 要点、数据完整性备案。

未写/未改：任何代码、`reports/runs/**`、`configs/prereg/**`；未重新计算任何统计量。

---

## 0.5 本轮状态（PI 裁决后，2026-11-23）

- **kd_only 基线与 provenance-repro run 仍在后台跑，数值待工程师汇总**。本轮**不填任何新数字**，只在正文相应位置写了显式待填占位：
  - `TO BE FILLED from p1_gpu_kdonly_mvp_seed{0,1,2} / p1_gpu_mvp_repro_seed{0,1,2}`（另含 `e0_gpu_mvp_repro_seed0`）。
- **主终点（成对 E_CF vs kd_only，簇级 paired bootstrap，CI 上界<0）在结果出来前不得下结论**；不得声称走"强基线仍有失真→进 P2"或"强基线接近 Self→边界研究"任一分支。
- 当前数值表取自勘误中标注 `superseded / provenance-unverified` 的旧 run，已在正文明确标注 provisional；待 repro 汇总后统一替换。
- 本轮只做措辞与结构修订（R1 去 reproducible、贡献(1) 限定范围、R4 broken transfer/quality_pass 口径、R6 勘误引用、待填占位），维持贡献(2)(3) withheld 与边界/实证研究定位。

---

## 1. 贡献措辞如何处理（§10 门槛）

- **只写贡献 (1)，且限定范围**："For the affine/ridge mapper tested here, we identify a gap between standard transfer utility and counterfactual response fidelity in cross-model KV handoff." 并附带：预注册成对反事实基准、机器精度实现门、`E_CF` 与 dual_correct/flip_consistency/coverage/info_gap 联合报告的纪律。
- **禁用 "reproducible"/"可复现" 措辞（PI 裁决 R1，最高优先级）**：旧 8 个 run 的 `git_hash=53e9bc5` 不含跑分代码，已标注 `superseded / provenance-unverified`；虽已新 commit `458de18` 并重跑，但闭环复审前全文（含摘要、贡献(1)、结论、cover letter）不得出现该形容词。统一改为中性表述"we report the implementation and configuration used / real-GPU benchmark on an as-run working tree, provenance under remediation"。
- **贡献 (2)（机制层）与 (3)（方法层）明确"withheld"**：正文引言用 `withheld` 小条目列出，明确理由为机制证据与方法证据均未产出。
- CF-RCT 方法章节（§3）明确标注 "design, not validated / proposed method not yet validated"。
- 结论明确：按决策树（§8）本工作应定位为**边界/实证研究论文**，不是高水平方法论文。
- 摘要与全文不出现任何"reduces / improves / localizes / mechanism-constrained mapper that closes the gap"等 (2)(3) 未证实措辞；withheld 条目只引用 protocol §10 的贡献模板编号，不含效果动词。
- 不把 `P>0.05` 写成等效；主终点未评估前不作任何 endpoint gain 声明。
- 全文定位为边界/实证研究；数据全为合成模板，标注"不适用于跨家族/真实世界迁移"的适用边界。
- P1 V-only≈Joint 只写为 "directional clue"，明确"not a mechanism finding (P2 was not run)"。

---

## 2. 如实写入的不利结果（结果章节 §5.4 "Adverse results and boundaries"）

1. **主验证对（4B→1.7B）质量退化**：joint dual_correct 从 Self 0.65–0.78 掉到 0.283–0.300，flip 仅 0.49–0.56，joint E_CF（≈5.37–6.08）接近/高于错文档与零缓存控制组；明确其为"broken transfer"而非干净的反事实失真，**定性为迁移失败边界、不计入 H1 正向证据**；`quality_pass` 仅表数据质量门，不含迁移效用（R4）。
2. **MVP V-only≈Joint**：K-only 很小（0.555–0.630），V-only（1.660–1.851）接近 Joint（1.934–2.123）；仅为线索，不升级为机制结论。
3. **MVP dual_correct 0.617–0.667 < 0.7**：Self 锚点本身在合成模板上不完美，未用 mock 偏置掩盖；若进方法比较会触发 tradeoff。
4. **P2–P5 未运行**：无机制诊断、无 CF-RCT 训练、无最终 δ、无封存测试、无泛化/成本结果，不支持任何科学结论。
5. **Huber δ 仅规则冻结**：网格与规则冻结（v2.1），最终值未在验证集锁定，故不报任何方法阶段数字。
6. **主终点未评估**：成对 E_CF vs kd_only（CI 上界<0）未跑，全文不作改善声明； nowhere 把 P>0.05 写成等效。
7. **Confound 备案**：E0 效应估计用多 token logprob（尺度≈20）与主终点 2 维 logit 尺度不同（误差上限 2.2e-16，不影响判定）；one-shot 全词表 kernel 路径残差 0.9993 已披露；主验证 run 的 `model_pair` 字符串误标（见 §4）。

---

## 3. 图表清单（图 1–7 / 表 1–3，全部只读冻结结果生成，不重算统计）

| 编号 | 内容 | 数据来源 | 当前状态 |
|---|---|---|---|
| 图 1 | 两篇已有工作→第三篇科学问题关系图 | 设计性示意 | 正文为文字占位；待绘图 |
| 图 2 | 严格 zero re-prefill 流程与 Self/Identity/Joint/Oracle 分界 | `algorithm_spec.md §3.4/§6.1` | 正文为文字占位；待绘图 |
| 图 3 | 反事实成对文档构造（含 F5 负控/F6 长度位置控制） | `protocol.md §3.2` | 正文为文字占位；待绘图 |
| 图 4 | 原生 vs 迁移响应差散点（分色 K/V/Joint 与任务域） | `scores.jsonl` | 依赖 E2 机制诊断，未跑，不画 |
| 图 5 | 层/头误差热图与 Oracle 修复 | E2 诊断产物 | 未跑，不画（禁止伪造） |
| 图 6 | 方法消融（KD / CF / 机制约束） | E3 产物 | 未跑，不画 |
| 图 7 | 泛化与成本—Pareto | E4/E5/E6 产物 | 未跑，不画 |
| 表 1 | 数据切片 / E0 实现门 | `e0_gpu_{mvp,main}_seed0/metrics.json` | 正文 E0 表已呈现 |
| 表 2 | 主结果（P1 MVP + 主验证，联合报告） | `p1_gpu_{mvp,main}_seed{0,1,2}/metrics.json` | 正文两张表已呈现 |
| 表 3 | 控制实验 / 显著性 / 训练成本 | `metrics.json` info_attribution + 未跑项 | 控制组聚合已写入正文；显著性/成本未跑，留空待填 |

注：正文现已包含 E0 门表、P1 MVP 表、P1 主验证表（即表 1/表 2 的核心内容）。图 4–7 与表 3 的成本/显著性部分必须等对应阶段真实产物出现后再生成，不得用 mock 或占位数字填充。

---

## 4. 数据完整性备案（写作者发现，需 PI/审稿人知悉）

- **主验证 run 的 `model_pair` 字符串误标（R6）**：`p1_gpu_main_seed{0,1,2}` 的 `config.json` 与 `runs_index.json` 中 `model_pair` 字段为 `"qwen3-1.7b-to-0.6b"`，但同一 config 的 `teacher` 路径为 `Qwen--Qwen3-4B`、`student` 为 `Qwen--Qwen3-1.7B`，`layer_map` 为 `{kind: proportional, n_teacher_layers: 36, n_student_layers: 28}`。正文按 `qwen3-4b-to-1.7b` 报告，**勘误已发布**：`reports/runs_index_errata.json` 中 `model_pair_corrected="qwen3-4b-to-1.7b"`，依据为路径 + 36→28 layer map；未改冻结 `scores.jsonl`，不影响任何计算指标。
- **可追溯性（R1，阻塞项）**：旧 8 个 run（含 `e0_gpu_mvp_seed0`、`p1_gpu_mvp_seed{0,1,2}`、`e0_gpu_main_seed0`、`p1_gpu_main_seed{0,1,2}`）的 `git_hash=53e9bc5` 不含跑分代码，勘误中标注 `superseded`；新 commit `458de18` 含跑分代码，已重跑 `e0_gpu_mvp_repro_seed0`、`p1_gpu_mvp_repro_seed{0,1,2}`。本稿数值表暂用旧 run 并已明确标注 provisional；闭环复审前禁用 "reproducible" 形容词。
- **`quality_pass` 与 verdict 口径（R4）**：`quality_pass=true` = 数据质量门（split 隔离、模板无重叠、标注一致），**不含**模型迁移效用；冻结判据返回 `distortion_exists` 是输入下的正确输出，但与"clean 失真"叙事不同。勘误新增正交字段 `transfer_broken`（主验证三 seed 为 true）作注释，不改冻结 verdict。论文 §5.4 已补该说明，且明确主验证对**不计入 H1 正向证据**。
- **bootstrap seed（R5）**：CI endpoints 依赖 bootstrap seed，point estimates 精确；pipeline 与审计脚本的 bootstrap seed 待统一并写入 run config。正文已补脚注。
- **`info_gap` 字段为空**：当前编排把控制组作为独立臂，逐对 `info_gap` 未填充；聚合口径 `info_attribution`（控制组 E_CF − Joint E_CF）已在正文报告并声明此偏差，未改冻结判据。
- **E0 尺度差异**：E0 效应估计用多 token 序列 logprob（≈17–20），主终点用候选首 token 2 维 logit；因测量误差上限 2.2e-16，远小于两种尺度，E0 判定不受影响，正文已备案。
- **one-shot kernel 残差**：整段一次 prefill 全词表 cosine 最小 0.9993（47/80 低于 0.9998），来自 sdpa kernel 路径差异，不计入 E0 主锚点（注入路径与原生两步 bit-identical，cosine=1.0），正文已披露。
- **引用占位**：`main.tex`  bibliography 中 KV-Lingo / CacheLink 标为 citation placeholder，须按 `protocol.md §9` 核查正式版本、日期与实验口径后再定稿。

---

## 5. Cover letter 要点（草稿，待 PI 定稿）

1. 主题：将工作定位为"反事实功能保真的评价层与边界实证研究"，**不**宣称新机制或新方法；来源可追溯性修复闭环前不使用 "reproducible/可复现" 形容词。
2. 要点一：问题重要性——标准 KV 迁移分数不保证反事实响应保真，可能导致"答对了但功能依赖被破坏"。
3. 要点二：贡献——预注册成对反事实基准 + 机器精度实现门（2.2e-16）+ 强制联合报告纪律；在等深对上给出 CI 不跨 0 的 gap，**明确限定为 tested affine/ridge mapper，强基线（kd_only 等）尚未评估**。
4. 要点三：诚实边界——主验证对揭示明显质量退化，如实报告为失败边界；P2–P5 未运行，明确不声称机制/方法贡献。
5. 要点四：数据与复现——全部数字来自真实 GPU run（`reports/runs/`），bf16+sdpa，zero_re_prefill，≥3 seed，簇级 paired bootstrap；mock 数字未使用。
6. 审稿人可重算：`scripts.bootstrap_ci_report` / `scripts.consistency_check`；附数据完整性备案（§4）。

---

## 6. 下一步（触发条件）

- 章节/全文提交 → 触发审稿人 adversarial review；改审循环每阶段最多 2 轮，第 3 轮由 PI 裁决。
- 若 P2/P3 后续真实运行且达到 §10 门槛，再按决策树决定是否升级为方法论文并启用贡献 (2)(3) 措辞；在此之前维持当前边界/实证定位。

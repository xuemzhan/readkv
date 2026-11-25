# 完整候选答案评分提前执行裁决（protocol-v2.8 · 测量稳健性补充）

> 裁决人：PI / 课题组长。日期：2026-11-24。
> 触发：真实 PI 明确要求现在执行《ReadKV GPU 实验方案：完整候选答案评分》（`refine-logs/GPU_SEQUENCE_SCORING_PLAN.md`、`GPU_SEQUENCE_SCORING_TRACKER.md`）。
> 治理冲突：① `configs/prereg/gpu_followup_v2.7.yaml` §4 `deferred_options.candidate_full_string_scoring = "推迟到投稿后（读数稳健性补充）"`，方案自身也写"沿用这一排期"；② 第二轮复审 `reports/review/independent_research_and_manuscript_review_2026-11-24.md` 把候选全文评分列为**后续稳健性实验**、明确"全文评分不是当前投稿门槛"，当前稿件有编译/匿名稿/指标口径/归因措辞等**定向大修阻塞**、建议暂缓提交。
> 依据：上述复审全文；`configs/prereg/gpu_followup_v2.7.yaml`、`configs/prereg/full_candidate_scoring_v2.8.yaml`（本次新增）；`docs/decisions/{p5_final_signoff,p5_final_resignoff,research_scope_update,full_candidate_scoring_ruling}.md`；`docs/protocol.md §8/§9/§10`。
> 本裁决**只写决策文档 + 新增 v2.8 冻结文件**：不改代码 / 数据 / `reports/runs/**` / 论文源文件；不写代码、不跑实验、不伪造数据或文献。

---

## 1. 核心裁定

> **按真实 PI 指令办理：允许提前执行候选全文评分。** 但必须新增 `configs/prereg/full_candidate_scoring_v2.8.yaml`（`frozen_at: protocol-v2.8`）**显式覆盖 v2.7 的 deferred 排期**；v2.7 与任何旧冻结文件**一字不回写**。本实验定性为**测量稳健性补充**：不恢复贡献、不重算主终点、不碰封存 test、**不是方法贡献**。

我没有选择"不应执行"分支，理由：真实 PI 的指令优先；该实验本身有科学价值（检验两个既有结论对评分方式的敏感性），且只要用新增版本覆盖排期、坚守先写后跑与边界，就不损害治理纪律，也不伪造结论。但真实 PI 与第二轮复审的张力必须如实固化在下面 §2–§4：提前执行 ≠ 解除投稿阻塞。

---

## 2. 与 v2.7 的关系：新增覆盖排期，不回写

| 项 | 处理 |
|---|---|
| v2.7 §4 `deferred_options.candidate_full_string_scoring = "投稿后"` | **由 v2.8 `schedule_override` 显式覆盖为"本轮执行"** |
| v2.7 原文（2×2 设计、判读四分支、不可变边界） | **保持冻结不变，不回写** |
| `GPU_SEQUENCE_SCORING_PLAN.md` 中"沿用投稿后排期" | 以 v2.8 为准；方案是 plan、非冻结判据，不改动原文 |
| v2.1–v2.6 / `protocol.yaml` | 不动；v2.8 为纯新增版本 |
| 覆盖范围 | **仅**候选全文评分的执行时点；不改变 v2.7 的科学结论、判读分支与贡献边界 |

> 治理要点："判据先写后跑"通过**新增版本**满足——在任何 `audit_seq_*` run 启动前，v2.8 已冻结矩阵、数据版本、评分口径、输入审计、统计与判读分支。不回写旧冻结文件保证既有审计轨迹可追溯。

---

## 3. 与最新复审（2026-11-24）的关系

- **复审定性**：候选全文评分 = 后续稳健性实验；当前论文有编译（第 753 行下划线致命错误、约 103/386 pt 溢出）、匿名稿缺失、指标口径（flip 分母、首 token 代理符号、KD 效用语言）、归因措辞等**定向大修阻塞**；复审建议"保留补实验、完成定向大修后复核、推迟提交当前版本"。
- **本裁决的处置**：
  1. 本实验是**补充稳健性证据**，不替代、不推迟、不解除当前论文的定向大修；大修项仍按复审清单独立关闭，仍是投稿阻塞。
  2. 本实验**不是当前投稿门槛**；即使全部完成，也不构成"可以立即提交"的许可。
  3. 实验结果按 v2.8 三判读分支如实入稿；若与首 token 一致 → 增强"两评分下方向相同"的表述；若对首 token 敏感或长度归一改变判读 → 如实披露，**不升级任何结论**。
  4. 复审关于"只有论文决定恢复更强全文评分或单缺陷因果主张时才需新 GPU 证据"——本裁决**明确不恢复**更强因果主张；全文评分仅服务于稳健性，不是为恢复 `manufactured/directly produced` 措辞。

---

## 4. 重新触发 P5 审稿 / 签 off

> **裁定：本实验完成后重新触发 P5 审稿与签 off。**

- 新增 GPU run（8 个）属新一轮证据产出，须经审稿合规审计（v2.8 §reviewer_checks）后，由 PI 重开 P5 审阅。
- 重新签 off 的**前置**：① v2.8 冻结且 8 run 按门控完成；② 审稿出稳健性合规 note；③ 第二轮复审的定向大修项全部关闭并有复核；④ 论文按三判读分支如实更新、编译与匿名稿达标。
- 贡献状态不因重新签 off 改变：贡献(1)(2) 撤回、贡献(3) withheld；P2/P3/P4 永久放弃；主终点未评估。
- 若本实验结果显示首 token 敏感（失败或翻转结论依赖评分口径），论文须相应收窄主张，PI 视情况决定是否需再一轮复审。

---

## 5. 预算与门控（沿用方案，冻结于 v2.8）

- **冒烟门**：seed0 的 A11/A00 固定小样本先过技术门（首 token 历史回放复现、单/多 token 整串一致性、A/B 顺序不变、Self/Identity 锚点、逐次输入审计全通过）。未过不跑任何正式格。
- **全量格**：冒烟通过后，seed0/1/2 的 A00/A11 各 60 对，共 6 格；单卡串行（并发 3–7× 惩罚）。
- **预算**：冒烟 + seed0 两全量格预留 30 分钟上机窗口；六格先按 **0.5–1 GPU 小时**占卡预算；以 seed0 实测每格耗时 / 每候选 token 数 / 显存峰值更新剩余预算。若只排到一格，先跑 `audit_seq_A11_s0`。
- **A01/A10**：可选、本轮不做；仅在论文要讨论 2×2 交互对整串评分是否稳健时等量补跑。
- **中止规则**：任何无法解释的差异（checkpoint / token 边界 / 精度 / 缓存位置）先暂停排查，不静默通过；审计失败即中止该格并保留信息。

---

## 6. 各角色任务清单

### 6.1 data-engineer（CPU 样本 / 哈希 / 分母审计）
- **可写**：`data/tasks/**` 的审计记录、`reports/data/**` 新审计文件（不覆盖旧文件）。
- **交付**：old(458de18)/repaired(efc3ba3) 的 train/val × seed0/1/2 导出与规范 LF SHA-256；全量 60 对与主分析分母核对（旧 42/42/41、修复 46/46/46，每格 6 族）；单列 F5/F6/相同候选；flip 分母（排除 F5+F6）、总库/验证格/Self 阈值后分母分清。
- **禁止**：不改合成 `cf_pairs.jsonl`、不评封存 test、不覆盖旧样本哈希绑定勘误。

### 6.2 engineer（实现评分入口 / 冒烟门 / 串行 8 run）
- **可写**：`src/readkv/**`（新增独立 teacher-forcing 评分入口，不复用贪解码 `inject_and_generate`）、`experiments/**`（新审计入口）、`reports/runs/audit_seq_*/**`（8 个新 run 产物）。
- **交付**：first/full/length-normalized 三读数；FP32 log-softmax、固定 token 边界、同分规则；逐次前向审计 `[Q,1×(m−1)]`、候选缓存独立、位置偏移、zero re-prefill；每 run 五类产物（config/scores/forward_audit/metrics/manifest）。
- **禁止**：不覆盖旧 2×2 归档、不读封存 test、不改冻结的 affine/ridge/τ/self_threshold 口径、不挑 seed。

### 6.3 scientist（统计口径与分析）
- **可写**：`docs/audit_seq_statistical_interpretation.md`（新增分析文档）、复核记录。
- **交付**：锁定 L、`L_full−L_first`、A11−A00 三比较；template_family 主 CI + pair-level 敏感性、10,000 resamples、<24 族 exploratory、样本加权口径；按 v2.8 三分支对号入座。
- **禁止**：不做事后择支、不作单项数据缺陷因果归因、不放宽强度边界、不恢复贡献。

### 6.4 reviewer（合规审计）
- **可写**：`reports/review/**`（新增稳健性审计 + compliance note）。
- **交付**：审计输入独立性/位置偏移/zero re-prefill/实际输入长度序列与证据抽检范围；核对三读数同样本、对角格首 token 锚点、统计口径、判读纪律；出合规 note，确认触发 P5 重审。
- **禁止**：不改代码/数据/判据/产物；不代替 PI 签 off。

### 6.5 writer（结果入稿 / 措辞）
- **可写**：`papers/readkv_v2_draft/**`（长稿；匿名稿由真实 PI 侧生成）、cover letter 草稿。
- **交付**：首 token/整串对照表与归一敏感性表纳入附录，保留首 token 主表；按判读分支措辞（一致 → "两评分下方向相同"；敏感 → 如实披露）；同步第二轮复审的定向大修项。
- **禁止**：不恢复贡献、不写方法增益或单项因果强措辞、不越过封面信上限（`p5_cover_letter_cap.md`）、不伪造数据。

### 6.6 doc-engineer（复现文档）
- **可写**：`README.md`、`docs/reproducibility.md`（同步状态）。
- **交付**：把 v2.8 排期覆盖与三读数口径写入复现文档，标明冻结版本、run 清单、数据哈希；说明本实验不重算主终点、不碰封存 test、不恢复贡献。
- **禁止**：不改论文正文、不改冻结判据、不改运行产物。

---

## 7. 结论

> **提前执行获批（按真实 PI 指令）**：新增 `configs/prereg/full_candidate_scoring_v2.8.yaml`（protocol-v2.8）显式覆盖 v2.7 的 deferred 排期，v2.7 与旧冻结文件不回写。本实验为**测量稳健性补充**，不恢复贡献、不重算主终点、不碰封存 test、不是方法贡献；不解除第二轮复审的定向大修投稿阻塞；完成后重新触发 P5 审稿 / 签 off。预算 0.5–1 GPU 小时、冒烟门 + 串行 8 run、A01/A10 本轮不做。

**签署：PI / 课题组长（完整候选评分提前执行裁决 · 2026-11-24）**

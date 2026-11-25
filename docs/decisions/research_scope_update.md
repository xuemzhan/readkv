# 课题范围正式更新裁决：从"反事实功能保真方法论文"转为"失败边界 + 数据泄漏教训的负面/实证 + 数据审计研究"

> 裁决人：PI / 课题组长。日期：2026-11-23。
> 性质：**课题范围更新（research scope update）终局裁决**。承接并固化 `reports/review/research_advisor/third_round_online_addendum.md` 的最新审查结论、`reports/review/meta_review/current_task_meta_review.md` 的重新审查结论、`docs/decisions/final_boundary_study_signoff.md` 的情形 C 收口，以及 `docs/decisions/human_decisions.md` 决策 8（永久放弃 P2/P3/P4）。
> 依据（冻结产物，数字仅转抄、不重算）：`docs/protocol.md` §1/§8/§9/§10；`docs/decisions/{clean_data_reversal_ruling,final_boundary_study_signoff,ai_dataset_final_ruling,anchor_confirmation,human_decisions}.md`；`configs/prereg/{external_validity_v2.4,annotation_convention_v2.5,ai_generated_data_v2.6,stats_convention_v2.3}.yaml`；`reports/review/research_advisor/third_round_online_addendum.md` §1–§4；`reports/runs/p1_clean_mvp_seed{0,1,2}` / `p1_kd_clean_mvp_seed{0,1,2}` / `e0_clean_mvp_seed0/metrics.json`。
> 本裁决**只写决策文档**：不改 `src/**`、不改 `reports/runs/**`、不改论文源文件、不改数据；不写代码、不跑实验、不润色文本；所有数值与文献仅转抄冻结产物/一手来源，不伪造。

---

## 0. 更新摘要（一句话）

> **原 V2.0 主线"跨模型 KV 迁移的反事实功能保真方法论文（H1/H2/H3 → 贡献(1)(2)(3)）"正式、永久地更新为"跨模型 KV 迁移失败边界 + 数据泄漏如何制造虚假科学发现的负面/实证 + 数据审计研究"。** 贡献(1) 撤回、贡献(2) 撤回（withheld）、贡献(3) withheld 全部维持；P2/P3/P4 不重启；封存 test 不碰；v2.4/v2.5/v2.6 冻结继续有效；G1 仅为可选低优先级确认，不纳入核心必做。

---

## 1. 正式课题更新

### 1.1 更新前后对照

| 维度 | 原课题（V2.0 方法论文） | 更新后课题（本裁决） |
|---|---|---|
| 核心叙事 | 发现"utility-preserving 反事实失真 gap"+ V 消费机制定位 + 机制约束 Mapper 修复 | 数据泄漏/退化对/模板重合制造假阳性 → 修复后方向性翻转 → affine 迁移失败边界；数据质量审计对基准结论的决定性影响 |
| 研究问题 | RQ1–RQ3 / H1–H4（正向可证伪假设） | RQ1'–RQ4'（负面/实证描述性问题，见 §2） |
| 贡献结构 | 评价层(1)+机制层(2)+方法层(3) | 贡献(1)(2) 撤回、贡献(3) withheld，**不设任何正向贡献**；论文定位为负面/实证/数据审计研究 |
| 主线实验 | P2 机制、P3 方法、P4 泛化、封存 test 主终点 | 全部取消；核心为 S1–S5 收尾 + SQuAD 锚点 + v2.6 数据工作包 + 文档同步 + 论文重写 |

### 1.2 更新理由（科学 + 治理双重，均来自冻结结论）

1. **科学**：干净数据上 affine 三 seed `transfer_broken=true`（E_CF 6.900/8.159/8.540、dual 0.417/0.283/0.383，`p1_clean_mvp_seed{0,1,2}`）确证迁移失败；旧正向信号源于数据缺陷（`data_readiness_audit.md` §2）；紧急复核判翻转可信（高、非实现 bug）。
2. **文献**：`third_round_online_addendum.md` §1 核验的 2026-10/11 工作已 anticipate 原三贡献空间——N1（2611.14051，utility≠fidelity）、N2（2610.22016，substitute-cache 负面结果）、N7（2608.04893，causal audit 方法论）覆盖评价层；N3（2610.15721）覆盖机制层 Value 侧；N4（2610.42116）、N5（2610.15095）、N6（2610.11358）、N8（2610.16165）提供很可能消除 gap 的强 baseline。原 H1/H2/H3 即使重启也无高新颖性正向路径。
3. **治理**：v2.4 明文永久放弃 P2/P3/P4；`human_decisions.md` 决策 8 确认放弃、以边界研究收口；v2.6 再次声明不是 P3 重启。

### 1.3 不可变边界（本更新**不**改变以下任一事项）

| 事项 | 状态 | 说明 |
|---|---|---|
| 贡献(1) 评价层 | **撤回（withdrawn）** | 针对原 affine/旧数据 "reproducible utility-preserving gap" 主张已证伪；kd 干净 gap 仅作探索性观察记录，不恢复为 §10 正式 claim。 |
| 贡献(2) 机制层 | **撤回（withdrawn / withheld）** | 机制对象（干净失真）不存在；旧 P2 证据基于污染数据；P2 未重跑。 |
| 贡献(3) 方法层 | **withheld** | 主终点未评估、P3 取消、无新方法证据。 |
| P2 / P3 / P4 | **不重启（永久放弃）** | 依决策 8 + v2.4；不另立"修复 broken transfer"新课题；任何重启须真实 PI 撤销决策 8、修订 v2.4、冻结新版本文件（v2.7+）并重新裁决——本裁决**不**启动该流程。 |
| 封存 test | **不碰** | 不为"救原研究"提前评测；所有证据限 val + 已授权锚点 + 数据探针。主终点（成对 E_CF vs kd_only，CI 上界<0）未评估、且方法层取消后不适用。 |
| 贡献恢复 | **不允许** | 本更新、M4/锚点、v2.6 数据工作包均不得恢复任何已撤回贡献。 |
| v2.4 / v2.5 / v2.6 | **继续有效（冻结不变）** | 本更新不回写、不覆盖、不废弃任一冻结版本；v2.6 维持"not activated"状态（见 §5.3）。 |
| P0/P1 终局 | GO（维持） | E0 干净复验 PASS、affine/kd 三 seed 齐全；定性为失败边界 + kd 情形 C 探索性观察。 |
| v2.1/v2.2/v2.3 | 冻结不变 | δ 基于 pre-fix 数据的事实如实披露；统计口径（template_family 主 CI、8 族 exploratory、flip 排除 F5+F6）不变。 |

---

## 2. 修订后的研究问题 RQ1'–RQ4'

> 以下问题均为**负面/实证描述性问题**，不设正向贡献门槛，不作为方法论文主张；每项标注证据来源与"失败/边界时"的诚实调整。

### RQ1'（方法学教训 · 核心）：数据质量缺陷在多大程度上制造了虚假的"utility-preserving gap"结论？

- **问题**：退化对、跨 split 逐字泄漏（含 train↔test 整对）、实体全共享、模板骨架重合、簇退化为逐对 i.i.d.，是否足以解释此前报告的"反事实 gap"？修复后结论是否发生方向性翻转？
- **证据来源（转抄冻结产物）**：`reports/data/data_readiness_audit.md` §2、`data_fix_report.md`（退化 18→0、泄漏≥15→0、实体重叠→0、flip 398、新 sha `f910f1f1…a894a`）；旧 run（E_CF 1.93–2.12、dual 0.62–0.67、`transfer_broken=false`，已 superseded）↔ clean run（affine E_CF 6.9–8.5、dual 0.28–0.42、`transfer_broken=true`）对照表；`clean_data_reversal_emergency_review.md`（翻转可信·高·非 bug）。
- **边界调整**：若审计轨迹不完整或对照数字无法从冻结产物复现 → 只报告"审计发现的缺陷清单"，不声称"翻转"；不把一般泄漏教训当首创（N7/ Kapoor-Narayanan 已确立），新颖性限定为"具体预注册翻转案例 + 完整审计轨迹"。

### RQ2'（失败边界 · 核心）：在干净数据上，tested affine mapper 的迁移失败边界由哪些条件刻画？

- **问题**：等深 MVP 对等深、合成域、val、8 个 template_family（exploratory）、dual 坍塌、`transfer_broken` 单信号触发——这些条件下 affine 迁移失败的具体形态与统计强度为何？
- **证据来源**：`p1_clean_mvp_seed{0,1,2}`（joint dual 0.417/0.283/0.383 vs Self 0.817/0.900/0.783；joint_dual_drop_vs_self≈0.4）；冻结 verdict=`distortion_exists` 与正交字段 `transfer_broken=true` 的口径分离披露；v2.3 簇级 CI（8 族 exploratory）。
- **边界调整**：如实披露 `joint E_CF` 接近但**未超过**错配/零缓存控制（seed0 joint 6.90 vs mismatch 8.38 / zero 8.58）；`transfer_broken` 由 dual-drop 单信号触发；不作"强显著/跨对泛化/跨模型"主张；N6（2610.11358）已将"affine 坍塌"类失败归为已知模式，本项贡献是受控反事实基准上的量化 + 泄漏归因，而非发现新失败类型。

### RQ3'（强基线探索性观察 · 非贡献）：kd_only 在保持迁移效用的同时是否仍保留探索性非零 E_CF gap，且该 gap 是否与常规 QA 质量解离？

- **问题**：强行为基线 kd_only 的 dual 保持（0.700/0.733/0.767）与稳定非零 E_CF（6.388/6.479/7.211）是否构成"utility 保持上的探索性 gap 观察"？该 gap 是否可由 SQuAD/ARC 锚点显示为"E_CF gap ≠ 常规质量退化"？
- **证据来源**：`p1_kd_clean_mvp_seed{0,1,2}`；`anchor_confirmation.md` 授权的 SQuAD 锚点评测（v2.4 三情形归类）；情形 C 细化见 `final_boundary_study_signoff.md` §1.2。
- **边界调整**：属探索性观察（8 族<24、pair-level CI、单 MVP 等深对、合成域），**不**写成贡献(1) 的恢复或 "reproducible gap"；锚点若复现→仅强化有限外部效度、若相反→收窄适用边界但不反转叙事、若混合→探索性披露（v2.4 预承诺）；N4/N5 强 baseline 很可能消除 gap，不得据此声称方法层增益。

### RQ4'（外部效度边界 · 数据/效度增强）：在 real=0、合成域、单对约束下，合规锚点与数据探针能把结论外推到什么程度？

- **问题**：SQuAD（必要时 ARC 顺位）锚点、v2.6 HellaSwag 种子 AI 数据探针，能在多大程度上支撑"失败边界跨数据源/跨切片存在"的有限外部效度，而不越过 real=0 的硬边界？
- **证据来源**：v2.4 外部效度协议、SQuAD 锚点五项登记（`squad_anchor_manifest.md`、`anchor_license_check.md`）、v2.6 冻结协议（not-activated，见 §5.3）。
- **边界调整**：锚点/探针只能作额外旁证，不是 real、不并入合成 test、不重算主终点、不恢复贡献；real=0 与"单一合成等深对"必须作为 limitation 明确披露；HellaSwag/ARC/SQuAD 许可与引用按 §6 核验后使用。

---

## 3. 研究设计边界

1. **证据层级**：确认性主终点已不适用（P3 取消）；全部结论按"内部探索性强证据 / 单 MVP 等深对 / 合成域 / val 8 族 exploratory"强度披露；封存 test 不碰。
2. **统计口径**：v2.3 主口径（template_family 簇级 paired bootstrap、`min_clusters_for_inference=24`、<24 标 exploratory、flip 排除 F5+F6、必报 pair-level 敏感性）不变；kd 三 seed 的 v2.3 簇级 CI 与 pair-level CI 须统一标注、不得混用（`meta_review` §3.1–3.2）；少簇覆盖存疑须披露。
3. **贡献门槛**：`docs/protocol.md §10` 三模板任一均**不满足**；论文按 §8 "强基线近 Self/失败条件研究 + 效果仅在合成域"分支定位为边界/实证/数据审计研究，不得保留贡献(2)(3) 措辞。
4. **先写后跑 / 不可回改**：任何新评测（锚点、数据探针）须在既有冻结版本（v2.4/v2.5/v2.6）口径下执行；不得按结果回改生成器、prompt、判据或筛选规则；不得挑 seed。
5. **可复现**：所有 run 写全 provenance（新 commit 纳入跑分代码、`git_hash`、`protocol_version`、数据 sha256、seed、dtype、kernel、`zero_re_prefill`、正交 `transfer_broken`）；数字一律转抄冻结产物，禁止 mock/占位进入主张。
6. **诚实披露清单（强制）**：`transfer_broken` 单信号、8 族 exploratory、单对等深、合成域、real=0、E_CF 仍低于无信息控制、info 归因 seed0 为 2 正 1 负、δ 网格三值不优于 kd_only、预算不对等、机器 verdict 与 `transfer_broken` 口径分离。

---

## 4. 任务清单与"完成"定义

> 全部产物写入各自允许路径；任何涉及判据/口径的改动须新增版本文件，不得回写 v2.0–v2.6。

### 4.1 数据任务（数据工程师）

| 任务 | 交付物 | "完成"定义 |
|---|---|---|
| S2 残留：manifest/acceptance_checks 的 v2.3 sha 同步/加注 | `data/tasks/manifest.json`、`reports/data/acceptance_checks.json` 同时记录回填前 `5200940c…` 与回填后 `e44c6acb…`，注明 PI commit `6413ba0` | 下游 `consistency_check` 对 clean run 不再报 sha 假阳性 |
| SQuAD 锚点归档维护（已归档，复核即可） | `reports/data/squad_anchor_manifest.md` 五项登记齐全、文件 sha256 `80a5225e…` 复核一致 | PI 复核哈希一致、用途仅评测不触发 SA |
| v2.6 HellaSwag 种子 AI 数据**工作包**（见 §5.3，not-activated） | 种子五项登记计划、LICENSE 归档与引用、generator/prompt 冻结草案、数据卡模板、README `data/generated/` 条目草案；**不生成数据、不创建 `data/generated/`** | 工作包文档齐备且明确标注"not activated / 待新版本授权"；无生成 run、无伪造记录 |

### 4.2 实验任务（工程师）

| 任务 | 交付物 | "完成"定义 |
|---|---|---|
| SQuAD 锚点评测（必要时 ARC 顺位） | `reports/runs/anchor_squad_{affine,kd}_seed0/`（依 `anchor_confirmation.md` §2 纪律）；ARC 须先五项登记 + PI 确认 | 产物入 `reports/runs/`、provenance 齐全、按 v2.4 三情形归类入报告；不混算主终点、不恢复贡献 |
| S1：数据哈希绑定勘误 | `reports/data_hash_binding_erratum.json`（已绑定 7 clean run 的 sha `f910f1f1…a894a`）复核闭环 | 投递前确认无遗漏 |
| S3：runs_index 最终确认 | `reports/runs_index.json`（26 run）、`reports/consistency_report.json`（29 run）复核 | 7 clean run `ok=true/traceable=true`、旧 run 标 superseded，无残留告警 |
| kd 三 seed 的 v2.3 审计产物 | kd 三 seed 纳入 `reports/bootstrap_summary.json`（template_family 主 CI + pair-level 敏感性 + exploratory） | C 判读口径统一、无 pair-level/cluster 混用（meta_review §3.1） |
| G1（可选，低优先级） | 若执行：仅 val、≥3 seed、ACCT/SwaT/CacheBridge/CacheFuse/kd_only，判据为 utility-preserving + gap 仍存在 | 预期多为 null；不纳入核心、不据此恢复贡献（见 §5.2） |

### 4.3 代码任务（工程师）

- 仅允许实现一致性修正（如 `summarize_cf` 的 `detail.evaluable_threshold` 改为实际阈值、缺键断言）；**不改任何冻结判据、E_CF 定义、τ、δ、统计口径**。
- "完成"定义：相关测试通过（如 pytest 复核），且 `git diff` 显示冻结判据文件无改动。

### 4.4 文档任务（文档工程师 + 写作者）

| 任务 | 交付物 | "完成"定义 |
|---|---|---|
| README 全量同步（投稿阻断项） | README 删除"22 run/P2 已收口/P3 已启动/P5 有条件 GO/贡献(2) 强形式"旧表述；改为 26/29 run、clean 数据、affine 失败边界、kd 情形 C 探索性、P2/P3/P4 取消、P5 暂缓、贡献(1)(2) 撤回、贡献(3) withheld | 与 `final_boundary_study_signoff.md`、`final_signoff.md`、本裁决逐项一致，无相反陈述 |
| S4/S5 措辞修正（写作者，强制） | 全文："E_CF 大幅升高、接近但未超过错配/零控制，伴 dual 坍塌"；明确 `transfer_broken` 单信号、8 族 exploratory、单 MVP 等深对、合成域、test 未评测 | 禁用词表零命中（见 §8 writer 指令） |
| 论文按新课题重写 + 引用更新 | `papers/readkv_v2_draft/main.tex`（经写作者，不改本裁决产物）；叙事改为失败边界 + 数据泄漏教训 + 数据审计；引用 §6 文献 | 贡献状态、强度边界、披露清单齐全；`[PLACEHOLDER]` 清零；按 §10 门槛定位为负面/实证/数据审计研究 |
| 顾问报告状态管理 | `current_task_review.md` 标注二轮结论已被 `final_boundary_study_signoff.md` 与本裁决超越；或出第三轮单页 | 后续读者不再把"kd 待决/S1–S3 未闭环"当当前事实 |

---

## 5. G1 定位与核心必做边界

### 5.1 核心必做（全部完成方可重开 P5 / 投递就绪）

1. S1–S5 收尾（溯源 + 披露 + kd 审计口径统一）；
2. SQuAD 锚点评测（必要时 ARC 顺位）；
3. v2.6 HellaSwag 种子 AI 数据工作包（not-activated，见 §5.3）；
4. README/文档全量同步；
5. 论文按新课题重写并引用最新文献（§6）。

> 全部完成的判据 = §4 各项"完成"定义满足 + 审稿出具 S1–S5 闭环合规意见 + venue 由真实 PI 指定（`human_decisions.md` 决策 5/10）。venue 未定前只到"投递就绪、不最终签 off"。

### 5.2 G1（可选 · 低优先级 · 不纳入核心必做）

- **定位**：依 `third_round_online_addendum.md` §3.2 轨道 C，G1 从"最高信息量最小实验"降为"可选的最终确认"。文献先验（N2/N4/N5）表明强 baseline 很可能消除 gap；G1 更像一次低成本"是否还有残余现象"的负面确认，不是救援机会。
- **若执行的硬约束**：仅 val、≥3 seed、至少含 ACCT/SwaT/CacheBridge/CacheFuse/kd_only；判据为 utility-preserving + gap 仍存在；不碰封存 test；结果多为 null，**不得据此恢复贡献或重开 P3**。
- **执行前提**：须独立排期、经 PI 确认算力后再启动；不阻塞 §5.1 核心必做。

### 5.3 v2.6 HellaSwag 种子 AI 数据工作包的定性（与冻结裁决一致）

> **重要澄清，防止与冻结裁决冲突**：`ai_dataset_final_ruling.md` 已撤回"有条件 GO"、判定 v2.6 "无适用对象 / not activated"，并明确不新增 v2.7、不创建 `data/generated/`、不启动生成。本裁决**维持该冻结裁决不变**。

- 本更新中的"v2.6 工作包"指**文档/协议准备工作包**：整理并归档 §4.1 所列种子五项登记计划、LICENSE 与引用、generator/prompt 冻结草案、数据卡模板、README 条目草案，作为可复现资产留档，**全程标注 not-activated**。
- **不启动**任何 HellaSwag 数据下载/生成；**不创建** `data/generated/`；**不产生**任何生成 run 或质量审计结果；**不得**称其为 real/人类标注。
- 若真实 PI 日后要以新证据/新资源重启生成，须**先撤销** `ai_dataset_final_ruling.md`、**新增**覆盖 v2.6 not-activated 状态的新版本 prereg（v2.7+）并经 PI 重新裁决；本裁决不启动该流程、不构成生成授权。

---

## 6. 引用更新要求（写作者；本裁决只列清单、不杜撰内容）

- **必须新增引用并正面区分**（来自 `third_round_online_addendum.md` §1，均经标题/作者/摘要/日期级核验；章节级细节须投递前全文核验，按协议 §9）：
  - arXiv 2611.14051 — Can KV Cache Be Reused Across Model Updates?（DeepSeek-V4-Flash；Functional Cache Divergence；utility≠fidelity）
  - arXiv 2610.22016 — Close Enough is Nowhere Near: Fidelity-Consumability Decoupling in KV Caches
  - arXiv 2610.15721 — To Cache or Not to Cache: Safety Incompatibility in Cross-Model KV Cache Reuse（VReparo）
  - arXiv 2610.42116 — ACCT: Asymmetric Cross-LLM Context Transfer
  - arXiv 2610.15095 — Swarm Telepathy: Prefill-Free KV-Cache Transfer Across Families
  - arXiv 2610.11358 — RaReCache: Rank disagreement-based Selective Recomputation
  - arXiv 2608.04893 — When Does Latent Communication Pay? A Causal Audit（预注册 TOST）
  - 及 N8 CacheFuse（2610.16165）、N9 BridgeKV 等（如实际使用再引）。
- **保留既有引用**：CacheLink、KV-Lingo、Heo et al.（2608.03893）、"Does Accuracy Equal Evidence?"（2608.01631）、Contrast Sets、Kaushik et al.、Kapoor & Narayanan（泄漏教训）、SQuAD/ARC/HellaSwag 官方引用；KV-Lingo/CacheLink 的 `[PLACEHOLDER]` 按 §9 核实正式版本/日期/口径后清零。
- **引用纪律**：只引用确实使用且可核验的文献；新颖性限定为"具体预注册翻转案例 + 成对反事实 E_CF 框架 + 完整审计轨迹"，不得声称一般泄漏教训或评价框架首创。

---

## 7. 协议版本处理：不新增 prereg 版本文件

> **裁定：本更新不新增 `configs/prereg/boundary_study_v2.7.yaml`（或任何 v2.7 文件）；说明理由如下。**

1. **无判据变更**：本更新只改变研究方向/问题表述/任务范围，未改 `E_CF` 定义、τ、Self 阈值、Huber δ、主终点、统计口径、flip 分母或任何 v2.1–v2.6 冻结项；不满足"改动冻结判据须新增版本"的触发条件。
2. **不得追溯预注册**：边界研究的证据（affine/kd 三 seed、clean 复验）已产出；在数据已入账后新写 "boundary_study prereg" 属追溯性预注册，违反先写后跑、损害诚信。研究问题 RQ1'–RQ4' 是对既有负面/实证研究的描述性重述，不是带阈值的新判定规则。
3. **后续实验已被现有版本覆盖**：SQuAD/ARC 锚点由 v2.4 覆盖；v2.5 覆盖 agent 交叉校验；v2.6 覆盖（not-activated）数据工作包；无需新版本授权。
4. **与冻结裁决一致**：`ai_dataset_final_ruling.md` 已明确"不新增 v2.7"；本裁决不推翻该决定。
5. **仅当触发时才新增**：若日后真实 PI 决定撤销决策 8 / 重启原研究 / 激活 v2.6 生成 / 引入改变判据的新口径（如 G1 正式判据、wild cluster bootstrap-t 纳入推断），须在那时按"只新增版本文件、不回写 v2.0–v2.6"流程冻结 v2.7+ 并重新裁决——本裁决不预先创建空版本。

> 结论：本更新的唯一落盘产物为 `docs/decisions/research_scope_update.md`；`configs/prereg/` 目录本轮不改动、不新增。

---

## 8. 给各角色的具体指令

### 8.1 科学家（scientist）
- **可写**：`docs/algorithm_spec.md`、`docs/experiment_design_E0_E7.md`、`docs/data_readiness_scientist.md`（仅同步到新课题表述）。
- **禁止**：不得设计新正向贡献/机制/方法实验；不得改冻结判据或重开 P2/P3/P4；不得把 G1 包装为救援。
- **交付**：将 RQ1'–RQ4' 写入研究设计文档；给出锚点/数据探针的有限外部效度解读口径（v2.4 三情形）；必要时评估 G1 作为可选确认的设计（不启动）。

### 8.2 数据工程师（data-engineer）
- **可写**：`data/tasks/manifest.json`、`reports/data/acceptance_checks.json`、`reports/data/**`（S2 sha 同步、锚点登记复核、v2.6 工作包文档）。
- **禁止**：不得改 `src/**`、不启动 HellaSwag 生成、不创建 `data/generated/`、不伪造种子哈希/生成记录/质量审计、不把探针称 real。
- **交付**：S2 残留闭环；SQuAD 五项登记复核；v2.6 工作包（not-activated，§5.3）。

### 8.3 工程师（engineer）
- **可写**：`reports/runs/**`（新锚点 run）、`reports/bootstrap_summary.json`、`reports/runs_index.json`、`reports/consistency_report.json`、`reports/data_hash_binding_erratum.json`、`src/readkv/**`（仅实现一致性修正）。
- **禁止**：不改冻结判据、不碰封存 test、不重算/改已冻结 CI 与 flip 分母、不挑 seed、不写 mock。
- **交付**：S1/S3 复核、kd 三 seed v2.3 审计产物、SQuAD（必要时 ARC）锚点评测、可选 G1（经 PI 排期后）。

### 8.4 审稿人（reviewer）
- **可写**：`reports/review/**`（新增合规/对抗复核报告）。
- **禁止**：不改代码/数据/判据/运行产物/论文；不代 PI 择支。
- **交付**：S1–S5 闭环后出具最终合规意见；必跑 `bootstrap_ci_report` + 扩展 `consistency_check`；核对 v2.3 口径一致、锚点不混算、贡献措辞未升格、v2.6 not-activated 无遗留产物；确认重开 P5 条件。

### 8.5 文档工程师（doc-engineer）
- **可写**：`README.md`、`docs/**` 中非冻结说明文档（同步状态用）。
- **禁止**：不改 `docs/protocol.md` 判据正文、不改 `configs/prereg/**`、不改论文源文件、不改运行产物。
- **交付**：README 全量同步（§4.4）；顾问报告状态标注；`data_card` 等轻微过期表述同步；与最终裁决逐项一致。

### 8.6 写作者（writer）
- **可写**：`papers/readkv_v2_draft/main.tex`、`notes.md`（经 §10 门槛约束）。
- **禁止**：不改冻结结果/产物；不使用贡献(2)(3) 措辞；不写 "reproducible gap / localized mechanism / reduces gap / E_CF 与控制相当 / across models / strong significance"；不伪造文献。
- **交付**：按新课题重写 + S4/S5 强制修正 + §6 引用更新 + 披露清单齐全；按 §10 定位为负面/实证/数据审计研究。

### 8.7 代码审查（code-reviewer）
- **可写**：`reports/review/**`（代码审计意见）。
- **禁止**：不改 `src/**`、不跑实验。
- **交付**：审计实现一致性修正未触碰冻结判据（git diff 核对）；核对 zero re-prefill、Oracle 隔离、provenance 字段、E_CF/统计口径未被改动。

### 8.8 论文审稿（paper-reviewer-a / paper-reviewer-b）
- **可写**：`reports/review/paper_review/**`（叙事与可信度审查意见）。
- **禁止**：不改论文源文件、不改数据/判据/产物。
- **交付**：A 审主张—证据一致性与负面结果披露；B 审可复现性、统计口径、图表—结论一致性；重点查贡献(2)(3) 是否被误升格、S4/S5 是否达标、新颖性是否限定到翻转案例 + E_CF 框架；venue 未定前不最终签 off。

---

## 9. 收口条件与签署

- **本更新生效后**：课题以"失败边界 + 数据泄漏教训的负面/实证 + 数据审计研究"为唯一主线；原方法论文路线永久收口。
- **P5 / 投递**：仍暂缓，直到 §5.1 五项核心必做完成 + 审稿合规意见 + 真实 PI 指定 venue；venue 未定前只到"投递就绪"。
- **不变量复核**：贡献(1)(2) 撤回、贡献(3) withheld；P2/P3/P4 不重启；封存 test 不碰；不恢复贡献；v2.4/v2.5/v2.6 继续有效；不新增 prereg 版本；不伪造数据/文献。
- **分歧裁决**：本裁决为 PI 终裁；角色间若有异议，以本裁决与 `final_boundary_study_signoff.md`、`ai_dataset_final_ruling.md`、`human_decisions.md` 为准；涉及真实 PI 授权事项（venue、真实文档采集、撤销决策 8、重启原研究/v2.6 生成）上报真实 PI，不得私自推进。

**签署：PI / 课题组长（课题范围更新终局裁决 · 2026-11-23）**

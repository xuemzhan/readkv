# 实验设计表（V3.0 · 失败边界 / 数据泄漏教训的负面结果实证研究）

> 状态：**设计产出（承接 PI 最终收口裁决）**。本表把原 V2.0「E0–E7 方法论文实验矩阵」重写为**失败的边界确认 + 数据审计 + 外部效度增强**的核心必做清单。所有数值为已冻结产物的记录值（出处随文标注），本文**不重算统计、不改冻结判据、不碰封存 test**。
> 依据：`reports/review/meta_review/current_task_meta_review.md`、`reports/review/research_advisor/third_round_online_addendum.md`、`docs/decisions/{final_boundary_study_signoff,clean_data_reversal_ruling,anchor_confirmation,ai_dataset_final_ruling}.md`、`configs/prereg/{stats_convention_v2.3,external_validity_v2.4,annotation_convention_v2.5,ai_generated_data_v2.6}.yaml`、`docs/protocol.md §7/§8`。
> 边界：只写设计；不改 `configs/prereg/**`、不改代码、不改运行产物、不改论文、不改主终点定义。

---

## 0. 共用口径与阶段状态

### 0.1 主终点与联合报告（冻结，仅引用）
```

g(C,q)   = log P(A|C,q) − log P(B|C,q)
D_self   = g(C_S(d_A),q) − g(C_S(d_B),q)
D_trans  = g(Ĉ_S(d_A),q) − g(Ĉ_S(d_B),q)
E_CF     = |D_trans − D_self|
normalized_E_CF = |D_trans − D_self| / (|D_self| + τ),  τ=1.0（冻结，仅引用）
```
- **封存 test 不评**：当前证据全部 `eval_splits=["val"]`；无"新方法 vs kd_only 成对 E_CF、CI 上界<0"的方法主终点检验。原 P3 主终点**未评估**。
- `E_CF` 永远与 `dual_correct` / `flip_consistency` / `coverage` / `info_attribution` 同报；F5 不入翻转分母、F6 条件控制；flip 分母按 v2.3 = 398（冻结值）。
- 统计按 **v2.3**：`template_family` 主聚类 + pair-level 敏感性 + min 24 簇 / exploratory；当前 8 族 → `exploratory=true`。簇数不足不作强推断。

### 0.2 阶段最终状态（引用，不改动）

| 阶段 | 状态 | 本表中位置 |
|---|---|---|
| P0 / E0 | GO（终局，已完成） | E0（已完成） |
| P1 基准 | GO（终局，已完成） | P1-affine / P1-kd（已完成） |
| **P2 机制** | **永久放弃（不重启）** | 标注为放弃，不列实验卡 |
| **P3 方法** | **永久放弃（不重启）** | 标注为放弃，不列实验卡 |
| **P4 泛化/成本** | **永久放弃（不重启）** | 标注为放弃，不列实验卡 |
| P5 投递 | 暂缓（8 项门槛未全闭环） | S1–S5 收尾 |
| G1 强基线确认 | **可选、低优先级，不纳入必做** | G1（可选卡，预期 null） |

### 0.3 判据/口径冻结项（引用）

| 项 | 状态 |
|---|---|
| 主终点、τ=1.0、self_threshold=0.1、统计设计 | ✅ 已冻结（`configs/protocol.yaml`） |
| v2.3 统计口径（含 flip 分母 398） | ✅ 已冻结（`stats_convention_v2.3.yaml`，仅引用） |
| v2.4 锚点/真实文档外部效度 + 预承诺三情形 | ✅ 已冻结（`external_validity_v2.4.yaml`，仅引用） |
| v2.5 自动化 agent 交叉校验（非人类标注） | ✅ 已冻结（`annotation_convention_v2.5.yaml`，仅引用） |
| v2.6 AI 生成数据提案 | **已评估并撤回**：not-activated、无产物、仅历史记录（不属任何数据工作包）；外部效度仅 SQuAD（必要时 ARC）锚点，`real=0` 维持（`ai_dataset_final_ruling.md`） |

---

## 1. 总表（核心必做 / 可选 / 放弃）

| 类别 | 编号 | 问题 / 内容 | 数据 / 臂 | 主指标 | 状态 |
|---|---|---|---|---|---|
| 必做（已完成） | **E0** | 实现门 / 测量误差上限 | 探针 40 对；Full-Prefill/Identity/round-trip/kernel | cosine、first-token KL、EM 一致率 | 已完成·PASS |
| 必做（已完成） | **P1-affine** | affine 是否迁移失败 | 干净 val；affine Joint + 控制组 | `E_CF` + dual + `transfer_broken` | 已完成·失败边界 |
| 必做（已完成） | **P1-kd** | kd_only 是否保 utility 但留 gap | 干净 val；kd_only Joint + 控制组 | `E_CF` + dual + 情形 C | 已完成·探索性 gap |
| 必做（收尾） | **S1–S5** | 溯源/口径/措辞/披露闭环 | 勘误 + 文档 | 数据哈希、CI 口径、措辞、强度边界 | 待收尾（投递前必须） |
| 必做（审计证据） | **AUDIT** | 数据缺陷如何制造假发现 | 旧（superseded）↔ 干净数据对照 | 退化对/跨 split 泄漏/实体重叠/方向翻转 | 证据已在冻结审计产物，写表 |
| 必做（外部效度） | **ANCHOR** | 失败边界是否跨数据源成立 | SQuAD dev（seed0，affine/kd）；必要时 ARC | 标准 QA EM/Accuracy + 三情形 | 已授权，待产出 |
| **可选（低优先）** | **G1** | 强 baseline 是否消除残余现象 | val、≥3 seed；ACCT/SwaT/CacheBridge/CacheFuse/kd_only | utility-preserving + gap 是否仍存 | 不纳入必做；预期多为 null |
| **永久放弃** | ~~E2/P2~~ | 机制定位 / Oracle 移植 | — | — | 不启动 |
| **永久放弃** | ~~E3/P3~~ | CF-RCT 方法增益 / 消融 | — | — | 不启动；封存 test 不评 |
| **永久放弃** | ~~E4/E5/E6/P4 / E7~~ | 泛化 / 跨结构 / 成本 / 候补分支 | — | — | 不启动 |

---

## 2. 逐项设计卡（核心必做）

### E0 — 实现门 / 测量误差上限（已完成 · PASS）
- **问题**：实现与测量误差是否显著小于待研究效应。
- **产物**：干净数据 E0 复验 PASS（cosine 1.0、KL 0、EM 0.975、round-trip、zero-re-prefill、2.2e-16≪效应/3；出处 `final_boundary_study_signoff §4`）。本文不重算。
- **作用**：排除"迁移失败是跑分实现 bug"的解释（跑分代码逐字未变、Self/Identity 锚点更健康）。

### P1-affine — affine 迁移失败边界（已完成）
- **问题**（RQ1）：tested affine mapper 在干净数据、单一等深 MVP 对上是否迁移失败。
- **数据/臂**：干净 val；affine Joint + 七类控制组；`d_A`/`d_B` 分别打分。
- **主指标**：`E_CF`（记录值 6.900 / 8.159 / 8.540，seed0/1/2，出处 `clean_data_reversal_ruling §0`）+ `dual_correct`（0.417/0.283/0.383，Self≈0.82）+ `transfer_broken=true`（三 seed 一致）。
- **定性**：`E_CF` 大幅升高、**接近但未超过**错配/零控制（seed0 mismatch 8.38 / zero 8.58），伴随 dual 坍塌≈0.4 → **失败边界**，不是 utility-preserving 失真。机器 verdict=`distortion_exists` 与 `transfer_broken=true` 并存须披露。
- **证据强度**：v2.3 exploratory（8 族<24）、单 MVP 等深对、合成域。

### P1-kd — kd_only 情形 C（已完成）
- **问题**（RQ3）：强行为基线 kd_only 是否保持 utility 却仍有 gap。
- **主指标**（记录值，出处 `final_boundary_study_signoff §1.1`）：`E_CF` 6.388/6.479/7.211；joint dual 0.700/0.733/0.767（Self 0.817/0.900/0.783）；dual_drop 0.117/0.167/0.017；flip 0.942/0.906/0.925；`transfer_broken=false`。
- **定性**：**情形 C**——kd 不 broken 但仍有稳定非零 gap。仅作**探索性观察**，不恢复贡献(1)。
- **口径注意**：`final_boundary_study_signoff §1.1` 表为 pair-level CI；meta_review §3.1/§3.2 指出应统一为 v2.3 `template_family` 主 CI（或明确标注 pair-level 为敏感性）。**此口径问题由 PI/审稿人出说明或勘误，本表不重算、不改表**。

### AUDIT — 数据审计前后对照（方法学核心证据）
- **问题**（RQ2）：数据缺陷如何制造虚假正向发现。
- **内容**：以冻结审计产物（`reports/data/{data_readiness_audit,data_fix_report,acceptance_checks.json}`）制作前后对照表：退化对 18→0、跨 split 泄漏≥15→0、实体重叠全共享→0、模板重合修复、flip 分母口径澄清（394/376→398）、结论方向"gap 存在"→"迁移失败"。
- **输出**：方法学教训——**数据质量审计对 KV 迁移基准结论具有决定性影响**。不重算，只引用冻结产物。

### S1–S5 — 审稿收尾（投递前必须，引用 `final_boundary_study_signoff §2/§5`）
- **S1**：clean run 数据哈希绑定勘误（sha `f910f1f1…a894a`），不改冻结 `scores.jsonl`。
- **S2**：manifest 的 v2.3 sha 同步/加注（回填前 `5200940c…` → 回填后 `e44c6acb…`，PI commit `6413ba0`，flip 分母 398）。
- **S3**：`runs_index` 26 run 最终确认（旧 19 标 superseded、新 7 权威）。
- **S4**：措辞精度——"E_CF 大幅升高、接近但未超过错配/零控制，伴 dual 坍塌"；禁写"达到无信息水平"。
- **S5**：强度边界披露——`transfer_broken` 单信号、exploratory（8 族<24）、单 MVP 等深对、合成域、test 未评。
- 另：kd 三 seed PENDING 清零、贡献表逐条核对、引用按协议 §9 核验。

### ANCHOR — 外部锚点（SQuAD 主 / 必要时 ARC 辅；已授权，待产出）
- **问题**：失败边界是否跨数据源成立；为 E_CF 提供外部锚点。
- **范围**：外部效度**仅保留 SQuAD（主锚点，事实/抽取式、最接近文档事实编辑语义），必要时 ARC（辅锚点，选择题）**；不纳入 HellaSwag 或其他锚点（`anchor_confirmation.md §4`、`external_validity_v2.4.yaml`）。
- **run**：`anchor_squad_affine_seed0` / `anchor_squad_kd_seed0`（seed0、仅评测、bf16/sdpa、`zero_re_prefill=true`、新 commit、config 含 git_hash + 数据 sha `80a5225e…`、串行）。出处 `anchor_confirmation.md §2`。
- **统计/判据**：按 **v2.4**；预承诺三情形 `reinforce_external_validity` / `narrow_scope` / `exploratory_disclosure`；锚点**不进合成 test 主终点 CI、不重算冻结主终点、不恢复任何贡献**。
- **定位**：仅增强外部效度（有限，人写维基事实文本）；`real=0` 硬边界维持不变。

---

## 3. 可选确认卡（低优先级，不纳入必做）

### G1 — 强基线确认（预期多为 null）
- **问题**：更强 baseline 是否消除残余 gap（判断原 H1 是否还活着的最便宜确认）。
- **若做**（出处 `third_round_online_addendum §3.2 轨道 C`）：仅 val、≥3 seed；纳入 ACCT / Swarm Telepathy / CacheBridge / CacheFuse / kd_only；判据为 utility-preserving 且 gap 仍存在。
- **预期**：文献先验（N2/N4/N5/N6/N8）表明多为 null 或仅剩不可部署差距；**不得据此恢复贡献、不得当作救援**。不纳入必做，资源优先给负面/边界论文与数据审计资产。

---

## 4. 永久放弃项（明确记录，避免复活）

| 原编号 | 原目标 | 放弃理由（引用） |
|---|---|---|
| E2 / P2 | K/V 机制定位、Oracle 修复、对称 Key 四目标 | 前提（干净失真）已塌、旧证据污染；`clean_data_reversal_ruling §1.2`、`final_boundary_study_signoff §4` |
| E3 / P3 | CF-RCT 方法增益、消融、**封存 test 主终点** | 方法层无目标、三 δ 负值、翻转后无意义；贡献(3) withheld；封存 test 不评 |
| E4 / E5 / E6 / P4、E7 | 泛化、跨结构、成本、候补分支 | 上游取消、无跨模型/真实文档证据；`final_boundary_study_signoff §4` |
| v2.6 AI 数据提案（历史记录，非任务） | HellaSwag 种子 AI 生成作为数据工作包 | 有条件 GO 被**最终撤回**、not-activated、**无产物、仅作历史记录**；不属必做/可选数据工作包；`ai_dataset_final_ruling.md`。外部效度仅 SQuAD（必要时 ARC）锚点，`real=0` 维持 |

> v2.6 AI 数据提案已评估并撤回：语义不适配（HellaSwag 是续写合理性而非可编辑事实命题，F1/F2/F3 不可作真人派生源）、同源 generator/evaluator 循环论证、与"锚点仅评测不发布"口径冲突（`docs/data/hellaswag_seed_semantic_assessment.md`、`ai_dataset_final_ruling.md §1`）。**不启动生成、无产物、仅历史记录**，不作为探针或数据工作包。
>
> 重启条件（仅记录在案，当前无计划）：P2 仅当重构出干净 utility-preserving 失真数据并经 PI 新裁决；P3 仅当把问题重定义为"修复 broken transfer"并提供新资源/新判据；否则永久取消。v2.4 已声明 P2/P3/P4 永久放弃，不另立新课题。

---

## 5. 跨实验合规清单

1. 证据只来自真实 GPU 后端的 `reports/runs/<run_id>/scores.jsonl`；mock 单独标注。
2. **封存 test 不评**；禁止改 τ / 聚类单元 / flip 分母 / δ / 删对照 / 按结果挑种子（各 `forbidden_after_freeze`）。
3. `E_CF` 永远与 `dual_correct`/`flip_consistency`/`coverage`/`info_attribution` 同报；机器 verdict 与 `transfer_broken` 分离披露。
4. 统计一律 v2.3（template_family 主 CI + pair-level 敏感性 + min24/exploratory）；锚点/real 按 v2.4；real 校验按 v2.5（非人类标注）；v2.6 AI 数据提案已撤回、无产物、仅历史记录——外部效度仅 SQuAD（必要时 ARC）锚点，`real=0` 维持。
5. 每次 run `zero_re_prefill=true`；Oracle 不进推理图；K-only/V-only 标 `deployable=false`。
6. kd 三 seed 的 v2.3 簇级口径统一由 PI/审稿人处理；本文不重算统计、不改冻结判据。
7. 投稿暂缓，P5 八项门槛（S1–S5 + PENDING 清零 + 贡献表核对 + 引用核验）闭环后再由 PI/审稿人重开。

---

## 6. 图表规划（更新：保留前后对照，删除机制/方法图）

- **保留**：① 数据审计前后对照表（RQ2 核心）；② 干净数据三 seed 表（affine 失败 + kd 情形 C，标注 exploratory）；③ 控制组 / 信息归因表；④ 外部锚点表（SQuAD，必要时 ARC；仅增强外部效度、不恢复贡献）。
- **删除**：机制热图（原图 5：层/头反事实误差 + Oracle 修复，P2 放弃）；方法消融图（原图 6：KD/CF/机制约束，P3 放弃）。
- 图表直接读取冻结结果文件生成，不回填、不编造、不重算。

## 7. 交接
- **工程师**：只执行已授权收尾（S1/S3/S2 中工程侧）与 SQuAD（必要时 ARC）锚点评测；v2.6 AI 数据提案已撤回、无产物，不实现任何生成；不碰封存 test、不开 P2/P3。
- **PI**：v2.6 AI 数据提案已按冻结裁定撤回、无产物、仅历史记录，无残留处置项；处理 kd 三 seed 的 v2.3 口径统一说明；闭环 P5 八项门槛。
- **写作者/审稿人**：按 §6 取舍图表；贡献措辞按 `final_boundary_study_signoff §3.2` 可写/禁写清单；重点复核 S4/S5 披露、exploratory 标注、v2.3 口径混用、Oracle 隔离。

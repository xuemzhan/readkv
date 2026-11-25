# 完整候选评分 R1 基线裁定：建立干净基线并重跑（protocol-v2.8）

> 裁决人：PI / 课题组长。日期：2026-11-24。
> 触发：合规审计 `reports/review/sequence_scoring_compliance_note.md` 判 P5 **NO-GO**，主因 R1——v2.8 判据、新评分代码、8 个 run 产物全部基于 `git_hash=a05e9b3` 的未提交工作树；该 hash 早于冻结与实现，其后 HEAD 前进会使 `consistency_check` 报 `run-producing code differs between config.git_hash and HEAD`，无法从 config 记录的 hash 精确重建。工程师在 `reports/review/sequence_scoring_script_fix_note.md` 修复 R2/R3 后明确指出：commit 后这 6 个正式 run 会被判代码漂移，且**未静默放宽**，交由 PI 裁量。
> 依据：`sequence_scoring_compliance_note.md` §0/§5、§7；`sequence_scoring_script_fix_note.md` §R1/§R2/§R3/验证记录；`sequence_scoring_run_report.md` §1（8 run 659s wall）、§5/§6；`configs/prereg/full_candidate_scoring_v2.8.yaml`；`docs/decisions/{full_candidate_scoring_ruling,p5_final_resignoff,gpu_supplement_ruling}.md`；`reports/review/independent_research_and_manuscript_review_2026-11-24.md` §3。
> 本裁定**只写本决策文档**：不改代码 / 数据 / `reports/runs/**` / 判据 / 论文；不写代码、不跑实验、不回写任何冻结文件。

---

## 1. 核心裁定（二选一的明确选择）

> **裁定：不接受"历史 git_hash + 如实披露无法重建"作为已知限制。要求建立干净冻结基线，按 v2.8 冻结口径重跑全部 8 个 run（新 id 后缀 `_b0`），以彻底关闭 R1。**

理由（权衡后选择重跑）：

1. **项目定位就是可复现负面实证研究**。本稿在 TMLR 的契合点是 reproducibility / negative empirical result；6 个正式 run 无法从自身记录的 git_hash 重建，直接击穿这一定位，且第二轮复审（2026-11-24 §3）对溯源要求严格（显式 teacher/student 路径、权重与 tokenizer revision/文件散列、区分历史实测/事后补录/当前快照）。接纳一个永久可追溯性缺口，与"判据先写后跑 + 可复现"的硬约束冲突。
2. **成本极低**。运行报告实测 8 个 run 共 **659s wall（≈11 分钟 GPU）**；重跑 + 一轮复审的代价远小于在论文中永久携带一个"无法从 config hash 重建"的硬伤。
3. **工程师行为正确应被 reward**。工程师未静默放宽 R1 并主动上报，是守纪律的表现；PI 应以"做对"而非"放宽"回应，维护治理可信度。
4. **重跑能真正关闭 R1**：把 v2.8 判据、裁决、代码、脚本、单测、CPU 数据先纳入同一**冻结基线提交**，再以该提交 hash 作为新 run 的 `git_hash` 跑分；此后只追加 run 产物/报告，不改产出代码，`consistency_check` 的产出代码比较即可通过（详见 §2–§4）。
5. **关闭 R1 是必要但非充分**：R4（scientist 判读归类）与第二轮复审的定向大修（编译/匿名稿/指标口径/归因措辞）仍独立待关；即便 R1 关闭，P5 仍需在这些项闭环后由 PI **新出**重新签 off。本裁定不承诺 R1 关闭即无条件 GO。

---

## 2. 冻结基线提交：必须纳入的路径（先提交，后跑分）

> 原则：**产出代码与判据在任何 `audit_seq_*_b0` run 启动前一次性提交**；基线提交 hash 记为 `B0`。新 run 的 `config.git_hash` = `B0`。`B0` 之后只允许追加产物/报告，不得再改产出代码。

### 2.1 判据 / 决策（原文不改，仅纳入版本控制）
- `configs/prereg/full_candidate_scoring_v2.8.yaml`
- `docs/decisions/full_candidate_scoring_ruling.md`
- `docs/decisions/sequence_scoring_baseline_ruling.md`（本文件）

### 2.2 代码 / 审计脚本 / 单测（产出代码，冻结于 B0）
- `src/readkv/models/gpu_backend.py`（M：`score_candidate_sequence` / `log_softmax_fp32` / `audit_sequence_forwards`）
- `experiments/sequence_scoring_gpu.py`（新评分入口）
- `scripts/consistency_check.py`（R2：协议白名单 + `_check_v28_fields`）
- `scripts/bootstrap_ci_report.py`（R3：字典型 E_CF 按三读数拆分）
- `tests/test_sequence_scoring.py`（新，7 项）
- `tests/test_sequence_scoring_scripts.py`（新，9 项）

### 2.3 CPU 数据产物（data-engineer 所有，不改动）
- `data/audit_2x2/sequence/`（6 个 `A{00,11}_seed{0,1,2}.jsonl` + `manifest.json` + `build_sequence_index.py`）
- `reports/data/sequence_scoring_data_audit.md`

### 2.4 方案 / 清单 / 审计文档（记录性，随基线纳入）
- `refine-logs/GPU_SEQUENCE_SCORING_PLAN.md`、`refine-logs/GPU_SEQUENCE_SCORING_TRACKER.md`（状态更新）
- `reports/review/sequence_scoring_{implementation_note,run_report,script_fix_note}.md`
- `reports/review/sequence_scoring_compliance_note.md`（reviewer 产物，不覆盖）

> **不在基线提交内**：8 个 `_b0` 新 run 产物（它们产生在 B0 之后，单独追加提交）。旧 run 产物按 §5 作为非权威历史一并纳入版本控制，但不得作为证据。

### 2.5 基线不可变纪律
- `B0` 之后**禁止修改** §2.2 任何产出代码。若确需代码修复，必须新建 `B1` 基线提交并从 `B0` 起**完整重跑全部 8 个 run（后缀 `_b1`）**，不得对个别格就地打补丁或混用不同基线的 run。
- 新 run 的 `config` 必须含：`git_hash=B0`、`protocol_version=2.8`、`version_tag`、`seed`、`input_sha256.train/val`、`dtype=bfloat16`、`kernel=sdpa`、`zero_re_prefill=true`、`sealed_test_read=false`、teacher/student 路径与 tokenizer 指纹、`criteria_source` 指向 v2.8。
- 判定准则：`consistency_check` 对新 run 报 `git_hash in_history=true`、`traceable=true`、产出代码差异为空、`protocol_compat.ok=true`、`v28_fields.ok=true`，方视为 R1 关闭。

---

## 3. 重跑矩阵与门控（沿用 v2.8，不改口径）

- **完全按 v2.8 冻结矩阵重跑**，评分口径、统计、三判读分支、forbidden_after_freeze 一字不改；后缀 `_b0` 仅为"干净基线重执行"的溯源标记，**不构成判据变更、无需新增 prereg 版本**。
- 门控**沿用 v2 冒烟**：先 seed0 的 A11/A00 固定小样本冒烟 → 首 token 回放 / 单 token full=first / 多 token teacher-forcing 位置 / 逐次输入审计 `[Q,1×(m−1)]` / 候选缓存独立 / zero re-prefill / Self-Identity 锚点 / A-B 顺序交换全部通过 → 再串行跑 6 个正式格。冒烟未过不得跑正式格；失败即中止并保留信息。
- 单卡串行（并发 3–7× 惩罚）；只跑 A00/A11，**不做 A01/A10**，**不评封存 test**。
- 预算：按运行报告实测 ≈11 分钟 GPU + 冒烟排查缓冲；以 seed0 实测耗时/显存更新。若只能排到一格，先跑 A11 seed0。

---

## 4. 新 run id 与权威集

### 4.1 新 run id（唯一权威集）
| 顺序 | run id | 用途 |
|---|---|---|
| 1 | `audit_seq_smoke_A11_s0_b0` | seed0 修复版冒烟（非权威） |
| 2 | `audit_seq_smoke_A00_s0_b0` | seed0 旧版冒烟（非权威） |
| 3 | `audit_seq_A11_s0_b0` | 修复版 60 对全量 |
| 4 | `audit_seq_A00_s0_b0` | 旧版 60 对全量 |
| 5–6 | `audit_seq_A11_s1_b0`、`audit_seq_A00_s1_b0` | seed1 |
| 7–8 | `audit_seq_A11_s2_b0`、`audit_seq_A00_s2_b0` | seed2 |
| 汇总 | `audit_seq_summary_b0` | CPU 复算 / 逐 seed 主表 / 敏感性表（不新增 GPU run） |

每格产物五类齐全：`config.json` / `scores.jsonl` / `forward_audit.jsonl` / `metrics.json` / `manifest.json`。

### 4.2 旧 run 处置
- 旧 8 个 `audit_seq_{A11,A00}_s{0,1,2}`、两 v2 冒烟 `..._smoke_{A11,A00}_s0_v2`、原失败 `..._smoke_A11_s0` **文件一律保留、不删除、不覆盖**。
- engineers 在 `reports/runs_index.json` / erratum 中把这些旧 id 标 `superseded` / `authoritative=false`，reason 统一为"pre-baseline：git_hash=a05e9b3 早于判据与代码，无法从该 hash 重建；已由 `_b0` 干净基线重跑取代"。
- 旧 run **仅供审计溯源，不得作为科学证据、不得进论文主表/附录数值、不得参与任何统计汇总**。

### 4.3 后续角色以哪套为准
- **scientist / reviewer / writer 仅以 `_b0` 八格 + `audit_seq_summary_b0` 为权威集**做判读归类、合规审计与入稿。
- 任何引用旧 id 的既有分析文档须改为引用 `_b0`，或在文档显式注明旧 id 为非权威历史。

---

## 5. 不可变边界（收口时再次确认）

- **不碰封存 test**：不读、不评；只 old(458de18)/repaired(efc3ba3) 的 train/val。
- **不恢复贡献**：贡献(1) 撤回、贡献(2) 撤回、贡献(3) withheld 维持；P2/P3/P4 永久放弃。
- **不改判据**：v2.8 矩阵/口径/分支/forbidden 不变；本裁定不新增 prereg 版本；不回写 v2.7、v2.1–v2.6、`gpu_supplement_ruling.md`、`p5_final_resignoff.md` 或任何既有冻结文件。
- **不是方法贡献**：本实验仅为读数稳健性补充；不重算 V2.0 主终点（封存 test 上 cf vs kd_only 成对 E_CF，CI 上界<0）、不声称方法增益、不作单项数据缺陷因果归因、不升级"跨评分一致"以外的强度措辞。
- **不伪造**：token 边界不一致、显存峰值未采集、同分、分母等如实记录；mock/smoke/失败产物不作证据。

---

## 6. 与既有裁决 / 判据的关系

| 文件 | 关系 |
|---|---|
| `configs/prereg/full_candidate_scoring_v2.8.yaml` | **不变**。重跑严格按 v2.8 冻结口径执行；`_b0` 是溯源后缀，非判据变更；不回写、不新增版本。 |
| `docs/decisions/full_candidate_scoring_ruling.md` | **不变**。其 §4"完成后重新触发 P5 审稿/签 off"继续有效；本裁定是 R1 的执行层处置，不改其 §2–§7 结论。 |
| `docs/decisions/gpu_supplement_ruling.md`（v2.7 2×2） | **不重开**。2×2 的 12 格 run 已在 HEAD 历史中、不属 R1 范围（`git_hash` 与产出代码一致）；本裁定不触碰其结论与 P5 GO。 |
| `docs/decisions/p5_final_resignoff.md`（2×2 后 GO） | **不回写**。该 GO 对应 v2.8 实验之前的状态；v2.8 已依裁决 §4 重开 P5。待 R1（本裁定）+ R2/R3（脚本已修）+ R4（scientist 归类）+ 第二轮复审定向大修全部闭环后，由 PI **新出**一份重新签 off（新文件），不改写旧签 off。 |
| `reports/review/independent_research_and_manuscript_review_2026-11-24.md` | 其"定向大修阻塞"与 R1 **独立**：关闭 R1 不等于解除投稿阻塞；编译/匿名稿/指标口径/归因措辞仍须单独关闭。 |

---

## 7. 各角色可执行指令

### 7.1 工程师（engineer）
1. 按 §2 路径清单创建**单一冻结基线提交 B0**（判据/裁决/产出代码/脚本/单测/CPU 数据/记录文档）；记录 `B0` 完整 hash。
2. 以 `B0` 为 `git_hash`，按 §3 门控 + §4.1 id 串行重跑 8 个 `_b0` run；`audit_seq_summary_b0` 做 CPU 汇总。
3. 新 run 产物单独追加提交；**B0 之后不得改 §2.2 产出代码**（如需改则走 B1 + 全量 `_b1` 重跑）。
4. 把 8 个旧 id 在 `runs_index.json` / erratum 标 `superseded`/`authoritative=false`（§4.2）。
5. 用已修复的脚本重跑 `consistency_check` 与 `bootstrap_ci_report`（输出重定向临时目录，不覆盖仓库报告），确认新 run `in_history=true`/`traceable=true`/产出代码差异空/`v28_fields.ok=true`/三读数 CI 产出；把结果交 reviewer。

### 7.2 主会话（parent session）
1. 监督 B0 提交先于任何 `_b0` run；确认提交后产出代码 diff 为空、HEAD 不再触发 R1。
2. 不得代为向 TMLR/OpenReview 投稿；投稿仍属真实 PI 人工动作。
3. 在 R1 关闭 + R4 + 定向大修闭环后，请求 PI 出新重新签 off（新文件，不回写旧签 off）。

### 7.3 科学家（scientist）
1. 以 `_b0` 权威集产出 `docs/audit_seq_statistical_interpretation.md`（关闭 R4）：按 v2.8 §7 三分支**对号入座**（结果前已冻结，注明"按预承诺条件归类、无事后择支"）。
2. 补 `reading_diff` / `cell_diff` / `reading_of_diff` 三项比较、pair-level 敏感性、样本加权口径、8 族 exploratory、E_CF 不跨口径比较。
3. 不作单项因果归因、不放宽强度、不恢复贡献。

### 7.4 审稿人（reviewer）
1. 对 `_b0` 权威集出稳健性合规 note（关闭 R1/R2/R3/R4 的复核）：确认 git 锚点可重建、输入审计、三读数同样本、统计口径、三分支归类、旧 id 已标非权威。
2. 明确记录"定向大修阻塞未由本实验解除"。

### 7.5 写作者（writer）
1. 首 token / 整串对照表与归一敏感性表一律转抄 `_b0` 权威集；旧 id 数值不得入稿。
2. 按 scientist 的分支归类措辞；不恢复贡献、不写方法增益/跨源普适、不越过封面信上限（`p5_cover_letter_cap.md`）。
3. 同步关闭第二轮复审定向大修项（编译两版、匿名 PDF 附录、2×2 表注、指标/归因措辞、cover letter）。

### 7.6 文档工程师（doc-engineer）
1. `README.md` / `docs/reproducibility.md` 同步：权威集改为 `_b0`、B0 基线 hash、旧 id 非权威历史；说明不重算主终点、不碰 test、不恢复贡献。

### 7.7 数据工程师（data-engineer）
1. 保持 `data/audit_2x2/sequence/**` 与数据审计文档不变（已随 B0 纳入版本控制）；如复核发现分母/哈希登记问题，仅以新勘误文件记录，不改冻结产物。

---

## 8. 结论

> **要求重跑，不接纳已知限制。** 建立单一冻结基线提交 `B0`（判据 + 代码 + 脚本 + 单测 + CPU 数据），以 `B0` 为 `git_hash` 按 v2.8 冻结口径重跑 8 个 `_b0` run（沿用 v2 冒烟门、单卡串行、≈11 分钟 GPU），彻底关闭 R1。旧 8 run 保留为非权威历史、标 superseded；scientist/reviewer/writer 仅以 `_b0` 权威集为准。v2.8 / gpu_supplement_ruling / p5_final_resignoff 一字不回写、不新增 prereg 版本；不碰封存 test、不恢复贡献、不改判据。P5 需待 R1 关闭 + R4 + 定向大修全部闭环后由 PI 新出重新签 off，本裁定不承诺立即无条件 GO。

**签署：PI / 课题组长（完整评分 R1 基线裁定 · 2026-11-24）**

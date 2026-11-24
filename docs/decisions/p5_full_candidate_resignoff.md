# P5 完整候选评分后重新签 off（V2.0 · TMLR · 终局条件性放行）

> 裁决人：PI / 课题组长。日期：2026-11-24。
> 性质：**新签 off**（new sign-off），不是对任何旧签 off 的改写。
> 触发：v2.8 完整候选评分全部任务（B0 基线重跑 + R1–R4 关闭 + 三分支判读）与第二轮定向大修（draft/匿名稿/arxiv 三稿）均按 reviewer 静态复核 PASS 闭环，要求 P5 重新签 off。
> 依据（均已落盘，数字仅转抄、不重算、不伪造）：`docs/decisions/sequence_scoring_baseline_ruling.md`（B0）、`docs/audit_seq_statistical_interpretation.md`（R4/分支①）、`reports/review/sequence_scoring_compliance_note_b0.md`（R1–R3/实验层）、`reports/review/manuscript_final_compliance_review.md`（七项大修静态 PASS）、`configs/prereg/full_candidate_scoring_v2.8.yaml`、`reports/review/independent_research_and_manuscript_review_2026-11-24.md`、`docs/decisions/{full_candidate_scoring_ruling,p5_final_resignoff,p5_cover_letter_cap,research_scope_update}.md`。
> 本签 off **只写本新文件**：不改代码 / 数据 / `reports/runs/**` / 论文 / 冻结判据；不写代码、不跑实验、不回写任何既有决策文件。

---

## 1. 这是新签 off，不回写旧签 off

> **裁定：本文件为独立新签 off；`docs/decisions/p5_final_resignoff.md` 原文一字不改、继续作为历史裁决留档。**

- 旧 `p5_final_resignoff.md`（2026-11-23，2×2 后无条件 GO）对应的是 v2.8 完整候选评分实验与第二轮复审（2026-11-24）**之前**的状态，已被二者超越：
  - 第二轮复审（`independent_research_and_manuscript_review_2026-11-24.md`）指出编译/匿名稿/指标口径/归因措辞七项定向大修阻塞，建议暂缓提交；
  - 真实 PI 指令提前执行候选全文评分，新增 v2.8（`full_candidate_scoring_ruling.md`）并因 R1 建立 B0 基线重跑（`sequence_scoring_baseline_ruling.md`）。
- 本签 off 取代旧签 off 成为**当前有效结论**；两者并存时以本文件为准。v2.1–v2.8 全部冻结判据未被回写。

---

## 2. 逐项核对（全部闭环）

| # | 核对项 | 状态 | 证据（转抄） |
|---|---|---|---|
| 1 | **B0 可重建 / R1 关闭** | ✅ | `git rev-parse HEAD` = `35e78e06917eb16461d6c925c8b0a435e99fd39c`（短 `35e78e0`）；`git diff 35e78e0 -- <产出代码+判据>` 与 `git diff HEAD -- <同上>` 均为空；6 个 `_b0` run `git_hash=35e78e0`、`in_history=true`、`traceable=true`、`run_code_unchanged_vs_head=true`、`dirty_run_paths=[]`。 |
| 2 | **R2 关闭** | ✅ | `PROTOCOL_WHITELIST=("2.0","2.1","2.7","2.8")`、`_check_v28_fields()` 并入 `protocol_compat.v28_fields`；实测 6 正式 `_b0` run `protocol_compat.ok=true`、`v28_fields.ok=true`。 |
| 3 | **R3 关闭** | ✅ | `_sequence_readings()`/`_ecf_value()` 识别 dict 型 E_CF（不再 `float(dict)`），逐 arm 逐 reading 产出 template_family 主 CI + pair 敏感性；`bootstrap_ci_report` 实测 55 runs 无崩溃、排除数 0，`no cross-reading E_CF comparison`。 |
| 4 | **R4 关闭 / 三分支判读** | ✅ | `docs/audit_seq_statistical_interpretation.md` 已产出：预承诺声明、按 v2.8 §7 结果前冻结条件**对号入座、无事后择支**，归类分支① `consistent_across_scoring`；三项比较三套 CI 齐全；无强显著/方法增益/贡献恢复。 |
| 5 | **门控与三读数** | ✅ | 两 `_b0` 冒烟先于六正式格（00:18/00:19 vs 00:20–00:24Z），`SMOKE_GATE_PASSED_NON_AUTHORITATIVE`、六格 `status=OK` 无 ABORTED；每格 120 行 scores 三读数齐全、单 token full=first max=0、480/480 逐次输入审计 `[Q,1×(m−1)]`/zero re-prefill、缓存互异；总 wall 655s。 |
| 6 | **序列评分分支①约束** | ✅ | 三组 A11 整串 L 为正、A11−A00 三口径同号、长度归一不改判读；措辞仅"两种候选评分下点估计方向一致"，报告幅度/区间、标 exploratory；A11 s1 `reading_diff` 主区间不含零但 L_full 仍正、cell_diff 未消失→不触发②，归一不改判读→不触发③。 |
| 7 | **定向大修七项静态 PASS** | ✅ | `manuscript_final_compliance_review.md` §0：①编译致命错误（draft/anon/arxiv 静态 PASS，arxiv 裸 E_CF 已修复）②2×2 表注/权重/计数/交互 ③因果措辞统一 ④指标口径 ⑤`_b0` 入稿 ⑥元数据（含如实标注未核）⑦匿名稿 全部 PASS；三稿数值一致。 |
| 8 | **旧 id 非权威** | ✅ | `reports/runs_index.json` 9 个旧 id（6 正式 + 3 冒烟 v2/失败）`superseded=true, authoritative=false`，reason 为 pre-baseline 无法从 a05e9b3 重建；6 个 `_b0` 正式格 `authoritative=true`。论文仅引用 `_b0`。 |
| 9 | **贡献状态与封存 test 边界** | ✅ | 贡献(1)(2) 撤回、贡献(3) withheld；P2/P3/P4 永久放弃；主终点未评估；封存 test 从未评测（8 run `sealed_test_read=false`）；未做 A01/A10；real=0；v2.6 not-activated。`git diff 35e78e0 -- configs/prereg/` 为空。 |

> 三处非阻塞残余（如实披露，不阻止条件放行）：reviewer note §3 列出——①本机无编译器、~103/~386 pt 溢出待可编译环境复核（即本签 off 的唯一外部条件）；②cover letter「most contrast intervals」未写 3/6 显式计数；③notes §5.2 与 bibitem 的 BridgeKV 作者核验措辞不一致。后两项为次要措辞，建议 writer 顺手统一，不影响科学结论。

---

## 3. 决议：CONDITIONAL FINAL SIGN-OFF（ready-to-submit，TMLR）

> **裁定：P5 = CONDITIONAL FINAL SIGN-OFF（附条件最终签 off，ready-to-submit），venue = TMLR。** 所有 agent 侧科学、实验、合规条件已闭环；放行仅取决于**唯一外部条件**——真实 PI 在可编译环境完成实际编译与人工投稿检查。agent 不代为投稿。

### 3.1 唯一外部条件（真实 PI 人工执行）

1. **实际编译三稿并复核溢出**：在可编译环境用 Tectonic/pdflatex 实际编译 `papers/readkv_v2_draft/main.tex`、`papers/readkv_v2_tmlr_anonymous/main.tex`、`papers/readkv_v2_arxiv/main.tex`，确认无致命错误；复核横向溢出（draft ~103 pt、arxiv ~386 pt）并按需处理。本机无编译器，reviewer 全部为静态检查，**未签"编译验证通过"**——这是本签 off 保留 CONDITIONAL 的唯一科学相关原因。

### 3.2 人工投稿检查清单（真实 PI 执行，agent 不代投）

| # | 事项 | 说明 |
|---|---|---|
| 1 | **署名邮箱** | Zhang Xuein <zxm0813@gmail.com>——确认有效且愿意公开。 |
| 2 | **OpenReview 提交** | 真实 PI 本人以 TMLR/OpenReview 账号提交（agent 不代为投递）；确认作者配额。 |
| 3 | **版权/许可** | 合成集 CC0、SQuAD 仅评测不发布衍生、KV-Lingo/CacheLink/N1–N9 引用合规；接受 TMLR CC-BY 出版许可。 |
| 4 | **cover letter AE/reviewer 建议** | 确认采用按 `p5_cover_letter_cap.md` 上限撰写的封面信（不用 general audit method / 跨源普适措辞）；确认 3–5 位 action editor / reviewer 建议名单；顺手把「most contrast intervals」改为「3 of 6」。 |
| 5 | **最终 PDF** | 确认三稿编译无误、匿名稿符合双盲、图表 textual placeholder 按 TMLR 要求处理（接受后补齐）、统一 notes §5.2 的 BridgeKV 作者核验措辞。 |

---

## 4. 所有 agent 任务完成；冻结判据未回写

> **裁定：所有 agent 的研究 / 实验 / 数据 / 代码 / 文档 / 审稿任务已完成；仅剩 §3 的真实 PI 人工动作。**

- 研究（RQ1'–RQ4'、新颖性限定、三分支判读）、实验（B0 基线 8 个 `_b0` run、旧 id 降权）、数据（CPU 分母/哈希审计）、代码（teacher-forcing 入口、R2/R3 脚本修复、单测 74 passed）、文档（draft/匿名稿/arxiv 三稿、README、`reproducibility.md`、封面信上限）、审稿（B0 合规 note、稿件最终合规 note）——全部签署闭环。
- **冻结判据 v2.1–v2.8 一字未回写**：v2.8 矩阵/口径/分支/forbidden、v2.7 2×2、v2.1–v2.6 统计与损失配置均保持冻结；本签 off 不新增 prereg 版本、不改任何既有决策文件。
- 边界不变：不碰封存 test、不恢复任何贡献、不重算主终点、不是方法贡献、不作单项数据缺陷因果归因、不升级"跨评分一致"以外的强度措辞（`p5_cover_letter_cap.md` 继续有效）。

---

## 5. 交付物状态清单

| 角色 / 交付物 | 状态 |
|---|---|
| scientist：`docs/audit_seq_statistical_interpretation.md`（R4/分支①） | ✅ 完成 |
| data-engineer：CPU 样本/哈希/分母审计、B0 数据冻结 | ✅ 完成 |
| engineer：teacher-forcing 入口、R2/R3 脚本修复、单测、`_b0` 8 run、旧 id superseded | ✅ 完成（B0=`35e78e0…`） |
| reviewer：`sequence_scoring_compliance_note_b0.md`（R1–R3/实验层）、`manuscript_final_compliance_review.md`（七项静态 PASS） | ✅ 完成（CONDITIONAL GO 意见） |
| writer：draft/匿名稿/arxiv 三稿 `_b0` 入稿、描述性 version contrast、样本加权、元数据同步 | ✅ 完成（静态 PASS） |
| doc-engineer：README / `reproducibility.md` 同步 `_b0` 权威集与 B0 | ✅ 完成 |
| PI：基线裁决、封面信上限、本新签 off | ✅ 完成 |
| 冻结判据 v2.1–v2.8 | ✅ 未回写 |
| 真实 PI 人工动作（编译/署名/OpenReview/许可/cover letter/最终 PDF） | ⏳ 待执行（唯一剩余） |

---

## 6. 给真实 PI 的最终说明

1. 论文已具备 TMLR 投稿资格，定位为**失败边界 + 数据泄漏教训 + 版本敏感性**的负面 / 实证 / 数据审计研究（modest contribution）；贡献(1)(2) 撤回、贡献(3) withheld，不夸大方法贡献。
2. v2.8 完整候选评分按冻结口径在干净 B0 基线上重跑，**两种候选评分下点估计方向一致**（分支①，exploratory），仅是读数稳健性补充，不恢复贡献、不重算主终点、不碰封存 test。
3. 最终签 off 为 **CONDITIONAL**：唯一科学相关条件是真实 PI 在可编译环境实际编译三稿并复核溢出（本机静态检查不足以签"编译通过"）；连同 §3.2 五项人工投稿检查完成后即可由真实 PI 经 OpenReview 自行提交。
4. agent 不代为投稿、不再产出任何研究/实验/文档产物；本签 off 后项目 agent 侧工作正式收口。
5. venue=TMLR、署名 Zhang Xuein 不变；封面信措辞以 `p5_cover_letter_cap.md` 为上限。

---

## 7. 结论

> **P5 = CONDITIONAL FINAL SIGN-OFF（ready-to-submit，TMLR）。** B0 可重建、R1–R4 全关、门控与三读数通过、序列评分分支①按预承诺归类、定向大修七项静态 PASS、旧 id 非权威、贡献与封存 test 边界不变。唯一外部条件为真实 PI 在可编译环境实际编译三稿并复核溢出 + 完成五项人工投稿检查；agent 不代投。**所有 agent 研究/实验/数据/代码/文档/审稿任务完成**，冻结判据 v2.1–v2.8 未回写，仅剩真实 PI 人工动作。

**签署：PI / 课题组长（P5 完整候选评分后重新签 off · 2026-11-24 · 新文件，不回写旧签 off）**

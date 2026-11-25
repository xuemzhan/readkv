# P5 最终重新签off（V2.0 · TMLR · 2×2 后 · 终局）

> 裁决人：PI / 课题组长。日期：2026-11-23。
> 触发：2×2 补充实验全部完成并通过审稿最终合规复核（`reports/review/final_2x2_compliance_note.md` 判 C1–C4 全闭环、P5 GO），要求 P5 重新签off。
> 依据：`reports/review/final_2x2_compliance_note.md`、`audit_2x2_formal_review.md`、`docs/audit_2x2_statistical_interpretation.md` v2、`configs/prereg/gpu_followup_v2.7.yaml`、`docs/decisions/{gpu_supplement_ruling,consistency_field_ruling,p5_final_signoff,final_implementation_plan,run_count_erratum}.md`、`papers/readkv_v2_draft/{main.tex,cover_letter.md}`、human_decisions.md。
> 本签off只写决策文档；不改 `src/**`、`reports/runs/**`、冻结判据、数据或论文；不写代码、不跑实验。

---

## 1. P5 最终决议：**GO（无条件放行至 ready-to-submit）**

> **裁定：P5 最终决议 = GO。** 基于审稿 GO、C1–C4 四项全部闭环、N1 标签已修正（commit 4a62bc0）、N2–N4 已披露、全部人工决策已落实。**无附条件门槛**——唯一剩余动作是真实 PI 的人工提交（§5），属流程动作而非科学/合规前置。

与此前 `p5_final_signoff.md`（附条件、锚点待补）和 `final_2x2_compliance_note.md` 前次（CONDITIONAL GO、C1/C2 待闭环）相比，本次为**终局 GO**：所有曾附条件项（锚点补入、C1 统计口径、C2 因果措辞、C3 假阳性、C4 论文补稿、N1 标签）均已闭环，无遗留前置。

---

## 2. 最终投稿主张边界（不可越）

- **定位**：empirical / boundary study（TMLR，modest contribution），失败边界 + 数据泄漏教训的负面/实证研究。
- **贡献状态（冻结）**：贡献(1) 撤回、贡献(2) 撤回、贡献(3) withheld；P2/P3/P4 永久放弃；v2.6 AI 生成集 not-activated；主终点（成对 E_CF vs kd_only，CI 上界<0）**未评估**；封存 test 从未评测；real=0（M4 受阻）；SQuAD 锚点 `exploratory_disclosure`。
- **2×2 结果定性（v2.7 §3 预承诺）**：`mixed_interaction`（**不**升级 `calibration_version_effect`）——九个校准对比点估计跨 seed 同号（唯一可称"方向稳定"的含义），但**不声称 CI 确认显著**；全部 exploratory（8 簇<24）。
- **归因边界（whole_version_only）**：2×2 只识别"整体语料版本切换"的影响；**禁止**归因到去重/退化对/模板重叠任一单项缺陷；结构未见模板主要在 probe/test，不能由 val 对照推断。
- **禁止表述**：单项缺陷因果（manufactured/directly produced/caused by/sufficient to）、贡献恢复、(3) 方法增益、跨源普适/真实文档验证/强显著性、主终点改善声称——审稿 §4 不放行清单全部维持。

---

## 3. 人工决策落实确认（逐项）

| 决策项 | 状态 | 证据 |
|---|---|---|
| venue = **TMLR** | ✅ 已落实 | human_decisions 决策 5；cover letter/论文一致 |
| 署名 **Zhang Xuein <zxm0813@gmail.com>** | ✅ 已落实 | main.tex、cover letter、投稿元数据一致 |
| 引用按需实际引用（R2 cover letter 声明） | ✅ 已落实 | cover letter §Reference-verification disclosure；正文 N1–N9 仅摘要级、无章节级确证；squad16/18 已在 bib |
| GPU 2×2 补充实验（决策 11） | ✅ 已完成 | 12 格全通过、C1–C4 闭环、审稿 GO |
| 其余决策 1–10 | ✅ 均落实 | M4 受阻披露 real=0、锚点先行、AI 数据撤回、P3 永久放弃等无回归 |

**无遗留未落实的人工决策。**

---

## 4. 四项非阻塞残余处置决定

| 编号 | 残余项 | 处置决定 | 影响投稿？ |
|---|---|---|---|
| **N1** | A10−A00 对比标签笔误 | **已修正**（commit 4a62bc0，main.tex line 745–746 现为 "legacy-validation calibration contrast (A10−A00; both cells use the legacy validation set)"）——核验属实，无需再动 | 否，已消除 |
| **N2** | Holm 多重比较未校正 | **披露即可**：全部 exploratory、不作强推断；已在限制段/补充材料披露（main.tex line 472 等提及 Holm 为主终点要求，2×2 段声明 exploratory 不作强显著）；无需补动作 | 否 |
| **N3** | L 尺度 1.67pp、20pp 阈值仅参考 | **披露即可**：正文表注/统计解释 v2 §6.5 已记，无需补动作 | 否 |
| **N4** | 对比②非配对独立簇重采样口径 | **披露即可**：`l_ci.json::predeclared_contrasts.method` 已逐项标注、2×2 段 line 764–766 附"non-paired resampling note"，无需补动作 | 否 |

**处置结论**：N1 已修正；N2–N4 均为已如实披露的次要项，**均不影响投稿，无补充动作**。

---

## 5. 给真实 PI 的最终人工提交清单（agent 不代为提交）

1. **署名与邮箱**：确认 Zhang Xuein <zxm0813@gmail.com> 有效且愿意公开。
2. **OpenReview 账号**：真实 PI 本人以 TMLR/OpenReview 账号提交（agent 不代为投递）。
3. **cover letter**：确认采用已含 R2 引用核验声明、贡献/限制诚实披露、无强因果措辞的最终版。
4. **版权/许可**：确认合成数据 CC0、SQuAD 仅评测不发布衍生、KV-Lingo/CacheLink/N1–N9 引用合规；接受 TMLR 的 CC-BY 出版许可。
5. **AE/reviewer 建议**：确认 cover letter 中的 action editor 与 reviewer 建议名单、关键词、≤200 词摘要。
6. **最终稿件**：确认 PDF 按 TMLR 匿名模板生成、图表可读、补充材料齐备（2×2 逐格 CI、三项敏感性、非配对重采样说明等已在 notes/补充材料）。

---

## 6. 项目最终状态记录

- **全部任务完成**：P0/E0 GO、P1 GO、P2/P3/P4 永久放弃、2×2 补充实验完成、P5 本次 GO。
- **证据链完整**：权威 run = 7 clean + 2 SQuAD 锚点 + 12 个 2×2 格（2×2 为补充受控观察，不并入主终点）；计数以 `reports/runs_index.json` 为准（含 run_count_erratum 只读勘误）。
- **git HEAD 与远程同步**：终局 HEAD=`b69b9a9`（审稿 note 时点），N1 修正 commit `4a62bc0` 已纳入；所有冻结判据 v2.1–v2.7 TRACKED 且未篡改；跑分代码在 HEAD 历史、工作区 clean。
- **无遗留待跑实验**：δ 复核取消、P2/P3 重跑取消、ARC/HellaSwag NO-Go、AI 生成集 not-activated、单缺陷因果/候选整串评分推迟或不做——**无任何待执行 run 或待补产物**。
- **剩余动作**：仅 §5 的真实 PI 人工提交（流程性），无科学/合规待办。

---

## 7. 结论

> **P5 终局决议：GO（无条件 ready-to-submit）。** C1–C4 全闭环、N1 已修正、N2–N4 已披露、全部人工决策落实、冻结判据未篡改、贡献/定位无回归。**论文可交真实 PI 按 TMLR 流程提交。** 投稿边界见 §2（mixed_interaction、whole_version_only、贡献(1)(2) 撤回/(3) withheld、主终点未评估），agent 不代为提交。

**签署：PI / 课题组长（P5 最终重新签off · 2026-11-23 · 终局）**

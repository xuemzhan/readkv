# Paper Reviewer B — 终审汇总（方法与实验可信度）

- 日期：2026-11-23 · 只读终审，未改论文 / 代码 / 数据 / 判据 / 运行产物。
- 完整意见：`reports/review/paper_b/paper_reviewer_b_final.md`

## 裁决

**P5 方法 / 统计可信度：CONDITIONAL GO（放行至 ready-to-submit）。** 无阻塞级风险；1 项主要项投递前必须修正，3 项次要收尾。

## 六项审查重点：全部通过

1. **R1 闭合 ✓** — `tab:cleanmvp`/`tab:cleankd`/`tab:reversal` 均并列 template-family 主 CI（8 族 exploratory）与 pair-level sensitivity，明确主次；affine 主 CI `3.564–10.100 / 4.357–11.584 / 5.326–11.610`、kd 主 CI `3.653–8.814 / 3.899–8.798 / 4.417–9.799` 与 `bootstrap_summary.json` 逐字一致。转换说明 `arxiv_conversion_notes.md:55–65` 如实记录跨源 pair-level 差异并声明以权威 JSON 为准、不重算。
2. **E_CF 口径 ✓** — τ=1.0、self_threshold=0.1（|D_self|≥0.1）、flip 排除 F5+F6（分母 398）、dual/flip/coverage/info_attribution 联合报告、机器 verdict `distortion_exists` 与 `transfer_broken` 分离，均正确。
3. **SQuAD 锚点 ✓** — EM 全 0 / F1 可区分归因与 `engineer_anchor_audit.md`、`senior_engineer_final.md` 一致（非 bug）；`exploratory_disclosure` 三情形引用正确；锚点不并入合成 CI。
4. **数据修复 ✓** — 退化 18→0、泄漏 ≥15→0、实体重叠→0、flip 398、SHA `f910f1f1…a894a` 与 `data_fix_report.md` 一致；zero-re-prefill 与 provenance 有真 hook + 哈希绑定佐证。
5. **bib/引用 ✓** — 19 键全解析；N1–N9 仅 arXiv preprint+年份、无编造 venue；SQuAD 两条 DOI 正确；N9b 已标注"作者未独立核验"。
6. **arXiv 格式 ✓** — main.tex 自包含（无本地 cls/sty、无 \input、无外部图）；README 编译序列正确；无 P2/P3/P4/G1/封存 test 产物混入。

## 主要（投递前必须修正）

- **M1** `main.tex:471–474`：称各臂 "matched（含 trainable parameter count / training steps / tuning budget）"，但 affine 为 0 参数 / 0 训练、kd_only 为 7.34M / 8 epoch，实际预算不对等；且 `research_scope_update.md:86` 把"预算不对等"列为强制披露。须如实改写为 matched on pairs/dtype/kernel/forward budget，并显式披露参数 / 步数不对等。不推翻负面结论，故非阻塞。

## 次要

- m1 `arxiv_conversion_notes.md:55–57`：affine `[5.499,8.313]` 错归于 notes.md（notes.md 实为 `[5.496,8.321]`），应改归历史裁决 / 旧稿。
- m2 `main.tex:276,331`：56 族 vs 8 族未桥接，scope `:120` 要求解释（val 仅 8 SEEN 族）。
- m3 N1–N9 章节级细节 §9 全文核验未闭环（仅摘要级；最终边界审计 R2，非阻塞）。

## 与冻结约束一致性

zero-re-prefill / 判据先写后跑 / 主终点 unevaluated / `P>0.05` 不作等效 / 联合报告 / 贡献门槛 §10 全部一致；无 mock 当证据、无贡献升格。

**结论：与 `final_boundary_audit.md` CONDITIONAL GO 一致；M1 修复 + m1–m3 收尾、venue 经真实 PI 指定后可投递。**

**签署：Paper Reviewer B（方法与实验可信度终审）· 2026-11-23。**

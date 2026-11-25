# 最终项目收口签 off（V2.0 · 失败边界 / 数据教训负面实证研究 · TMLR）

> 裁决人：PI / 课题组长。日期：2026-11-23。
> 性质：**最终项目收口签 off**——确认所有角色交付物、P5 ready-to-submit 条件与全部研究任务闭环；此后仅剩真实 PI 人工执行的投递动作。
> 触发前提（parent 会话已确认完成）：① paper A/B 终审修复收尾完成；② doc-engineer 的 README / 可复现文档完成；③ data-engineer 的 GPU 实验数据整理完成。
> 依据（全部为冻结产物/既有决策，数字仅转抄、不重算、不伪造）：`docs/decisions/{research_scope_update,p5_final_signoff,p5_cover_letter_cap,final_boundary_study_signoff,ai_dataset_final_ruling,human_decisions,venue_recommendation}.md`；`reports/review/{paper_a_final,paper_reviewer_b,paper_b/paper_reviewer_b_final,meta_review/current_task_meta_review,final_boundary_audit,code_review_final,senior_engineer_final}.md`；`papers/readkv_v2_{arxiv,draft}/**`；`README.md`、`docs/reproducibility.md`；`reports/data/gpu_experiments/v1/**`；`reports/{bootstrap_summary,anchor_eval_summary,consistency_report,runs_index}.json`；`configs/prereg/`（v2.1–v2.6）。
> 本签 off **只写决策文档**：不改代码 / 数据 / 判据 / 论文 / 运行产物；不写代码、不跑实验、不润色文本。

---

## 1. 各角色交付物状态（全部闭环）

| 角色 | 交付物 | 状态 | 依据 |
|---|---|---|---|
| **科学家（scientist）** | RQ1'–RQ4' 写入研究设计；锚点/探针有限外部效度解读；G1 未启动定位 | ✅ 完成 | `research_scope_update.md` §2/§5；论文 Related Work / Limitations 已限定新颖性 |
| **数据工程师（data-engineer）** | S2 残留闭环；SQuAD 五项登记；**GPU 实验数据整理**；v2.6 工作包 not-activated | ✅ 完成（触发前提③） | `reports/data/gpu_experiments/v1/`（manifest 校验 126/126 raw、28/28 scores、12,040+960 tidy 全通过，`README.md` 已签署）；`s2_hash_annotation.md`；`data/generated/` 不存在 |
| **工程师（engineer）** | S1 数据哈希绑定、S3 runs_index（28 run）、kd 三 seed v2.3 审计产物、2 SQuAD 锚点 run | ✅ 完成 | `data_hash_binding_erratum.json`；`runs_index.json` / `consistency_report.json`（31 项，7 clean + 2 锚点 ok=true）；`bootstrap_summary.json` |
| **审稿人 / 高工 / 代码审查（reviewer / senior-engineer / code-reviewer）** | broken-transfer 可信复核、final boundary audit、code review final、senior engineer final | ✅ 完成 | `clean_data_reversal_emergency_review.md`（可信·高）、`final_boundary_audit.md`（CONDITIONAL GO）、`code_review_final.md`、`senior_engineer_final.md` |
| **论文审稿 A（paper-reviewer-a）** | 叙事/证据强度终审 CONDITIONAL GO；M1–M4 + M3 封面信措辞上限 | ✅ 完成（触发前提①，修复收尾完成） | `paper_a_final.md`（无阻塞、无主要；M3 已由 `p5_cover_letter_cap.md` PI 收口） |
| **论文审稿 B（paper-reviewer-b）** | 方法/统计可信度终审 CONDITIONAL GO；M1 预算不对等披露 + m1–m3 | ✅ 完成（触发前提①，修复收尾完成） | `paper_reviewer_b.md`、`paper_b/paper_reviewer_b_final.md`（6 项重点全通过；无阻塞） |
| **文档工程师（doc-engineer）** | **README 全量同步 + 可复现指南**；顾问报告状态管理 | ✅ 完成（触发前提②） | `README.md`（31 run、clean 定性、TMLR、P5 附条件签 off、v2.6 not-activated 全部同步）；`docs/reproducibility.md`（环境/数据/复现命令/9 run 口径齐全） |
| **写作者（writer）** | 论文按新课题重写；锚点结果补入；S4/S5 措辞；引用无 PLACEHOLDER；封面信草稿 | ✅ 完成 | `papers/readkv_v2_arxiv/{main.tex,references.bib,README.md,arxiv_conversion_notes.md}`、`papers/readkv_v2_draft/{main.tex,notes.md}`；paper A/B 终审确认定位正确 |
| **PI** | 范围更新、P5 签 off、封面信上限、本收口签 off | ✅ 完成 | `research_scope_update.md`、`p5_final_signoff.md`、`p5_cover_letter_cap.md`、本文件 |

---

## 2. P5 ready-to-submit 条件闭环核对

| # | 条件 | 状态 |
|---|---|---|
| S1–S5 | 数据哈希绑定 / v2.3 sha 注记 / runs_index / 措辞精度 / 单信号+exploratory 披露 | ✅ 全部闭环（见 `p5_final_signoff.md` §1、`final_boundary_audit.md`） |
| 6–8 | kd 三 seed 入稿 PENDING 清零 / 数据修复前后对照 / real=0 受阻披露 | ✅ 闭环 |
| 9 | v2.4 SQuAD 锚点探索性结果补入并定性 `exploratory_disclosure` | ✅ 闭环（写作者已补，paper A/B 终审核对与 `anchor_eval_summary.json` 一致） |
| 10–13 | 署名 Zhang Xuein / 引用无 PLACEHOLDER / 贡献清单(1)(2)撤回(3)withheld / venue=TMLR | ✅ 闭环 |
| A | paper A 终审 CONDITIONAL GO + M1–M4 修复收尾 | ✅ 闭环 |
| B | paper B 终审 CONDITIONAL GO + M1 预算不对等披露 + m1–m3 收尾 | ✅ 闭环 |
| CAP | 封面信措辞上限（M3）以论文 `main.tex:813-816` 为界 | ✅ 闭环（`p5_cover_letter_cap.md`） |
| DOC | README + reproducibility + GPU 数据整理 | ✅ 闭环（触发前提②③） |

> **裁定：P5 ready-to-submit 条件全部闭环。** 所有科学结论、贡献状态、边界披露、venue、署名、引用、数据/文档/封面信措辞均已就绪且经冻结产物与终审核对达标。论文审稿 A/B 的 CONDITIONAL GO 均为"放行至 ready-to-submit"、无阻塞/无改变负面结论的主要项；其收尾项已闭环。

---

## 3. 冻结不变量复核（收口时再次确认）

- 贡献(1) 撤回、贡献(2) 撤回、贡献(3) withheld；P2/P3/P4 永久放弃（决策 8）；G1 未执行。
- 封存 test 未评测、主终点（成对 E_CF vs kd_only，CI 上界<0）未评估；所有 clean 结论 exploratory（8 族<24、单合成等深对、单 dual-drop 信号）。
- real=0；SQuAD 锚点仅评测、`exploratory_disclosure`；v2.6 提案 not-activated、无 `data/generated/`、无遗留产物。
- v2.1–v2.6 冻结判据未被回写；zero re-prefill / 判据先写后跑 / 联合报告 / §10 贡献门槛全程一致；无 mock 当证据、无贡献升格、无伪造数据/文献。
- 论文自述与封面信上限一致：新颖性限定为"具体预注册翻转案例 + 成对 E_CF 审计轨迹"，不声称通用审计方法 / 一般泄漏教训 / 跨源普适（见 `main.tex:168-172,813-816` 与 `p5_cover_letter_cap.md`）。

---

## 4. 剩余事项：**仅供真实 PI 人工执行**（agent 不代为执行）

| # | 事项 | 说明 |
|---|---|---|
| 1 | **署名邮箱确认** | Zhang Xuein <zxm0813@gmail.com>——确认邮箱有效且愿意公开（`p5_final_signoff.md` §6 第 1 条） |
| 2 | **OpenReview 提交** | 真实 PI 本人用 TMLR/OpenReview 账号提交；agent 不代为提交；确认作者配额（决策 5） |
| 3 | **版权 / 许可确认** | 确认合成集 CC0、SQuAD 仅评测不发布衍生、引用许可合规；接受 TMLR CC-BY 出版许可（`p5_final_signoff.md` §6 第 3 条） |
| 4 | **cover letter AE / reviewer 建议终审** | 真实 PI 认可按 `p5_cover_letter_cap.md` 撰写的封面信与 3–5 位 action editor / reviewer 建议名单；措辞不得越过封面信上限 |
| 5 | **最终稿件版本确认** | 确认编译无误、图表 textual placeholder 按 TMLR 投稿要求处理（接受后补齐）；§9 章节级全文口径复核属非阻塞投递前项 |

---

## 5. 最终结论

> **所有研究任务完成。** 课题已按 `research_scope_update.md` 收口为「跨模型 KV 迁移失败边界 + 数据泄漏教训的负面 / 实证 / 数据审计研究」；P0/P1 终局 GO，P2/P3/P4 永久放弃，P5 附条件最终签 off 且 ready-to-submit 条件**全部闭环**；每个角色的交付物（科学家、数据工程师、工程师、审稿/审计、论文审稿 A/B、文档工程师、写作者、PI）均已签署完成；论文立场、贡献状态、边界披露、封面信措辞上限与全部冻结判据一致。
>
> 本签 off 之后，**不存在任何遗留的研究 / 实验 / 数据 / 文档 / 审稿任务**；仅剩 §4 的 5 项真实 PI 人工投递动作（署名邮箱确认、OpenReview 提交、版权/许可确认、cover letter AE/reviewer 建议终审、最终稿件版本确认）。agent 团队工作到此收口。

**签署：PI / 课题组长（最终项目收口签 off · 2026-11-23）**

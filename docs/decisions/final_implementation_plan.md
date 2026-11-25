# 最终落实计划：收尾项责任分工、GPU 决策与投递检查（V2.0 · TMLR）

> 裁决人：PI / 课题组长。日期：2026-11-23。
> 触发：真实 PI 指令"根据最新审稿结论与 GPU 下一步工作，安排团队落实"；依据 `reports/review/final_boundary_audit.md`（HEAD 4613200）R1–R5、D3，及用户对本工作区（HEAD 4613200 之后）的只读状态同步。
> 依据：`reports/review/{final_boundary_audit,anchor_eval_review}.md`、`docs/decisions/{p5_final_signoff,final_boundary_study_signoff}.md`、`papers/readkv_v2_draft/{main.tex,notes.md}`、`reports/runs_index.json`、`configs/prereg/stats_convention_v2.3.yaml`、用户状态同步。
> 本计划只写决策文档；不改 `src/**`、`reports/runs/**`、已冻结判据、数据或论文；不写代码、不跑实验。**不重新讨论已定科学结论。**

---

## 0. 当前状态总览（以本轮只读核验为准，区分"审计告警"与"现状"）

> 多项审计告警由审计期间的并行提交已修复；PI 本轮独立只读核验，**已闭环项不再重复安排**。

| 项 | 审计告警（4613200） | 本轮核验现状 | 判定 |
|---|---|---|---|
| **R1** CI 口径 | 表格只报 pair-level 单一 CI | main.tex `tab:cleanmvp` 第 538 行 `6.900 [3.564,10.100] [5.496,8.321]`、`tab:cleankd` 第 629 行 `6.388 [3.653,8.814] [5.340,7.400]` **已并列主 CI(template_family)+敏感性(pair-level)**，表头第 536/627 行标两列、正文第 616 行 "carries two" | **✅ 已闭环，无需再改** |
| **R2** N1–N9 作者名 | bibitem 无作者名、仅摘要级核验 | bibitem n1–n9a 已有作者名（如 n1 "Z. Tao, F. Jin, and J. Zhao"）；n9b BridgeKV 为机构式署名。**但"全文口径核验"是否完成无法从文件判定** | ⚠️ 作者名已补；**全文核验口径需 PI 裁定**（见 §2 R2） |
| **R3** SQuAD 引用 | 未进 bibliography | `bibitem{squad16}`/`{squad18}` 已存在（line 860–866），正文 line 657 `\cite{squad16,squad18}` | **✅ 已闭环，无需再改** |
| **D3** v2.6 跟踪 | v2.6 未纳入 git | 用户核验 `git ls-files` 返回该文件（随 d0f54de 提交） | **✅ 已闭环** |
| **R4** 历史 run 状态 | 3 run ok=false/superseded=false、不在索引 | 本轮核验：`delta_lock_v2p1_2p0_par`、`kdonly_mvp_seed1_par`、`seed2_fast` **均不在 runs_index.json**（既未标 superseded 也不在权威清单）；consistency 仍可能因目录存在报 ok=false | ⚠️ **仍需落实**（见 §2 R4） |
| **R5** "26 run"陈旧 | 冻结文档写 26，实际 28 | "26 run"出现在**已冻结/已签署的 PI 裁决文档**（p5_final_signoff:16、final_boundary_study_signoff:48/110、research_scope_update、experiment_design 等）及若干报告 | ⚠️ **仍需处理，但须守"不回写冻结裁决"纪律**（见 §2 R5） |

**已闭环（无需再安排）**：R1、R3、D3、N1–N9 作者名补齐。
**仍需落实**：R2 的"全文核验口径"裁定、R4、R5。

---

## 1. R1 口径说明（PI 出具，供留档；当前已落实）

虽然 R1 已在提交稿修复，PI 出此口径说明以防回归，写作者不得私改数字：

> **v2.3 CI 呈现口径**：所有成对 E_CF 主终点（P1/P3 clean 结果）必须以 **template_family 簇级 bootstrap CI 为主 CI**；**pair-level CI 仅作敏感性分析，必须与之并列呈现**，不得只报较窄的一套（v2.3 `forbidden_after_freeze` 与 `pair_level_sensitivity.required=true`）。当簇数 <24（当前 8 族）须标 `exploratory=true`。**数字以 `reports/bootstrap_summary.json`（31 runs）为准，任何人不得为实现"更好看"而替换或私改。**
- 当前主 CI（template_family）：affine seed0 `6.900 [3.564,10.100]`；kd seed0 `6.388 [3.653,8.814]`——均为 exploratory、下界>0。
- 当前敏感 CI（pair-level）：affine seed0 `[5.496,8.321]`；kd seed0 `[5.340,7.400]`。
- 结论不变：两套口径下界均>0，支持而推翻不了情形 C 判读。
- **责任**：写作者保持现有并列格式（已达标），审稿人在最终 compliance note 确认无回归。

---

## 2. 仍需落实项：责任、动作、验收、顺序

### R2【次要】N1–N9 全文口径裁定

- **PI 裁定（本计划给出）**：科学家的 online addendum 与 meta-review 已如实声明 N1–N9 为"标题+arXiv+年份"级核验、未逐篇读全文；bibitem 作者名已补（现状属实）。**采用"cover letter 说明占位"路线**，不宣称已全文核验：写作者不得把 N1–N9 的章节级细节写成已核实事实；在 cover letter 加一句"Related-work citations N1–N9 are identified by title/arXiv/version/date from public metadata; full-text reading was not completed at submission." 
- **责任人**：写作者（cover letter 加说明）；审稿人（合规复核时确认无"章节级细节当已核实"的表述）。
- **验收**：cover letter 含该声明；正文 N1–N9 引用仅为存在性/标题级，无未核实的细节性主张。
- **顺序/依赖**：独立于 R4/R5，可与 R4 并行。

### R4【次要】3 个历史 run 状态标注

- **事实**：三 run 不在 runs_index.json（权威清单），目录可能仍在 `reports/runs/`，导致 consistency_check 扫描时报 ok=false/superseded=false。
- **PI 裁定**：**不改任何 run 产物**；由工程师在 `reports/runs_index.json` 的 superseded 区段**显式加入三个条目**并标 `superseded=true` + `superseded_reason`（如 "pre-clean-data / historical delta-lock or stalled kd seed, not authoritative"），或在 `runs_index_errata.json` 加注。优先 errata/索引层，不改 scores/config。
- **责任人**：工程师（索引/勘误层）；审稿人（复核 consistency 告警是否归零）。
- **验收**：三 run 在索引/errata 中可查且标 superseded；`consistency_check` 对这三个不再以"未标注历史 run"形式报 ok=false（若因 HEAD 前进而报 code-diff，按历史 run 合理解释并在审计注记）。
- **顺序/依赖**：独立于 R2/R5。

### R5【次要】"26 run"陈旧计数——守"不回写冻结裁决"纪律

- **PI 裁定**：这些"26 run"出现在**已冻结/已签署的 PI 裁决文档**（p5_final_signoff.md:16、final_boundary_study_signoff.md:48/110）与 research_scope_update.md、experiment_design_E0_E7.md 等。**按纪律不回写已冻结/已签署裁决文档**。处理方式是**新增一份勘误说明**（本计划即为载体），而非改旧文件。
- **具体动作**：由 PI 在本计划中登记勘误——"凡已签署裁决文档中的'26 run'均为加入 2 个 SQuAD 锚点前的旧计数，当前权威计数为 **28 run**（19 旧 superseded + 9 权威 = 7 clean + 2 锚点），以 `reports/runs_index.json` 为准"。不改任何旧文档正文。
- **责任人**：PI（本计划登记勘误）；文档工程师（如需，在非冻结的 README/临时文档同步为 28，但不动已签署裁决）。
- **验收**：勘误记录存在；旧冻结文档未被回写（git diff 为空）；下游以 runs_index 28 为准。
- **顺序/依赖**：独立。

---

## 3. GPU 下一步决策：ARC 锚点 → **NO-Go（不跑，维持现状直投）**

> **裁定：不投入 GPU 跑 ARC（辅）/HellaSwag（可选）锚点；维持 SQuAD 已完成的现状，按 TMLR 现状投递。**

理由：
1. **非门槛**：ARC/HellaSwag 是 v2.4 允许的"顺位增强项"，**非 P5 硬门槛**；SQuAD 主锚点已完成并判 `exploratory_disclosure`，已满足"有限外部锚点"的最低要求。
2. **预期收益近零**：SQuAD 锚点已显示"affine 坍塌方向复现、kd 对照未复现、EM 全臂触底、单 seed/240 例"→ exploratory_disclosure。ARC（选择题）/HellaSwag（常识补全）与 SQuAD 同为"有限标准 QA 旁证"，再加 1–2 个仍属 exploratory，无法把"探索性"升级为"强外部效度"——边际信息不 value 额外成本。
3. **成本非零且有前置**：ARC/HellaSwag 需先完成下载 + 五项登记 + 许可复核（HellaSwag MIT、ARC CC BY-SA）+ 新 run 的 provenance/审计/论文补写，<1h GPU 但伴随 1–2 人日工程与文档工作，且会再次触发论文一致性复核（R1–R5 刚收口）。在"ready-to-submit"节点引入新结果，边际风险（新口径、新数字需重审）大于边际收益。
4. **与已定结论一致**：贡献(1)(2) 撤回、贡献(3) withheld、边界/负面定位不因增锚点而变；没有科学理由为"更丰富"而延后。

**执行指令**：工程师不启动 ARC/HellaSwag run；数据工程师不新增锚点归档；写作者不再补锚点内容；维持现有 2 个 SQuAD 锚点 + 7 个 clean run。ARC/HellaSwag 作为"未来工作"在论文中一句带过即可（若尚未写），不作为本次投稿内容。

---

## 4. 全部落实后的最终投递检查清单与负责人

| # | 检查项 | 负责人 | 完成标准 |
|---|---|---|---|
| 1 | R1 CI 口径并列（已达标，防回归） | 写作者 + 审稿人 | 两表主 CI+pair 敏感性并列、exploratory 标注、数字未被私改 |
| 2 | R2 cover letter 加"N1–N9 标题/arXiv/年份级核验"声明 | 写作者 | 声明存在；正文无未核实章节级细节 |
| 3 | R3 SQuAD 引用（已达标） | 写作者 | bibitem squad16/18 + 正文 cite 在位 |
| 4 | R4 三历史 run 在索引/errata 标 superseded | 工程师 → 审稿人复核 | runs_index/errata 可查、consistency 无"未标注历史 run"告警 |
| 5 | R5 "26 run"勘误（本计划登记，不改旧裁决） | PI | 勘误存在；旧冻结文档 git diff 为空；下游用 28 |
| 6 | D3 v2.6 已跟踪（已达标） | （无需动作，留档） | git ls-files 含 v2.6 |
| 7 | 贡献/定位/贡献清单无回归 | 审稿人（compliance note） | 贡献(1)(2) 撤回、(3) withheld、无跨源/真实验证主张 |
| 8 | 署名 Zhang Xuein <zxm0813@gmail.com>、venue=TMLR、引用核验 | 写作者 + 真实 PI | 全文一致 |
| 9 | **真实 PI 人工最终动作**：确认署名邮箱、TMLR OpenReview 账号提交、版权/许可声明、cover letter、AE/reviewer 建议 | **真实 PI**（agent 不代为提交） | 全部确认后在 TMLR 正式提交 |

**延后事项**：无（P2/P3/P4 永久放弃、AI 生成集 not-activated、ARC/HellaSwag 本次不做）。

---

## 5. 第一步动作

**第一步（并行，无依赖）**：
- 工程师：在 `reports/runs_index.json`（或 errata）为 R4 三历史 run 补 `superseded=true` 标注（§2 R4），完成后通知审稿人复核。
- 写作者：在 cover letter 加入 R2 的 N1–N9 核验级别声明（§2 R2）。
- PI：本计划已登记 R1 口径与 R5 勘误（无需额外动作）。
- **GPU：不启动任何新 run**（§3）。

上述 R2/R4 完成后，审稿人出最终 compliance note（检查清单第 7 项），真实 PI 完成第 9 项人工检查即可在 TMLR 提交。

**签署：PI / 课题组长（最终落实计划 · 2026-11-23）**

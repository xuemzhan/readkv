# P5 最终签off（V2.0 · TMLR · 失败边界/数据教训实证研究）

> 裁决人：PI / 课题组长。日期：2026-11-23。
> 触发：真实 PI 指定 venue = **TMLR**（human_decisions.md 决策 5，采纳 PI 首选推荐），所有证据与门槛就绪，要求 P5 最终签off。
> 依据：`papers/readkv_v2_draft/{main.tex,notes.md}`、`docs/decisions/{final_boundary_study_signoff,final_signoff,m4_target_adjustment,ai_dataset_final_ruling,venue_recommendation,anchor_confirmation}.md`、`reports/review/{clean_data_reversal_emergency_review,p2_f1f2_closure_review,meta_review/current_task_meta_review}.md`、`reports/engineer_status.md §13–15`、`configs/prereg/`（v2.1–v2.6）、human_decisions.md（决策 1–10）。
> 本签off只写决策文档；不改 `src/**`、`reports/runs/**`、已冻结判据、数据或论文；不写代码、不跑实验。

---

## 1. P5 条件清单逐项核对

| # | 条件（源自 final_boundary_study_signoff §5 / m4_target_adjustment §5） | 状态 | 证据 |
|---|---|---|---|
| S1 | clean run 数据哈希绑定 | ✅ 闭环 | `reports/data_hash_binding_erratum.json`（7 clean run 绑定 `f910f1f1…a894a` + commit） |
| S2 | v2.3 sha 回填前后注记 | ✅ 闭环 | `reports/data/s2_hash_annotation.md`；manifest/acceptance 已同步 `e44c6acb…` 并保留旧值 `5200940c…`；meta_review 确认 |
| S3 | runs_index 更新 | ✅ 闭环 | 26 run（旧 19 superseded、新权威），engineer_status §13.4 |
| S4 | 措辞精度（"接近但未超过控制 + dual 坍塌"） | ✅ 达标 | main.tex line 60–62 "approaches but does not exceed the mismatched/zero controls, while correctness collapses" |
| S5 | 单信号 + exploratory 强度边界 | ✅ 达标 | 全文 exploratory、8 族<24、`transfer_broken` 单信号披露 |
| 6 | kd 三 seed 数值入稿、PENDING 清零 | ✅ | main.tex §5.x 表（6.388/6.479/7.211 等）；notes.md line 28 "PENDING 已清零" |
| 7 | 数据修复披露（前后对照） | ✅ | main.tex 摘要 + §datafix（旧 1.93–2.12/broken=false ↔ 新 6.90–8.54/broken=true） |
| 8 | real=0 受阻披露（含 SciTSR 不适配） | ✅ | main.tex §real（line 374–392）、notes.md |
| 9 | v2.4 锚点探索性判读（exploratory_disclosure） | ⚠️ **结果已产出、判读已定，论文数值待补入** | engineer_status §15（SQuAD 两 run、判 `exploratory_disclosure`）；但 main.tex line 380 仍写 "any future external anchor evidence"、notes.md line 21/114 标"锚点数值待补" |
| 10 | 署名 Zhang Xuein <zxm0813@gmail.com> | ✅ | main.tex line 36 |
| 11 | 引用已实际核验（无 PLACEHOLDER） | ✅ | main.tex 注释 line 28–30 "no [PLACEHOLDER] references remain"；KV-Lingo/CacheLink 有真实作者/arXiv ID/doi |
| 12 | 贡献清单（1 撤回/2 撤回/3 withheld） | ✅ | main.tex 贡献段与结论 |
| 13 | venue = TMLR | ✅ | human_decisions.md 决策 5 |

**唯一未完成项**：第 9 项的**论文锚点数值补入**——这是写作者正在做的工作（用户已说明）。审稿侧、证据侧、冻结判据侧均已就绪。

---

## 2. P5 决议：附条件最终签off（Conditional Final Sign-off）

> **裁定：批准 P5，进入"投递就绪（ready-to-submit）"状态；设一个唯一收尾门槛——写作者把 SQuAD 锚点探索性结果补入论文 + 审稿人出 P5 compliance note 确认后，即可由真实 PI 在 TMLR 正式提交。** 本签off不构成"忽略锚点缺漏直接投稿"的许可。

- 所有科学结论、贡献状态、venue、署名、引用、S1–S5 均已就绪且经核对达标；
- 唯一残余是论文层面的锚点数值补入（写作者进行中）与相应一致性复核——这是**机械性收尾**，不改变任何科学结论，故不重新触发阶段裁决；
- 锚点结果已由审稿/工程侧判为 `exploratory_disclosure`（affine 坍塌方向复现、kd 对照未复现、EM 触底、单 seed/240 例），论文补入时须按此定性，不得改写为"强化跨数据源普适性"。

---

## 3. 论文最终定位与投稿主张边界

- **定位**：empirical / boundary study，失败边界 + 数据泄漏教训的负面/实证研究（TMLR，modest contribution）。
- **贡献状态（不可变）**：贡献(1) 撤回、贡献(2) 撤回、贡献(3) withheld；P2/P3/P4 永久放弃；AI 生成集提案已撤回（v2.6 not-activated）、无遗留产物。
- **可主张**：①可复现的数据审计方法论（重建后方向反转的前后对照，SHA 固定）；②干净数据上 affine 迁移失败边界（情形 C：dual 坍塌、transfer_broken=true）；③kd 保持效用但仍有 exploratory 非零 gap；④SQuAD 锚点的**有限、探索性**标准 QA 观察（exploratory_disclosure）。
- **禁止主张**：跨数据源普适性、真实文档外部效度已验证、任何已撤回贡献的恢复、方法增益、"strong significance"；所有 clean 结果与锚点均标 exploratory（8 族<24）。

---

## 4. 给写作者的 TMLR 投稿指令

### 4.1 必须补入的锚点内容（当前唯一缺项）
1. SQuAD dev-v2.0（CC BY-SA 4.0，仅评测/不改写/不发布衍生）两臂结果：`anchor_squad_affine_seed0` Self EM/F1 0.000/0.1975 → Joint 0.000/0.0051；`anchor_squad_kd_seed0` Joint 0.000/0.0014（engineer_status §15）。
2. 按 v2.4 三情形**定性为 `exploratory_disclosure`**：affine 坍塌方向复现，但 kd 对照未复现、EM 全臂触底（base 0.6B 未针对 SQuAD 微调）、仅 seed0/240 例——**不得**判 `reinforce_external_validity` 或 `narrow_scope`，不得反转叙事。
3. 明确：锚点仅有限标准 QA 域观察，不替代真实反事实文档、不恢复贡献、不与合成 test 混算、不重算冻结 CI。
4. 删除/改写 line 380 的 "any future external anchor evidence" 这类"锚点尚未产出"的过时表述，改为如实报告已完成锚点。
5. 补 SQuAD 引用（Rajpurkar et al., EMNLP 2016 doi:10.18653/v1/D16-1264；Rajpurkar & Jia et al., ACL 2018 doi:10.18653/v1/P18-2124），注明 SQuAD 2.0 dev、CC BY-SA 4.0、仅评测。

### 4.2 TMLR cover letter 要点（按 TMLR 政策，不得夸大）
- **普适贡献定位**：强调"可复现的数据审计方法论"——数据缺陷（退化对、跨 split 泄漏、模板骨架重合、bootstrap 簇退化）如何制造虚假显著发现，修复后结论反转；这是 TMLR scope 中"揭示方法强弱点的实验研究 / 复现性研究"的直接契合点，避免被判 audience too narrow。
- **诚实披露 modest 贡献与限制**：明示贡献(1)(2) 撤回、贡献(3) withheld、单等深对、合成域、real=0、exploratory 统计、SQuAD 锚点有限——TMLR 验收标准明确"modest contribution acceptable"，诚实披露优于夸大。
- **Reproducibility Certification 适用性**：说明本研究以固定 SHA（`f910f1f1…a894a`）、commit 链（458de18→efc3ba3→6413ba0→…）、预注册（v2.1–v2.5）实现完全可复现，符合 TMLR Reproducibility 精神；该认证由编辑决定，投稿时如实主张适用性即可，不保证获得。
- **原创性声明**：说明本稿非会议论文扩写、为原创（TMLR 不接受扩写版）；署名 Zhang Xuein；确认所有作者知情同意（单作者）。
- 按 TMLR 要求提供 3–5 位 action editor / reviewer 建议、关键词、≤200 词摘要、cover letter（PDF/纯文本）。

---

## 5. 给审稿人的最后合规意见请求

在写作者补入锚点后，请审稿人做**一次最终一致性核验**并出 **P5 compliance note**，重点：
1. 锚点数值与 engineer_status §15 / `anchor_eval_summary.json` 一致，定性严格为 `exploratory_disclosure`（未强化、未反转、未混算）；
2. 论文贡献表述与 §3 边界逐条一致（无已撤回贡献恢复、无跨源普适/真实文档验证主张）；
3. S1–S5、引用、署名、venue、数据修复/real=0 披露无回归；
4. v2.1–v2.6 冻结文件未被回写；AI 生成集无遗留产物。
该 note 是正式提交的最后一道合规确认；审阅通过后即可由真实 PI 提交。

---

## 6. 投稿前人工最终检查清单（真实 PI 确认）

1. **署名与邮箱**：Zhang Xuein <zxm0813@gmail.com>——确认邮箱有效且愿意公开。
2. **TMLR 提交**：真实 PI 本人用 OpenReview 账号提交（agent 不代为提交）；确认提交系统与作者配额（TMLR Generalized Harmonic Quota，单作者通常充裕）。
3. **版权/许可声明**：确认合成数据集 CC0、SQuAD 仅评测不发布衍生、KV-Lingo/CacheLink 引用许可合规；确认接受 TMLR 的 CC-BY 出版许可。
4. **cover letter 与 AE/reviewer 建议**：确认真实 PI 认可 §4.2 的 cover letter 要点与推荐人名单。
5. **最终稿件版本**：确认锚点已补入、P5 compliance note 已出、main.tex 编译无误、图表占位符按 TMLR 要求处理（当前图仍为 textual placeholder，TMLR 允许投稿时说明，接受后补齐）。

**仍需延后的事项**：无——P2/P3/P4 永久放弃，AI 生成集已撤回，venue 已定。唯一人工动作是上述检查 + 正式提交。

---

## 7. 结论

- **P5：附条件最终签off（批准，进入 ready-to-submit）**。唯一收尾：写作者补 SQuAD 锚点探索性结果 + 审稿人出 P5 compliance note；二者为机械性收尾，不改变科学结论。
- **投稿边界**：TMLR empirical/boundary study；贡献(1)(2) 撤回、贡献(3) withheld；情形 C 探索性；SQuAD 锚点 exploratory_disclosure；禁止跨源普适/真实文档验证主张。
- **人工检查**：署名邮箱、TMLR 账号提交、版权/许可声明、cover letter、最终稿件——确认后由真实 PI 正式提交；无延后事项。

**签署：PI / 课题组长（P5 最终签off · 2026-11-23）**

# 论文审稿人 B 终审：方法与实验可信度（arXiv 投稿包 `papers/readkv_v2_arxiv`）

- 角色：Paper Reviewer B（方法 / 实验可复现性、统计口径、图表—结论一致性）。
- 日期：2026-11-23。审阅性质：**只读终审**；未改论文 / 代码 / 数据 / 判据 / 运行产物。
- 审阅对象：`papers/readkv_v2_arxiv/{main.tex,references.bib,README.md,arxiv_conversion_notes.md}`；对照 `papers/readkv_v2_draft/{main.tex,notes.md}`。
- 冻结依据：`reports/{bootstrap_summary.json,anchor_eval_summary.json,consistency_report.json,runs_index.json}`；`reports/data/data_fix_report.md`、`acceptance_checks.json`；`docs/decisions/{research_scope_update.md,final_boundary_study_signoff.md}`；`configs/prereg/{stats_convention_v2.3.yaml,external_validity_v2.4.yaml}`、`docs/protocol.md`；审计报告 `final_boundary_audit.md`、`code_review_final.md`、`senior_engineer_final.md`、`engineer_anchor_audit.md`。
- 方法：逐项交叉比对文件—行号与冻结产物；所有数字**不重算**，只核对其与权威 JSON 的逐字一致性；bib 键用 grep 全量解析。

---

## 0. 总体裁决

> **P5 方法 / 统计可信度：CONDITIONAL GO（放行至 ready-to-submit，附 1 项投递前必须修正的主要项 + 3 项次要收尾）。** 不给无条件 GO。

- 任务指定的 6 个审查重点中，**R1 闭合、E_CF 口径、SQuAD 锚点、数据修复对照、bib/引用、arXiv 格式可复现性 6 项均通过核验**；论文正文数值与 `bootstrap_summary.json` / `anchor_eval_summary.json` **逐字一致**，无统计口径误用、无 mock 混入、无封存 test / P2/P3/P4/G1 产物泄漏。
- 但有 **1 项主要问题（M1）**：论文声称各臂"matched（含 trainable parameter count / training steps / tuning budget）"，却未披露 affine（0 参数、0 训练）与 kd_only（7.34M 参数、8 epoch）的实际**预算不对等**——而 `research_scope_update.md:86` 把"预算不对等"列为**强制披露清单**。这是内部自相矛盾 + 强制披露缺失，须在投递前修正；不推翻负面 / 边界结论，故不列阻塞。
- **无阻塞级风险**：未发现方向推翻、诚信问题、判据篡改、zero-re-prefill 违规、`P>0.05` 当等效、封存 test 评测或贡献升格。与 `final_boundary_audit.md` 的 CONDITIONAL GO 一致。

---

## 1. 六个审查重点逐项核验

### 1.1 R1 是否闭合 —— 通过（闭合）

三张报告 E_CF 的表均**并列** template-family 主 CI（8 族 exploratory）与 pair-level sensitivity，且明确主次，与 `bootstrap_summary.json` 逐字一致：

| 表 | 位置 | 核验 |
|---|---|---|
| `tab:cleanmvp` | `main.tex:504–530`（表体 525–527） | affine seed0 `6.900 [3.564,10.100]/[5.496,8.321]`、seed1 `8.159 [4.357,11.584]/[6.648,9.701]`、seed2 `8.540 [5.326,11.610]/[7.046,10.051]` —— 与 bootstrap_summary `runs/p1_clean_mvp_seed{0,1,2}.arms.joint` 完全一致 ✓ |
| `tab:cleankd` | `main.tex:605–628`（表体 623–625） | kd seed0 `6.388 [3.653,8.814]/[5.340,7.400]`、seed1 `6.479 [3.899,8.798]/[5.431,7.529]`、seed2 `7.210 [4.417,9.799]/[6.074,8.331]` —— 与 `runs/p1_kd_clean_mvp_seed{0,1,2}` 完全一致 ✓ |
| `tab:reversal` | `main.tex:549–573`（566 行） | 三 seed 主 CI / 敏感性 CI 并列给出，旧侧标 n/a（degenerate pair-level bootstrap）✓ |

- 口径陈述正确：`main.tex:512–514`「template_family CI is the main CI; the pair-level CI is reported alongside and never alone」；`main.tex:456–459` 在统计纪律节重申；表头/表注标明「primary (template_family) / sensitivity (pair-level)」「n_clusters=8、exploratory=true」。较窄 pair-level **未被当作唯一 95% CI**。`v2.3 forbidden_after_freeze` 的"只报 pair-level"禁令未触发。
- **转换说明中的微小差异如实处理**：`arxiv_conversion_notes.md:55–65` 明确记录 notes.md / signoff 中 pair-level 数字（affine seed0 `[5.499,8.313]`、kd seed0 `[5.360,7.400]`、seed1 `[5.419,7.539]`、seed2 `7.211/[6.078,8.322]`）与 `bootstrap_summary.json` 的差异，声明"不重算、不静默调和、以 bootstrap_summary + 最新 draft 为准"，并说明元审查旧主 CI（如 kd seed1 `[3.883,8.773]`）用 bootstrap_seed=0 复跑、非本包采用值。处理透明，两套下界均 >0，不影响任何方向性结论。核验：这些差异确在 `metrics.json`（如 `p1_clean_mvp_seed0/metrics.json:186`=8.3134）与历史裁决文档中存在，转抄选择有据。✓

### 1.2 E_CF 定义 / τ / 阈值 / flip 排除 / 联合报告 / verdict 分离 —— 通过

- `main.tex:420–428`：`E_CF=|D_trans−D_self|`、归一化 `{...}/(|D_self|+τ)`、**τ=1.0**，与 `docs/protocol.md:118–125` 及 `external_validity_v2.4.yaml:66` 一致 ✓。
- `main.tex:429–441`：`E_CF` 非质量度量的说明；与 `dual_correct`、`flip_consistency`（Self 有效子集 **|D_self|≥0.1**，见 433 行）、`coverage`、`info_attribution` 联合报告；说明 per-pair `info_gap` 未设、报告聚合 `info_attribution`；`transfer_broken` 正交标注。与 v2.4 `:66–67` 和 protocol §4.1/§4.3 一致 ✓。
- flip 排除 F5+F6、分母 398：`main.tex:237–240`、`296–297`；与 `stats_convention_v2.3.yaml:23–31`（`excludes:[F5,F6]`、`recomputed_value:398`）及数据修复报告一致 ✓。
- 主终点与统计纪律 `main.tex:446–459`：成对 E_CF 差、template-family 簇级 paired bootstrap（10,000 resamples、95% CI）+ pair-level sensitivity、`primary_baseline=kd_only`、CI 上界 <0、≥3 seed、Holm、`P>0.05` 不作等效、主终点 unevaluated ✓。
- 机器 verdict 与 transfer_broken 分离 `main.tex:630–637`：`distortion_exists`（quality_pass 仅指数据质量门）与 `transfer_broken=true` 回答不同问题，双字段披露 ✓。

### 1.3 SQuAD 锚点 —— 通过

- EM 全 0 / F1 可区分的解释 `main.tex:652–653,671–674`：EM 触底因 base 0.6B 未 SQuAD-tuned，与 `engineer_anchor_audit.md:57–59`、`senior_engineer_final.md:41–46`（真 hook、可读 pred、F1 分度、非实现 bug）一致 ✓。数值 Self `0.000/0.1975`、affine Joint F1 `0.0051`（2.6%，drop 0.1924）、kd `0.0014`（0.7%，drop 0.1961）与 `anchor_eval_summary.json:28–46,52–53` 逐字一致 ✓。
- 三情形 `exploratory_disclosure` 引用正确 `main.tex:644–679`：affine 失败方向复现、kd 保持 utility 对照**未**复现、EM 全臂触底、单 seed 240 例 → 混合判据；与 `external_validity_v2.4.yaml:98–114`、`anchor_eval_summary.json:49–59` 一致 ✓。
- 锚点不并入合成 CI `main.tex:678`：明确 "not pooled with the synthetic test"；`bootstrap_summary.json` 中两锚点 `arms={}, protocol=v1.0, stats=n/a`，`consistency_report.json` 标 `anchor_run=true`，未混算 ✓。

### 1.4 数据修复前后对照 + zero-re-prefill / provenance —— 通过

- `tab:datafix`（`main.tex:263–283`）：退化 18→0、逐字泄漏 ≥15→0、实体重叠 8 姓名→0、flip 分母 394→398、SHA `f910f1f1…a894a`（旧 `6058fd6d…d1887`）、基础结构/族 8/40→24/56 —— 与 `data_fix_report.md:12–19,62–79` 逐项一致 ✓。
- zero-re-prefill / 臂边界 `main.tex:353–397`（Table `tab:arms`、Figure 3）：Joint 唯一可部署，Self/Identity/K-only/V-only/Oracle 离线；前向 hook 断言；E0 复验 `main.tex:490–499`（cosine 1.0、KL 0、EM 0.975、2.2e-16）与 `senior_engineer_final.md:58–67`、`consistency_report.json`（7 clean run ok/traceable=true）一致 ✓。
- 7 clean run `data_sha256=f910f1f1…a894a` 见 `runs_index.json:506–629`，与论文 Data Availability `main.tex:865–878` 一致 ✓。

### 1.5 bib 条目与引用键 / N1–N9 / SQuAD DOI / N9b —— 通过（附次要核验提示）

- 正文全部 `\citep/\citet` 键（grep 22 处）：`kapoor2023, kvlingo, cachelink, heo2026, n1–n9b, contrastsets, kaushik2020, acc_evidence, squad16, squad18` —— 全部在 `references.bib`（19 条）中解析 ✓。
- N1–N9 均为 `@misc` + `note={arXiv preprint arXiv:...}` + year，**无编造 venue** ✓；`references.bib:168–173` 的 `n9b` 带「Author list not independently verified」note ✓；SQuAD DOI `10.18653/v1/D16-1264` / `10.18653/v1/P18-2124` 正确（`references.bib:84,93`）✓。
- 次要提示（见 R3）：`arxiv_conversion_notes.md:95–97` 与 `notes.md:148–155` 自承 N1–N9 仅摘要级核验、章节级细节未读全文；Related Work 中若把章节级描述当作已核实事实，应按协议 §9 投递前全文核验或在 cover letter 说明。

### 1.6 arXiv 格式可复现性 —— 通过

- `main.tex:9–19` 仅用 arXiv-safe 标准包，**无本地 .cls/.sty、无 \input、无 \includegraphics**；图 1–3 为 `fbox/parbox` 文本示意图，自包含 ✓。
- README 编译序列 `pdflatex → bibtex → pdflatex ×2`（`README.md:17–29`）正确 ✓。
- 无 P2/P3/P4/G1/封存 test 产物混入：论文仅在"取消 / 未执行"语境提及（`main.tex:639–642,845,818–819`），无机制 / 方法数值；`senior_engineer_final.md:131–139`、`code_review_final.md:74–92` 经 git / run 清单双重确认无越界 ✓。

---

## 2. 问题清单

### 阻塞（Blocking）
**无。** 未发现方向推翻、诚信 / 判据篡改、zero-re-prefill 违规、统计口径误用或封存 test 泄漏。

### 主要（Major，投递前必须关闭）

**M1. 预算不对等的强制披露缺失 + "matched" 表述内部矛盾**
- 位置：`main.tex:471–474`：「The design requirement is matched calibration pairs, dtype/kernel, forward budget, **trainable parameter count, training steps, and tuning budget across arms**. In the clean-data results the mapping arm is a **zero-trainable-parameter** affine mapper …; the **matched** kd_only control is reported in Section 4.6.」
- 问题：(a) 文本把"trainable parameter count / training steps / tuning budget"列为跨臂 matched 的设计要求，但同段紧接声明 affine 为 0 可训练参数、closed-form ridge（等价于 0 训练步），而 kd_only 实际为 7.34M 参数 / 8 epoch（`engineer_anchor_audit.md:58`、`current_task_review.md` L49：7340032 参数 / train 8ep）——两者在这些轴上**并不 matched**，文本自相矛盾；(b) `research_scope_update.md:86` 把"预算不对等"列入**强制诚实披露清单**，正文未披露该不对等。这是以统计 / 公平性诚实为卖点的负面研究，审稿人可逐条击穿。
- 影响：不改变 affine 失败边界 / kd 情形 C 的定性（无正向方法主张、主终点未评估），故不列阻塞；但属投递前必须修正。
- 建议（写作者，仅改论文）：在 §4.6（Model pairs and baselines）或 §4.7 把该句改为如实表述——例如「The arms are matched on calibration pairs, dtype/kernel and forward budget; they are **not** matched on trainable parameter count or training steps (affine: 0 trainable parameters, closed-form ridge, 0 epochs; kd_only: 7.34M parameters, 8 epochs) — a budget asymmetry disclosed here per the frozen scope.」不要删除披露，也不要把"matched"泛化到参数 / 步数。

### 次要（Minor，收尾项）

- **m1. 转换说明数值归属微误**：`arxiv_conversion_notes.md:55–57` 把 affine seed0 pair-level `[5.499,8.313]` 归于"notes.md 与 final_boundary_study_signoff.md"，但 `notes.md:48` 实际记录的是 `[5.496,8.321]`（bootstrap_summary 值）；`[5.499,8.313]` 实出自 `clean_data_reversal_ruling.md:16` / `README.md:167` / `engineer_status.md:284` / `final_boundary_audit.md:105` 对旧稿的引用。数字本身不影响论文正文，但建议把归属改为"旧提交稿 / 历史裁决文档"，保持留痕准确。
- **m2. 8 族 vs 56 族未桥接**：`main.tex:276` 报告重建后 56 族 / 24 结构，`main.tex:331,696,762` 又报告 clean CIs 仅 8 族 exploratory；`research_scope_update.md:120` 明确要求"需在论文解释"。`data_fix_report.md:72` 有解释（val split 仅用 8 个 SEEN 族，新 16 结构专供 test/probe），但论文正文未连起这条因果。建议在 §Data 或 §Limitations 加一句：val 60 对仅覆盖 8 个 template_family，故 clean CIs 为 8 族 exploratory，即使全库有 56 族。
- **m3. N1–N9 章节级细节核验（§9）未闭环**：`arxiv_conversion_notes.md:95–97`、`notes.md:148–155` 自承仅摘要级核验；`final_boundary_audit.md` R2 亦列此项。Related Work 中关于 N2「eight substitute-cache methods remain at the no-information baseline」、N3「value-reuse bias exceeds key-reuse bias」、CacheLink「four-arm K/V source-swap diagnostic」、N7「preregistered equivalence test」等章节级陈述，投递前应由真实 PI / 审稿人全文核验，或降级为摘要级措辞并在 cover letter 说明。不阻塞（审计已判 R2 非阻塞）。

- 附记（非本包问题，供 PI 知悉）：`final_boundary_audit.md` R5 指出冻结文档仍写"26 run"，实际 28（含 2 锚点）。该陈旧计数在 `final_boundary_study_signoff.md:48`、`p5_final_signoff` 中，不在 arXiv 包内；arXiv 正文未引用 run 计数，无科学影响。

---

## 3. 与冻结判据 / 项目硬约束的一致性

- zero-re-prefill：Joint 唯一可部署、hook 真校验、Oracle 离线，符合 §2 ✓。
- 判据先写后跑：τ=1.0、self_threshold=0.1、flip 排除 F5+F6、δ=0.5（且 δ 复核永久取消）均未被改动；无按测试结果调参 ✓。
- 主终点 = 封存测试成对 E_CF 差（簇级 paired bootstrap、CI 上界<0）——**明示未评估**；未把 p>0.05 当等效 ✓。
- 联合报告 dual/flip/coverage/info_gap 在两张 E_CF 表中齐备 ✓。
- 贡献表述门槛（protocol §10）：贡献(1)(2) withdrawn、(3) withheld，无正向贡献措辞、无跨模型 / 真实世界 / 强显著主张 ✓。
- Mock 非证据：`main.tex:783–784` 明示 mock/smoke 非证据；正文无 mock 数字 ✓。

---

## 4. 给各角色的处置建议

- **给写作者**：仅改 M1（预算不对等如实披露，去掉跨臂 matched 的参数 / 步数表述）；可选处理 m2（8 族桥接）。不得改任何冻结数字 / CI。
- **给科学家**：方法描述缺口已在 M1 / m2 覆盖；`CF-RCT`（`main.tex:399–415`）明确标为"proposed design only, never validated"，损失项与 δ 的处置表述正确，无待补方法描述。
- **给 PI**：P5 方法 / 统计可信度**可放行至 ready-to-submit**，条件是 M1 修正 + m1–m3 收尾venue 指定后由真实 PI 投递；本审阅不代替 PI 的 venue / 署名 / 时机决策，也不构成"忽略 M1 直接投递"的许可。

---

## 5. 结论

任务指定的 6 项审查重点**全部通过**：R1 已闭合且数值与 `bootstrap_summary.json` 逐字一致、跨源差异如实记录；E_CF 口径 / τ / 阈值 / flip 排除 / 联合报告 / verdict 分离表述正确；SQuAD 锚点 EM-F1 归因与 `exploratory_disclosure` 与工程 / 高工审计一致且未并表；数据修复对照与 zero-re-prefill / provenance 可信；bib 键全解析、N1–N9 仅 arXiv+年份、SQuAD DOI 正确、N9b 已标注；arXiv 源自包含、编译序列正确、无越界产物。

**唯一的投递前主要门槛为 M1（预算不对等强制披露缺失 + "matched" 矛盾）**，另有 3 项次要收尾。**P5 方法 / 统计可信度：CONDITIONAL GO（放行至 ready-to-submit）。**

**签署：Paper Reviewer B（方法与实验可信度终审）· 2026-11-23。**

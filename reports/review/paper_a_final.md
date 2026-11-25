# 论文终审意见 — Paper Reviewer A（叙事与证据强度）

- 角色：paper-reviewer-a（主张—证据一致性、负面结果披露、新颖性与措辞门槛）。
- 日期：2026-11-23。
- 审阅方式：**一手只读**。逐行通读 arXiv 提交版（`papers/readkv_v2_arxiv/{main.tex,references.bib,README.md,arxiv_conversion_notes.md}`）与草稿版（`papers/readkv_v2_draft/{main.tex,notes.md}`），对照冻结裁决与阶段审计（`research_scope_update.md`、`final_boundary_study_signoff.md`、`ai_dataset_final_ruling.md`、`human_decisions.md`、`p5_final_signoff.md`、`final_boundary_audit.md`、`current_task_meta_review.md`、`third_round_online_addendum.md`、`code_review_final.md`、`senior_engineer_final.md`），并把论文全部关键数值与冻结产物 `reports/bootstrap_summary.json`、`reports/anchor_eval_summary.json`、`reports/runs/p1_clean_mvp_seed{0,1,2}/metrics.json`、`p1_kd_clean_mvp_seed0/metrics.json` 做独立比对。
- **未改任何文件**（含论文、代码、数据、判据、运行产物）；统计全部读自冻结产物，未重算。

---

## 0. 总判定

> **CONDITIONAL GO（实质接近 GO）——P5 可放行；条件仅为 4 项次要（minor）收尾，均不触及方向、冻结判据或核心证据。无阻塞（Blocking）项，无主要（Major）项。**

一句话结论：arXiv 提交版把叙事严格收束为「失败边界 + 数据泄漏教训的负面/实证/数据审计研究」，所有已撤回贡献、机制定位、方法增益措辞均已清除；主张—证据一致、边界披露充分、新颖性限定到「具体预注册翻转案例 + 成对 E_CF 审计轨迹」，与 `docs/protocol.md §10` 门槛及 `research_scope_update.md` 终裁逐条吻合。与冻结 signoff（CONDITIONAL GO / ready-to-submit）一致，建议放行，但投递前应闭环下列次要项。

---

## 1. 逐项审查结论（对照五项重点）

### 1.1 叙事定位：负面 / 实证 / 数据审计，无正向残留 —— 通过

- 标题、摘要、引言、结论一致定性为「negative / empirical data-audit / failure-boundary / audit study」（`main.tex:21-22,32-33,68-69,803`）。
- 全文对 `novel / first / improve / mechanism / general` 的 44 处命中经逐条核查，**全部处于否定、撤回或规避语境**：`both are withdrawn`（:65）、`not a method or mechanism paper`（:68）、`We no longer claim to identify a general counterfactual gap, to localize a mechanism, or to improve transfer`（:128-129）、`our contribution is not a general distinction, a mechanism-layer first, or a new audit method`（:169-172）、`We make no claim of ... a mechanism-layer first, or any method improvement; nor do we claim a new audit method or general leakage lesson`（:813-816）。**未发现任何残留的正向贡献、机制定位或方法增益措辞。**
- 明确声明「Findings reported here (negative / empirical results, not positive contributions)」（:100-101）、`None of these is a positive contribution in the sense of the frozen contribution criteria`（:127）、贡献(1)(2) withdrawn / (3) withheld、P2/P3/P4 永久取消、主终点未评估（:128-132, 639-642, 840-844）。
- §CF-RCT 仅作 "proposed design only, never validated"（:399-415），δ 复核永久取消、不报任何 δ 相关结果（:413-415）——与冻结裁决一致。

### 1.2 主张—证据一致性：全部在冻结产物支持范围内 —— 通过

独立核对（详见第 3 节核对表）：

- **前后翻转**：`1.93–2.12 → 6.90–8.54`、dual `0.617–0.667 → 0.283–0.417`、`transfer_broken false → true`（:564-570）与 notes.md §1.3、冻结退出记录一致。
- **affine 三 seed 失败边界**：6.900 / 8.159 / 8.540，dual 0.417 / 0.283 / 0.383，flip 0.750 / 0.736 / 0.755，cov. 0.867 / 0.883 / 0.883，`transfer_broken=true`×3（:525-527）——与 `bootstrap_summary.json` 与三份 metrics.json 逐字一致。
- **kd 情形 C 探索性 gap**：6.388 / 6.479 / 7.210，dual 0.700 / 0.733 / 0.767（drop 0.117 / 0.167 / 0.017），`transfer_broken=false`×3（:623-625）——与 `bootstrap_summary.json` 一致；以 `bootstrap_summary.json` 的 7.210 为准（草稿 notes.md/final_boundary_study_signoff 的 7.211 为已披露的非权威舍入差异，见 `arxiv_conversion_notes.md:55-65`），选择正确。
- **SQuAD 锚点**：affine Joint F1 0.0051（2.6%，drop 0.1924）/ kd 0.0014（0.7%，drop 0.1961），Self EM/F1 0.000/0.1975、Joint EM 全 0，`exploratory_disclosure`（:652-679）——与 `anchor_eval_summary.json` 一致。
- **E_CF 接近但未超过控制**：seed0 joint 6.900 vs mismatch 8.383、zero 8.584、random 6.765；info attribution +1.483 / +1.684 / −0.135（:535-539）经 `metrics.json` 逐字核对无误。论文限定为「mismatched and zero-cache controls」并披露「mixed（2 正 1 负）」归因，**未写「达到/相当于无信息水平」**，S4 达标。
- **强制披露全集均在位**：sealed test 未评、主终点未评估、real=0、单合成等深对、合成域、8 族 exploratory、单信号 dual-drop、机器 verdict 与 `transfer_broken` 口径分离、`P>0.05` 不作等效、mock 非证据 —— 摘要（:31-50）与 Adverse/Limitations/Status（:681-708, 748-785, 829-854）多处一致陈述。
- **双 CI 并列（原 R1 阻塞项）**：`tab:cleanmvp`、`tab:cleankd`、`tab:reversal` 三表均并列 `template_family` 主 CI（`n=8`, exploratory）与 pair-level 敏感性（:504-517, 605-628, 549-573），主次标注明确 —— 已闭环。
- **联合报告**：每张 E_CF 表含 dual / flip / coverage / `transfer_broken`，控制组 gap 以 `info_attribution` 披露（:429-441）——达标。

### 1.3 负面结果披露、相关工作区分、新颖性限定 —— 通过

- Adverse results 5 条 + Limitations 7 条（:681-708, 748-785）覆盖质量坍塌主导、单信号与混合控制、探索性强度、先验信号为数据伪影、外部效度未验证。**负面结果披露充分，无掩盖。**
- 相关工作逐项正面引用并区分：KV-Lingo / CacheLink / Heo（:138-150）、"Does Accuracy Equal Evidence?"（:179-182）、Contrast Sets / Kaushik（:174-178）、Kapoor-Narayanan（:78-82, 742-743）、N1–N9（:152-172）。明确 `We do not treat the utility/fidelity distinction as our invention`（:149-150）、`These works anticipate ... our contribution is not a general distinction, a mechanism-layer first, or a new audit method`（:168-172）。
- 新颖性严格限定为「a concrete preregistered before/after reversal case with a paired counterfactual E_CF audit trail on one synthetic benchmark」（:171-172, 740-742）；不声称一般泄漏教训、utility/fidelity 首创、评价框架首创。与 `research_scope_update.md §6`（:168）和 §10 门槛一致。

### 1.4 摘要 / 图表 / 封面信 / 引用披露 —— 基本通过（见次要项 M2/M3）

- **摘要 ≤200 词**：合规。包内记录 171 whitespace tokens（`README.md:45`）/ 191 rendered tokens（`notes.md:35`），两种口径均 <200；强制边界措辞全部保留（:40-50）。建议统一记录口径（见 M4）。
- **图表—结论一致**：图 1–3 为诚实标注的 text-only schematic（`main.tex:84-98, 242-252, 381-397`，caption 均注明 "schematic; text-only"）；无机制热图 / 方法消融 / 泛化成本图（对应结果已撤回或未跑，未伪造）。5 张数据表均逐字转抄冻结产物，表题与正文结论一致。
- **cover letter**：无独立文件；`notes.md:166` 草稿要点第①条即「不宣称正向贡献」，第④条列全撤回/withheld/未评估/未评测/real=0/单对/exploratory，定位正确。但 `p5_final_signoff.md:61` 的「普适贡献定位：强调可复现的数据审计方法论」存在措辞升级风险（见 M3）。
- **N9b BridgeKV 作者未核**：如实披露 —— `references.bib:168-173` 加 note「Author list not independently verified; cited as arXiv preprint only」且无 author 字段；`arxiv_conversion_notes.md:83-84`、`notes.md:155` 均注明；正文（:165）仅作 arXiv preprint 引用，无作者主张。**披露充分。**
- **章节级引用未全文核验**：在包级文档中如实披露（`arxiv_conversion_notes.md:95-97`、`notes.md:148,154`、`final_boundary_audit.md:88` 的 R2），冻结 signoff 判为非阻塞的投递前 §9 项。但正文对若干章节级细节以既定事实陈述（见 M2）。

### 1.5 v2.6 / real=0 / 冻结边界表述 —— 通过

- v2.6「evaluated and withdrawn (not activated)」「no `data/generated/`」「no human-seeded / model-generated dataset or result」在 `main.tex:316-321, 183-184, 780-784, 819, 846, 875-878` 六处一致；草稿 `notes.md §0.1` 同步删除 v2.6 结果表。**无 AI 数据结果残留，与 `ai_dataset_final_ruling.md` 一致。**
- M4 blocked / real=0 / SciTSR 语义不适配 / v2.5 无适用对象（:299-314, 756-760, 848, 851）——与 `final_boundary_study_signoff.md §2` 和 `ai_dataset_final_ruling.md` 一致。
- P2/P3/P4 永久取消、G1 未执行、封存 test 未碰、贡献不恢复（`main.tex:639-642, 843-844, 820-822`）——与 `human_decisions.md` 决策 8 和 `research_scope_update.md §1.3` 一致。

---

## 2. 分级问题清单

### 阻塞（Blocking）：**无**

未发现封存 test 读取、挑 seed、判据回改、mock 当证据、Oracle 信号泄漏进 Joint 推理图、零再预填充违规或已撤回贡献升格。

### 主要（Major）：**无**

### 次要（Minor）：

**M1 — 状态段措辞与最终冻结状态不一致（保守型，不伤证据，但应更新）**
- 位置：`papers/readkv_v2_arxiv/main.tex:856-859`；`README.md:55-58`。
- 问题：仍写「defers formal submission pending ... citation verification, and PI sign-off ... does not itself authorise submission」，与更新的冻结状态不符 —— `p5_final_signoff.md:32-38,48`（P5 附条件最终签off、ready-to-submit、venue=TMLR）、`final_boundary_audit.md:15`（CONDITIONAL GO→ready-to-submit）、`notes.md:162,163,175`（引用已核验、P5 已签off）均表明引用核验主体已完成、PI 已指定 venue。当前措辞引用的是更早的「暂缓」框架。
- 建议：把状态段改为反映最新冻结记录（P5 附条件 GO / ready-to-submit / TMLR / 真实 PI 经 OpenReview 自行提交）；至少把「citation verification ... pending」改为「§9 章节级全文口径复核为非阻塞投递前项」。若该版本用于实际投递，建议整段移除「submission deferred」字样。**不改任何数字或判据。**

**M2 — 相关工作章节级细节以既定事实陈述，未经全文核验（包级已如实披露）**
- 位置：`main.tex:143-145`（CacheLink "four-arm K/V source-swap diagnostic"）、`:158-159`（N3 "value-reuse bias exceeds key-reuse bias"）、`:165-167`（N7 "mismatched/zero/random cache controls with a preregistered equivalence test"）。
- 问题：`third_round_online_addendum.md:6` 与 `notes.md:148,154` 明示 N1–N9 仅核到标题/作者/摘要/日期，`current_task_meta_review.md:138` 与 `notes.md:141` 特别指出 CacheLink 四臂诊断属「章节级细节仅摘要级核验」；`arxiv_conversion_notes.md:95-97` 亦承认未在本次独立复核。上述句子未带保留语。
- 建议（投递前二选一，冻结 signoff 判为非阻塞）：① 按协议 §9 对这几条具体声明做一次全文口径核验后保持原文；或 ② 改为摘要级措辞（如 "its abstract reports a K/V source-swap diagnostic" / "reports value-reuse bias exceeding key-reuse"）。优先级最高为 CacheLink 四臂诊断（meta-review §3.5 点名）。**不新增文献、不编造出处。**

**M3 — 封面信「普适贡献定位」与论文自我限定存在措辞升级风险**
- 位置：`docs/decisions/p5_final_signoff.md:61`（§4.2 第 1 条「普适贡献定位：强调可复现的数据审计方法论 ... 避免被判 audience too narrow」）。决策文档我不可改，此处仅提示投递执行时的风险。
- 问题：论文 `main.tex:813-816` 明确 `nor do we claim a new audit method or general leakage lesson`；若封面信为「避免 audience too narrow」而把数据审计方法论升格为「通用/一般化审计方法贡献」，将与论文主体自述冲突，构成叙事越界。`notes.md:166` 的封面信草稿本身定位正确（第①条不宣称正向贡献），风险来自 signoff 的定位建议。
- 建议：撰写正式封面信时，把审计严格表述为「a concrete preregistered reversal case + paired E_CF audit trail on one synthetic benchmark」及 TMLR 语境下的「reproducibility / empirical boundary study」，**不得**写成新的通用审计方法或一般泄漏教训；以论文 :813-816 为封面措辞上限。真实 PI 对 audience 顾虑自行权衡，但不得因此升格主张。

**M4 — 两处口径记账 / 清晰度（轻微，可被审稿人提问，建议顺手处理）**
- (a) `main.tex:46,456-459` 用「8 template_family clusters」，而数据表 `tab:datafix:276` 报「24 / 56 structures / families」。二者并不矛盾（8 为干净 run 所用 60 对 val 子集中出现的 template_family 取值数，见 `senior_engineer_final.md §3.1`），但正文未点破。建议补一句说明，以免审稿人质疑「为何 56 族只做 8 簇」。**不改数值。**
- (b) 摘要字数记账不一：`README.md:45` 记 171 tokens，`notes.md:35` 记 191 tokens，均 <200 故合规；建议统一为一种计数口径并落账。另摘要 `:39` 的 "from ≈0.82" 与正文 `:105` 的 "≈0.78–0.90" 分别为 seed0 与跨 seed 范围，一致但可在摘要统一表述。

---

## 3. 关键数值独立核对表（读自冻结产物，未重算）

| 论文声明 | 论文位置 | 冻结产物值 | 结论 |
|---|---|---|---|
| affine joint E_CF 6.900 / 8.159 / 8.540，主 CI [3.564,10.100]/[4.357,11.584]/[5.326,11.610]，pair-level [5.496,8.321]/[6.648,9.701]/[7.046,10.051] | :525-527, :566 | `bootstrap_summary.json runs/p1_clean_mvp_seed0 joint: "6.900 [3.564, 10.100]" / "6.900 [5.496, 8.321]"`（其余 seed 同表） | ✓ 逐字一致 |
| kd joint 6.388 / 6.479 / 7.210，主 CI [3.653,8.814]/[3.899,8.798]/[4.417,9.799]，pair-level [5.340,7.400]/[5.431,7.529]/[6.074,8.331] | :592-595, :623-625 | `bootstrap_summary.json runs/p1_kd_clean_mvp_seed0 joint: "6.388 [3.653, 8.814]" / "6.388 [5.340, 7.400]"` | ✓ 逐字一致 |
| dual 坍塌 0.817→0.417；控制 mismatch 8.383 / zero 8.584 / random 6.765；info +1.483/+1.684/−0.135 | :525, :535-539 | `p1_clean_mvp_seed0/metrics.json`: self dual 0.817, joint dual 0.417, controls 8.3827/8.584/6.7648, attribution +1.483/+1.684/−0.135 | ✓ 逐字一致 |
| seed2 控制均高于 joint（8.540 < mismatch 9.432 / zero 9.684 / random 9.854） | :535（限定 seed0） | `p1_clean_mvp_seed2/metrics.json`: joint 8.540, controls 9.432/9.684/9.854 | ✓ 「未超过控制」成立 |
| SQuAD affine 0.0051(2.6%) / kd 0.0014(0.7%)，Self 0.1975，EM 全 0，exploratory_disclosure | :652-679 | `anchor_eval_summary.json`；`final_boundary_audit.md §3` 复核值 | ✓ 一致 |
| 数据缺陷：退化对 18→0、泄漏≥15→0、骨架 100%→∅、flip 394→398、SHA `6058…d1887 → f910…a894a` | :273-280 | `data_fix_report.md` / `acceptance_checks.json`（final_boundary_audit §1 S1/S2 实测 sha256 一致） | ✓ 一致 |
| v2.6 not-activated / 无 `data/generated/` | :316-321 等 | `ai_dataset_final_ruling.md`；`final_boundary_audit.md §5`（磁盘实测目录不存在） | ✓ 一致 |

---

## 4. 给写作者的可执行修改清单（逐条）

1. **[M1]** 更新 `main.tex:856-859` 与 `README.md:55-58` 的状态段，使之与 `p5_final_signoff.md`（P5 附条件 GO / ready-to-submit / TMLR）一致；删除或改写「citation verification pending / submission deferred」。
2. **[M2]** 投递前对 `main.tex:143-145,158-159,165-167` 的章节级引用细节做 §9 全文核验；若来不及，改为摘要级保留措辞（优先 CacheLink 四臂诊断）。不新增文献。
3. **[M3]** 撰写正式封面信时以 `main.tex:813-816` 为措辞上限：审计定位为「具体预注册翻转案例 + 成对 E_CF 审计轨迹 / 单合成基准」，不升格为通用审计方法或一般泄漏教训。
4. **[M4a]** 在 `main.tex` 指标/统计段补一句说明：8 个 template_family 簇来自干净 run 的 60 对 val 子集，区别于重建语料整体的 56 族（不改数值）。
5. **[M4b]** 统一摘要字数记账口径；核对摘要 `:39` 的 native dual 表述与正文范围表述的一致性。

> 以上全部为措辞/记账/核验收尾，**不涉及任何数字、E_CF 定义、τ、δ、flip 分母、统计口径或冻结判据的改动**。

---

## 5. 给 PI 的放行建议

> **CONDITIONAL GO — 建议 P5 放行。** 论文叙事与证据强度已达投稿标准：无阻塞、无主要项；贡献(1)(2) 撤回、(3) withheld、P2/P3/P4 永久取消、real=0、单合成对、exploratory、主终点未评估、封存 test 未评等边界全部在位且与冻结裁决逐条一致；M1–M4 为可在投递前机械闭环的次要项。与 `final_boundary_audit.md` 的 CONDITIONAL GO、`p5_final_signoff.md` 的附条件最终签off 结论一致。真实 PI 经 OpenReview 自行提交；M2（§9 全文核验）与 M3（封面信措辞上限）建议在真实 PI 提交前最终确认。

---

## 6. 给科学家的主张—证据缺口反馈

- 未发现主张超出证据的情形；无需科学家补充新实验或新机制说明。
- 唯一与「主张—证据」相关的是引用层而非科学层：M2 所列 3 处相关工作章节级细节目前仅有摘要级核验支撑，若无法完成全文核验，应把对应措辞降到摘要级，避免以既定事实陈述未核实细节。
- 负面/边界结论的证据强度上限已被论文如实标注（val-only、8 族 exploratory、单合成等深对、real=0、锚点 exploratory_disclosure），科学家无需也不会被要求放宽该上限。

---

**签署：paper-reviewer-a（叙事与证据强度终审 · 2026-11-23 · 一手只读，未修改任何文件）**

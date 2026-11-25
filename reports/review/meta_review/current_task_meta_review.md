# 对 research-advisor《当前任务独立审查报告》的元审查与重新审查

- 审查对象：`reports/review/research_advisor/current_task_review.md`（一轮 10:59；二轮 11:27 落盘）
- 审查日期：2026-11-23
- 审查方式：逐条核对报告引用与断言 → 对照 11:46 后的 PI 最终裁决与新 run 产物 → 对关键统计口径做只读复算 → 给出重新审查结论
- 说明：本文只评估“审查结论”本身，不替代 PI 裁决，不改任何代码/数据/冻结判据/运行产物/论文。

---

## 0. 结论摘要

### 0.1 对顾问结论的裁定

> **方向正确，但结论已过期，不能作为当前终审结论。**

- **成立**：原“utility-preserving 反事实失真 gap + V-消费机制定位”主线已被干净数据证伪；affine 三 seed 坍塌、旧正向信号源于数据缺陷、贡献(1)/(2) 应撤回、P2/P3 应取消——这些判断与 PI `clean_data_reversal_ruling.md` / `final_boundary_study_signoff.md` 一致。
- **过期**：报告写“clean kd_only seed1/2 未产出、A/B/C 择支待决、S1–S3 溯源未闭环、runs_index 未更新”；这些在 11:39–12:57 之间已被新产物/PI 裁决解决或改写。
- **过强**：报告把新负面结果称为“已确证/结果合理”，但当前证据是 **val-only、8 个 template_family、单 MVP 等深对、合成域、exploratory**；应表述为“内部探索性证据强到足以支持失败边界定位”，而不是确认性结论。
- **不够独立**：二轮结论主要是对 PI 裁决的“同意并确认”，没有独立复核 PI 的 C 类判读和 v2.3 统计口径；元审查补做了这项核查，发现一个报告未捕获的审计缺口（见 §3.1）。

### 0.2 重新审查后的结论

> **PIVOT 成立；失败边界研究可继续（CONDITIONAL GO）；现在投稿为 NO-GO/暂缓。**

- 原正向主线：**PIVOT（已由 PI 收口，元审查确认）**。
- 新定位“跨模型 KV 迁移失败边界 + 数据泄漏教训”：**CONDITIONAL GO**，条件是完成 §4 的审计/文档/措辞收尾。
- 投稿：**暂缓**。P5 的 8 项门槛尚未全部闭环；README 仍与最终裁决直接冲突。
- 贡献状态：贡献(1) 撤回、贡献(2) 撤回、贡献(3) withheld；kd 干净三 seed 的稳定 gap 只能作为**探索性观察**，不得恢复为正式贡献。

---

## 1. 顾问结论中成立、应保留的部分

1. **affine 干净数据坍塌是真实的，不是实现 bug。**
   - `p1_clean_mvp_seed{0,1,2}`：joint E_CF 6.900/8.159/8.540，dual 0.417/0.283/0.383（Self 0.817/0.900/0.783），三 seed `transfer_broken=true`。
   - 跑分代码 458de18..efc3ba3 逐字未变；Self/Identity 锚点更健康；K/V-only 近 Self、仅 Joint 坍塌——支持“迁移失败”而非“跑分实现坏了”。
   - 证据：`reports/review/clean_data_reversal_emergency_review.md`；`reports/runs/p1_clean_mvp_seed*/metrics.json`。

2. **旧正向信号确由数据缺陷造成。**
   - 18 个退化对、≥15 组跨 split 逐字泄漏（含 train↔test 整对）、实体全共享、模板骨架重合、簇退化为逐对 i.i.d.；修复后退化对 0、泄漏 0、实体重叠 0、flip 分母 398。
   - 证据：`reports/data/data_readiness_audit.md`、`reports/data/data_fix_report.md`、`reports/data/acceptance_checks.json`。

3. **PI 撤回贡献(1)/(2)、取消 P2/P3/P4、维持贡献(3) withheld 是正确的。**
   - 证据：`docs/decisions/clean_data_reversal_ruling.md`、`docs/decisions/final_boundary_study_signoff.md` §1.2/§4。

4. **相关工作约束成立。**
   - CacheLink（arXiv 2610.15509）已公开“重构保真≠接收端效用、K/V 功能重要性、四臂诊断、功能监督”；Heo et al.（2608.03893）已公开闭式 ridge 且部分对急剧退化；"Does Accuracy Equal Evidence?"（2608.01631）已公开压缩下的 answer-evidence gap；Contrast Sets（2004.02709）/Kaushik（1909.12434）已确立成对反事实评测；Kapoor & Narayanan（2207.07048）已确立泄漏危机的一般教训。
   - 元审查已独立核验 W1–W4（KV-Lingo / CacheLink / Heo et al. / "Does Accuracy Equal Evidence?"）的 arXiv 标题、作者、摘要与日期（访问 2026-11-23）；W5/W6/W14 沿用报告引用，本次未逐一抓取全文。本课题的新颖性只能限定为“具体预注册翻转案例 + 成对反事实 E_CF 框架 + 完整审计轨迹”，不能声称一般泄漏教训或机制层为首次。

5. **README 仍过期、S4/S5 措辞仍需修正。**
   - 这两点在最终裁决后仍然成立，且 README 问题比顾问报告写得更严重（见 §3.3）。

---

## 2. 报告中已过期或需要修正的断言

### E1｜“clean kd_only seed1/2 未产出、A/B/C 待决”——已过期

- 报告 §8.8（约 353–357 行）写“seed1/2 未产出”“仍待决”。
- 实际：`p1_kd_clean_mvp_seed1`（11:20）、`seed2`（11:39）均已落盘；PI 11:46 `final_boundary_study_signoff.md` 已确认 **情形 C**：
  - seed0：6.388 [5.360,7.400]，dual 0.700，drop 0.117，broken=false
  - seed1：6.479 [5.419,7.539]，dual 0.733，drop 0.167，broken=false
  - seed2：7.211 [6.078,8.322]，dual 0.767，drop 0.017，broken=false
- 结论：报告应把“待决”改为“已收口为 C；kd 稳定非零 gap 仅探索性观察，不恢复贡献(1)”。

### E2｜“S1–S3 溯源未闭环、runs_index 未更新”——大部分已过期

- **S1**：已由 `reports/data_hash_binding_erratum.json` 绑定 7 个 clean run 的数据 sha `f910f1f1…a894a`；`reports/engineer_status.md §14` 记录闭环。
- **S2**：`data/tasks/manifest.json` / `acceptance_checks.json` 现已同时记录回填前 `5200940c…` 与回填后 `e44c6acb…`，并注明 PI commit `6413ba0`；`stats_convention_v2_3_sha256` 已指向 `e44c6acb…`，不再是“未澄清的 sha 不一致”。
- **S3**：`reports/runs_index.json` 现有 **26** 项，包含 `e0_clean`、`p1_clean×3`、`p1_kd_clean×3`；`reports/consistency_report.json` 现有 **29** 项，上述 7 个 clean run 均 `ok=true/traceable=true`。
- 仍成立的部分：README 仍写“22 个 run”；`bootstrap_summary.json` 仍只有 26 项且**不含 kd_clean 三 seed**（见 §3.1）。

### E3｜“结果=合理/已确证”——表述过强

- 当前 clean 证据只评 **val**（`eval_splits=["val"]`），封存 test 从未评测；`p1_clean` 的 v2.3 主 CI 是 **8 个 template_family < 24**，报告自己标了 exploratory，却仍用“已确证”描述结果。
- `transfer_broken` 由 dual-drop 单信号触发；`joint_ecf_ge_control=false`（E_CF 仍低于错配/零控制）；info attribution seed0 为 2 正 1 负。
- 因此更准确的定性是：“**在已测 val、单 MVP 等深对、合成域、exploratory 口径下，affine 失败边界的内部证据强且三 seed 一致**”；不应写成确认性/可泛化结论。PI 最终裁决本身也要求 S5 披露单信号与 exploratory。

### E4｜“PIVOT + 新定位 CONDITIONAL GO”的时态需要更新

- 报告写“PIVOT（原主线）+ 新定位 CONDITIONAL GO（待择支）”；现在“待择支”已完成，结论应改为：
  - **PIVOT（原主线）— 已确认**；
  - **失败边界研究 — CONDITIONAL GO（待 S1–S5/文档/引用收尾）**；
  - **投稿 — 暂缓/NO-GO**，不是“可投的 CONDITIONAL GO”。

### E5｜test 16 簇 vs val 8 簇的表述精度

- 报告多处用“test 16 簇 < 24”作为主要限制；但当前所有 clean P1/kd 证据都在 **val（8 族）** 上，`test` 根本未评。
- 应把“当前证据的 8 族 exploratory”放在主句；“test 16 族也不足 24”作为未来封存测试的前置风险，而不是当前结果的直接限制。

### E6｜独立性不足

- 二轮结论以 PI 裁决为锚点，写“同意并确认”，但没有独立回答：
  - PI 把 kd 判为 C 是否在 v2.3 簇级口径下仍成立？
  - 最终裁决的 C 表使用 pair-level CI，是否与 v2.3 主口径一致？
  - 失败边界论文的“负面结果”定位是否会被审稿人视为“方法学不足”而非有效 negative result？
- 元审查对第一点做了只读复算（§3.1）；后两点仍应提交 PI/审稿人，而不是由顾问自行确认。

---

## 3. 报告未捕获或低估的问题（元审查新增）

### 3.1【主要】kd_clean 三 seed 已进 consistency，但未进 v2.3 bootstrap 汇总

- `reports/bootstrap_summary.json`：26 个 run，**不含** `p1_kd_clean_mvp_seed{0,1,2}`。
- `reports/consistency_report.json`：29 个 run，**包含** kd_clean 三 seed，且 `ok=true`。
- `final_boundary_study_signoff.md` §1.1 的 kd 表使用 **pair-level CI**（6.388 [5.360,7.400] 等），不是 v2.3 的 `template_family` 主 CI。
- 元审查用 `scripts/bootstrap_ci_report.py::summarize_run` 做只读复算（n_resamples=10000，seed=0）：
  - seed0：6.388 **[3.653, 8.814]**，8 族，exploratory=true
  - seed1：6.479 **[3.883, 8.773]**，8 族，exploratory=true
  - seed2：7.210 **[4.362, 9.757]**，8 族，exploratory=true
- 解读：**方向仍支持 C（下界 >0），不是推翻 PI 的 C 判读**；但“审计产物”和“论文表格”应使用 v2.3 簇级 CI，或明确标注 pair-level，不能在同一份收口材料里混用口径。这是报告未捕获的审计一致性缺口，属于投稿前必须修复项。

### 3.2【主要】最终裁决的 C 表与 v2.3 统计口径存在混用

- `final_boundary_study_signoff.md` §1.1 表头是 `E_CF [CI]`，给的是 pair-level CI；同文件 §2 S5 又要求“exploratory（8 族<24）披露”。
- 这不算数据错误，但会让审稿人问：“为什么 C 类判读用 pair-level CI，而 affine 的 v2.3 主 CI 用 template_family？”建议在最终表/附录同时列 template-family 主 CI 与 pair-level 敏感性，避免选择性报告。
- 该问题涉及冻结统计口径的解释，**应由 PI 新增说明或勘误，不应由写作者私下改表**。

### 3.3【主要】README 与最终裁决直接冲突，严重程度高于顾问报告描述

- README 仍写：
  - “22 个 run”；
  - “P2 已完全收口”（实际 P2 正式取消）；
  - “P3 已由人工决策启动”（实际 P3 正式取消、永久放弃）；
  - “P5 为有条件 GO”（实际 P5 暂缓、未签 off）；
  - “贡献(2) 强形式，已获 PI 解禁”（实际贡献(2) 已撤回）。
- 证据：`README.md`:22–25、170；对照 `docs/decisions/final_boundary_study_signoff.md`:28、34、94、103–110。
- 这不是普通“文档过期”，而是**对外材料与最终科学裁决相反**；在修复前不应投稿、不应对外发布 README 状态。顾问报告虽然提到 README 过期，但未把它提升为“投稿阻断项”。

### 3.4【次要】报告自身的结构可维护性

- 报告同时保留一轮原文、就地标注、§8 修订、§9 合规声明；§0/§1 也含二轮修订文本，与 §8.3/§8.8 重复。科学内容可追溯，但“当前有效结论”需要读者自己拼合，容易再次产生“哪段为准”的歧义。
- 建议：第三轮直接产出“当前有效版”单页结论 + 保留旧版为附录/历史文件，而不是继续叠加横幅。

### 3.5【次要】外部证据的核验粒度

- 元审查已核验 W1/W2/W3/W4 的 arXiv 标题、作者、摘要与日期真实存在；但报告对 CacheLink“§4.3 四臂 RR/NR/RN/NN”等**章节级细节**、以及 W11 中 ARC/SQuAD 官方页细节，属于“未逐一抓取全文”的二手/部分核验。
- 这不影响主结论（这些文献确实存在且主题相关），但引用进论文前仍须按协议 §9 做全文口径核验，不能把报告中的章节号直接当已核实事实。

---

## 4. 重新审查后的分级结论

| 维度 | 元审查评级 | 理由 |
|---|---|---|
| **方向** | **合理（PIVOT 正确）** | 原正向假设被干净数据证伪；失败边界 + 数据泄漏教训是真实、可发表的负面/实证问题；但新颖性窄，须限定到具体翻转案例 + E_CF 框架。 |
| **方案** | **存疑（可继续，需收尾）** | 预注册/冻结/联合报告/决策树纪律有效；但 v2.3 主口径与 kd 审计产物不一致、强基线不全、合成域/单对、少簇 exploratory。 |
| **实验** | **存疑（内部证据强，非确认性）** | affine 三 seed val 证据一致；kd 三 seed 已完成但缺 v2.3 主 CI 产物；封存 test 未评；M4 real=0 已披露；SQuAD 锚点待产出。 |
| **结果** | **基本合理（限探索性/单对/合成域）** | 负面结果（affine 失败边界 + 泄漏翻转）可支持；但“已确证”应降为“内部探索性强证据”；kd 的 C 类 gap 只能作探索性观察，不恢复贡献。 |
| **总体** | **PIVOT 成立；失败边界研究 CONDITIONAL GO；投稿暂缓/NO-GO** | 不是重开原主线，也不是现在可投；完成 §5 清单后再由 PI/审稿人重开 P5。 |

---

## 5. 接受本结论前必须闭环的动作

1. **README 全量同步**：26/29 run、clean 数据、affine 三 seed 坍塌、kd C 类探索性观察、P2/P3/P4 取消、P5 暂缓、贡献(1)/(2) 撤回、贡献(3) withheld；删除“P2 已收口/P3 已启动/P5 有条件 GO/贡献(2) 强形式”旧表述。**这是投稿阻断项。**
2. **kd_clean 的 v2.3 审计产物**：把三 seed 纳入 `bootstrap_summary.json`（template_family 主 CI + pair-level 敏感性 + exploratory=true），并在最终裁决表/论文表中统一口径；或由 PI 明确说明为何 C 类判读使用 pair-level CI。
3. **S4/S5 措辞**：全文改为“E_CF 大幅升高、接近但未超过错配/零控制，伴 dual 坍塌”；明确 `transfer_broken` 单信号、8 族 exploratory、单 MVP 等深对、合成域、test 未评测。
4. **引用核验**：按协议 §9 对 CacheLink/Heo/Accuracy≠Evidence/Contrast Sets/Kapoor-Narayanan 做全文口径核验（元审查只到摘要级）；替换论文 `[PLACEHOLDER]`。
5. **顾问报告状态管理**：将 `current_task_review.md` 的二轮结论标注为“已被 `final_boundary_study_signoff.md` 超越”，或出第三轮单页更新；避免后续读者把“kd 待决/S1–S3 未闭环”当当前事实。
6. **M4/锚点**：real=0 已由 PI 正式接受并披露；SQuAD 锚点按 `anchor_confirmation.md` 产出后，按 v2.4 三情形归类，不恢复贡献。此项不阻塞边界研究收尾，但影响外部效度档位。

---

## 6. 结论失效条件

- 若 kd_clean 的 v2.3 簇级 CI 下界跨 0 或效应消失 → C 类判读需降级，边界研究叙事需重写；当前只读复算下界均 >0，暂不支持此情形。
- 若发现 clean run 读取封存 test、挑 seed、改判据 → 诚信问题，直接 NO-GO；当前未见（`eval_splits=["val"]`、冻结判据 diff 空）。
- 若 README 在投稿前仍未同步 → 不是科学结论失效，而是**投稿合规阻断**；不能以“论文写对了”抵消对外文档相反陈述。
- 若外部文献被证明已完整覆盖“成对反事实 E_CF × 跨模型 zero re-prefill” → 新颖性进一步下降；失败边界/审计案例仍可作为负面/实证结果，但不能声称评价框架首创。

---

## 7. 最终一句话

> **顾问的 PIVOT 方向判断是对的，但其“kd 待决、S1–S3 未闭环、结果已确证”的表述已被 11:46 后的最终裁决和三 seed 产物超越；重新审查后的结论是：PIVOT 确认，失败边界研究 CONDITIONAL GO，投稿暂缓/NO-GO，直到 README、kd 的 v2.3 审计、S4/S5 与引用核验全部闭环。**

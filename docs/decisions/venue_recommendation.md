# 投稿 Venue 推荐（V2.0 · 供真实 PI 拍板）

> 裁决人：PI / 课题组长（推荐角色）。日期：2026-11-23。
> 触发：真实 PI 授权 PI 推荐投稿 venue，要求给 2–3 个候选供最终拍板。记录将追加至 `human_decisions.md`。
> 依据：论文 `papers/readkv_v2_draft/main.tex`（摘要/结论，负面结果 / boundary study / 贡献(1)(2) 撤回、(3) withheld / real=0 / 单 MVP 对 / v2.3 exploratory）、`docs/decisions/{final_boundary_study_signoff,m4_target_adjustment}.md`；venue 信息来自本轮 websearch/webfetch 一手调研（URL 见各候选）。
> **本文件只是推荐，最终 venue 由真实 PI 拍板，agent 不代为决定。**

---

## 0. 论文画像（用于匹配）

- **类型**：empirical / boundary study，负面结果 + 方法论警示（数据泄漏/模板重合如何制造虚假显著发现；修复后 affine 迁移失败边界）。
- **证据**：合成 F1–F6（real=0 已披露）、SQuAD/ARC 锚点（有限外部锚点）、单 MVP 等深对、v2.3 下 8 族<24 标 exploratory、贡献(1)(2) 撤回/(3) withheld、P2/P3/P4 永久放弃。
- **优势**：真实可复现的数据审计前后对照（SHA 固定）、诚实披露、方法论警示有普适价值。
- **软肋**：单模型对、合成域、exploratory 统计（CI 效力弱）、无真实文档、无方法贡献——强 venue 的审稿人可能以"证据强度不足/贡献有限"击穿。

---

## 1. 候选一（首选）：TMLR — Transactions on Machine Learning Research

- **URL/依据**：https://jmlr.org/tmlr/editorial-policies.html （本轮 webfetch 一手核实，全文可读）
- **① 负面/方法论友好度**：scope 明确欢迎 "experimental and/or theoretical studies yielding new insight into the design and behavior of learning systems"、"accounts of applications of existing techniques that **shed light on the strengths and weaknesses of the methods**"、"**reproducibility studies** of previously published results or claims"；设 **Reproducibility Certification**；验收标准明言 "even if the contribution or significance of the work is modest" 亦可接受。→ **高度友好**（本研究是"揭示方法弱点 + 复现性/审计研究"）。
- **② 领域匹配**：ML 方法学与评测（KV cache / cross-model transfer / evaluation methodology）属其核心 scope。→ 高。
- **③ 证据强度容忍**：验收问题是"claims supported by accurate, convincing evidence + TMLR 读者是否有兴趣"；接受 modest 贡献，但也要求 "accurate, convincing and clear evidence"。→ **中等偏友好**；单模型对/exploratory 可能被要求补实验，但 'modest contribution acceptable' 与 Reproducibility Certification 对本研究有利。
- **④ 实际约束**：**开放获取、对作者零费用**（网页原文："imposes no fees or payments to authors"），滚动投稿（无年度 deadline），双盲 + 公开评审。作者配额 Generalized Harmonic Quota (N1=2,N9=9) 对单作者通常充裕。
- **风险提示**：(a) 不接受"会议论文扩写版"，需确保本文是原创、未与已发表稿重叠；(b) 编辑可能认为 KV cache 专项"audience too narrow"（但本研究的"数据审计方法论"有更广受众，应在 cover letter 强调这一点）；(c) 若被 AE 初筛判 out-of-scope/证据不足会较快拒稿。

## 2. 候选二：EASE 2027 — Reproducibility and Negative Results (RENE) track

- **URL/依据**：https://conf.researchr.org/track/ease-2027/ease-2027-reproducibility-and-negative-results （websearch 摘要一手）；deadline 见 https://conf.researchr.org/dates/ease-2027 （摘要截止 2027-02-22；会议 2027-06-15..18，Hanoi）
- **① 负面/方法论友好度**：**极佳且专门**——track 名称即"Reproducibility and Negative Results"，明确欢迎 "Null or non-significant findings"、"**Analyses revealing that apparently robust improvements disappear under alternative evaluation procedures, datasets, metrics**"、"**Evidence that evaluation metrics, benchmarks, datasets... may lead to misleading comparisons**"。本研究"修复数据缺陷后虚假 gap 消失/反转"几乎逐字对应。→ 主题命中度最高。
- **② 领域匹配**：EASE 主题是 **software engineering 的 evaluation & assessment**；本研究是 LLM/NLP 模型压缩与评测，**非 SE**。→ **中等偏低**（需把论文叙事向"AI/ML-based SE 的评测可信度"靠拢，可能是硬伤）。
- **③ 证据强度容忍**：RENE 有专门评审标准，但明确要求 "a negative result should reflect an **absence or reversal of an effect, rather than primarily reflecting inadequate methodology**"。本研究结论恰是"早期正向结果是方法学缺陷（泄漏）造成的"——**可能被判为 'inadequate methodology' 而非合法 negative result**，这是核心风险；需在投稿时把贡献重构为"审计方法 + 修复后真实边界（affine 迁移失败）"的 effect reversal，而非仅"方法学批评"。
- **④ 实际约束**：会议有注册费与页码/格式（ACM sigconf）；时间上可行（2026-11 距 2027-02 摘要截止约 3 个月）。具体 APC/费用未在本次检索中确证，不臆断。
- **风险提示**：(a) SE 领域错配可能被 desk reject 或审稿人质疑；(b) "inadequate methodology"判据与本研究叙事的张力（见③）；(c) 需按 ACM 模板改写格式。

## 3. 候选三：ACL 2027（经 ACL Rolling Review 提交）

- **URL/依据**：https://aclrollingreview.org/cfp ；https://aclrollingreview.org/dates （ACL 2027 最终 ARR 提交约 2027-01；ARR 滚动周期）；https://2026.aclweb.org/calls/main_conference_papers/ （ACL 系列 CFP 原文：欢迎 negative findings、reproduce/fail to reproduce）
- **① 负面/方法论友好度**：**极佳**——ARR CFP 原文："A negative results paper might report on **non-reproducibility or non-generalizability** of previously published results, their **misattribution ('right for the wrong reasons')**, or present an idea that seemed great but didn't work." 本研究"数据泄漏导致 right-for-wrong-reasons 的虚假 gap"与此高度契合。→ 极佳。
- **② 领域匹配**：NLP/LLM 评测方法学，主题最贴合（KV transfer、E_CF 评测、counterfactual fidelity）。→ 最高。
- **③ 证据强度容忍**：**最低**——ACL 顶会竞争激烈（搜索结果显示 ACL 2026 接收率约 15%）；单模型对、合成域、exploratory 统计（8 簇<24）、无真实文档、无方法贡献，极易被审稿人以"证据不足/影响有限"击穿。可考虑 Findings 或 ARR 后转投，但门槛仍高。
- **④ 实际约束**：ARR 滚动提交（需预留审稿周期）；会议/开放获取政策以 ACL 官方为准（本次未逐项确证费用，不臆断）。
- **风险提示**：(a) 接收率极低、证据强度软肋致命；(b) 2027-01 截止需在此之前完成全部 P5 门槛（含 venue 之外的引用/署名/审稿），时间紧；(c) 建议仅在真实 PI 愿意冲击高 tier 且能补强实验时选。

---

## 4. 推荐结论与排序

> **首选：TMLR。** 次选：EASE 2027 RENE track。第三：ACL 2027（ARR）。

**首选 TMLR 的理由**：
1. **匹配度与容忍度的最佳平衡**——scope 明确欢迎"揭示方法弱点""复现性研究""modest 贡献"，与本研究"数据审计 + 失败边界 + 方法论警示"定位天然契合；
2. **对当前证据强度最友好的高信誉 venue**——ACL/EASE 要么门槛过高（ACL 证据软肋致命）、要么领域错配（EASE 非 SE），TMLR 的 "modest contribution acceptable + Reproducibility Certification" 最能容纳"单模型对 + exploratory + 无方法贡献"的现实；
3. **实际约束最优**——OA 零费用、滚动投稿无 deadline 压力（避免 2027-01/02 的硬截止与 P5 门槛冲突）；
4. **叙事可扬长避短**——在 cover letter 强调"可复现的数据审计方法论"这一普适贡献，弱化 KV cache 专项的窄受众问题。

**为何不首选 EASE/ACL**：EASE RENE 主题命中最高但 SE 领域错配 + "inadequate methodology"判据风险；ACL 领域最贴但证据软肋在顶会审稿下几乎必被击穿、接收率极低、截止紧。

**共性风险（所有候选）**：单 MVP 等深对、合成域、v2.3 exploratory（8 簇<24）、real=0、贡献(3) withheld——这是论文的结构性软肋，任何 venue 都须靠"诚实披露 + 方法论警示的普适价值 + 数据审计前后对照的可复现性"来补偿，而非夸大贡献。

---

## 5. 最终拍板声明

> **以上为 PI agent 基于一手调研的推荐，最终 venue 由真实 PI 拍板，agent 不代为决定。** 真实 PI 指定 venue 后，我方按该 venue 格式要求完成 P5 定稿（署名 Zhang Xuein <zxm0813@gmail.com>、引用核验、S1–S5 收尾、锚点结果归类），在 venue 未定前维持"投递就绪、不最终签 off"。

---

**签署：PI / 课题组长（venue 推荐 · 2026-11-23；供真实 PI 拍板）**

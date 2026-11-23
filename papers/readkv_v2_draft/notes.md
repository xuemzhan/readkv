# 写作者笔记 —— readkv_v2_draft（仅内部，不投递）

> 状态：论文配套笔记。所有数值只读自 `reports/runs/**` 与 `reports/data/**` 冻结产物，本笔记未重新计算任何统计。
> 最新裁决：**干净数据方向性翻转紧急裁决** `docs/decisions/clean_data_reversal_ruling.md`（2026-11-23）——贡献(1) 冻结降级、贡献(2) 撤回、旧 P1/P2 全部 superseded、论文重定位为负面/实证结果。

---

## 0. 本次已写文件

- `papers/readkv_v2_draft/main.tex`：全文 LaTeX（摘要、引言、相关工作、方法、实验、结果、结论、附录 A），已按紧急裁决整体重写为「迁移失败边界 + 数据泄漏教训」的负面/实证结果论文。
- `papers/readkv_v2_draft/notes.md`（本文件）：状态清单、贡献处理、图表清单、数据完整性备案、cover letter 要点。

未写/未改：任何代码、`reports/runs/**`、`configs/prereg/**`；未重新计算任何统计量；未编造 kd/P2 数值。

---

## 0.5 本轮状态（紧急翻转轮，2026-11-23）

- **科学方向翻转（最高优先，PI 紧急裁决 `clean_data_reversal_ruling.md`）**：干净数据 P1 MVP 三 seed（`p1_clean_mvp_seed{0,1,2}`，git `efc3ba3`）显示 **broken transfer**：joint E_CF 6.900 / 8.159 / 8.540，dual 0.417 / 0.283 / 0.383，全部 `transfer_broken=true`。原贡献(1) 的「utility-preserving gap」与贡献(2) 的机制信号源于数据缺陷，**修复后翻转为迁移失败**。
- **贡献(1) 冻结降级、贡献(2) 撤回 withheld**：不再以任何正向形式声称 gap 或 V 消费机制定位；旧 P1/P2 正向数值彻底移出结论，仅作为 Table 2（前后对照）的历史侧出现。
- **主表换干净数据**：Table 1（`tab:cleanmvp`）填 P1 干净三 seed；Table 2（`tab:reversal`）为修复前后方向对照。**kd_only 干净数据三 seed 已补入**：E_CF 6.388/6.479/7.211、joint dual 0.700/0.733/0.767、flip 0.91–0.94、transfer_broken=false；按情形 C 仅作探索性观察，不恢复为正式贡献。
- **kd_only 干净三 seed 仍在跑**；结果决定择支（都 broken→纯失败边界；kd 不 broken 且接近 Self→数据缺陷制造虚假发现的方法学负面结果）。
- **δ 复核暂停、P2 不启动（取消）、P3 维持暂停/实质取消**；P2/P3/P4 均未在干净数据上运行。
- **E0 干净复验已通过**（`e0_clean_mvp_seed0`，cosine 1.0、KL 0、EM 0.975、round-trip、2.2e-16 ≪ 效应、zero_re_prefill），翻转不是 cache round-trip 实现残差。
- **数据修复披露保留**：v2.0→v2.1 缺陷/修复/验收 11/11/v2.3 口径（见正文 §「Data correctness...」与 `tab:datafix`）。
- **投稿暂缓**（承接 `data_readiness_ruling`，且理由更强：核心贡献被推翻）；**审稿紧急复核中**（排除实现 bug、判 broken transfer 可信度）。
- 历史状态（已被取代）：此前 R1 闭环、`*_repro_*` 权威 run（`458de18`）、P2 三 seed（`6784780`）强形式解禁等签 off **对新数据不再适用**，以紧急裁决为准。

---

## 1. 贡献措辞如何处理（§10 门槛——现已全部撤回）

- **贡献(1) 撤回**：删除 "We identify a reproducible gap between standard transfer utility and counterfactual response fidelity…"。干净数据上 joint dual 坍塌、E_CF 达错配/零缓存控制水平，是 broken transfer，不是 utility-preserving 失真；正向证据基础已不存在。
- **贡献(2) 撤回 withheld**：删除强形式 "We localize the gap to receiver-side Value-consumption pathways…" 及所有机制定位；原 P2 证据建立在被污染数据上，不可信；PI 不等 P2 重跑、直接撤回。
- **贡献(3) 维持 withheld**：CF-RCT 未训练，主终点（成对 E_CF vs kd_only，CI 上界<0）未评估，P3 已暂停/取消。
- **不声称的正向主张**：任何「反事实失真普遍存在」「V 消费侧机制定位」「方法改善 gap」「跨模型/真实世界泛化」。
- **本报告的两条发现是负面/实证结果，非 §10 正向贡献**：① 干净数据上 affine mapper 在 MVP 等深对的迁移失败边界；② 数据泄漏如何制造虚假科学发现的前后对照方法学教训。
- **禁止词**："reproducible gap"、"utility-preserving distortion"（正向用法）、"localize the gap"、"We identify a gap"、"robustly/across model pairs"、"causal/sole cause"。
- 不把 `P>0.05` 写成等效；主终点未评估前不作任何 endpoint gain 声明；mock 数字非证据；封存 test 未评测。

---

## 2. 如实写入的不利结果（结果章节 §「Adverse results and boundaries」）

1. **质量坍塌是主观察**：干净数据 joint dual 较 Self 降约 0.4（seed0），E_CF 6.90–8.54 与错配/零缓存控制相当，三 seed 全 `transfer_broken=true`。
2. **混合控制信号**：info_attribution mismatch +1.483、zero +1.684 为正、random −0.135 为负，伴随 dual 坍塌；失败判读依据联合模式，审稿紧急复核其稳健性（排除实现 bug）。
3. **旧非等深对失败**：4B→1.7B 旧结果 joint dual 0.28–0.30、失败边界；run 已 superseded（pre-fix 数据），无干净数据等价物。
4. **旧正向信号是数据产物**：修复后 gap 与机制消失并翻转（Table 2），是核心方法学教训。
5. **剩余限制**：全合成数据、real=0、无外部锚点、单等深对、F5 长度分层 61，均限定结论。
6. **统计 caveat**：旧 pairwise CI 仅 8 族、v2.3 下属探索性；干净 CI 以 template_family 为主簇 + 必报 pair-level 敏感性。

---

## 3. 图表清单（只读冻结结果生成，不重算统计）

| 编号 | 内容 | 数据来源 | 当前状态 |
|---|---|---|---|
| 图 1 | 两篇已有工作→科学问题关系图 | 设计性示意 | 文字占位；待绘图（叙事已改为数据泄漏教训） |
| 图 2 | 严格 zero re-prefill 流程与四臂分界 | `algorithm_spec.md §3.4/§6.1` | 文字占位；待绘图 |
| 图 3 | 反事实成对文档构造与正/负控制 | `protocol.md §3.2` | 文字占位；待绘图 |
| 图 4 | 前后方向对照（旧 vs 干净 E_CF/dual） | `p1_gpu_mvp_repro_seed*`（旧，superseded）+ `p1_clean_mvp_seed*`（新） | 可据 Table 2 绘制；新表为权威 |
| 图 5 | 机制热图 / Oracle 修复 | 旧 `p2_gpu_mvp_seed*`（已撤回） | **不画**：机制主张撤回，禁止伪造 |
| 图 6 | 方法消融 | E3 | 未跑，不画 |
| 图 7 | 泛化与成本—Pareto | E4/E5/E6 | 未跑，不画 |
| 表 1（`tab:datafix`） | 数据缺陷前后对照 | `reports/data/data_fix_report.md`、`acceptance_checks.json`、`docs/data/data_card.md` | 正文已呈现 |
| Table 1（`tab:cleanmvp`） | 干净 P1 MVP 三 seed | `p1_clean_mvp_seed{0,1,2}/metrics.json`（`efc3ba3`） | 正文已填新值 |
| Table 2（`tab:reversal`） | 修复前后方向翻转对照 | 旧 repro run + 干净 clean run | 正文已呈现 |
| — | kd_only 干净三 seed | 已补入（6.388/6.479/7.211；探索性） | p1_kd_clean_mvp_seed{0,1,2}/metrics.json |

注：正文数值表（数据修复表、干净 P1 表、翻转对照表）均从冻结产物转抄。旧 P1/P2 数值只出现在翻转对照的历史侧；不得用 mock 或旧 run 作最终结论。

---

## 4. 数据完整性与口径备案

- **数据缺陷与修复（最高优先，`data_readiness_ruling.md`）**：旧 v2.0（sha `6058fd6d…d1887`）的 18 退化对、≥15 组跨 split 逐字泄漏、实体全共享、train/test 骨架 100% 重合、bootstrap 簇退化、flip 分母 394/457 冲突，是内部正确性缺陷（抬高指标、压窄 CI，披露无法补救）→ 重建 v2.1（sha `f910f1f1…a894a`，验收 11/11、53 单测通过）。剩余为外部效度限制（合成域、real=0、单 MVP 对、F5 长度分层 61），仅披露。**修复直接推翻了旧正向信号**（见翻转对照）。
- **v2.3 统计口径**（`configs/prereg/stats_convention_v2.3.yaml`）：主簇 `template_family` + 必报 pair-level 敏感性；族数<24 标 exploratory；flip excludes=[F5,F6]=398。
- **干净数据 provenance**：P1 clean 与 E0 clean 均 git `efc3ba3`、`zero_re_prefill=true`、bf16/sdpa、三 seed 齐全；审稿紧急复核正在排除「数据重建引入实现回归（实现 bug）」的可能。
- **冻结 verdict 与正交字段并存**：干净数据上冻结判据仍返回 `distortion_exists`（distortion_present ∧ quality_pass），但 `quality_pass` 仅指数据质量门；正交 `transfer_broken=true` 将结果定性为失败边界。下游须联合读取，禁止只看 verdict 判「干净失真」。
- **早期备案（仍有效）**：`model_pair` 字符串误标勘误见 `reports/runs_index_errata.json`；`info_gap` 逐对字段未填、报 `info_attribution`（控制 E_CF − joint E_CF）；one-shot kernel 残差 0.9993 不属实现误差；引用 KV-Lingo/CacheLink 为占位，须按 `protocol.md §9` 核验。

---

## 5. Cover letter 要点（草稿，待 PI 定稿；投递暂缓）

1. 主题：负面/实证结果论文——「跨模型 KV 迁移的失败边界 + 数据泄漏如何制造虚假科学发现」；**不**宣称任何正向贡献。
2. 要点一：数据质量对基准结论的决定性影响——前后对照实证显示修复缺陷后一项「显著」发现完全翻转。
3. 要点二：干净数据上 affine mapper 在 MVP 等深对的迁移失败边界（dual 坍塌、E_CF 接近无信息控制、三 seed `transfer_broken=true`）。
4. 要点三：诚实边界——贡献(1)(2) 撤回、贡献(3) withheld、主终点未评估、封存 test 未评测、P2/P3/P4 未跑；真实文档缺失、单模型对。
5. 要点四：数据与复现——数字来自真实 GPU run（干净 `efc3ba3`），bf16/sdpa、zero_re_prefill；新 v2.1 数据验收 11/11，统计按 v2.3；mock 非证据；P>0.05 不作等效。
6. 审稿人可重算：`scripts.bootstrap_ci_report` / `scripts.consistency_check`；附数据完整性备案（§4）；紧急复核结果待出。

---

## 6. 下一步（触发条件）

- **最高优先**：kd_only 干净三 seed 已补入正文并按 §3.3 判读为情形 C（kd 不 broken、不接近 Self、稳定非零 gap → 边界研究）；PI 已最终收口，贡献(1)(2) 撤回、贡献(3) withheld、P2/P3/P4 取消、投稿暂缓。
- **审稿紧急复核**：确认 broken transfer 可信度（排除实现 bug）；若为实现 bug 则冻结结论、工程修复重跑；若可信则维持紧急裁决。
- **数据修复重跑**：E0 已复验、P1 干净已产出；P2 不启动、P3 暂停；按 v2.3 主报 template_family CI + pair-level 敏感性。
- **引用核验**：`[PLACEHOLDER]` 引用按 `protocol.md §9` 投递前完成。
- **投稿暂缓**：待 kd 择支 + 审稿复核 + PI 签 off；在此之前不得投递、不得沿用旧 run 作最终结论。

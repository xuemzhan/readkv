# 最终 Compliance Note（R2 / R4 收口 · P5 投递前合规结论）

> 审稿人：reviewer（对抗性审阅 / readkv）。日期：2026-11-23。
> 依据：`docs/decisions/final_implementation_plan.md`（R2/R4/R5 责任与验收）、`reports/review/final_boundary_audit.md`（前次 CONDITIONAL GO 及 R1–R5）、`papers/readkv_v2_draft/{cover_letter.md,notes.md,main.tex}`、`reports/runs_index.json`、`reports/runs_index_errata.json`。
> 当前 HEAD=`21d3415`（审计时点）。**范围**：仅核验 R2/R4 是否闭环 + 无回归；不重复此前已通过项（R1/R3/D3/R5 及历次阶段审计）。本轮未改代码/数据/prereg/论文/run 产物。

---

## 0. 总结论

> **R2 已闭环 ✅；R4 已闭环 ✅。整体 P5 投递前合规结论：PASS（ready-to-submit）。可交真实 PI 按 TMLR 流程提交（署名、邮箱、OpenReview 账号、版权/许可、AE/reviewer 建议仍由真实 PI 人工完成，agent 不代为投递）。**
>
> 附 4 项**非阻塞残余项**（§4），其中 R5 计数漂移建议以只读勘误提示 PI，不影响投稿。

---

## 1. 必做动作执行结果（输出重定向 /tmp，未写回仓库）

| 动作 | 结果 |
|---|---|
| `.venv/bin/python -m scripts.bootstrap_ci_report --output /tmp/opencode/bootstrap_summary_final.json` | 成功，31 runs；仓库 `reports/bootstrap_summary.json` **未被改写**（`git diff HEAD` 为空） |
| `.venv/bin/python -m scripts.consistency_check --output /tmp/opencode/consistency_report_final.json` | checked=31, failed=22, head=21d3415, dirty_run_paths=[]；仓库 `reports/consistency_report.json` **未被改写** |
| prereg 完整性 | `git diff HEAD -- configs/prereg/ configs/protocol.yaml` = 空（未篡改）；`ai_generated_data_v2.6.yaml` 现为 **TRACKED**（D3 维持闭环） |

**无回归确认**：9 个权威 run（7 clean + 2 SQuAD 锚点）在最新审计中**全部 `ok=true / traceable=true`**；22 个失败项**全部为已标 superseded 的历史 run**（无「非 superseded 失败」）；clean affine seed0 主 CI 仍为 `6.900 [3.564,10.100]`（template_family）+ 敏感 `[5.496,8.321]`（pair-level），与冻结权威值一致，未被私改（R1 无回归）。

---

## 2. R2 判定 — **已闭环** ✅

- **cover letter 声明确实存在**：`papers/readkv_v2_draft/cover_letter.md` §「Reference-verification disclosure (item R2)」（第 69–80 行）明确写：「N1–N9 identified by title / arXiv ID / version / date from public metadata; author names completed from arXiv API metadata; **full-text reading was not completed at submission** … cite only for existence and title/abstract level, make **no section-level or detailed claim**」。与计划 §2 R2 要求逐字对应。
- **notes.md 已同步**：notes.md 第 12/179 行记录 cover letter 的 R2 声明与「N1–N9 仅存在性/标题/摘要级引用、未写章节级细节为已核实」。
- **正文无「章节级细节当已核实」正向表述**：main.tex 相关工作段落（第 158–194 行）统一使用 "their reported abstracts state…"、"we have verified these works at **abstract level only** and make **no claim about section-level diagnostic detail**"（第 165–166 行）、"**As reported in their abstracts**, recent work already separates…"（第 174 行）；N1–N9 的具体描述均以摘要级转述呈现（如 n1 Functional Cache Divergence、n2 consumability、n3 value-bias），无章节级/方法细节的确证性主张。KV-Lingo/CacheLink/SQuAD 亦仅元数据级。bibitem n9b（BridgeKV）明确标注「Author list not independently verified; cited as arXiv preprint only」（第 856–857 行）。
- **判定**：R2 验收标准（cover letter 含声明 + 正文无未核实章节级细节）**全部满足**。

---

## 3. R4 判定 — **已闭环** ✅

- **索引状态**：`reports/runs_index.json` 共 **31 项 = 22 superseded + 9 authoritative**；三个目标 run——`delta_lock_v2p1_2p0_par`、`p1_gpu_kdonly_mvp_seed1_par`、`p1_gpu_kdonly_mvp_seed2_fast`——**均在索引中且 `superseded=true`**，带 `superseded_reason`（pre-clean-data 历史 run、git_hash=a04990d 跑分代码 diff 失败、非 9 权威之一、不影响结论）。
- **errata 同步**：`runs_index_errata.json` 的 `superseded_runs` 含三个目标；新增 `r4_historical_runs` 专节（authority=final_implementation_plan §2 R4）逐一登记。
- **无未索引 run 目录**：`reports/runs/` 下 31 个目录与索引 31 项**完全一一对应**（无未索引目录、无索引悬空项）。
- **consistency 告警**：三个目标 run 在最新审计中 `ok=false` 但 `superseded=true`，失败原因为「run-producing code differs between config.git_hash and HEAD」（git_hash=a04990d 为旧 HEAD）——属计划 §2 R4 验收明确允许的「因 HEAD 前进报 code-diff，按历史 run 合理解释」情形，**不再以「未标注历史 run」形式误报**；全库无「非 superseded 失败」。
- **未改 run 产物**：`git diff HEAD -- reports/runs/*/{scores,config,metrics}.json` = 空。R4 仅在索引/勘误层落实，符合「不改 run 产物」纪律。
- **判定**：R4 验收标准（三 run 可查且标 superseded + 无误报）**全部满足**。

---

## 4. 非阻塞残余项清单（不影响投稿，供 PI 知悉）

| 编号 | 项 | 等级 | 说明 / 建议 |
|---|---|---|---|
| N1 | **R5 计数漂移**：`final_implementation_plan.md` §2 R5 勘误登记「28 run（19 superseded + 9 权威）」，但 R4 落实后 runs_index 现为 **31 项（22 superseded + 9 权威）**。权威 9 不变，仅历史 superseded 从 19→22（R4 新增 3） | 次要（计数/文档） | 计划已写明 R5 勘误（用户提示条件不满足，无需另提示）。建议 PI 以**只读勘误**补记「总计数 28→31 / superseded 19→22，权威仍 9」，**不回写已签署冻结裁决**（符合 R5 纪律）；下游以 runs_index 为准。不影响科学结论。 |
| N2 | **errata `authoritative_runs` 口径不一致**：errata 的 `authoritative_runs` 列 11 项（旧 repro + p2 系列），与 runs_index 权威 9 项（7 clean + 2 锚点）不同 | 次要（索引内部） | 两文件定位不同（errata 为历史累积、runs_index 为当前权威），下游判定权威以 runs_index 为准；建议文档工程师在 errata 加一行说明避免误读。不影响投稿证据。 |
| N3 | **锚点 config 无 `model_pair` 字段**致 `consistency_check` 的 `model_pair_check` 返回 ok=false 但静默不计入 problems（此前 anchor_eval_review D4 已记） | 次要（审计工具） | 锚点为标准 QA、无 KV model_pair 概念，属字段不适用；建议审计脚本对外部锚点显式标「N/A」。不阻塞。 |
| N4 | **`final_implementation_plan.md` 头部称依据 HEAD=4613200**，而本轮审计时点 HEAD=21d3415（后续归档 commit）；冻结判据与权威 run 未变 | 次要（时点） | 纯时点差，plan 的 R1/R5 结论仍成立；无科学影响。 |

以上均为披露/计数/工具层次，**不构成投稿阻塞**，无需重新审计。

---

## 5. P5 投递前合规结论与建议

1. **合规判定：PASS（ready-to-submit）**。R2、R4 均闭环；R1（两表并列 CI）、R3（squad16/18）、D3（v2.6 已跟踪）、R5（计划已登记勘误）维持闭环；权威 9 run 全部通过审计、provenance 一致、无回归。
2. **贡献/定位无回归**：贡献(1) 撤回、贡献(2) 撤回 withheld、贡献(3) withheld；主终点未评估、封存 test 未评测、real=0、单一合成等深对、8 簇 exploratory、锚点 exploratory_disclosure——均有披露，无跨源普适/真实文档验证/方法增益主张（与前次 final_boundary_audit 一致，本轮未发现回归）。
3. **是否可交真实 PI 提交 TMLR：可以**。建议真实 PI 完成计划 §4 第 9 项人工动作：确认署名邮箱（Zhang Xuein \<zxm0813@gmail.com\>）、TMLR OpenReview 账号提交、版权/许可声明、cover letter、AE/reviewer 建议；并对 §4 N1（R5 计数）作只读勘误补记。
4. **不触发**：本轮无实现 bug、无判据篡改、无 Oracle 泄漏、无 mock 混入、无贡献升格；无需停冻结或重跑任何实验。

---

## 6. 结论

R2（cover letter N1–N9 核验级别声明 + 正文无章节级细节确证）与 R4（三历史 run 在 runs_index/errata 标 superseded、索引 31 项无遗漏、未改 run 产物）**均已闭环**。重跑两审计脚本（输出定向 /tmp、未污染仓库产物）确认：9 权威 run 全通过、22 失败全为 superseded 历史 run、无回归、prereg（含已跟踪的 v2.6）未篡改。整体 P5 投递前合规判定 **PASS**，可交真实 PI 按 TMLR 流程提交；§4 列 4 项非阻塞残余（主要为 R5 计数由 28→31 的只读勘误）供 PI 知悉。真实 PI 的人工提交动作与策略选择不由本 note 代替。

**签署：reviewer（对抗性审阅），2026-11-23。**

# 2×2 GPU 补充实验 · 阶段合规审计报告（protocol-v2.7）

> 审稿人：reviewer（对抗性审阅 / readkv）。日期：2026-11-23。
> 依据：`configs/prereg/gpu_followup_v2.7.yaml`（冻结）、`reports/audit_2x2_formal_summary.json`、`reports/audit_2x2_bootstrap.json`、`reports/audit_2x2_smoke_report.md`、`reports/engineer_status.md` §16、12 格 run 产物、`data/audit_2x2/**`、`scripts/consistency_check.py`、`papers/readkv_v2_draft/main.tex`。
> 当前 HEAD=`8168ec1`。**范围**：2×2 补充实验合规审计。本轮未改代码/数据/prereg/论文/run 产物。

---

## 0. 总体判定

> **数据/指标/provenance/失败留痕合规（12 格真实、对角 60/60 一致、哈希全匹配）。但发现两项需 PI 决断的合规问题：**
> - **C1（主要·统计口径）**：12 格 scores 缺失 `template_family` 字段，bootstrap 退化为 `cluster-fallback`（60 逐对唯一簇、`exploratory=false`），**违反 v2.7 §2 强制的 template_family 主聚类 + <24 簇 exploratory 标记**；L 主终点与预固定对比**只有点估计、无 bootstrap CI**。
> - **C2（主要·因果措辞）**：main.tex 仍保留 "data defects manufactured / directly produced / caused by" 的单项因果强措辞；v2.7 §3 判读即便走 `calibration_version_effect` 分支，也只允许"两个版本整体切换"的受控观察，**禁止归因到去重/退化对/模板重叠任一单项**，并要求在无稳健校准效应时撤除上述强措辞。2×2 结果支持"校准版本效应方向稳健"，可保留受控观察措辞，但现文的单项因果句仍越界。

**consistency 假阳性判定**：确认为**字段对接假阳性，数据/指标无误**（详见 §3）；选项二（审计脚本识别新字段）在技术上更优但涉及 `scripts/**` 改动，需 PI 决断采用哪一项。

**阶段建议**：2×2 阶段的**数据层可验收**；**P5 重新签 off 前置条件 = C1、C2 闭环 + consistency 假阳性处置 + 论文补 2×2 受控观察段**（§6）。

---

## 1. 必做动作执行结果

| 动作 | 结果 |
|---|---|
| `.venv/bin/python -m scripts.bootstrap_ci_report --output /tmp/...` | 成功，43 runs；仓库 bootstrap 产物未改写（`git diff HEAD` 空） |
| `.venv/bin/python -m scripts.consistency_check --output /tmp/...` | checked=43, failed=34, head=8168ec1, dirty_run_paths=[]；仓库 consistency 产物未改写 |
| prereg 完整性 | `git diff HEAD -- configs/prereg/ configs/protocol.yaml` = 空；v2.1–v2.7 **全部 TRACKED**，未篡改 ✅ |

failed=34 = 22 历史 superseded + 12 个 2×2 字段假阳性（见 §3），**无其它非 superseded 失败**。

---

## 2. 12 格 provenance / 数据 / 对角核对（全部通过 ✅）

- **provenance（12/12）**：每格 config 含 `git_hash`（fec8a64/43cc800/…/8e85071 等，逐格 commit）、`calibration_version`/`validation_version`（legacy/fixed 四组合）、`seed`（0/1/2）、`bootstrap_seed`、`dtype=bfloat16`/`kernel=sdpa`/`zero_re_prefill=true`、`layer_map`=identity 28→28、`mapper`=affine_per_layer_head、`ridge_lambda=0.001`、`input_sha256`（train/val 四份）、`identity_check=true`、`joint_zero_re_prefill=true`。teacher/student 为审计入口硬编码默认（Qwen3-1.7B→0.6B，等深断言）。✅
- **数据哈希（48/48）**：12 格各 4 条 `input_sha256` 与磁盘 JSONL 磁盘实测**全部匹配**，并与 `data/audit_2x2/{legacy,fixed}/_index.json` 登记一致（legacy=458de18 生成器、fixed=efc3ba3 生成器，各 train120/val60）。✅
- **L 值复算（12/12）**：从每格 scores 重算 `L = mean(self dual) − mean(joint dual)`，与 formal_summary 的 L 值**全部一致**（如 A11_s0=0.400、A00_s1=−0.050）。✅
- **对角核对（6/6）**：A00_s{0,1,2} 与 `p1_gpu_mvp_repro_seed{0,1,2}`、A11_s{0,1,2} 与 `p1_clean_mvp_seed{0,1,2}`，按 `sample_hash==cache_hash` 匹配的 joint E_CF **各 60/60 逐对完全一致**。属实。✅

---

## 3. consistency 假阳性专项判定

- **事实**：12 格在 consistency_check 中 `ok=false`，**唯一原因**为 `unknown model_pair '': no PAIR_EXPECT entry and teacher/student paths do not identify a known pair`；同时 12 格 `traceable=true`、`run_code_unchanged_vs_head=true`、`code_tracked=true`、`dirty_run_paths=[]`。无其它失败原因。
- **成因**：审计入口 config 用 `calibration_version`/`validation_version` + 四份数据路径 `input_sha256` 标识数据版本，**有意不写 `model_pair`/teacher/student 字段**（模型由入口硬编码默认 1.7B→0.6B + 等深 28→28 断言唯一确定）。`consistency_check.py` 的 `_check_model_pair` 只认 `model_pair`/teacher/student 路径，不识别新的版本字段 → 误报。
- **判定**：**确认为字段对接假阳性，非数据/指标错误**。模型身份、数据、指标、provenance 均已独立核实无误（§2）。
- **v2.7 是否允许替代字段**：v2.7 §1 `run_environment.model_pair="MVP 等深 Qwen3-1.7B→0.6B（28→28）"` 要求模型口径固定，但**未规定必须以 `model_pair` 字段字面呈现**，也未禁止用等价的 `calibration_version/validation_version` + 硬编码 teacher/student 表达。故替代字段在 v2.7 下**合规**，但造成审计工具契约失配。
- **两种处置（请 PI 择一）**：
  - **选项 A（报告标注，零代码改动）**：在 compliance note / errata 显式标注「2×2 格 `model_pair` 不适用，模型由入口硬编码 1.7B→0.6B + 等深断言唯一确定；consistency 的 ok=false 仅为字段假阳性」。优点：不动 `scripts/**`、符合本项目「审计脚本不宜在签 off 节点频繁改动」的保守纪律；缺点：每次审计均显示 12 条假阳性告警，需人工解释。
  - **选项 B（修审计脚本，工程师在 `scripts/**` 实现）**：扩展 `_check_model_pair`，识别 `calibration_version/validation_version` + `input_sha256` 组合并按入口硬编码默认推断 MVP 对，使 12 格 `ok=true`。优点：告警归零、机器可读结论干净；缺点：改审计代码，须纳入新 commit 并回归测试，且不应改变任何历史 run 产物。
  - **审稿倾向**：若追求「投递前审计零告警、下游自动汇总不误判」，**建议选项 B**（由工程师实现 + 新 commit + 回归），因为这是工具契约 bug、修复不触及冻结判据或 run 产物；若 PI 优先最小改动与零回归风险，选项 A 亦完全可接受。本审计**不代为决定**，按 PI 裁择执行。

---

## 4. 统计口径合规（发现 C1，主要）

- **v2.7 §2 要求**：bootstrap 主聚类单元 = `template_family`；pair-level 作敏感性；簇数 <24 标 `exploratory=true`；不得只报较窄的一套。
- **实测偏差**：`audit_2x2_bootstrap.json` 中 12 格全部为 `cluster_unit="cluster-fallback"`、`n_clusters=60`、`exploratory=false`（96 个 arm 条目全如此）。根因：审计入口写 scores 时只写 `cluster`（逐对唯一，如 `val-T-F1-person-C-000`）与 `slice_id`，**未把源 JSONL 已有的 `template_family` 字段带入 scores**（对比：p1_clean scores 含 `template_family`，9 族）；bootstrap 因缺该字段回退到逐对唯一簇。
- **影响量化**（A00_s0 joint 独立复算）：template_family 聚类 = **8 簇、`exploratory=true`**、CI `[1.373, 2.427]`；而报告 fallback = 60 簇、`exploratory=false`、CI `[1.614, 2.324]`。**即当前 2×2 CI 重演了 v2.3 已修的「逐对唯一簇→CI 偏窄、未标探索性」缺陷**，与冻结 v2.7 口径不符。
- **主终点无 CI**：v2.7 主指标为 L（Self−Joint 双侧正确率差），预固定对比为 L 的四格差；formal_summary 这些对比**仅给点估计**（如 calibration effect 0.3667），未提供配对 bootstrap CI。v2.7 §2 要求对成对终点做 bootstrap，当前 L 对比未产出相应区间。
- **敏感性**：v2.7 `predeclared_sensitivity`（F1–F4、剔除候选相同样本、F6）在 formal_summary 中**未见执行结果**。
- **判定**：C1 为**主要统计口径偏差**，不否定 12 格数据真实性，但使 2×2 的显著性/探索性陈述不符合 v2.7 冻结口径。需在 P5 重新签 off 前补齐：将 `template_family` 带入 scores 并重跑 bootstrap（得 8 簇 exploratory CI）、为 L 对比产出配对 CI、报告三项预固定敏感性。

---

## 5. 对论文因果措辞的放行/限制建议（发现 C2，主要）

- **2×2 结果对应的判读分支**：三 seed 上固定 val 换校准语料，L 差方向全正（legacy val：0.367/0.283/0.217；fixed val：0.133/0.333/0.067），对应 v2.7 §3 `calibration_version_effect`（方向稳健）。按该分支 action，论文**可保留「校准语料版本在这些样本上影响迁移判断」的受控观察措辞**。
- **但 v2.7 硬边界**：`causality_boundary` 明确四格只识别「两个数据版本整体切换」，**不得**说成去重/退化对/模板重叠任一单项缺陷的因果；`causality_wording_rule` 要求否则撤除 "data defects manufactured/directly produced" 强措辞。
- **main.tex 现状（越界）**：第 67 行 "data defects manufactured a false…"、第 361 行 "These defects directly produced the spurious positive findings"、第 564 行表题 "Directional reversal caused by repairing the data"、第 589 行 "concrete data defects were sufficient to manufacture a…"、第 738 行 "defects manufactured a statistically convincing but false positive"。这些是**单项/整体缺陷→翻转的因果强措辞**，越过 v2.7 允许的「版本整体切换受控观察」边界。
- **建议（限制，不放行强因果）**：写作者按 v2.7 将因果句降级——可写「在受控 2×2 对照中，校准语料版本切换在各 seed 上稳定改变 L（受控观察）」；将 "manufactured/directly produced/caused by" 改为「修复前后方向翻转（描述性）」；明确「无单项缺陷因果识别、未见模板主要在 probe/test 无法用 val 推断」。**在 C2 完成前，不建议放行现有因果措辞**。

---

## 6. 风险清单与 P5 重新签 off 前置条件

| 编号 | 项 | 等级 | 前置处置 |
|---|---|---|---|
| C1 | 2×2 bootstrap 退化为 pair-fallback、无 L 对比 CI、未标 exploratory、缺三项敏感性（§4） | **主要** | 工程师把 `template_family` 带入 scores 并重跑 bootstrap（8 簇 exploratory）、补 L 对比配对 CI 与三项敏感性；审稿人复核 |
| C2 | main.tex 单项/整体因果强措辞越 v2.7 边界（§5） | **主要** | 写作者按 v2.7 降级为「版本整体切换受控观察 / 描述性翻转」，删 "manufactured/directly produced/caused by" |
| C3 | consistency 字段假阳性（§3） | 次要 | PI 择一：选项 A 报告标注 / 选项 B 工程师修脚本识别新字段（+新 commit+回归） |
| C4 | 论文缺 2×2 受控观察段（当前 main.tex 无 2×2 内容） | 次要 | 写作者新增一段如实报告四格 L、calibration effect 方向与归因边界 |

**P5 重新签 off 前置条件（全部满足方可放行）**：
1. C1 闭环（统计口径合规，template_family 主 CI + exploratory + L 对比 CI + 敏感性）；
2. C2 闭环（因果措辞按 v2.7 降级，无单项缺陷因果）；
3. C3 由 PI 择定处置并在审计/errata 落实；
4. C4 论文补 2×2 受控观察段，贡献(1)(2) 撤回/(3) withheld、主终点未评估、封存 test 未碰等不变量无回归；
5. 复核通过后由真实 PI 人工完成 TMLR 提交动作（署名/邮箱/账号/版权/AE 建议）。

**不变量确认**：本实验未恢复任何贡献、未触碰主终点/封存 test、未改样本定义或 L 口径（formal_summary interpretation 与 summary 的 contribution_status_unchanged 一致）；12 格数据/provenance/对角核对真实无误——这些**不构成阻塞**。

---

## 7. 结论

2×2 补充实验的**数据真实性、provenance、对角一致性与失败留痕全部合规**（12 格哈希全匹配、对角 60/60、L 值复算一致、冒烟 2 失败+修复 commit c1a161a/03c9f50 留痕齐全、正式格全 attempt1、逐格 commit 链完整）；consistency 的 12 条 ok=false 确认为**字段对接假阳性**（数据/指标无误，v2.7 允许替代字段），处置方式请 PI 在选项 A/B 间择定。但存在**两项主要合规问题**：C1（bootstrap 退化 pair-fallback、无 L 对比 CI、未标 exploratory、缺敏感性，违反 v2.7 §2）与 C2（main.tex 单项因果强措辞越 v2.7 §3 归因边界）。据此**不建议立即 P5 重新签 off**；须按 §6 五项前置条件闭环（核心为 C1 统计口径补齐与 C2 因果措辞降级）后再交真实 PI 提交。**贡献(1)(2) 撤回、(3) withheld、边界/负面定位维持不变。**

**签署：reviewer（对抗性审阅），2026-11-23。**

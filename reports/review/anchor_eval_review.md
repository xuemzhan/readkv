# SQuAD 外部锚点评测 · 阶段合规复核报告

> 审稿人：reviewer（对抗性审阅 / readkv）。日期：2026-11-23。
> 依据：`docs/decisions/final_boundary_study_signoff.md`（S1/S2 收尾背景）、`configs/prereg/external_validity_v2.4.yaml`（预承诺三情形）、`reports/anchor_eval_summary.json`、`reports/engineer_status.md` §15、`reports/runs/anchor_squad_{affine,kd}_seed0/**`、`reports/data/anchor_license_check.md`。
> 当前 HEAD=`b7b9f50`。**范围**：锚点阶段合规复核（provenance / 许可 / 统计口径 / 三情形判读 / 贡献状态不变）。本轮未改代码/数据/prereg/论文。

---

## 0. 总体判定

> **合规判定：通过。锚点评测在 provenance、许可、数据隔离、统计口径与预承诺三情形判读上均合规；`exploratory_disclosure` 归类合理；贡献(1)(2)(3) 状态未变；无「跨源普适性/恢复贡献」主张。可进入 P5 最终签 off 的合规复核环节（最终投递仍受真实 PI 的 venue/署名/时机人工决策约束）。**

附 4 项需在 P5 投递前如实披露的边界（§5），均不改变合规判定。

---

## 1. 必做动作执行结果

| 动作 | 结果 |
|---|---|
| `.venv/bin/python -m scripts.bootstrap_ci_report` | 成功，31 runs → `reports/bootstrap_summary.json`；两个锚点 run 的 `arms={}`、`protocol=v1.0`、`stats_convention=n/a` → **锚点未被纳入合成 E_CF CI**，符合「不混算/不重算冻结 CI」 |
| `.venv/bin/python -m scripts.consistency_check` | checked=31, failed=22 → `reports/consistency_report.json`；**两个锚点 run 均 `ok=true / traceable=true / code_tracked=true / dirty_run_paths=[]`**（22 失败为历史旧 run，与本阶段无关，见 §5.4） |
| prereg 完整性 | 受跟踪的 v2.1/v2.2/v2.3/v2.4/v2.5/protocol `git diff HEAD` = 空（未篡改）；**v2.6 未纳入 git 跟踪**（见 §5.3） |

---

## 2. 必做项逐条核实

### 2.1 provenance 与数据隔离 ✅

- 两个 run 的 `config.json`：`git_hash=b7b9f50`(=HEAD)、`zero_re_prefill=true`、`dtype=bfloat16`、`kernel=sdpa`、`seed=0`、`bootstrap_seed=0`、`data_sha256=80a5225e…82d8`、experiment 内 `protocol_version=2.4`、`synthetic_test_used=false`、`anchor_usage=evaluation_only (no rewriting, no derived corpus release)` —— **字段齐全**。
- `sha256sum data/anchors/squad/dev-v2.0.json` = `80a5225e94905956a6446d296ca1093975c4d3b3260f1d6c8f68bc2ab77182d8`，与 summary/config/metrics/engineer §15 的登记**逐字一致**。
- 代码溯源：`git diff 938f3a0 b7b9f50 -- experiments/ src/readkv/ scripts/` = **空**；锚点评测入口由 commit `938f3a0` 引入，run 时 HEAD=`b7b9f50`，跑分代码与 HEAD 一致、工作区 clean → **无 R1 重演**。
- **仅评测用途**：`data/anchors/squad/` 下只有原始 `dev-v2.0.json` + `LICENSE-CC-BY-SA-4.0.txt`，**无任何改写语料或衍生 corpus 发布**；scores.jsonl 的 `split=anchor_squad_dev`，独立于合成 test。合规。

### 2.2 EM/F1 独立复算 ✅

从两个 `scores.jsonl`（各 480 行 = 240 例 × self/joint）独立重算：

| run | self EM/F1 | joint EM/F1 | joint/self F1 | 与 summary |
|---|---|---|---|---|
| affine | 0.000 / 0.197473 | 0.000 / 0.005067 | 2.6% | 一致 |
| kd_only | 0.000 / 0.197473 | 0.000 / 0.001389 | 0.7% | 一致 |

数值与 `anchor_eval_summary.json`/metrics 完全吻合。检查 `pred` 字段（如 `"France\nOkay, so the question is asking where Normandy is located..."`）显示 base 0.6B 生成冗长自由文本而非纯抽取答案——**EM 全臂触底属未微调 base 模型的预期行为**，F1 作为分度指标使用恰当。

### 2.3 v2.4 三情形判读复核 ✅

v2.4 `predeclared_interpretation` 三情形：reinforce（复现 affine 失败 + kd 保持 utility）/ narrow_scope（结果与合成相反）/ exploratory_disclosure（混合或样本不足）。

实际结果：affine 失败方向**复现**（F1 0.1975→0.0051）；但 kd_only **也坍塌**（0.1975→0.0014，未复现合成域「kd 保持 utility」对照）；EM 全臂触底；仅 seed0 / 240 例。按 v2.4「锚点臂 seed0 即可」合规，但样本与信号混合。判 `exploratory_disclosure` —— **归类合理**（既不满足 reinforce 的「kd 保持 utility」条件，也不属于 narrow_scope 的「affine 不坍塌/gap 消失」）。符合 v2.4 hard_rule：未事后择支、未改判据、未恢复贡献。

### 2.4 贡献状态与措辞约束 ✅

- `anchor_eval_summary.json` 明确 `contribution_status_unchanged`：contribution_1=withdrawn、2=withheld、3=withheld，与 v2.4 invariants 一致。
- `findings` 明确「不反转叙事、不恢复任何贡献」「不足以强化失败边界的跨数据源普适性」。**未出现「跨源普适性」「恢复贡献」「方法增益」主张**。合规。

---

## 3. 统计纪律

- **未混算/未重算**：bootstrap 输出中锚点 `arms={}`、`protocol=v1.0`、`stats_convention=n/a`，确认锚点不进入合成 E_CF 主终点、不重算冻结 CI；summary 明记 `synthetic_test_mixing: NONE`。✅
- **seed 口径**：v2.4 明示「锚点臂 seed0 即可」，单 seed 不违规。✅
- **聚类**：锚点输出 EM/F1 分度指标，v2.4 未要求锚点做 template_family/source 簇 bootstrap（该要求针对 real 臂与 E_CF 主终点）；锚点按整体 EM/F1 报告，无「逐对唯一簇冒充独立样本」问题。✅

---

## 4. 合规通过项汇总

| 项 | 判定 |
|---|---|
| git_hash/zero_re_prefill/dtype/kernel/data_sha256 齐全且一致 | ✅ |
| 数据哈希指向 80a5225e…82d8（实测一致） | ✅ |
| 仅评测用途、未改写/再发布 SQuAD 语料、许可文件在位 | ✅ |
| 与合成 test 未混算、未重算冻结 CI | ✅ |
| EM/F1 独立复算一致、EM 全 0 为 base 模型预期 | ✅ |
| v2.4 三情形判 `exploratory_disclosure` 合理、无事后择支 | ✅ |
| 贡献(1)(2)(3) 状态未变、无跨源普适性/恢复贡献主张 | ✅ |
| 锚点 run 通过 consistency_check；provenance 无 R1 重演 | ✅ |
| 受跟踪 prereg（v2.1–v2.5）未篡改 | ✅ |

---

## 5. 剩余风险 / P5 投递前需披露项

| 编号 | 项 | 等级 | 处置 |
|---|---|---|---|
| D1 | **EM 全臂触底 + F1 替代指标解释边界**：EM=0 使跨臂比较只能依赖 F1；base 0.6B 未微调、生成冗长文本，F1 绝对值低且受输出长度/格式影响。F1 坍塌（0.1975→0.005/0.001）可作相对臂对照，但不应表述为「SQuAD 任务能力」绝对结论 | 次要 | 论文须写明「EM floor / F1 仅相对对照 / base 未微调」，summary limitations 已覆盖，保持 |
| D2 | **样本量 240 + 单 seed**：仅 240 answerable 例、seed0；v2.4 允许锚点 seed0，但不足以支撑强统计推断 | 次要 | 维持 `exploratory_disclosure`，禁止强显著性/普遍化措辞 |
| D3 | **v2.6 未纳入 git 跟踪**：`configs/prereg/ai_generated_data_v2.6.yaml` 为 untracked（其余 v2.3–v2.5 均 tracked）。本阶段锚点评测不依赖 v2.6，但冻结文件的版本可追溯性存在缺口 | 次要 | 请权限角色补 commit；与本锚点结论无关，不阻塞本阶段 |
| D4 | **consistency failed=22 + model_pair_check 静默跳过**：22 失败均为历史 run 因 HEAD 前进触发「run code differs vs HEAD」；另锚点 config 无 `model_pair` 字段，`model_pair_check` 返回 ok=false 但**未被计入 problems**（ok 仍为 true）——审计对该字段静默放行 | 次要 | 不构成锚点不合规；建议审计脚本对外部锚点显式标注「model_pair 不适用」，避免误读 |

---

## 6. P5 最终签 off 建议

- **合规判定：通过**，锚点阶段可进入 P5 最终签 off 的合规复核环节。
- **建议 PI**：在 P5 签 off 前确认 (a) 论文已按 §5 D1/D2 披露 EM floor / F1 边界 / 240 例 / 单 seed / 探索性；(b) v2.6 补 commit（D3）；(c) 贡献(1)(2)(3) 状态与「边界/负面结果」定位维持不变；(d) venue/署名/投递时机由真实 PI 人工决策（v2.4 forbidden 末条）。
- **不触发**：本阶段未发现任何需停冻结、改判据或恢复贡献的情形；锚点结果不与合成 test 混算、不改动已撤回的贡献状态。

---

## 7. 结论

SQuAD 外部锚点评测在 provenance（git/data 哈希/code diff 全一致）、许可与仅评测用途、数据隔离（未混算合成 test、未重算冻结 CI）、EM/F1 复算、v2.4 三情形判读与贡献状态不变等方面**全部合规**；`exploratory_disclosure` 归类合理，EM 全 0 与 F1 坍塌的解释边界已如实记录。两个锚点 run 通过一致性审计，受跟踪 prereg 未篡改。剩余 D1–D4 均为披露/溯源层次要项，不改变合规判定。**合规判定：通过；建议可进入 P5 最终签 off 的合规复核，最终投递仍受真实 PI 人工决策约束，审稿侧不定稿。**

**签署：reviewer（对抗性审阅），2026-11-23。**

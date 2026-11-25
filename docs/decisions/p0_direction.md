# 阶段方向批复与 Go/No-Go 前置决议（P0 · V2.0）

> 决议人：PI / 课题组长。日期：2026-11-22。适用协议：`docs/protocol.md` V2.0（2026-11-22 修订），`configs/protocol.yaml` version 2.0。
> 本决议是**方向批复 + 前置意见**，不是任何阶段的放行证书，也不产生科学结论。所有阶段放行须在 `reports/runs/<run_id>/scores.jsonl` 真实产物与审稿人审计之后另行裁决。
> 依据核对文件：`README.md`、`docs/protocol.md`、`docs/agent_team.md`、`docs/gpu_handoff.md`、`configs/protocol.yaml`、`configs/eval.yaml`、`configs/gates.yaml`、`configs/prereg/` 全部四个判据文件。

---

## 1. 确认的研究主线与主终点

### 1.1 V2.0 主线（确认，冻结方向）

主线为**反事实功能保真（counterfactual functional fidelity）**，而非"训一个更强 Mapper"。判据：

- RQ1–RQ3 的证据要求见 `docs/protocol.md §1.1`；可证伪假设 H1–H4 见 §1.2。
- 评价层 / 机制层 / 方法层三层证据中，**只有评价层新增而无机制或方法改善时，不声称完成高水平方法论文**（§1.2、§10）。
- 严格 zero re-prefill：Joint 是唯一可部署迁移臂；K-only / V-only / Oracle 仅为离线诊断，不得宣传为可部署方法。教师对 `d_A`、`d_B` 必须各自独立 Prefill，禁止篡改缓存字节伪造另一文档。
- 判据先写后跑；封存测试只读，不得按结果调超参。

PI 裁决：**维持 V2.0 主线不变，驳回任何以"提升常规 QA / likelihood / 平均分布分数"为单一目标的路线收窄。**

### 1.2 主终点 E_CF 定义（确认，冻结）

```
g(C,q)   = log P(A|C,q) − log P(B|C,q)
D_self   = g(C_S(d_A),q) − g(C_S(d_B),q)
D_trans  = g(Ĉ_S(d_A),q) − g(Ĉ_S(d_B),q)
E_CF     = |D_trans − D_self|
normalized_E_CF = |D_trans − D_self| / (|D_self| + τ)
```

- **主终点 = 封存测试上新方法与最强行为基线（`configs/eval.yaml` 中 `primary_baseline: kd_only`）的成对 `E_CF` 差异**；模板 / 来源簇级 paired bootstrap，95% CI，**CI 上界 < 0** 才视为稳健改善（`configs/protocol.yaml statistics`、§4.5、§9）。
- `E_CF` **必须与双向成功率 `dual_correct`、方向一致率 `flip_consistency`、覆盖率 `coverage`、与无信息控制组差距 `info_gap` 联合报告**（§4.1、§4.3，`configs/protocol.yaml jointly_report`）。单独 `E_CF` 下降不构成改善声明——`D_self≈0` 时恒定输出也可低误差。
- F5 为非翻转负控，不计入"必须翻转"分母（`flip_denominator_excludes: [F5]`）；F6 做长度 / 位置控制。
- ≥3 训练种子报告方差，不把"若干 seed 均值略高"作强结论；多重比较用 Holm；`P>0.05` 不等于等效。

---

## 2. 已冻结判据清单与版本号

### 2.1 主协议与统计配置

| 文件 | 版本 / 状态 | 冻结要点 |
|---|---|---|
| `docs/protocol.md` | V2.0，2026-11-22 修订 | 研究问题、E_CF 指标族、审计对照、统计设计、机制判据、决策树（§8）、贡献门槛（§10） |
| `configs/protocol.yaml` | version "2.0"，`frozen: true` | τ 选择 `validation_only`；τ=1.0；self_threshold=0.1；主终点 `paired_E_CF_difference`；统计 ci=0.95 / n_resamples=10000 / cluster_paired / cluster_unit=template_or_source_doc / min_training_seeds=3 / Holm；切片 F1–F6；数据规模 probe 40 / train 120 / val 60 / test 300；7 类控制组 |
| `configs/eval.yaml` | V2 评测配置 | seeds [0,1,2]；tau=1.0；self_threshold=0.1；primary_baseline=kd_only；模型对 mvp/main/stress；device cuda / dtype bfloat16 / kernel sdpa |
| `configs/gates.yaml` | version "1.0"（V1 遗留锚点） | H1 identity cosine ≥0.9998；H2 epsilon=0.02；H3 exploitability。仅作审计门 / 锚点，**V2 主终点不是这些门** |

### 2.2 预注册决策规则（`configs/prereg/`）

| 文件 | `frozen_at` | 适用阶段与判据 | 角色定位 |
|---|---|---|---|
| `phase1_benchmark_decision.yaml` | `protocol-v2.0` | **P1 主线**：H1。`distortion_present + quality_pass` → `distortion_exists`（继续 P2/P3）；`no_distortion + quality_pass` → `boundary_study`（按决策树转向）。封存后禁止 `changing_tau_on_test` / `dropping_controls` / `selecting_seeds_by_result` | V2 主线判据 |
| `phase3_method_decision.yaml` | `protocol-v2.0` | **P3 主线**：H3。`method_contribution` 需 `ecf_improved=true AND ci_upper<0 AND flip_consistency≥0.7`；`ecf_improved 且 dual_correct<0.7` → `tradeoff`；否则 `method_downgraded`。禁止 `changing_loss_weights_on_test` / `changing_tau_on_test` / `dropping_seeds` | V2 主线判据 |
| `stage1_decision.yaml` | `protocol-v1.0` | 对称 Key 前置：arms A/B/C/D，primary `corrected_em_k_only`；C≥0.15 且 CI 排除 A/B 且 D≤C → positive；routing 改善而 EM 不动 → negative | **V1 遗留机制基线**，非 V2 主终点判据，不得用它判定 E_CF |
| `stage2_decision.yaml` | `protocol-v1.0` | consumer-space 三道门：V-only/Joint 过 H2 → `consumer_space_general`；部分改善 → `partial`；无改善 → `task_conditioned`。禁止改 epsilon / 删臂 / 换 benchmark | **V1 遗留机制基线**，非 V2 主终点判据 |

PI 提示：现有两个 V1（`protocol-v1.0`）判据是机制前置 / 审计基线，**不得与 V2 主线判据混用**；V2 阶段放行只看 `phase1_*` 与 `phase3_*` 及 §4.5 统计门槛。

### 2.3 冻结参数逐项核对（含一处缺口，如实记录）

| 参数 | 冻结状态 | 值 / 说明 |
|---|---|---|
| decision rule | ✅ 已冻结 | `configs/prereg/` 四文件 `frozen: true`；§8 决策树六分支 |
| 主终点 | ✅ 已冻结 | `paired_E_CF_difference`，簇级 paired bootstrap，CI 上界 < 0 |
| τ | ✅ 已冻结 | `validation_only`，τ=1.0（`configs/protocol.yaml`、`configs/eval.yaml`） |
| Self 有效阈值 | ✅ 已冻结 | `self_threshold=0.1` |
| Huber 阈值 | ✅ **已冻结（protocol-v2.1，见 §7）** | 新增 `configs/prereg/phase3_loss_config_v2.1.yaml`：δ 标称 1.0，验证集网格 {0.5,1.0,2.0} 与固定选择规则；最终值须在封存测试前由验证集网格锁定，不得按测试结果调整 |

PI 裁决（缺口处理，非改判据）：**PI 不自行填入任何 Huber 数值，也不事后修改已冻结文件。** 由科学家基于验证集数据给出 Huber 阈值与标签平衡策略的建议值；在最终裁决阶段以**新增版本判据文件**冻结。该缺口已于 2026-11-22 以 `configs/prereg/phase3_loss_config_v2.1.yaml`（`frozen_at: protocol-v2.1`）完成冻结，详见 §7；δ 的最终取值仍须由验证集网格在封存测试前锁定，并由审稿人专项复核。

---

## 3. P0–P5 放行判据摘要与当前 Go/No-Go 前置意见

### 3.1 放行判据摘要（依据 `docs/agent_team.md §4`、`docs/gpu_handoff.md §6`）

| 阶段 | 主导 | 放行判据 |
|---|---|---|
| P0 基座 | 工程师 | E0 实现门通过（测量误差上限显著低于待研究效应）；Identity / cache round-trip 一致性、形状 / 位置 / 数值一致性全部通过；`zero_re_prefill` 标志就位 |
| P1 基准 | 科学家 | 确认存在**未被强基线消除**的反事实失真（`phase1_benchmark_decision.yaml`）；否则按 §8 决策树转边界研究 |
| P2 机制 | 科学家 | 机制诊断在**验证集有预测价值**（不仅事后相关）；产出候选机制公式；K/V 四臂与局部分解就位 |
| P3 方法 | 工程师 | 相对强基线有**非偶然改进**（满足 `phase3_method_decision.yaml` 的 `ci_upper<0`、`flip_consistency≥0.7` 且常规任务不退化）；否则停止扩大模型 |
| P4 泛化 | 工程师 | 非等深 pair、未见模板 / 真实文档、封存测试；报告跨设置稳定性、CI、失败边界与不利结果 |
| P5 成稿 | 写作者 | 通过 `docs/protocol.md §10` 贡献表述门槛；PI 签 off 投递 |

### 3.2 PI 当前 Go/No-Go 前置意见（关键裁决）

本机已核实具备真实 GPU 证据产出条件（见 §4），故采用**条件放行（Conditional GO）**：方向与设计工作直接放行；证据产出在满足前置条件后放行，科学结论与投递仍须证据 + 审计齐备后另行裁决。

**证据阶段放行的三项前置条件（缺一不可）**：

- **(a) Huber 阈值冻结**：✅ **已满足（v2.1）**——PI 已以新增文件 `configs/prereg/phase3_loss_config_v2.1.yaml` 冻结 δ 标称值、网格与选择规则（见 §7）；待科学家/工程师在验证集运行网格并于封存测试前锁定最终 δ 值，审稿人复核。P3 的 Huber 前置门由 No-Go 更新为**条件满足**。
- **(b) E0 实现门通过**：按 `docs/gpu_handoff.md` 逐项实现 `models/hooks.py`，Identity / cache round-trip / 形状位置数值一致性全部通过，测量误差上限显著低于待研究效应。
- **(c) 真实证据 + 审计通过**：真实 GPU run 在 `reports/runs/<run_id>/scores.jsonl` 产出正式结果，并通过审稿人 `bootstrap_ci_report` + `consistency_check` 审计。

| 事项 | 前置意见 | 理由 |
|---|---|---|
| V2.0 方向 / 主终点 / 冻结判据 | **GO（确认）** | 与 §1–§2 核对一致，无歧义；目标准予冻结 |
| 科学家算法规格书、E0–E7 实验设计表、数据构造方案、GPU 接续清单 | **GO（准备）** | 属设计产出；Huber 阈值建议值由科学家给出，最终裁决阶段按 (a) 冻结 |
| P0 E0 实现门**运行与放行** | **条件 GO（满足 (b) 后放行）** | 本机具备 4090 24GB GPU 与依赖安装条件；须按 `docs/gpu_handoff.md` 逐项实现 `models/hooks.py`、E0 实测通过后才签发 P0 放行证书 |
| P1–P4 证据产出 | **条件 GO（满足 (a)(b)(c) 后放行）** | 真实 GPU 证据来源已具备，但 mock 数字不是科学证据；无 `reports/runs/` 真实产物与审计即无统计结论 |
| P5 投递 / §10 贡献措辞(2)(3) | **NO-GO（当前，待证据）** | 门槛证据未产出；未经机制 / 方法证据不得使用贡献(2)(3) 措辞 |
| 阶段间跃迁（P0→P1 等） | **条件 GO（按闭环裁决）** | 每阶段跃迁须经"产物齐备 → 审稿人 `bootstrap_ci_report` + `consistency_check` → PI 裁决"闭环，不接受跳阶段 |

一句话总结：**方向 GO / 证据条件 GO（Conditional GO），总体结论不变**。(a) 已满足，(b)(c) 待完成；证据产出仍须 E0 实现门通过 + 真实 run 的 `scores.jsonl` + 审稿审计通过；mock 数字不得作为科学证据。任何科学结论与投递均待真实证据与审计后另行裁决。

### 3.3 决策树授权（PI 保留裁决权）

`docs/protocol.md §8` 分支由 PI 在**真实证据齐备后**执行，现预先声明裁决口径：

- 强基线已接近 Self → 批准转向边界 / 失败条件研究，不得坚持"所有方法反事实失真"。
- 有失真但机制诊断无跨样本预测价值 → 降级为现象报告，不得把局部热图解释为因果理论。
- 机制有效但 CF 方法不优于 KD → 方法贡献降级，不得挑选种子 / 任务掩盖无效。
- CF 改善 `E_CF` 但常规任务退化 → 要求调整多目标约束或如实报告权衡，不得省略退化。
- 仅在合成域成立 → 明确适用边界，不得宣称通用 / 真实世界迁移。
- 机制与方法均稳定优于强基线 → 补齐跨模型、成本、统计、公开代码后再考虑投递。

现有证据状态不足以触发上述任何分支，故本次不作分支裁决。

---

## 4. 执行环境与证据效力声明（硬约束）

PI 核实本机环境（2026-11-22 实测更正，取代此前"无 GPU / 无依赖"的错误判断）：**具备真实 GPU 证据产出的硬件与软件条件**——NVIDIA GeForce RTX 4090（24564 MiB，空闲约 23272 MiB），驱动 580.65.06；uv 0.9.17（可用 `uv venv` + `uv pip install -e ".[dev]"` 安装依赖）；PyPI 与 https://modelscope.cn/ 可访问，模型 / 数据可从 ModelScope 下载；磁盘约 361 GB 可用。据此明确：

1. **具备条件不等于已产出证据。** 环境满足 `docs/gpu_handoff.md §0` 的单卡 24GB 要求，但证据仍须按该文档逐项实现 `models/hooks.py` 并通过 E0 实现门后才能进入 P1；在此之前不得声称任何阶段已放行。README 中"51 passed"为仓库声称的历史状态，**本机尚未复现、不构成当前证据**。
2. **必须先过 E0 实现门**：在 4090 上以真实 dtype / kernel 实测 Identity / cache round-trip / 显式 position offset 的残差，确认测量误差上限显著低于待研究效应；`logit cosine ≥0.9998` 仅为 V1 继承的 identity 锚点参考值，非 V2 主终点阈值。
3. **Mock 数字不是科学证据。** 所有"计划数字、示意数值、mock 报告（`reports/*mock*`）、README 示例命令输出"仅用于验证判据接线与报告格式，**一律不得**写入论文结果、不得作为 Go 依据、不得作为统计结论来源。
4. **证据唯一来源**：`reports/runs/<run_id>/scores.jsonl`（真实 GPU 后端，正式 `run_id`，非 mock 目录），所有主结果可由此重算；统计脚本与训练脚本分离。
5. **不得把计划当证据**：`docs/protocol.md`、`docs/gpu_handoff.md` 中的样本量、效应、成本均为目标值 / 规划值，不是观测结论。
6. **不可变产物**：`reports/runs/*` 不可写、不可改；违反判据的运行只能新开 `run_id`，不得回改。
7. **zero re-prefill**：每次运行须记录 `zero_re_prefill` 标志；Joint 臂禁止学生处理文档 token；Oracle 不进 Joint 推理图。
8. **先写后跑**：封存测试运行前必须完成 §9 固定项 + prereg 机器可读 conditions；封存后禁止改 τ / 删对照 / 按结果挑种子（见各 prereg `forbidden_after_run`）。

PI 立场：具备真实 GPU 条件意味着"证据条件 GO"，但**绝不等同于降低判据**。禁止以 mock 结果判断 P1 失真、以计划替代结论、或在 E0 未实测通过前跳阶段。

---

## 5. 给下游的明确指令

### 5.1 给科学家

1. **确认主线**：按 V2.0 反事实功能保真设计，不得收窄为"训更强 Mapper"；所有设计对照 `docs/protocol.md §1.2 / §4.1 / §6`。
2. **交付算法规格书 + E0–E7 实验设计表**：明确 `CF-RCT-lite`（L_KD+L_CF）与 `CF-RCT-mech`（加机制约束）；机制选择规则只用训练 / 验证集，不碰封存测试标签。
3. **执行 Huber 验证集网格（v2.1 规则已冻结）**：按 `configs/prereg/phase3_loss_config_v2.1.yaml` 在验证集网格 {0.5,1.0,2.0} 上依固定优先级选出最终 δ，于封存测试前锁定并记录 split id 与搜索成本；不得写入 `configs/protocol.yaml` 或既有 prereg 文件。最终 δ 未锁定前 P3 封存测试仍为 No-Go。
4. **对齐公平比较**：KD-only / CE-only / Consumer-space / 强行为 Mapper 同数据、同 Forward 预算、同参数量、同调参预算；明确 `primary_baseline=kd_only`；普通 QA 与反事实 QA 同报。
5. **P1  honesty gate**：若强基线已接近 Self，主动按决策树提交"边界 / 失败条件研究"建议，不得预设新方法胜出。
6. **不写代码、不改运行产物、不动 `configs/prereg/` 既有冻结文件**（如需变更走新版本）。

### 5.2 给工程师

1. **环境与模型获取**：用 `uv venv` + `uv pip install -e ".[dev]"` 安装依赖；Qwen3 模型 / 数据从 **ModelScope**（https://modelscope.cn/）下载，核对 checkpoint revision 并记录。按 `configs/models.yaml` 与 `docs/gpu_handoff.md §1` 的模型分层执行：**MVP 1.7B→0.6B（等深）→ 主验证 4B→1.7B（非等深）→ 8B 仅离线 teacher 推理**（离线生成缓存后卸载教师，不与学生训练同时驻留）。
2. **实现门优先**：在 4090 上实现 `models/hooks.py`（`capture_teacher_cache` / `inject_and_generate` / `verify_zero_re_prefill`），逐项替换 mock 并用同判据回归，先通过 E0 测量误差上限门再谈 P1。
3. **同 dtype / 同 kernel 对齐**：所有对照实验统一 dtype（bfloat16）与 attention kernel（sdpa），同 kernel 同 dtype 公平比较；bf16 小效应噪声不得事后忽略（见 `configs/eval.yaml resource`、`docs/gpu_handoff.md §7`）。
4. **独立双文档**：`d_A`、`d_B` 分别独立 Prefill，禁止篡改缓存字节；记录 shape / position_ids / 层映射 / RoPE 元数据 / 哈希；教师离线落盘后卸载。
5. **数据构造**：按六类切片 F1–F6 生成反事实对，F5 负控、F6 长度 / 位置控制，候选顺序随机交换，按实体 / 来源 / 模板簇隔离 split；规模遵循 `configs/protocol.yaml data_sizes`。
6. **正式产物**：仅在真实 GPU 后端产出 `reports/runs/<正式 run_id>/scores.jsonl` 与可复现环境清单；mock 产物单独标注，不混入正式 `run_id`；不得写 `reports/runs/*`（运行产物不可变，由实验流程生成）。
7. **统计合规**：≥3 seed（seeds [0,1,2]）、簇级 paired bootstrap（10000 resamples）、Holm 多重比较；`E_CF` 与 `dual_correct`/`flip_consistency`/`coverage`/`info_gap` 同报；每次运行确保 `zero_re_prefill=true`。
8. **不得改冻结判据 / 测试集指标**；不以 mock 冒充真实结果；下载或环境异常如实上报。

### 5.3 给审稿人（抄送，阶段产物到位后介入）

阶段产物提交后运行 `scripts.bootstrap_ci_report` 与 `scripts.consistency_check`，核对 `configs/prereg/` 未被动态篡改，并按 `phase3_loss_config_v2.1.yaml reviewer_checks` 专项复核：δ 最终值来自验证集网格且在封存测试前锁定（非 mock 占位 1.0）、标签平衡四项落实、E2 判据在独立文档上检验且 Oracle 未泄漏、E6 阈值在 E6 前以新版本冻结。

---

## 6. 变更与升级规则

- 本决议不修改任何已冻结判据；如需变更，**新增版本号并写明理由**，不回改历史文件。
- 已跑实验按当时的 `protocol_version` 解释。
- 角色间分歧由 PI 最终裁决并记录理由；PI 无法判断时列出两种选项的证据与风险，请求人工（真实 PI）决策。
- 下一裁决触发条件：E0 实测通过 + 阶段产物齐备 + 审稿完成。在此之前，证据产出维持本决议的**条件 GO（Conditional GO）**状态；未满足 §3.2 (a)(b)(c) 前置条件前不签发任何阶段放行证书，P5 投递与贡献(2)(3) 措辞维持 NO-GO。

---

## 7. 冻结裁决记录（2026-11-22 · protocol-v2.1）

**触发**：科学家交付 `docs/algorithm_spec.md` 与 `docs/experiment_design_E0_E7.md`，在两份文档「给 PI 的冻结请求」中申请补冻 δ、标签平衡、机制预测阈值及 E0/E2/E6 阈值；原 protocol-v2.0 仅规定"验证集固定"而无数值（见 §2.3）。

**裁决动作**：**新增** `configs/prereg/phase3_loss_config_v2.1.yaml`（`frozen_at: protocol-v2.1`，`frozen: true`），不回写任何既有冻结文件；主终点、τ=1.0、self_threshold=0.1 与统计设计沿用 protocol-v2.0 不变。

**冻结清单（摘要）**：

| 项目 | 冻结结论 | 状态 |
|---|---|---|
| Huber δ | 标称 1.0（logit），网格 {0.5,1.0,2.0}（必要时 `clip(q70,0.5,2.0)` 补候选）；固定优先级"E_CF 最小 → dual_correct/flip_consistency 不劣于 kd_only → 普通 QA 不退化" | ✅ 规则冻结；最终值待验证集锁定 |
| 标签平衡 | A/B 1:1、候选顺序 50/50、F5 固定配比（不入翻转分母）、L_CF 仅 Self 有效子集 | ✅ 已冻结 |
| λ 选择 | λ_KD=1.0 锚点；λ_CF/λ_local/λ_reg 同验证集/网格/预算选择并记录成本 | ✅ 规则冻结 |
| E0 误差容限 | 测量误差上限 ≤ 待研究效应 1/3（比例立即冻结）；效应由 40 对探针在 E0 前估算 | ✅ 已冻结 |
| E2 预测判据 | repair 命中率显著高于随机（簇级 bootstrap CI 下界>0）、方向一致 ΔE_CF>0 占比>0.5、分解残差≈0 | ✅ 操作化判据冻结 |
| E6 成本阈值 | **待 E6 前冻结**：触发时点为"E0 通过且 P0 放行后、E6 首跑前"，基于 MVP 学生 Full-Prefill 实测 TTFT 锁定 r_cost 与 ε_q | ⏳ 明确延期 + 触发时点 |

**对前置条件的影响**：§3.2 条件 (a) 由"待冻结"更新为**已满足（条件性）**——δ 的标称值、网格与选择规则已冻结；剩余动作是科学家/工程师在验证集运行网格、于封存测试前锁定最终 δ 值并经审稿复核。**P3 的 Huber 前置门由 No-Go 更新为条件满足；但 P3 封存测试仍受 (b) E0 门、(c) 真实 run + 审计约束，未满足前不放行。**

**总体结论**：方向 GO / 证据条件 GO（Conditional GO）保持不变，P5 投递与贡献(2)(3) 措辞维持 NO-GO。

**一致性提示（不改科学家文档，仅记录）**：`docs/experiment_design_E0_E7.md` 第 154 行仍含"本机无 GPU / 证据 NO-GO"表述，与本机已更正的环境事实（§4：RTX 4090 + uv + 已验证网络）冲突。请科学家/写作者在后续版本同步修正该表述为"方向 GO / 证据条件 GO（见 p0_direction.md §3.2 / §4 / §7）"；PI 不代改他人交付文档。

**签署：PI / 课题组长（V2.0 方向批复 · 2026-11-22；v2.1 冻结裁决 · 2026-11-22）**

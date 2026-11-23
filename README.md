# readkv

跨模型 KV 迁移的**可复现实验平台**。V2.0 研究主线和三篇论文定位：

> 反事实功能保真：即使 Mapper 在常规 QA / likelihood / 平均分布上接近学生原生缓存，是否仍保留文档事实受控变化时学生输出应出现的对应变化？

需求来源：`docs/raw/跨模型KV迁移_第三篇论文研究方案_V2.0_详细版.pdf`（V2.0 方案，2026-11-22）与两篇已有论文 PDF。目标架构见 `docs/architecture.md`，冻结判据与统计设计见 `docs/protocol.md`，GPU 接续见 `docs/gpu_handoff.md`，智能体群协作见 `docs/agent_team.md`。V2.0 论文题目、指标名（`E_CF`）、算法名（`CF-RCT`）均为工作版本。**本仓库当前证据全部来自真实 GPU 产物（`reports/runs/**`）；mock 数字只用于接线回归，不是科学证据。**

## 设计原则

1. **反事实保真为一级指标**：以成对反事实文档的 `E_CF = |D_trans − D_self|` 为主终点，但必须与双向成功率、方向一致率、coverage、无信息对照联合报告，避免“恒定输出也低误差”的退化。
2. **机制与评价并重**：Routing / Consumption 局部诊断必须在独立数据上有预测价值；只有评价层新增而无机制或方法改善时，不声称完成高水平方法论文。
3. **消费侧为目标**：默认 mapper 拟合在 student 读取状态的空间（attention output / o-projection），representation-space 与对称 Key 目标仅作机制基线 / 前置实验。
4. **严格 zero re-prefill**：除离线 Oracle 诊断外，student 的 forward 不接受任何上下文 token；每次运行记录 `zero_re_prefill` 标志；Joint 是唯一可部署的迁移臂。
5. **先写判据后跑**：`configs/prereg/` 中的 decision rule 与 τ / Huber 阈值必须先冻结；统计结论只能由 `reports/runs/<run_id>/scores.jsonl` 重算；封存测试前完成预注册。
6. **单卡预算**：Teacher 缓存离线落盘、之后卸载；8B 只做离线推理；不做长上下文与大规模非线性搜索；普通 QA 与反事实 QA 同报。

## 实现状态

- **V2 全栈已落地**：评价层 / 机制层 / 方法层（设计）在 mock 后端完整实现；GPU 后端的 `models/hooks.py` 真实前向适配**已实现并通过 P0 / E0 实现门**（不再需要按 `docs/gpu_handoff.md` 补做 hooks）。`--backend gpu` 可用。
- **测试**：`pytest` **53 passed**（V1 + V2 + hooks/kd 相关测试；较旧的“51 passed”已过期）。
- **真实 GPU 证据**：P0 / E0、P1、P2 已完成，累计 **22 个 run** 纳入 `bootstrap_ci_report` 与 `consistency_check` 汇总（其中 8 个旧 run 为 `superseded`，不计入可复现主结论；可复现主证据为 `*_repro_*` 权威 run，commit `458de18` / P2 审计 `6784780`）。主验证非等深对（4B→1.7B）旧 run 仅为 broken-transfer 失败边界，不计 H1 正向证据。
- **P2 已完全收口**：E2 三判据达标，F1（逐对 `delta_rand` 复算）/ F2（≥3 seed 与 U 稳健性）/ F5（smoke 清理）闭环，三 seed 全部 `mechanism_predictive`。
- **P3 已由人工（真实 PI）决策启动**：PI 已在 `docs/decisions/p3_task_plan.md` 排期，采用**分阶段门控**——实现 + 烟测门 → kd vs cf_lite 探路（2 方法 × 3 seed）→ 由门控决定是否续跑 cf_mech；不盲目全量 3×3。此前 P3/P4 为 NO-GO，现 P3 状态更新为“已启动、按门控推进”：可微 readout 与 `experiments/P3_gpu.py` 入口已实现（commit `885a36a`），烟测进行中，尚未产出正式 P3 run。
- **P4 仍 NO-GO**；**P5 为有条件 GO**：批准以「边界 / 实证研究（empirical / boundary study）」定位投递。详见「阶段状态」节。

## 目录

```
configs/
  protocol.yaml / eval.yaml / models.yaml / pairs.yaml / gates.yaml  # 协议、评测、模型对、门限
  prereg/phase*/decision.yaml                # 冻结的 decision rule（含数值算子）
  prereg/phase3_loss_config_v2.1.yaml        # v2.1：E0 容差、E2 判据、δ 选择规则
  prereg/phase3_loss_config_v2.2.yaml        # v2.2：δ=0.5 最终锁定（frozen_at: protocol-v2.2）
src/readkv/
  runtime/  models/  cache/                  # 底座 + CF-RCT + 双文档独立预填 + 实现门 E0
  data/build_cf_pairs.py                     # 六类切片的成对反事实构造（F1–F6）
  diagnostics/route_value.py                 # Routing/Consumption 分解 + Oracle + 对称 Key
  train/cf_rct.py  train/kd_gpu.py           # KD / CF-lite / CF-mech 成对训练 + GPU KD trainer
  evaluate/cf_pipeline.py                    # V2 端到端管线；counterfactual.py 为指标核心
  evaluate/                                  # V1 三道门与探针（保留作基线）
  stats/
experiments/
  P0_gpu.py  P1_gpu.py  P1_kd_gpu.py  P2_gpu.py  P3_gpu.py  # 真实 GPU 入口（已实现）
  P0..P5 / P3_method.py                      # mock / V1 阶段编排（mock 非证据）
scripts/
  gen_teacher_cache.py                       # 离线 teacher 缓存（mock / gpu）
  bootstrap_ci_report.py  consistency_check  # CI 重算与一致性审计
  export_task_data.py  measure_reconstruction_r2.py
reports/
  runs/<run_id>/                             # V2 不可变运行产物
  review/                                    # 4 份阶段 / P2 对抗审稿报告
  runs_index.json  runs_index_errata.json  p2_*.json  bootstrap_summary.json
  consistency_report.json  huber_delta_lock.json  engineer_status.md
docs/
  protocol.md  architecture.md  gpu_handoff.md  agent_team.md
  algorithm_spec.md  experiment_design_E0_E7.md  p3_resource_estimate.md
  decisions/                                 # final_signoff / contribution2_final_form /
                                             # p3_task_plan / huber_delta_lock / p0_direction / …（PI 裁决）
  raw/
papers/readkv_v2_draft/                      # main.tex（初稿）+ notes.md（权威数值清单，仅内部）
tests/                                       # V1 + V2 单元测试（53 passed）
.opencode/agents/                            # 已配置 agent 的 Prompt（见「Agent 团队」）
```

冻结判据与权威数值的单一来源：`configs/prereg/**`、`docs/decisions/**`、`reports/runs/**/metrics.json`、`reports/engineer_status.md`、`papers/readkv_v2_draft/notes.md`。本 README 只转抄这些来源，不重新计算统计。

## 快速开始

### 1. 安装依赖（本机实测可用）

```powershell
uv venv .venv
uv pip install --python .venv/bin/python -e ".[dev]" modelscope
.venv/bin/python -m pytest                          # 53 passed（V1 + V2）
```

环境：Python 3.13.11 / torch 2.15.0+cu132 / transformers 5.24.0 / CUDA 可用 / RTX 4090 24GB。

### 2. Mock 流程（CPU 即可，**mock 数字不是科学证据**）

```powershell
.venv/bin/python -m experiments.P0_baseline --backend mock --run-id p0 --n-train 120 --n-val 60 --n-test 300
.venv/bin/python -m experiments.P1_benchmark --backend mock --run-id p1 --n-train 120 --n-val 60 --n-test 300
.venv/bin/python -m experiments.P2_mechanism --backend mock --run-id p2 --n-train 120 --n-val 60 --n-test 300
.venv/bin/python -m experiments.P3_method --backend mock --run-id p3 --n-train 120 --n-val 60 --n-test 300
.venv/bin/python -m experiments.P4_generalization --backend mock --run-id p4 --pair main --n-train 120 --n-val 60 --n-test 300
.venv/bin/python -m experiments.P5_paper --backend mock --run-id p5 --n-train 120 --n-val 60 --n-test 300

# 离线缓存（mock 接线验证）
.venv/bin/python -m scripts.gen_teacher_cache --pair qwen3-4b-to-1.7b --n-pairs 360 --dry-run
.venv/bin/python -m scripts.gen_teacher_cache --pair qwen3-4b-to-1.7b --n-pairs 360 --backend mock
```

`--backend mock` 用确定性 CPU 后端跑通**完整管线**，仅用于接线 / 报告格式回归；**不得进入任何正式结论**。

### 3. 真实 GPU 流程（正式证据唯一来源）

从 ModelScope 下载模型（已安装 `modelscope` CLI；下载后把本地 snapshot 路径传给 `--model` / `--teacher` / `--student`，格式参照 `reports/runs/**/config.json`，例如 `/root/.cache/modelscope/models/Qwen--Qwen3-0.6B/snapshots/master`）：

```powershell
.venv/bin/modelscope download Qwen/Qwen3-0.6B
.venv/bin/modelscope download Qwen/Qwen3-1.7B
.venv/bin/modelscope download Qwen/Qwen3-4B
```

模型分层：MVP 1.7B→0.6B（等深）、主验证 4B→1.7B（非等深）、8B 仅离线 teacher 推理。以下为本机实际可用的入口与参数（参数取自各入口的 argparse，未编造）：

```powershell
# P0 / E0 实现门（学生本体自注入，identity mapper）
.venv/bin/python -m experiments.P0_gpu --run-id e0_gpu_mvp_seed0 \
  --model /root/.cache/modelscope/models/Qwen--Qwen3-0.6B/snapshots/master \
  --n-probes 40 --seed 0

# P1 基准（MVP affine/ridge mapper；seed 0/1/2 各跑一次）
.venv/bin/python -m experiments.P1_gpu --run-id p1_gpu_mvp_seed0 \
  --teacher /root/.cache/modelscope/models/Qwen--Qwen3-1.7B/snapshots/master \
  --student /root/.cache/modelscope/models/Qwen--Qwen3-0.6B/snapshots/master \
  --seed 0

# P1 kd_only 主基线（--method kd；cf_lite 用 --method cf_lite --huber-delta 0.5）
.venv/bin/python -m experiments.P1_kd_gpu --run-id p1_gpu_kdonly_mvp_seed0 \
  --teacher /root/.cache/modelscope/models/Qwen--Qwen3-1.7B/snapshots/master \
  --student /root/.cache/modelscope/models/Qwen--Qwen3-0.6B/snapshots/master \
  --method kd --seed 0

# P2 机制诊断（K/V 四臂 + 分解 + Oracle held-out）
.venv/bin/python -m experiments.P2_gpu --run-id p2_gpu_mvp_seed0 \
  --teacher /root/.cache/modelscope/models/Qwen--Qwen3-1.7B/snapshots/master \
  --student /root/.cache/modelscope/models/Qwen--Qwen3-0.6B/snapshots/master \
  --seed 0

# 报告重算与一致性审计
.venv/bin/python -m scripts.bootstrap_ci_report
.venv/bin/python -m scripts.consistency_check
```

说明：

- 以上 GPU 入口均写 `config.json`（含 `git_hash` / `protocol_version` / `seed` / `dtype=bfloat16` / `kernel=sdpa` / `zero_re_prefill=true` / `bootstrap_seed`）、`scores.jsonl`、`metrics.json`、`manifest.json`；正式 run 的 `git_hash` 必须指向含全部跑分代码且工作区 clean 的 commit（否则触发 R1 可复现性缺陷）。
- **P3 GPU 入口已就绪、烟测先行**：`experiments/P3_gpu.py`（commit `885a36a`）提供 `--method {kd,cf_lite,cf_mech} --seed {0,1,2}`，复用可微 `torch_candidate_logits()`，δ=0.5 从 v2.2 读取。按 `docs/decisions/p3_task_plan.md` 先跑烟测（non-authoritative，置于 `reports/_non_authoritative/`，**不得当证据**），门通过后按 kd vs cf_lite 串行探路、再决定是否续 cf_mech：
  ```powershell
  .venv/bin/python -m experiments.P3_gpu --run-id p3_smoke_cflite_seed0 \
    --teacher /root/.cache/modelscope/models/Qwen--Qwen3-1.7B/snapshots/master \
    --student /root/.cache/modelscope/models/Qwen--Qwen3-0.6B/snapshots/master \
    --method cf_lite --seed 0 --smoke
  ```
  当前 `experiments/P3_method.py` 仍是 mock 入口，不得当作 P3 证据；正式 P3 run 尚未产出。
- 全部阶段**串行**跑（并发会因 GPU 争用放大 3–7×，见 `docs/p3_resource_estimate.md`）；≥3 seed 是硬约束；封存 test 只读最终评测；δ=0.5 已锁定，测试期间不得再调。

## 关键结果摘要

全部数值转抄自 `reports/runs/**/metrics.json`、`reports/engineer_status.md`、`papers/readkv_v2_draft/notes.md`，CI 为簇级 paired bootstrap（10,000 resamples）。

| 项 | 结果 | 来源 |
|---|---|---|
| **P0 / E0 实现门** | **PASS**：Self-vs-Identity cosine=1.0、first-token KL=0、EM=1.0（80/80）、cache round-trip bit-identical、zero-re-prefill（80/80）；测量误差上限 **2.2e-16** ≪ 效应/3=6.95 | `e0_gpu_mvp_repro_seed0`，commit `458de18` |
| **P1 MVP joint E_CF** | 三 seed **1.968 / 1.934 / 2.123**（约 1.93–2.12），CI 下界均 >0；全部 `distortion_exists`、`transfer_broken=false` | `p1_gpu_mvp_repro_seed{0,1,2}` |
| **kd_only 三 seed** | E_CF **0.735 / 1.034 / 1.539**，CI 下界均 >0；相对 affine≈1.968 缩小约 22%–63%，但**未消除**（identity=0），跨 seed 幅度不稳定；预算不对等（60 对/3ep vs 120 对/8ep）已披露 | `p1_gpu_kdonly_mvp_seed{0,1_par,2_fast}` |
| **P2 四臂（seed0）** | Self 0 / K-only 0.582 / V-only **1.626** / Joint **1.777**（仅 Joint `deployable=true`）：定量确认 V-only≈Joint，失真主要落在接收端 Value 消费侧，Key 路由为次 | `p2_gpu_mvp_seed0_delta_rand_audit` |
| **P2 局部分解** | 17,920 单元，固定 Query 恒等式下最大残差 **2.96e-13 ≈ 0**（数值自检）；局部恒等式非全模型因果分解 | `p2_gpu_mvp_seed{0,1,2}` |
| **P2 Oracle held-out** | repair point **0.275–0.350**，95% CI 下界均 >0；方向一致 0.725–0.750；**4/5 核心单元 `(12,5,V/both)`、`(25,4,V/both)` 跨 3 seed 全重合**（第 5 单元轻微漂移）；train 8 对选 U、val 40 对零重叠、未碰封存 test、Oracle 未进推理图 | `p2_gpu_mvp_seed{0_delta_rand_audit,1,2}`、`reports/p2_seed_robustness.json` |
| **Huber δ** | **δ=0.5（logit 单位）** 已在 `configs/prereg/phase3_loss_config_v2.2.yaml`（`frozen_at: protocol-v2.2`）冻结；硬护栏口径：δ=1.0 因 dual 0.65<0.70 被否，δ=2.0 双重劣化 | `docs/decisions/huber_delta_lock.md` |

**主终点（封存 test 上 CF 方法 vs kd_only 的成对 `E_CF` 差异，要求 95% CI 上界 < 0）尚未评估**——CF-RCT 未训练，故不作任何“改善”声明。

## 贡献与定位

- **贡献(1)（全部达标）**：预注册成对反事实基准（commit `458de18` 可复现）、机器精度实现门（2.2e-16）、`E_CF` 与 dual/flip/coverage/info_gap 联合报告的纪律；gap 限定在**已测的 affine/ridge/kd_only mapper 范围**（kd 三 seed 缩小但未消除）。
- **贡献(2)（强形式，已获 PI 解禁）**：受控缓存干预下将 gap 定位到**接收端 Value 消费路径**（Key 路由为伴随效应），措辞可用强动词 “We localize the gap to receiver-side Value-consumption pathways under controlled cache interventions”，但**范围严格限定 MVP 等深对 (1.7B→0.6B)** + 局部固定 Q 恒等式 + Oracle 仅离线诊断；禁用 "across model pairs / causal / necessary and sufficient / sole cause / exclusively"；必须披露 F4/F6（局部恒等式非全模型因果分解、三判据非独立（2 统计信号 + 1 多数门槛）、4/5 核心单元跨 seed 稳定且第 5 单元漂移）。依据 `docs/decisions/contribution2_final_form.md`。
- **贡献(3)（方法层）withheld**：CF-RCT 未训练、主终点未评估；论文§3 标注 “design, not validated”。
- **定位**：按决策树（`docs/protocol.md §8`）本工作为**边界 / 实证研究（empirical / boundary study）**，不是高水平方法论文；任何把贡献(3) 写成已证实或声称 CF-RCT 改善的版本不予签 off。
- **数据边界**：全部数据为合成模板，标注“不适用于跨家族 / 真实世界迁移”。

## 阶段状态（P0–P5，按 PI 最新裁决）

| 阶段 | 状态 | 依据 |
|---|---|---|
| **P0 / E0** | **GO（最终）** | E0 repro PASS，R1 闭环（`final_signoff.md`） |
| **P1 基准** | **GO（最终）** | repro 权威 run + kd 三 seed，联合报告齐全，broken-transfer 边界正确标注 |
| **P2 机制** | **GO（完全收口）** | E2 三判据达标、F1/F2/F5 闭环、三 seed `mechanism_predictive`（`contribution2_final_form.md`） |
| **P3 方法** | **此前 NO-GO；现由人工决策启动、PI 已排期（分阶段门控）** | 入口已实现（`885a36a`），烟测门 → kd vs cf_lite 探路 → 门控决定 cf_mech；接受 `no_method_gain` 为合法结论（`p3_task_plan.md`） |
| **P4 泛化** | **NO-GO（维持）** | 未见模板 / 真实文档 / 封存 test 未运行；跨对泛化无证据 |
| **P5 投递** | **有条件 GO（条件更新）** | 批准边界/实证研究定位投递；门槛：seed 数三 seed、贡献(2) 强形式披露、贡献(3) withheld、`[PLACEHOLDER]` 引用核验 |

## Agent 团队

已在本仓库 `.opencode/agents/` 配置 8 个协作 agent（角色设计与协作流程见 `docs/agent_team.md`）：

| Agent | 职责 |
|---|---|
| **pi** | 定方向、冻结 `configs/prereg/**`、P0–P5 Go/No-Go 与投递裁决，仲裁角色分歧 |
| **scientist** | 算法与机制设计（CF-RCT 系列）、损失函数、机制诊断、novelty 核查 |
| **engineer** | GPU hooks / 后端、反事实对构造、跑 P0–P5 阶段脚本、产出 `scores.jsonl` 与可复现环境 |
| **writer** | LaTeX 论文、图 1–7 / 表 1–3、cover letter，严守 §10 贡献门槛 |
| **reviewer** | P0–P5 对抗审阅、统计合规与一致性审计，运行 `bootstrap_ci_report` / `consistency_check` |
| **engineer-2** | 并行工程师实例：分担 kd_only seed 补跑与结果汇总 |
| **engineer-3** | 并行工程师实例：分担 Huber δ 网格并行锁定与审计辅助 |
| **doc-engineer** | 维护 `README.md` 与 `docs/` 说明文档，只转抄冻结产物，不改代码 / 判据 / 运行产物 |
| **research-advisor** | 联网独立评估方向 / 方案 / 实验 / 结果的合理性，给出带证据与不确定性的 Go / Conditional Go / Pivot / No-Go 结论（不改判据 / 数据 / 运行产物） |

协作流程：PI（定方向/冻结判据）→ 科学家（规格书 + E0–E7 设计）→ 工程师（实现 + 跑实验 + `scores.jsonl`）→ reviewer / 审稿（统计合规、对抗审阅）→ writer（论文 / 投递材料）→ PI（Go/No-Go 与投递拍板）。角色间分歧由 PI 裁决；每个阶段写改审循环最多 2 轮，第 3 轮由 PI 直裁。所有角色共同遵守「判据先写后跑」「mock 非证据」「zero re-prefill」「不可逆产物」等硬约束。

## 关键指标说明

- `E_CF = |D_trans − D_self|`，`D = g(C(d_A),q) − g(C(d_B),q)`，`g(C,q) = log P(A|C,q) − log P(B|C,q)`。
- 主终点是**新方法与最强行为基线（kd_only）的成对 E_CF 差异**（封存 test，簇级 paired bootstrap，CI 上界 < 0 视为稳健改善）；P1/P2 的 E_CF 是相对 Self 锚点，**不是**主终点，不得混用。
- F5 是非翻转负控，不计入“必须翻转”分母；F6 做长度/位置控制。
- `τ` / Huber δ 阈值只在验证集固定（δ=0.5 已冻结于 v2.2）；封存测试运行前完成预注册（`configs/prereg/`）；封存测试期间不得再调 δ/λ。
- ≥3 seed 为硬约束，逐 seed 报点估计与 CI；任何 seed 缺失必须降级表述，不得伪造或挑选 seed；`P>0.05` 不作等效。
- 若仅“失真现象”成立而机制/方法无增益，按决策树改写为边界/实证研究论文，不保留贡献(3)措辞。

## 约束与边界说明（沿用，勿删）

- `--backend mock` 仅接线回归；**mock 数字不是科学证据**，不进入任何正式结论。
- `quality_pass` 仅表示**数据质量门 pass**（split 隔离 / 模板无重叠 / 标注一致），**不含**模型迁移效用；下游须联合读取 `transfer_broken` 正交字段，禁止只看冻结 verdict `distortion_exists` 判“干净失真”。
- 主验证对（4B→1.7B）旧 run 为 broken-transfer 失败边界（joint dual 0.28–0.30、joint E_CF 5.37–6.08），`git_hash=53e9bc5`、`provenance-unverified`，**不得作为可复现主结论来源、不计入 H1 正向证据**；其 `model_pair` 字符串误标已在 `reports/runs_index_errata.json` 勘误为 `qwen3-4b-to-1.7b`（依据 teacher 路径 + 36→28 layer_map，不影响指标）。
- E0 效应估计用多 token logprob（尺度约 17–20）与主终点 2 维 logit 尺度不同；one-shot full-prefill 全词表 cosine 最小 0.9993（sdpa kernel 路径差异，非实现误差）；均因误差上限 2.2e-16 极小不影响 E0 判定，已如实披露。
- `info_gap` 逐对字段为空，聚合口径 `info_attribution = 控制组 E_CF − joint E_CF` 已在正文报告并声明该偏差，未改冻结判据。
- δ 网格（0.5/1.0/2.0）val E_CF 2.7496/1.5968/2.7625 **全部高于 kd_only（0.735）**，本网格无正方向；预算 60 对/3ep vs kd 120 对/8ep、δ=0.5 压线非劣均已披露，属 P3 重大风险预警，但按决策树不触发方法降级分支（主终点未评估）。
- 不可变产物：`reports/runs/<run_id>/` 一经落盘不改；统计结论只能由 `scores.jsonl` 重算（`scripts.bootstrap_ci_report`）；`scripts.consistency_check` 校验 git_hash ancestry / 跑分代码一致性 / zero_re_prefill / model_pair / dtype / kernel。
- `[PLACEHOLDER]` 引用须按 `docs/protocol.md §9` 在投递前核实正式版本 / 日期 / 口径。

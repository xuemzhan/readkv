# readkv

跨模型 KV 迁移的**可复现实验平台**（现状：**负面 / 边界实证研究**）。

> **最终科学定性（2026-11-23，PI 收口）**：原 V2.0「反事实功能保真」主线（H1/H2/H3：utility-preserving gap → V 消费侧机制定位 → CF-RCT 方法改善）在干净数据上被**证伪**，已整体 NO-GO / PIVOT。项目现定位为「**跨模型 KV 迁移的失败边界 + 数据泄漏如何制造虚假科学发现**」的失败边界 / 数据教训实证研究：干净数据上 tested affine mapper 在等深 MVP 对迁移失败（dual 坍塌、`transfer_broken=true`），旧正向 gap / 机制信号源于数据泄漏 / 退化对 / 模板重合；强基线 kd_only 保持迁移效用但仍有稳定非零 gap（**情形 C，仅探索性观察**）。

需求来源：`docs/raw/跨模型KV迁移_第三篇论文研究方案_V2.0_详细版.pdf`（V2.0 方案，2026-11-22）与两篇已有论文 PDF。目标架构见 `docs/architecture.md`，冻结判据与统计设计见 `docs/protocol.md`，GPU 接续见 `docs/gpu_handoff.md`，智能体群协作见 `docs/agent_team.md`。**当前唯一有效的裁决链**：`docs/decisions/clean_data_reversal_ruling.md` → `docs/decisions/final_boundary_study_signoff.md` → `docs/decisions/research_scope_update.md` → **`docs/decisions/p5_final_signoff.md`（P5 附条件最终签 off / ready-to-submit，venue=TMLR）** → `docs/decisions/human_decisions.md`（真实 PI，决策 5 已指定 TMLR；决策 6 署名）+ `docs/decisions/{m4_target_adjustment,ai_dataset_final_ruling}.md`；旧签 off（`final_signoff.md`、`contribution2_final_form.md` 等）对干净数据**不再适用**。V2.0 论文题目、指标名（`E_CF`）、算法名（`CF-RCT`）均为工作版本。**正式数值只来自真实 GPU 产物（`reports/runs/**`）；mock / smoke / `reports/_non_authoritative/**` 数字只用于接线回归，不是科学证据。**

## 设计原则

以下为项目冻结的实验纪律（承接 V2.0）；其最终科学结论以本文件开头的「最终科学定性」与 `final_boundary_study_signoff.md` 为准。

1. **反事实保真为（预注册的）主终点**：以成对反事实文档的 `E_CF = |D_trans − D_self|` 为主终点，但必须与双向成功率、方向一致率、coverage、无信息对照联合报告，避免“恒定输出也低误差”的退化。**主终点至今未评估**（见「关键结果摘要」）。
2. **机制与评价并重**：Routing / Consumption 局部诊断必须在独立数据上有预测价值；只有评价层新增而无机制或方法改善时，不声称完成高水平方法论文。干净数据上机制前提已塌，P2 正式取消。
3. **消费侧为目标**：默认 mapper 拟合在 student 读取状态的空间（attention output / o-projection），representation-space 与对称 Key 目标仅作机制基线 / 前置实验。
4. **严格 zero re-prefill**：除离线 Oracle 诊断外，student 的 forward 不接受任何上下文 token；每次运行记录 `zero_re_prefill` 标志；Joint 是唯一可部署的迁移臂。
5. **先写判据后跑**：`configs/prereg/` 中的 decision rule 与 τ / Huber 阈值必须先冻结；统计结论只能由 `reports/runs/<run_id>/scores.jsonl` 重算；封存测试前完成预注册。
6. **单卡预算**：Teacher 缓存离线落盘、之后卸载；8B 只做离线推理；不做长上下文与大规模非线性搜索；普通 QA 与反事实 QA 同报。

## 实现状态

- **V2 全栈已落地（实现层面）**：评价层 / 机制层 / 方法层（设计）在 mock 后端完整实现；GPU 后端的 `models/hooks.py` 真实前向适配已实现并通过 P0 / E0 实现门，不再需要按 `docs/gpu_handoff.md` 补做 hooks；`--backend gpu` 可用。
- **测试**：`pytest` **53 passed**（V1 + V2 + hooks/kd 相关测试）。
- **真实 GPU 证据（最终口径）**：干净数据权威主证据为 **7 个 clean run**：`e0_clean_mvp_seed0`、`p1_clean_mvp_seed{0,1,2}`、`p1_kd_clean_mvp_seed{0,1,2}`；另有 **2 个 SQuAD 外部锚点 run**：`anchor_squad_{affine,kd}_seed0`。`reports/runs/` 下共 31 个 run 目录，其余为已 `superseded` 的旧 run（pre-fix 数据）与 δ 网格 run，仅作历史 / 前后对照，不进入当前结论。`bootstrap_summary.json` / `consistency_report.json` 当前均 31 项，7 clean + 2 锚点 `ok=true/traceable=true`（kd 情形 C 的 pair-level vs v2.3 簇级 CI 标注统一见 `docs/reproducibility.md §5.2`）。
- **数据**：`data/tasks/manifest.json`（`cf_pairs_v2.1`，sha `f910f1f1…a894a`，520 对：probe40/train120/val60/test300、`real=0`）；退化对 0、跨 split 重叠 0、实体重叠 0、flip 分母 398；统计口径 v2.3（`template_family` 主簇 + pair-level 敏感性，8 族 < 24 → `exploratory=true`）。
- **阶段门控**：P0 / E0、P1 为 **GO（终局）**；**P2 / P3 / P4 正式取消且永久放弃**（真实 PI 决策 8，不另立「修复 broken transfer」新课题）；**P5 = 附条件最终签 off（ready-to-submit）**, venue 已由真实 PI 指定为 **TMLR**（决策 5）；唯一机械性收尾为「写作者把 SQuAD 锚点探索性结果补入论文 + 审稿人出 P5 compliance note」，完成后由**真实 PI 本人经 OpenReview 提交**（agent 不代为提交）。详见「阶段状态」与 `docs/decisions/p5_final_signoff.md`。
- **贡献与投稿**：贡献(1) 撤回、贡献(2) 撤回（withheld）、贡献(3) withheld；`real=0`；主终点未评估、封存 test 未评测；论文定位为 TMLR 的**失败边界 / 数据教训负面实证研究（modest contribution）**，已完成 S1–S5、署名、引用核验（无 `[PLACEHOLDER]` 残留），进入附条件最终签 off / ready-to-submit。外部效度仅保留 SQuAD/ARC 锚点 + `real=0` 受阻披露；AI 生成数据集提案已评估并撤回（not activated），无遗留产物，不恢复任何贡献。§9 章节级全文口径复核为非阻塞投递前项。

## 目录

```
configs/
  protocol.yaml / eval.yaml / models.yaml / pairs.yaml / gates.yaml  # 协议、评测、模型对、门限
  prereg/phase*/decision.yaml                # 冻结的 decision rule（含数值算子）
  prereg/stats_convention_v2.3.yaml          # v2.3：template_family 主簇 + pair-level 敏感性
  prereg/external_validity_v2.4.yaml         # v2.4：锚点仅评测、预承诺三情形、不恢复贡献
  prereg/annotation_convention_v2.5.yaml     # v2.5：agent 交叉校验（real=0 故无适用对象）
  prereg/ai_generated_data_v2.6.yaml         # v2.6：AI 生成数据提案（冻结但 not-activated，无 data/generated/ 产物）
  prereg/phase3_loss_config_v2.{1,2}.yaml     # v2.1/v2.2：E0 容差、E2 判据、δ=0.5（历史，P3 取消）
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
data/
  tasks/manifest.json  tasks/cf_pairs.jsonl  # v2.1 干净合成对（sha f910f1f1…a894a，real=0）
  anchors/squad/dev-v2.0.json                # SQuAD 2.0 dev 外部锚点（仅评测，CC BY-SA 4.0）
reports/
  runs/<run_id>/                             # V2 不可变运行产物（含 clean / 锚点 run）
  review/                                    # 阶段 / P2 对抗审稿报告
    research_advisor/                        # current_task_review.md（PIVOT）+ third_round_online_addendum.md
    meta_review/                             # current_task_meta_review.md（对顾问报告的元审查）
    clean_data_reversal_emergency_review.md  # 翻转可信（高）紧急复核
  data/                                      # 数据审计 / 锚点许可 / S2 哈希注记
  runs_index.json  runs_index_errata.json  bootstrap_summary.json
  consistency_report.json  huber_delta_lock.json  engineer_status.md
  data_hash_binding_erratum.json             # S1：7 个 clean run 的数据 sha 绑定
  clean_data_rerun_summary.json  anchor_eval_summary.json
docs/
  protocol.md  architecture.md  gpu_handoff.md  agent_team.md
  algorithm_spec.md  experiment_design_E0_E7.md  p3_resource_estimate.md
  data/                                      # 数据卡、real 源 / HellaSwag 语义评估
  decisions/                                 # clean_data_reversal_ruling / final_boundary_study_signoff /
                                             # human_decisions / m4_* / ai_dataset_* / anchor_confirmation / …
  raw/
papers/readkv_v2_draft/                      # main.tex（负面结果重写稿）+ notes.md（权威数值清单，仅内部）
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

# P2 机制诊断（K/V 四臂 + 分解 + Oracle held-out）——历史入口，P2 已正式取消
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
- **已取消阶段的入口与烟测产物不是证据**：`experiments/P3_gpu.py` / `experiments/P3_method.py` 仅为历史实现产物（P3 已正式取消且永久放弃）；`reports/_non_authoritative/**`（如 `p3_smoke_cflite_seed0`、`p2_smoke_tmp`）与 `reports/p3_smoke_report.md` 均为 **non-authoritative / 未定稿**，不得作为证据引用，也不得用其数字声称方法增益。
- **SQuAD 外部锚点**（`anchor_squad_{affine,kd}_seed0`）已完成，仅 seed0、仅评测、按 v2.4 预承诺三情形归类为 `exploratory_disclosure`；不与合成 test 主终点混算，不恢复任何已撤回贡献。外部效度仅保留 SQuAD/ARC 锚点 + `real=0` 受阻披露；AI 生成数据集提案已评估并撤回（not activated），v2.6 冻结但无 `data/generated/` 遗留产物，`real=0` 硬边界不变。
- 当前权威 run 均**串行**跑（并发会因 GPU 争用放大 3–7×，见 `docs/p3_resource_estimate.md`）；≥3 seed 是硬约束（外部锚点例外：仅 seed0）；封存 test 全程**未评测**；δ 复核已永久取消，v2.2 的 δ=0.5 仅为形式登记、不再调整。

### 4. 可复现性（从零复现权威证据）

面向外部人员的完整从零复现指南见 **`docs/reproducibility.md`**（环境版本、模型路径、数据哈希、逐 run 命令、产物核对与审计、已知限制、禁止事项）。命令摘要（均在 `/root/readkv` 执行；权威证据只需 Qwen3-0.6B + 1.7B）：

```bash
# 安装 + 测试 + 模型
uv venv .venv
uv pip install --python .venv/bin/python -e ".[dev]" modelscope
.venv/bin/python -m pytest                                   # 53 passed
.venv/bin/modelscope download Qwen/Qwen3-0.6B
.venv/bin/modelscope download Qwen/Qwen3-1.7B

# 权威 9 run（串行）；T=1.7B snapshot，S=0.6B snapshot（见 docs/reproducibility.md §1）
.venv/bin/python -m experiments.P0_gpu --run-id e0_clean_mvp_seed0 \
  --model <S> --n-probes 40 --seed 0 --dtype bfloat16 --kernel sdpa
.venv/bin/python -m experiments.P1_gpu --run-id p1_clean_mvp_seed{0,1,2} \
  --teacher <T> --student <S> --seed {0,1,2} --mapper affine --n-resamples 10000
.venv/bin/python -m experiments.P1_kd_gpu --run-id p1_kd_clean_mvp_seed{0,1,2} \
  --teacher <T> --student <S> --seed {0,1,2} --method kd --epochs 8 --lr 1e-3 --eval-splits val
.venv/bin/python -m experiments.anchor_squad_gpu --run-id anchor_squad_{affine,kd}_seed0 \
  --teacher <T> --student <S> --method {affine,kd} --seed 0 --n-examples 240

# 数据哈希 / 审计（权威期望：consistency 9 ok = 7 clean + 2 锚点，22 failed 为历史 superseded）
sha256sum data/tasks/cf_pairs.jsonl          # f910f1f1…a894a
sha256sum data/anchors/squad/dev-v2.0.json   # 80a5225e…82d8
.venv/bin/python -m scripts.consistency_check
.venv/bin/python -m scripts.bootstrap_ci_report
```

> `{0,1,2}` 表示按 seed 逐条展开为 3 条独立命令（串行），`<T>/<S>` 为 §1 的本地 snapshot 绝对路径。上述命令复现的是**产物格式与统计口径**，不恢复任何已撤回贡献；封存 test 未评测、主终点未评估、`real=0` 仍为硬边界。已知限制（模型 revision 未钉 commit、驱动/uv 版本未记录、整理数据 `reports/data/gpu_experiments/v1/` 待补等）见 `docs/reproducibility.md §6–§7`。

## 关键结果摘要

全部数值转抄自 `reports/runs/**/metrics.json`、`reports/engineer_status.md`、`docs/decisions/**`、`papers/readkv_v2_draft/notes.md`，不重新计算统计。CI 为簇级 paired bootstrap（10,000 resamples）；干净数据按 v2.3 以 `template_family` 为主簇，8 族 < 24 → `exploratory=true`。

| 项 | 结果（当前权威产物） | 来源 |
|---|---|---|
| **P0 / E0 实现门** | **PASS（终局）**：`e0_clean_mvp_seed0`，Self-vs-Identity cosine 1.0、first-token KL 0、EM 0.975、cache round-trip bit-identical、zero-re-prefill 全通过；误差上限 **2.2e-16** ≪ 效应/3=6.95 | `e0_clean_mvp_seed0`；`engineer_status.md §13.1`；`final_boundary_study_signoff.md §4` |
| **P1 affine 三 seed（干净数据）** | **迁移失败边界**：joint E_CF **6.900 [5.499, 8.313] / 8.159 [6.647, 9.702] / 8.540 [7.057, 10.062]**；joint dual **0.417 / 0.283 / 0.383**（Self≈0.82，drop≈0.4）；flip 0.750/0.736/0.755；coverage 0.867/0.883/0.883；三 seed 全 `transfer_broken=true`。seed0 E_CF 接近但**未超过**错配 8.38 / 零缓存 8.58 控制（S4） | `p1_clean_mvp_seed{0,1,2}`（git `efc3ba3`）；`clean_data_reversal_ruling.md §0`；`engineer_status.md §13` |
| **P1 kd_only 三 seed（情形 C · 探索性）** | **不 broken 但稳定非零 gap**：joint E_CF（pair-level CI）**6.388 [5.360, 7.400] / 6.479 [5.419, 7.539] / 7.211 [6.078, 8.322]**；Self dual 0.817/0.900/0.783，joint dual **0.700 / 0.733 / 0.767**（drop 0.117/0.167/0.017 < 0.2），flip 0.942/0.906/0.925；三 seed 全 `transfer_broken=false`。v2.3 主簇 8 族 < 24，CI 为 pair-level，template-family 主 CI 更宽 → `exploratory=true`，**仅作探索性观察，不恢复贡献(1)** | `p1_kd_clean_mvp_seed{0,1,2}`（git `6413ba0`）；`final_boundary_study_signoff.md §1.1/§1.2`；`engineer_status.md §13` |
| **数据修复前后方向翻转** | 旧（已 superseded）：E_CF 1.93–2.12 / dual 0.62–0.67 / `broken=false` ↔ 干净：E_CF 6.9–8.5 / dual 0.28–0.42 / `broken=true`；18 退化对→0、≥15 组跨 split 逐字泄漏→0、flip 分母 398 → 核心方法学教训 | `clean_data_reversal_ruling.md §0/§4`；`notes.md §4` |
| **SQuAD 外部锚点（v2.4 · 探索性）** | 官方 SQuAD v2.0 dev 240 answerable、seed0；Self EM/F1 = 0.000 / 0.1975；Joint(affine) 0.000 / **0.0051**（F1 坍塌至 self 的 2.6%）、Joint(kd_only) 0.000 / **0.0014**（0.7%）。EM 全臂触底、kd 对照未复现合成域「保持效用」→ `exploratory_disclosure`，不强化外部效度、不恢复贡献 | `anchor_squad_{affine,kd}_seed0`；`engineer_status.md §15`；`anchor_confirmation.md` |
| **M4 / real / AI 生成数据提案** | M4 **受阻披露 real=0**（许可/网络/人力 + 源语义不适配；唯一 CC0 候选 SciTSR-pd 语义不适配，未采纳）；不生成 real split、不启动 real run；**AI 生成数据集提案已评估并撤回（not activated）**，v2.6 冻结但无 `data/generated/` 遗留产物，不是 real、不恢复贡献。外部效度仅保留 SQuAD/ARC 锚点 + `real=0` 受阻披露 | `m4_target_adjustment.md`；`ai_dataset_final_ruling.md`；`notes.md §0.5` |
| **主终点 / 封存 test** | **未评估**：CF 方法 vs kd_only 在封存 test 上的成对 E_CF 差异（95% CI 上界 < 0）从未计算；封存 test 全程未评测；P3 正式取消且永久放弃，贡献(3) 维持 withheld | `final_boundary_study_signoff.md §1.2/§4`；`notes.md §1` |

> 冻结 verdict `distortion_exists` 与正交字段 `transfer_broken` 口径分离：干净数据上机器 verdict 仍返回 `distortion_exists`（冻结判据未改），但科学定性以 `transfer_broken=true` 为准，是**迁移失败**，不是 H1 的正向证据。旧 affine 原型（`*_repro_*`，commit `458de18`）与旧 P2 机制产物（`6784780`）已 `superseded`，仅作历史 / 翻转对照；Contribution(2) 所依赖的 V 消费侧机制定位已撤回。

## 贡献与定位

- **贡献(1)（评价层）——撤回**：原「可复现的、未被强基线消除的 utility-preserving 反事实 gap」在干净数据上翻转为 broken transfer，正向证据基础已不存在。kd 干净 gap 仅为情形 C 探索性观察，**不恢复为正式 claim**。
- **贡献(2)（机制层）——撤回 / withheld**：机制对象（干净失真）不存在，旧 P2 证据建立在被污染数据上，P2 未重跑且已正式取消。
- **贡献(3)（方法层）——withheld**：CF-RCT 未训练、主终点未评估、P3 正式取消且永久放弃；论文方法层标注 “design, not validated”。
- **定位**：按决策树（`docs/protocol.md §8`）为**失败边界 / 数据泄漏教训的负面 / 实证研究（empirical / boundary study）**，不是方法论文。任何恢复贡献(1)(2)、声称 CF-RCT 改善或 V 消费侧机制定位的版本不予签 off。
- **数据边界**：全部数据为合成模板（`cf_pairs_v2.1`，CC0），`real=0`，禁止「真实世界 / 跨模型 / 跨对泛化」表述；外部效度仅保留 SQuAD/ARC 有限标准 QA 外部锚点 + `real=0` 受阻披露；AI 生成数据集提案已评估并撤回（not activated，无遗留产物），不恢复贡献。

## 阶段状态（P0–P5，按 PI 最终裁决）

| 阶段 | 最终状态 | 依据 |
|---|---|---|
| **P0 / E0** | **GO（终局）** | 干净数据 E0 复验 PASS（cosine 1.0、KL 0、EM 0.975、round-trip、2.2e-16 ≪ 效应、zero-re-prefill），`final_boundary_study_signoff.md §4` |
| **P1 基准** | **GO（终局）** | 干净三 seed：affine 迁移失败边界 + kd 情形 C（探索性）；机器 verdict 与 `transfer_broken` 分离披露 |
| **P2 机制** | **正式取消（不重启）** | 前提（干净失真）已塌，旧证据污染；重启仅当重新构造干净 utility-preserving 失真数据并经 PI 新裁决，当前无此计划 |
| **P3 方法** | **正式取消（永久放弃）** | 真实 PI 决策 8：方法层无目标、三 δ 负值、翻转后无意义；不另立「修复 broken transfer」新课题 |
| **P4 泛化** | **正式取消 / NO-GO** | 上游取消、无跨模型 / 真实文档证据、`real=0` |
| **P5 投递** | **附条件最终签 off / ready-to-submit（TMLR）** | `p5_final_signoff.md`：S1–S5、数据修复 / real=0 披露、kd 三 seed 入稿、署名（Zhang Xuein）、引用核验（无 PLACEHOLDER）、贡献清单全部达标；**venue 已由真实 PI 指定为 TMLR**（`human_decisions.md` 决策 5，采纳 PI 首选推荐）；唯一收尾：写作者补入 SQuAD 锚点探索性结果 + 审稿人出 P5 compliance note（机械性收尾，不改科学结论），随后由**真实 PI 本人经 OpenReview 提交，agent 不代为提交** |

## Agent 团队

角色设计与协作流程见 `docs/agent_team.md`；Prompt 配置于 `.opencode/agents/`（14 个，含 research-advisor）。已参与本轮工作的 agent：

| Agent | 职责 / 本轮产物 |
|---|---|
| **pi** | 定方向、冻结 `configs/prereg/**`、P0–P5 Go/No-Go 与投递裁决，仲裁角色分歧；出具 `clean_data_reversal_ruling.md` / `final_boundary_study_signoff.md` |
| **scientist** | 算法与机制设计、损失函数、机制诊断、novelty 核查；real 源 / HellaSwag 语义评估 |
| **engineer** | GPU hooks / 后端、反事实对构造、跑 P0–P5 阶段脚本、产出 `scores.jsonl` 与可复现环境；干净重跑与锚点评测 |
| **writer** | LaTeX 论文、图 1–7 / 表 1–3、cover letter，严守 §10 贡献门槛；按裁决重写为负面结果稿 |
| **reviewer** | P0–P5 对抗审阅、统计合规与一致性审计，运行 `bootstrap_ci_report` / `consistency_check`；紧急复核翻转可信（高） |
| **engineer-2** | 并行工程师实例：分担 kd_only seed 补跑与结果汇总 |
| **engineer-3** | 并行工程师实例：分担 Huber δ 网格并行锁定与审计辅助 |
| **doc-engineer** | 维护 `README.md` 与 `docs/` 说明文档，只转抄冻结产物，不改代码 / 判据 / 运行产物 |
| **research-advisor** | 联网独立评估方向 / 方案 / 实验 / 结果，给出 Go / Conditional Go / Pivot / No-Go 结论（不改判据 / 数据 / 运行产物）；产物 `reports/review/research_advisor/current_task_review.md`（PIVOT）与 `third_round_online_addendum.md`（第三轮主会话代执行，因额度不足，非独立 agent 签署） |
| **meta_review（审查产物）** | `reports/review/meta_review/current_task_meta_review.md`：对顾问报告的元审查，裁定 PIVOT 确认、失败边界研究 CONDITIONAL GO、投稿暂缓（**历史结论，已被 `p5_final_signoff.md` 的附条件最终签 off / TMLR 超越**） |

协作流程：PI（定方向/冻结判据）→ 科学家（规格书 + E0–E7 设计）→ 数据工程师 / 工程师（数据 manifest + 实现 + 跑实验 + `scores.jsonl`）→ reviewer / 顾问 / 元审查（统计合规、对抗审阅）→ writer（论文 / 投递材料）→ PI（Go/No-Go 与投递拍板）。角色间分歧由 PI 裁决；每个阶段写改审循环最多 2 轮，第 3 轮由 PI 直裁。所有角色共同遵守「判据先写后跑」「mock / smoke / `_non_authoritative` 非证据」「zero re-prefill」「不可逆产物」等硬约束。

## 关键指标说明

- `E_CF = |D_trans − D_self|`，`D = g(C(d_A),q) − g(C(d_B),q)`，`g(C,q) = log P(A|C,q) − log P(B|C,q)`。
- 主终点是**新方法与最强行为基线（kd_only）的成对 E_CF 差异**（封存 test，簇级 paired bootstrap，CI 上界 < 0 视为稳健改善）——**至今未评估**；P1 / P2 的 E_CF 是相对 Self 锚点的诊断量，**不是**主终点，不得混用。
- F5 是非翻转负控，不计入“必须翻转”分母；F6 做长度 / 位置控制；flip 分母 398（排除 F5、F6）。
- `τ` / Huber δ 阈值只在验证集固定（v2.2 的 δ=0.5 为形式登记，P3 取消后 δ 复核永久取消）；封存测试运行前完成预注册；封存 test 全程未评测。
- ≥3 seed 为硬约束，逐 seed 报点估计与 CI；任何 seed 缺失必须降级表述，不得伪造或挑选 seed；`P>0.05` 不作等效。清洁数据的所有 CI 在 v2.3 下 `exploratory=true`。
- 干净数据上连「失真现象」都翻转为迁移失败，机制 / 方法前提同时塌陷 → 已按决策树收口为失败边界 + 数据教训的负面 / 实证研究；贡献(1)(2) 撤回、贡献(3) withheld。

## 约束与边界说明（沿用，勿删）

- `--backend mock` 仅接线回归；`reports/_non_authoritative/**`、smoke run、P3 烟测报告均非权威；**mock / smoke / `_non_authoritative` 数字不是科学证据**，不进入任何正式结论。
- **封存 test 全程未评测，主终点（CF vs kd_only 成对 E_CF 差异）未评估**；任何「改善 / 缩小 gap / utility-preserving」的 endpoint 声明均不成立。
- `quality_pass` 仅表示**数据质量门 pass**（split 隔离 / 模板无重叠 / 标注一致），**不含**模型迁移效用；下游须联合读取 `transfer_broken` 正交字段，禁止只看冻结 verdict `distortion_exists` 判「干净失真」。
- 旧 run（pre-fix 数据，`git_hash=53e9bc5` 等）全部 `superseded`、provenance-unverified，不作可复现主结论来源、不计入 H1 正向证据；主验证对（4B→1.7B）旧 run 仅为 broken-transfer 失败边界（joint dual 0.28–0.30、joint E_CF 5.37–6.08），其 `model_pair` 误标已在 `reports/runs_index_errata.json` 勘误为 `qwen3-4b-to-1.7b`。
- E0 效应估计用多 token logprob（尺度约 17–20）与主终点 2 维 logit 尺度不同；one-shot full-prefill 全词表 cosine 最小 0.9993（sdpa kernel 路径差异，非实现误差）；均因误差上限 2.2e-16 极小不影响 E0 判定，已如实披露。
- `info_gap` 逐对字段为空，聚合口径 `info_attribution = 控制组 E_CF − joint E_CF` 已在正文报告并声明该偏差，未改冻结判据。
- δ 网格（0.5/1.0/2.0）val E_CF 2.7496/1.5968/2.7625 **全部高于当时 kd_only（0.735）**，本网格无正方向；P3 取消后 δ 复核永久取消，v2.2 的 δ=0.5 仅为形式登记。
- **S4 措辞（强制）**：统一写「joint E_CF 大幅升高、接近但尚未超过错配 / 零缓存控制（seed0: 6.90 vs 8.38 / 8.58），伴随 dual 坍塌至 0.28–0.42」，禁写「与控制相当 / 达到无信息水平」；**S5 强度边界**：`transfer_broken` 由 dual-drop 单信号触发、`exploratory=true`（8 族 < 24）、单一 MVP 等深对、合成域、封存 test 未评测，禁写「强显著性 / 跨对泛化 / 跨模型 / 因果」。
- `final_boundary_study_signoff.md §1.1` 的 kd 表使用 pair-level CI；元审查（`reports/review/meta_review/current_task_meta_review.md`）指出 v2.3 主簇口径与 kd 审计产物尚需统一或明确标注，属投稿前审计收尾项，须由 PI 解释、不得私下改表。
- 不可变产物：`reports/runs/<run_id>/` 一经落盘不改；统计结论只能由 `scores.jsonl` 重算（`scripts.bootstrap_ci_report`）；`scripts.consistency_check` 校验 git_hash ancestry / 跑分代码一致性 / zero_re_prefill / model_pair / dtype / kernel。
- 引用（KV-Lingo arXiv:2609.32610、CacheLink arXiv:2610.15509、SQuAD 两篇）已按 `protocol.md §9` 实际核验并替换 `[PLACEHOLDER]`（`main.tex` 无占位残留）；外部文献的章节级口径须在投递前复核。
- 署名统一：**Zhang Xuein \<zxm0813@gmail.com\>**（真实 PI 决策 6）；**venue 已由真实 PI 指定为 TMLR**（`human_decisions.md` 决策 5，锚点结果出来后指定、采纳 PI 首选推荐；依据 `venue_recommendation.md`），不再是「延后 / 首选」。**投递由真实 PI 本人经 OpenReview 提交，agent 不代为提交**；投稿前须完成人工最终检查清单（署名邮箱有效、TMLR 账号与作者配额、CC0/CC BY-SA/引用许可声明、cover letter 与 AE/reviewer 建议、锚点已补入 + P5 compliance note + 稿件编译无误；见 `docs/decisions/p5_final_signoff.md §6`）。§9 章节级引用全文口径复核为非阻塞投递前项。

# GPU v3.0 范围裁决（G0 · 真实 PI 新授权）

> 裁决人：**真实 PI（用户）**。日期：2026-11-25。
> 来源：真实 PI 在本次会话中对 `docs/audit/GPU_experiment_plan_2026-11-25.md` 的逐项答复；由 main agent 原样记录，不回写任何已冻结裁决或判据。
> 依据：`docs/audit/GPU_experiment_plan_2026-11-25.md`（提案，§0/§7/§8 明确「方案本身不构成运行授权」）、`docs/audit/revision_status.md`（E1/E2/E5/E6/E8 列为「需 GPU 的未完成项」）。
> 性质：**新研究立项裁决**。仅授权 G0–G4 流程的启动；不构成对当前稿件、v2.1–v2.9 冻结判据或任何已签 off 结论的改写。

---

## 1. G0 范围裁决（逐项，真实 PI 答复原样记录）

| 工作包 | PI 答复 | 执行含义 |
|---|---|---|
| **E1** 单缺陷干预筛查 | **授权** | 按方案 §3 先做 CPU 数据变体构造/审计与独立入口，通过后再进入 GPU pilot；按新研究报告，不称「因果贡献分解」、不声称泄漏普遍制造假阳性 |
| **E2** held-out test 评测 | **授权（含 test 解锁）** | PI 明确解锁此前未评测的 test split；仍须先锁定数据 SHA、代码 commit、模型/tokenizer、指标、seed、排除规则与统计脚本，一次性 dedicated evaluator，不得在 test 上调参/返修/多轮查看后再跑；称「此前未评测的 held-out split」，不称「sealed」 |
| **E5** 第二模型对复验 | **授权** | Qwen3-4B→1.7B 有限复验；P4 仍为 NO-GO，本项仅为新授权下的独立案例，不称「跨模型泛化」、不删失败结果 |
| **E6** 强/预算匹配基线 | **授权** | 先过方法复现门（全文方法/代码/权重/许可/mapper 结构/训练目标/zero-re-prefill）；无可忠实复现的外部方法时，使用明确命名的预算匹配内部对照，分项披露参数量、GPU 时间、前向/反向次数、显存与目标 |

## 2. 结果去向（真实 PI 答复）

> **另立新研究**（不纳入当前稿件）。所有 E1/E2/E5/E6 产物写入独立报告与新的 `reports/runs/<run_id>/`；**不回写** `papers/readkv_v2_*`、不重新触发当前 P5 CONDITIONAL SIGN-OFF、不恢复任何已撤回贡献、不重算已冻结主终点。

## 3. 预注册授权（真实 PI 答复）

> **确认授权**：在**任何 GPU run 之前**先冻结 `configs/prereg/gpu_followup_v3.0.yaml`（本裁决同时授权 main agent 代 PI 执行冻结）。冻结后按 G1→G2→G3→G4 顺序推进；不得先跑后改判据。

---

## 4. 流程门（沿用方案 §7，未授权前不得越门）

| 门 | 工作 | 放行条件 | 占 GPU |
|---|---|---|---|
| G0 | 范围裁决 | **本文件已完成** | 否 |
| G1 | 新 prereg + CPU 数据/基线审计 | `gpu_followup_v3.0.yaml` 冻结；数据哈希、变体清单、模型来源、判读分支全部完成 | 否 |
| G2 | 技术 pilot | 单 seed/小样本通过 Self/Identity、层映射、zero-re-prefill、显存与时间门 | pilot 实测 |
| G3 | 核心批准实验 | E1/E2/E5/E6 按各自矩阵运行；串行、独立 run ID、不覆盖归档 | 每格实测 × 格数 + 缓冲 |
| G4 | 统计与独立审阅 | family bootstrap + pair 敏感性；所有 seed 与失败 run 入账；无事后择支 | 否 |

## 5. 不可变边界（本裁决再次确认）

- 当前稿件（`papers/readkv_v2_draft` / `readkv_v2_tmlr_anonymous` / `readkv_v2_arxiv`）只读；论文因果措辞、投稿决策不因本裁决改变。
- v2.1–v2.9 冻结判据一字不回写；「判据先写后跑」始终生效。
- E1 单因素筛查不识别缺陷交互；E2 三次 mapper-seed 评分不是三份独立 test replicate；E5 不称普遍泛化；E6 外部方法未过复现门不得称 faithful baseline。
- 不运行/不重跑已完成的 v2.7 2×2 与 A00/A11 序列评分；不恢复 P2/P3/P4；不混入 SQuAD/ARC/HellaSwag/真实文档/AI 生成数据。
- agent 不代为投稿；本裁决不涉及投稿动作。

---

**签署**：真实 PI（用户）答复，由 main agent 原样记录（G0 · 2026-11-25）。

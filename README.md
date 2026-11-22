# readkv

跨模型 KV 迁移的**可复现实验平台**。V2.0 研究主线和三篇论文定位：

> 反事实功能保真：即使 Mapper 在常规 QA / likelihood / 平均分布上接近学生原生缓存，是否仍保留文档事实受控变化时学生输出应出现的对应变化？

需求来源：`docs/raw/跨模型KV迁移_第三篇论文研究方案_V2.0_详细版.pdf`（V2.0 方案，2026-11-22）与两篇已有论文 PDF。目标架构见 `docs/architecture.md`，冻结判据与统计设计见 `docs/protocol.md`，GPU 接续见 `docs/gpu_handoff.md`。V2.0 是待验证的研究计划，论文题目、指标名（`E_CF`）、算法名（`CF-RCT`）均为工作版本。

## 设计原则

1. **反事实保真为一级指标**：以成对反事实文档的 `E_CF = |D_trans − D_self|` 为主终点，但必须与双向成功率、方向一致率、coverage、无信息对照联合报告，避免“恒定输出也低误差”的退化。
2. **机制与评价并重**：Routing / Consumption 局部诊断必须在独立数据上有预测价值；只有评价层新增而无机制或方法改善时，不声称完成高水平方法论文。
3. **消费侧为目标**：默认 mapper 拟合在 student 读取状态的空间（attention output / o-projection），representation-space 与对称 Key 目标仅作机制基线 / 前置实验。
4. **严格 zero re-prefill**：除离线 Oracle 诊断外，student 的 forward 不接受任何上下文 token；每次运行记录 `zero_re_prefill` 标志；Joint 是唯一可部署的迁移臂。
5. **先写判据后跑**：`configs/prereg/` 中的 decision rule 与 τ / Huber 阈值必须先冻结；统计结论只能由 `reports/runs/<run_id>/scores.jsonl` 重算；封存测试前完成预注册。
6. **单卡预算**：Teacher 缓存离线落盘、之后卸载；8B 只做离线推理；不做长上下文与大规模非线性搜索；普通 QA 与反事实 QA 同报。

## 目录

```
configs/                       # 模型对、门限、各阶段超参、预注册判据
  protocol.yaml                #   V2 协议（E_CF、τ、统计、切片、控制）
  eval.yaml                    #   V2 评测配置与模型对
  prereg/phase*/decision.yaml  #   冻结的 decision rule（含数值算子）
src/readkv/
  runtime/  models/  cache/    # 底座 + CF-RCT + 双文档独立预填 + 实现门 E0
  data/build_cf_pairs.py       # 六类切片的成对反事实构造（F1–F6）
  diagnostics/route_value.py   # Routing/Consumption 分解 + Oracle + 对称 Key
  train/cf_rct.py              # KD / CF-lite / CF-mech 成对训练
  evaluate/cf_pipeline.py      # V2 端到端管线；counterfactual.py 为指标核心
  evaluate/                    # V1 三道门与探针（保留作基线）
  stats/
experiments/P0..P5             # V2 阶段编排（V1 stage0..4 保留作回归）
scripts/                       # 离线缓存生成、bootstrap 汇总、一致性检查
reports/runs/<run_id>/         # V2 不可变运行产物
tests/                         # V1 + V2 单元测试（51 passed）
```

**实现状态**：V2 全部功能（评价层 / 机制层 / 方法层）已在 mock 后端完整落地并通过 51 个测试；V1 骨架保留作回归与行为基线。GPU 后端仍需按 `docs/gpu_handoff.md` 实现 `models/hooks.py` 的真实前向适配（接口契约与 mock 一致）。

## 快速开始

```powershell
python -m pip install -e ".[dev]"
python -m pytest                                  # 51 passed（V1 + V2）

# V2 阶段（mock，CPU 即可跑完整管线）
python -m experiments.P0_baseline --backend mock --run-id p0 --n-train 120 --n-val 60 --n-test 300
python -m experiments.P1_benchmark --backend mock --run-id p1 --n-train 120 --n-val 60 --n-test 300
python -m experiments.P2_mechanism --backend mock --run-id p2 --n-train 120 --n-val 60 --n-test 300
python -m experiments.P3_method --backend mock --run-id p3 --n-train 120 --n-val 60 --n-test 300
python -m experiments.P4_generalization --backend mock --run-id p4 --pair main --n-train 120 --n-val 60 --n-test 300
python -m experiments.P5_paper --backend mock --run-id p5 --n-train 120 --n-val 60 --n-test 300

# 离线缓存（mock 接线验证；GPU 需先实现 hooks）
python -m scripts.gen_teacher_cache --pair qwen3-4b-to-1.7b --n-pairs 360 --dry-run
python -m scripts.gen_teacher_cache --pair qwen3-4b-to-1.7b --n-pairs 360 --backend mock

# 报告重算与审计
python -m scripts.bootstrap_ci_report
python -m scripts.consistency_check
```

`--backend mock` 用确定性 CPU 后端跑通**完整管线**；**mock 数字不是科学证据**。真实实验需要 24GB GPU 与模型权重，按 `docs/gpu_handoff.md` 逐项替换 mock 接口后使用 `--backend gpu`。模型分层：MVP 1.7B→0.6B（等深）、主验证 4B→1.7B（非等深）、8B 仅离线压力测试。

## 关键指标说明

- `E_CF = |D_trans − D_self|`，`D = g(C(d_A),q) − g(C(d_B),q)`，`g(C,q) = log P(A|C,q) − log P(B|C,q)`。
- 主终点是**新方法与最强行为基线的成对 E_CF 差异**（簇级 paired bootstrap，CI 上界 < 0 视为稳健改善）。
- F5 是非翻转负控，不计入“必须翻转”分母；F6 做长度/位置控制。
- `τ` / Huber 阈值只在验证集固定；封存测试运行前完成预注册（`configs/prereg/`）。
- 若仅“失真现象”成立而机制/方法无增益，按决策树改写为边界/实证研究论文，不保留贡献(2)(3)措辞。

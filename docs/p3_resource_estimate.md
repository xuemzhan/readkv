# P3（方法层）资源与时间评估

> 基于本机真实 GPU run 的实测耗时与当前代码状态估算，供人工决策（PI 签off将 P3/P4 列为 NO-GO，是否启动属人工决策项）。
> 所有数字来自 `reports/runs/*/metrics.json` 的 `elapsed_sec` / `training.train_sec` 与本机硬件实测，不是计划值。

## 1. 本机资源

| 项 | 实测 |
|---|---|
| GPU | RTX 4090，24564 MiB，当前空闲 24081 MiB |
| CPU | 训练进程约 300–700% |
| 磁盘 | 1.2 TB 可用（已用 330 GB） |
| 已缓存模型 | Qwen3-0.6B 1.5 GB、1.7B 3.8 GB、4B 7.6 GB（均在本地，无需重新下载） |
| 单训练 run 显存 | 约 7.8 GB（kd_only 实测），单卡最多并存 3 个 |

## 2. 实测基准耗时（干净单跑，无争用）

| 作业 | 配置 | 实测 |
|---|---|---|
| `p1_gpu_kdonly_mvp_seed0` | kd，8 epoch / 120 对 | train 1043 s（17.4 min）+ eval ≈131 s → **elapsed 1174 s（19.6 min）** |
| `p2_gpu_mvp_seed{0,1,2}` | 四臂 + 分解 + Oracle held-out | **elapsed 1076 / 1078 / 1118 s（≈18 min）** |
| `delta_lock_v2p1_0p5` | cf_lite，3 epoch / 60 对 | train 488 s + eval ≈279 s → **elapsed 767 s（12.8 min）** |
| `e0_gpu_mvp_repro_seed0` | E0 门 | elapsed 88 s |
| `p1_gpu_mvp_repro_seed{0,1,2}` | 纯评测 | elapsed 440 / 318 / 307 s（5–7 min） |

**争用惩罚（实测）**：2–3 个 GPU 任务并发时，kd 训练由 1043 s 放大到 3135 s（3×）乃至 7606 s（7.3×），δ 网格由 767 s 放大到 3866 s（5×）。**结论：P3 应串行跑，并发不省时间。**

## 3. 代码缺口（主要前置成本）

1. **无 `experiments/P3_gpu.py`**：现有 `experiments/P3_method.py` 是 mock 入口，其 summary 自带说明「mock 结果仅用于训练/对照接线验证，不是科学结论」。
2. **GPU 后端缺可微读出**：`src/readkv/models/gpu_backend.py` 只有 `candidate_logits()`（不可微），而 `train/cf_rct.py` 的 `L_KD/L_CF/L_local` 依赖 `backend.torch_candidate_logits()`（仅 `mock_backend.py` 实现）。需为冻结学生实现可微候选 logits 并保持返回形状不变。
3. **P3 决策规则已冻结**：`configs/prereg/phase3_method_decision.yaml`（`mechanism_and_method_both_win` / `ecf_improves_but_task_degrades` / `no_method_gain`），训练预算需在三法间配平；δ=0.5 已由 v2.2 冻结。

## 4. P3 工作量估算

| 工作项 | 估算 |
|---|---|
| 实现可微 candidate readout + P3_gpu 入口 + 预算配平 | 主要实现工作；需 1 个新 commit，且必须纳入 git 避免 R1 重演 |
| 每方法每 seed 训练+评测 | kd ≈20 min；cf_lite ≈20–25 min；cf_mech（多 L_local 前向）≈25–35 min |
| 必需 run 数 | 3 方法（kd / cf_lite / cf_mech）× 3 seed = **9 个 run**（≥3 seed 为硬约束，不得丢 seed） |
| 9 个 run 串行 GPU 时间 | **约 3.5–5 h**（按每 run 23–32 min） |
| 消融/λ 网格（如决策需要） | +3–6 run，+1–2.5 h |
| 聚合、bootstrap 主终点、审计、写作者更新 | +0.5–1 h |

**总计：实现 + 9 run 串行 ≈ 5–7 h 墙钟时间**（不含 λ 网格）；并发反而因 3–7× 争用惩罚而更慢。
**额外资源**：磁盘约 +60 MB run 产物；无需新增模型；无需联网。

## 5. 风险与收益判断

- **负结果风险高**：δ 网格三个值（0.5/1.0/2.0）的 val E_CF 全部高于 kd_only（0.735），P3 主终点（新方法与 kd_only 的成对 E_CF 差异，要求 CI 上界<0）很可能不成立，按冻结决策树会落入 `no_method_gain` → 贡献(3) 维持 withheld。即：可能花 5–7 h 确认一个负面结论。
- **P2 已收口**：贡献(2) 强形式已获 PI 解禁，当前稿件已可投递为 empirical/boundary study；P3 不是投递硬门槛。
- **不可省略的约束**：≥3 seed、预算配平、同 dtype/kernel、zero re-prefill、不得按封存测试调 δ 或 λ；任何 seed 缺失必须降级表述，不得伪装。

## 6. 建议

- 若目标是**尽快投递**：不启动 P3，直接走 P5 投递材料；P3 留作接收后/并行工作。
- 若目标是**冲击贡献(3)**：启动 P3，但按最坏情况预留 5–7 h GPU 串行时间，并接受 `no_method_gain` 的合法结论；先实现可微 readout 并用单 seed 单方法做烟测，再决定是否全量跑。
- 折中：先只跑 kd vs cf_lite（2 方法 × 3 seed ≈ 2.5–3 h）做主终点探路；若方向为负则按决策树降级，不继续 cf_mech。

# P3 实现前置 + 烟测门报告（本轮仅实现与烟测，未启动正式 P3 run）

> 依据：`docs/decisions/p3_task_plan.md` §2（实现前置 5 项）、§5 门 1（烟测门）。
> 日期：2026-11-23。所有结果来自真实 GPU（bf16/sdpa），烟测产物标记为 **non-authoritative**，不构成科学结论。

---

## 1. 实现前置完成情况（PI §2.1–2.5）

| # | 任务 | 状态 |
|---|---|---|
| 2.1 | 新建 `experiments/P3_gpu.py`（`--method {kd,cf_lite,cf_mech}`、`--seed {0,1,2}`）；复用 `train/cf_rct.py` + `evaluate.cf_pipeline`；主终点=封存 test 上 cf vs kd_only 的成对 E_CF 差异（CI 上界<0），与 P1/P2 相对 Self 口径分离 | ✅ |
| 2.2 | `GPUBackend.torch_candidate_logits`：可微、接口/返回形状与 mock 一致（候选在同一生成位置取首 token logits，`(2,)`），梯度经映射缓存回传 gθ；学生权重冻结；不注入人工正确性偏置 | ✅ |
| 2.3 | 三法预算配平：同 epochs/lr/rank/参数量/Forward 计数记账；`train/cf_rct.py` 新增逐步 loss 日志；λ_KD=1.0 锚点、δ=0.5（v2.2）、τ=1.0、self_threshold=0.1 冻结引用 | ✅ |
| 2.4 | 新 commit 纳入全部跑分代码；跑分路径工作区 clean、`git diff <commit> HEAD -- <跑分路径>` 为空 | ✅ commit **`ee74382`** |
| 2.5 | 烟测 run `p3_smoke_cflite_seed0`，置于 `reports/_non_authoritative/` | ✅ 通过（见 §3） |

**commit**：`885a36a`（首版实现）→ `ee74382`（loss 日志 + loss_check）。HEAD=`ee74382`；`git status --porcelain -- <跑分路径>` 为空，`git diff ee74382 HEAD` 为空，R1 不重演。

## 2. 烟测配置

- run_id `p3_smoke_cflite_seed0`（non-authoritative，cf_lite，seed0，8 train / 8 val / **test=0 不读封存 test 标签**，1 epoch，lr=1e-3，rank=0，δ=0.5，τ=1.0，bf16/sdpa，n_resamples=100）。
- 产物：`reports/_non_authoritative/p3_smoke_cflite_seed0/{config.json,scores.jsonl,metrics.json,ecf_ledger.jsonl,manifest.json}`（**不在** `reports/runs/`）。

## 3. 烟测门逐项验收

| 门项 | 实测 | 通过 |
|---|---|---|
| 可微 readout 梯度回传 mapper | `mapper_grad_norm=1791.5`，448/448 mapper 参数梯度非零 | ✅ |
| 学生权重梯度为 None/0 | `student_grad_tensors=0`、`student_grad_norm=0.0` | ✅ |
| loss 可下降 | 8 步逐步 loss 1.2254 → 0.0000（`decreased=true`；8 对小样本上收敛到 0 属烟测过拟合，非证据） | ✅ |
| zero_re_prefill | config.json `zero_re_prefill=true`；Joint 路径不读 C_S(d)（沿用已验证 hooks） | ✅ |
| 三法预算记账字段齐全 | config `budget={epochs,lr,rank,trainable_params=7340032,student_forward_calls=65,train_sec,seed}`；`lambda={KD,CF,local,reg}` 覆盖三法开关 | ✅ |
| 产物 schema 与 P1/P2 一致 | scores.jsonl 80 行，含 `pair_id/arm/E_CF/D_self/D_trans/dual_correct/flip_consistency/cluster/g_*/evaluable` 等；与 P1 run 逐对键集合对照为子集；`coverage` 为臂级汇总（metrics.json arms.*.coverage），P1/P2 同样如此 | ✅ |
| 主终点字段存在 | `metrics.json.primary_endpoint={point:0,ci:[0,0],improved:false}`（cf_lite 自比基线，烟测预期为 0）；定义字段写明"封存 test 上 cf vs kd_only 成对 E_CF 差异、CI 上界<0" | ✅ |
| provenance | config `git_hash=ee74382`、`protocol_version=2.0`、seed/dtype/kernel/bootstrap_seed 齐全 | ✅ |
| non-authoritative 标记 | 位于 `reports/_non_authoritative/`，metadata `non_authoritative=true`，`smoke=true` | ✅ |

**烟测门结论：PASS（Go）**。未发现接线失败；未进入正式 P3 run。

## 4. 纪律与边界

- 烟测只用 train/val，**未读封存 test 标签**，未用 smoke 数字调任何超参（δ=0.5、τ=1.0 均取冻结值）。
- 未改 `configs/prereg/**`（含 v2.1/v2.2）、未改 `docs/protocol.md`、未改任何已有 `scores.jsonl`。
- 烟测 decision=`method_downgraded`（自比基线的预期结果），**不得**解读为 cf_lite 真实无效——正式主终点须在封存 test 上与 kd_only 配对评估。
- 学生主权重在 `P3_gpu.load()` 中显式 `freeze_model`，并在 `torch_candidate_logits` 中防御性断言 `requires_grad=False`。

## 5. 下一步建议（待 PI 确认）

1. 经 PI 确认烟测门通过后，按 `p3_task_plan.md` §3.1 串行启动探路：`p3_gpu_kdonly_mvp_seed0`（primary baseline 先行）→ 同 seed 保存 kd mapper → `p3_gpu_cflite_mvp_seed0/1/2` 用 `--baseline-mapper-path` 载入对应 seed 的 kd mapper 计算真实主终点；三 seed 齐全后再按 §5 门 2 决定是否续 cf_mech。
2. 全程串行（PI §7 并发禁令），单 run 60 min 无 metrics 即熔断。
3. 贡献(3) 维持 withheld 直至 P3 主终点 + P4/E5 + E6 证据齐全（PI §6.4）。

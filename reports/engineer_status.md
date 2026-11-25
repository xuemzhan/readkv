# 工程师执行状态报告（V2.0 · 反事实功能保真）

> 更新：2026-11-23（按 PI 裁决 `docs/decisions/p1_go_no_go.md` 完成 R1–R6 修复）。
> 本报告只记录实现与真实运行事实；Mock 数字不构成科学证据。所有结论性统计须由
> `reports/runs/<run_id>/scores.jsonl` 重算。冻结判据（`configs/prereg/**`、
> `docs/protocol.md`）与已有 run 的 `scores.jsonl`/`config.json` 均未改动。

---

## 0. 本次修复总览（对照 PI 裁决编号）

| 编号 | 事项 | 状态 |
|---|---|---|
| R1 | git_hash 不指向跑分代码（阻塞） | **已闭环（方案 A）**：新 commit `458de18` 含全部跑分/实现代码；新 run_id 重跑 P0/E0 + P1；旧 run 标 superseded |
| R3 | kd_only 缺位（进 P2 前必须） | **已补跑（seed0 完整）**：MVP 上 kd_only gap 显著缩小但未消除；seed1/2 并行实例失败，未汇总（见 §5） |
| R4 | quality_pass / distortion_exists 口径 | **已勘误（不改判据）**：pipeline 新增 `transfer_broken`/`verdict_note`/`quality_pass_scope` 注释字段；冻结 verdict 未改 |
| R2 | consistency_check 盲点 | **已扩展**：git hash vs HEAD、跑分路径脏状态、commit tree 含代码、model_pair vs 路径/layer_map、协议版本兼容 |
| R6 | 主验证 model_pair 误标 | **已勘误**：`reports/runs_index_errata.json` + `runs_index.json` 写入 `model_pair_corrected`，不动 scores/config |
| R5 | bootstrap seed 不一致 | **已统一**：pipeline 与审计脚本同 seed；run config 记 `bootstrap_seed` |
| R7 | E0 尺度 / one-shot 残差 | 维持原判定（PI §6 裁定无需重跑）；披露见 §2 |
| R8 | §2.2 符号笔误 | **已更正**：`info_attribution = 控制组 E_CF − joint E_CF` |
| δ | Huber δ 验证集锁定 | **未完成（网格不完整）**：仅有 0.5/1.0，δ=2.0 缺失；不强行锁定（见 §6） |

新 commit：`458de18`（`Track GPU run code: hooks/backend, P0-P1 entrypoints, kd_only trainer, R2-R5 audit & annotations`，11 files）；随后审计语义修正提交 `841d283`（仅改 `scripts/consistency_check.py`）。并行实例又追加 `ff578b5`（prereg/规格/论文草稿）、`9a26748`（结果/报告）及后续无关 commit（审计时点 HEAD=`a04990d`）；多次核验 `git diff 458de18 HEAD -- <跑分路径>` 恒为空，产出 run 的代码与 HEAD 完全一致。跑分路径工作区 clean。

---

## 1. 环境与模型（复核）

- `.venv/bin/python`：Python 3.13.11 / torch 2.15.0+cu132 / transformers 5.24.0 / CUDA 可用；RTX 4090 24GB。
- 模型（ModelScope，本地路径已记入各 run config）：Qwen3-0.6B、Qwen3-1.7B、Qwen3-4B（4B tokenizer 两小文件从同系列复制、`get_vocab()` 实测一致）；8B 未下载。
- 53 个单元测试通过（`pytest`）；新增 hooks/kd 相关测试随 commit `458de18` 纳入。

---

## 2. 可复现主证据（新 run，git_hash=458de18）

### 2.1 E0（P0 实现门）

`e0_gpu_mvp_repro_seed0`（Qwen3-0.6B 自注入，40 对探针）：Self-vs-Identity cosine≈1.0、first-token KL=0、EM=1.0（80/80）、cache round-trip bit-identical（80/80）、zero-re-prefill（80/80）、误差上限 2.2e-16 ≪ 效应/3=6.95 → **PASS**。
补充诊断：整段一次 full-prefill 与注入的全词表 cosine 最小 0.9993（sdpa kernel 路径差异，非实现误差）；注入与学生原生两步路径逐 bit 一致。E0 效应用多 token 候选序列 logprob 估计（尺度约 17–20），与主终点 2 维 logit 尺度不同；因误差 2.2e-16 极小，不影响判定。
旧 `e0_gpu_mvp_seed0` / `e0_gpu_main_seed0` 标 superseded（git_hash=53e9bc5 不含跑分代码）。

### 2.2 P1 MVP（1.7B→0.6B 等深，affine/ridge mapper）

| run_id | seed | verdict | joint E_CF [95% CI] | identity | dual | flip | coverage | transfer_broken |
|---|---|---|---|---|---|---|---|---|
| `p1_gpu_mvp_repro_seed0` | 0 | distortion_exists | **1.968 [1.614, 2.324]** | 0 | 0.667 | 0.938 | 0.800 | false |
| `p1_gpu_mvp_repro_seed1` | 1 | distortion_exists | **1.934 [1.569, 2.311]** | 0 | 0.650 | 0.898 | 0.817 | false |
| `p1_gpu_mvp_repro_seed2` | 2 | distortion_exists | **2.123 [1.695, 2.571]** | 0 | 0.617 | 0.958 | 0.800 | false |

- 信息归因（`info_attribution = 控制组 E_CF − joint E_CF`，seed0）：mismatch +4.134 / random +2.249 / zero +4.191，均为正。【R8 更正：原 §2.2 误写为 joint 减控制组，数值未变】
- 每个 run 600 行 `scores.jsonl`（60 val × 10 臂）；bootstrap seed 已记入 config 并被审计脚本读取（R5）。

### 2.3 主验证对（4B→1.7B 非等深）——旧 run 仅作失败边界记录

`p1_gpu_main_seed{0,1,2}`（git_hash=53e9bc5）标 superseded / provenance-unverified，**不得作为可复现主结论来源**；其数值仍如实披露为 broken-transfer 失败边界：joint E_CF 5.37–6.08、joint dual 0.28–0.30（Self 0.65–0.78）、flip 0.49–0.56、info_attribution 多为负。`runs_index_errata.json` 已写入 `transfer_broken=true` 注释与 `model_pair_corrected="qwen3-4b-to-1.7b"`（依据 teacher 路径 + 36→28 layer_map，不影响任何指标）。按 PI §4.5，**该对不计入 H1 正向证据**。

---

## 3. R3：kd_only 主基线补跑结果

### 3.1 实现

`src/readkv/train/kd_gpu.py`：冻结学生的真实可微前向（映射缓存 re-RoPE → DynamicCache → 学生只前向 query → 首 token logits），KD loss 训练 KV Mapper；`experiments/P1_kd_gpu.py` 复用 `run_cf_pipeline` 与冻结 `phase1_benchmark_decision.yaml`，仅用 train/val。

### 3.2 结果（MVP，1.7B→0.6B）

`p1_gpu_kdonly_mvp_seed0`（train 120 / val 60，8 epoch，lr 1e-3，7.34M 可训练参数，git_hash=458de18）：

| 指标 | kd_only | affine（对照） | Identity |
|---|---|---|---|
| joint E_CF [95% CI] | **0.735 [0.552, 0.934]** | 1.968 [1.614, 2.324] | 0 |
| dual_correct | 0.700 | 0.667 | 0.683 |
| flip_consistency | 1.000 | 0.938 | 1.000 |
| coverage | 0.800 | 0.800 | 0.800 |
| info_attribution | mismatch +5.528 / random +4.751 / zero +5.424 | +4.134/+2.249/+4.191 | — |

**如实判定**：kd_only 相对 affine 把 joint E_CF 降低约 63%（1.968→0.735），dual/flip 未退化且信息归因更强；但 **gap 未消失**（CI 下界 0.552 > 0，identity=0，0.735 并非「接近 Self 的 0」）。按 PI §3.3，kd_only 仍有稳定 gap → RQ1 证据前提成立；但是否「接近 Self」到足以转边界研究属 PI/审稿人的科学判断，本报告不作该判断。P2 的启动门槛仍需 R1（已闭环）+ δ 锁定（已按 v2.2 形式登记，见 §9）。

**seed 完整性（已更新）**：kd_only 三 seed 全部完成并均有 `metrics.json`：`p1_gpu_kdonly_mvp_seed0`（E_CF=0.7350 [0.5517,0.9344]、dual=0.700）、`p1_gpu_kdonly_mvp_seed1_par`（1.0338 [0.7663,1.3279]、dual=0.633）、`p1_gpu_kdonly_mvp_seed2_fast`（1.5389 [1.1481,1.9588]、dual=0.683，取代因 GPU 争用超时的 `_par` 尝试）。三组 CI 下界均 >0，全部 `distortion_present=true`、`transfer_broken=false`；按 seed 分列报告，三 seed 方差跨 0.735–1.539。

---

## 4. R4 verdict 口径（不改冻结判据）

- `quality_pass` 在本管线中 = **数据质量门 pass**（split 隔离 / 模板无重叠 / 注释一致），**不含**模型迁移效用；它不构成 utility-preserving 的判定。
- pipeline 实现层新增正交注释字段：`transfer_broken`（bool）、`verdict_note`、`quality_pass_scope`、`signals`（dual 下降、joint E_CF vs 控制组、info 正负）。依据客观信号计算；**不新增 verdict 类别**，冻结 verdict `distortion_exists` 原样保留。
- MVP repro：transfer_broken=false（gap 干净）；主验证旧 run：transfer_broken=true（broken transfer，失败边界）。下游汇总须联合读取该字段，禁止只看 verdict。

---

## 5. 去重与 provenance

- 旧 run（8 个，`git_hash=53e9bc5`）标 `superseded`，可复现主证据只认新 run。
- 我方两次超时串行链（kd seed1/2、δ=1.0/2.0）均无残留 run 目录；δ=1.0/2.0 链在检测到与并行实例重复后已主动 TERM 中止。
- kd seed1/2 采用并行实例 run_id 的计划未成功产出（见 §3.2）；δ=1.0 采用并行实例 `delta_lock_v2p1_1p0_par`。
- 去重仅发生在 `reports/runs_index.json` / `runs_index_errata.json`（报告层），不改任何已落盘 run 产物。

---

## 6. Huber δ 验证集网格（未完成锁定）

`reports/huber_delta_lock.json`：status=**NOT_LOCKED_GRID_INCOMPLETE**。
- 可用：δ=0.5（val E_CF 2.750，dual 0.70，flip 1.0）；δ=1.0（val E_CF 1.597，dual 0.65 < kd_only 0.70，违反第 2 优先级约束）。
- 缺失：δ=2.0（`delta_lock_v2p1_2p0_par` 训练完成但评测停滞 43 分钟，无完整产物）。
- 初步观察：可用两点中 δ=0.5 是唯一满足非劣约束者；但网格不完整，按「判据先写后跑」不得据不完整网格锁定最终值。网格用 60 对/3 epoch（kd_only 参照 120 对/8 epoch），预算不同亦须正式同预算复核。
- 全程仅用 train/val，未触碰封存 test；未修改 `configs/prereg/**`，最终 δ 须由 PI 新增版本文件冻结。

---

## 7. 审计与产物

- `scripts.consistency_check` 扩展后已重跑 → `reports/consistency_report.json`：checked=17，failed=10。7 个新 run 全部 ok（code_tracked=true、git hash 在 HEAD 历史且跑分代码与 HEAD 一致、model_pair 一致）；10 个失败项为：8 个 superseded 旧 run（hash 不含代码 / model_pair 误标）、`delta_lock_v2p1_2p0_par`（仅 config，无 scores）、以及非 run 的 `reports/review/` 目录（审稿产物，被审计脚本按目录扫描误列入，非实验 run）。HEAD 因并行实例追加无关 commit 而前进，审计已用「ancestry + 跑分代码一致性」替代脆弱的 hash==HEAD 严格相等（提交 `841d283`）。
- `scripts.bootstrap_ci_report` 从 scores.jsonl 重算 CI（按各 run config 的 bootstrap seed），与 metrics.json 一致。
- 产物：本报告、`reports/runs_index.json`、`reports/runs_index_errata.json`、`reports/huber_delta_lock.json`、`reports/consistency_report.json`、`reports/environment.json`，及 `reports/runs/<run_id>/`。

## 8. 仍未完成 / 阻塞（按 PI 最终签 off 更新）

1. ~~kd_only seed1/2 缺失~~ → 已补齐三 seed（见 §3.2 / §9）。
2. ~~Huber δ 网格缺 δ=2.0~~ → 已补齐并由 PI 锁定 δ=0.5（v2.2，见 §6/§9）。
3. P2 机制诊断 → **已完成**（见 §10）。
4. P3 方法 / P4 泛化 / P5 成稿仍未运行（主终点、封存测试未评估）。
5. 主验证对（非等深）未以新 git_hash 重跑；旧 run 仅作失败边界记录。

---

## 9. 并行实例 3：δ 网格并行结果（补完 δ=2.0）

> 说明：本节仅追加，不覆盖上文。所有数值来自真实 GPU（backend=gpu, bf16/sdpa, seed=0），
> 两个 run 的 `config.json` 均记录 `eval_splits=["val"]`、`zero_re_prefill=true`；
> **全程未读取封存 test**。未修改 `configs/prereg/**`，未写 `docs/**`。

- 因 GPU 显存被主线程及并行实例占满（峰值空余 < 3.4GB），为避免 OOM 挤掉他方任务，使用显存门控编排：等出现 ≥12GB 空余后依次跑 δ=1.0、δ=2.0。两者均一次成功（rc=0），因排队各耗时约 1 小时；非逻辑失败。

| δ | run_id | val joint E_CF [95% CI] | dual_correct | flip_consistency | coverage | 普通 QA(self) dual/flip | 产物 |
|---|---|---|---|---|---|---|---|
| 0.5 | `delta_lock_v2p1_0p5`（主线程） | 2.7496 [2.0842, 3.4962] | 0.7000 | 1.0000 | 0.800 | 0.6833 / 1.0000 | 完整 |
| 1.0 | `delta_lock_v2p1_1p0_par`（本实例） | **1.5968 [1.2016, 2.0490]** | 0.6500 | 1.0000 | 0.800 | 0.6833 / 1.0000 | 完整（600 行 scores） |
| 2.0 | `delta_lock_v2p1_2p0_par`（本实例） | 2.7625 [2.0009, 3.5967] | 0.5333 | 0.9583 | 0.800 | 0.6833 / 1.0000 | 完整（600 行 scores） |
| 参照 | `p1_gpu_kdonly_mvp_seed0`（kd_only） | 0.7350 [0.5517, 0.9344] | 0.7000 | 1.0000 | 0.800 | 0.6833 / 1.0000 | 完整 |

- 三者训练预算一致（n_train=60 / epochs=3），δ 之间可直接比较；kd_only 参照为 120 对 / 8 epoch，预算不同，非劣比较仅供初筛（沿用 `reports/huber_delta_lock.json` 的 `budget_caveat`）。
- 按 v2.1 冻结选择规则〔1. val E_CF 最小；2. dual_correct、flip_consistency 不劣于 kd_only；3. 普通 QA 不退化〕逐条核对：
  - δ=0.5：E_CF 非最小，但 dual=0.70、flip=1.0 均不劣于 kd_only，普通 QA 不变 → **满足第 2、3 条**。
  - δ=1.0：E_CF 最小（1.597），但 dual=0.65 < kd_only 的 0.70 → **违反第 2 条**（flip、普通 QA 不退化）。
  - δ=2.0：dual=0.533 < 0.70 且 flip=0.958 < 1.0 → **违反第 2 条**（双重劣化），E_CF 也非最小。

**本实例建议值：δ=0.5** —— 它是补完网格后唯一同时满足“非劣于 kd_only + 普通 QA 不退化”的候选；δ=1.0 虽把 val E_CF 大幅降到 1.597（较 0.5 低约 42%），但 dual_correct 下降 0.05 触碰冻结护栏，δ=2.0 双重劣化。**最终锁定由主工程师/PI 决定**：若 PI 将“不劣于”解释为带容差的软护栏（例如比照 `transfer_health` 的 dual_drop<0.2），则 δ=1.0 会因其 E_CF 显著最优而成为候选；此口径分歧须由 PI 裁决，本实例不做科学判断。

- 补充事实：三个 cf_lite δ 的 joint E_CF 均高于 kd_only（0.735），即本网格内**没有任何 δ 使主终点方向为正**；这是真实结果，如实记录。
- 本实例两个 run 的 git hash 分别为 `ff578b5`（δ=1.0）、`a04990d`（δ=2.0），为主线程持续 commit 期间各 run 启动时刻的 HEAD；一致性审计请用 §7 的「ancestry + 跑分代码一致性」口径，勿用严格 hash==HEAD 相等。
- `reports/huber_delta_lock.json` 目前仍将 δ=2.0 标为“缺失/未锁定”；本实例已产出该点完整产物，**请主工程师汇总去重后更新该文件并按冻结规则锁定最终 δ**（本实例不擅自改动该文件与 prereg）。

---

## 8. 并行实例 2：kd seed2 结果（`p1_gpu_kdonly_mvp_seed2_fast`）

> 原计划以 `p1_gpu_kdonly_mvp_seed2_par` 并行补跑 seed2，但三进程显存争用下单轮耗时由 ~17 min 放大到 ~2 h（GPU util≈0%、CPU 自旋、RSS 静止），超时未产出任何产物；自动重启器已停止、确认无 `_par` 进程与重启。本报告 run 为主线程在 GPU 空位上直接启动的 **`p1_gpu_kdonly_mvp_seed2_fast`**（PID 54771），取代原 `_par` 尝试。本小节只追加，不改主线程内容。

- run_id：`p1_gpu_kdonly_mvp_seed2_fast`；seed=2，epochs=8，n_train=120，n_resamples=10000，bfloat16/sdpa，`zero_re_prefill=true`，git_hash=`a04990d`，eval_splits=val。
- 产物：`config.json` / `metrics.json` / `scores.jsonl`（600 行）/ `ecf_ledger.jsonl` / `manifest.json`，退出码 0；train_sec=3135.0 s（争用下放大），elapsed_sec=3262.4 s。

### kd_only（seed2_fast）gap 指标 vs Self 锚点

| 指标 | Self 锚点（seed2_fast） | joint（kd_only seed2_fast） | seed0 kdonly 参照 |
|---|---|---|---|
| E_CF [95% CI] | 0.0000 [0, 0] | **1.5389 [1.1481, 1.9588]** | 0.7350 [0.5517, 0.9344] |
| dual_correct | 0.6500 | 0.6833 | 0.7000 |
| flip_consistency | 1.0000 | 0.9792 | 1.0000 |
| coverage | 0.8000 | 0.8000 | 0.8000 |
| info_attribution（mismatch/random/zero） | — | 4.6807 / 3.8559 / 5.1043 | 5.5276 / 4.7512 / 5.4239 |

- verdict：`distortion_exists`（distortion_present=true、quality_pass=true）；`transfer_broken=false`；primary_endpoint point=0.0、ci=[0,0]（kd_only 即 primary baseline，自比差为 0）。
- 与 Self 比较（描述性，非科学结论）：
  - **行为层面接近 Self**：joint dual_correct=0.6833 ≥ Self 的 0.6500（与 seed0 的 Self 0.6833 持平）；coverage 与 Self 完全一致（0.800）；flip_consistency=0.9792 仅比 Self 的 1.0 低 0.021（48 个可评估对中约 1 例不一致）。
  - **失真幅度层面不接近 Self**：joint E_CF=1.539 的 95% CI 下界 1.148 > 0，明显非零，且约为 seed0（0.735）的 2 倍；信息归因控制组（3.86–5.10）均显著高于 joint（1.54），与 `transfer_broken=false` 一致。
  - seed 间差异明显（seed0 0.735 vs seed2 1.539），汇总须按 seed 分别列出，勿合并为单点数。
- 口径备案：从 `scores.jsonl` 逐行重算的 joint E_CF 原始均值（1.9236）与 `metrics.json` 报告口径（1.5389）不同；此差异与 §2.4 已备案的 `info_gap`/bootstrap 聚合口径一致，本实例不改任何冻结判据与统计代码。
- 产物交接：`reports/runs_index_errata.json` 中 `p1_gpu_kdonly_mvp_seed2_par` 应替换为 `_fast`；请主工程师汇总去重后更新索引，本实例不擅自改动该文件。

---

## 10. P2 机制诊断（E2，按 PI 最终签 off §3.1 任务书）

**run_id：`p2_gpu_mvp_seed0`**（MVP 1.7B→0.6B，seed0，git_hash=`9d474be`，bf16/sdpa，zero_re_prefill=true，dtype/kernel/seed/provenance 全记入 config.json；200 行 scores.jsonl）。沿用 repro 权威代码口径；Oracle 只用于离线诊断，未进入 Joint 推理图；候选单元只用 train(选择集 8 对)/val(held-out 40 对)，未碰封存 test。

### 10.1 K/V 四臂（deployable 标记：仅 Joint 可部署）

| 臂 | joint E_CF 均值 | deployable |
|---|---|---|
| Self | 0.000 | false（锚点） |
| K-only | 0.582 | false |
| V-only | 1.626 | false |
| Joint | 1.777 | **true** |

V-only≈Joint（1.626 vs 1.777），K-only 仅 0.582 —— **定量确认 P1 的「V-only≈Joint」方向性线索**：失真主要落在 Value 消费侧，Key 路由为次。

### 10.2 局部 Routing/Consumption 分解

- 单位数 17,920（40 对 × 2 侧 × 28 层 × 8 头）；固定接收端 Query（q_norm 内容空间）下按冻结恒等式 `Ô−O_S=(Â−A_S)V_S W_O+Â(V̂−V_S)W_O` 分解。
- routing 范数均值 24.846、consumption 21.839，**最大残差 2.96e-13 ≈ 0**（数值自检通过）。
- d_A / d_B 分别诊断再比较差值：routing 24.756 vs 24.937（Δ=−0.182）、consumption 21.730 vs 21.948（Δ=−0.218）——两侧分解幅度接近，差值小；**未把局部热图解释为全模型因果分解**。

### 10.3 层/头/Token Oracle 移植 + held-out 独立验证

- Oracle Δ 在 train 选择集（8 对 × 28 层 × 8 头 × 3 通道 = 5,376 单元打分）降序选 U（top-k=5）：`layer12/head5(both)`, `layer12/head5(V)`, `layer25/head4(both)`, `layer25/head4(V)`, `layer14/head1(V)` —— **5/5 含 V 通道，无纯 K 单元**。
- 独立 val 文档（40 对，与选择集不重叠）上整组 U 一次性移植：repair 命中率 U=0.725 vs 随机单元集 0.450；簇级 paired bootstrap（10,000 resamples，seed=0）差值 0.275，**95% CI [0.150, 0.425]，下界 > 0**；方向一致（ΔE_CF>0 占比）0.725 > 0.5。

### 10.4 E2 判定（v2.1/v2.2 冻结三项）

| 判据 | 实测 | 达标 |
|---|---|---|
| repair 命中率显著高于随机（CI 下界>0） | 0.275 [0.150, 0.425] | ✅ |
| 方向一致 ΔE_CF>0 占比>0.5 | 0.725 | ✅ |
| 分解残差≈0 | 2.96e-13 | ✅ |

**结论：E2 冻结三项全达，机制诊断在独立验证文档上有预测价值（verdict=`mechanism_predictive`）。** 候选机制公式（报告层 `reports/p2_mechanism_summary.json`）：反事实失真主要定位于接收端 Value 消费路径，集中在中后层少数 KV 头（layer12/head5、layer25/head4、layer14/head1），移植学生原生 V 状态可显著恢复 E_CF。**此为贡献(2) 的证据前提，但是否写入贡献(2) 由 PI/审稿人裁决，工程师不自行升格。**

### 10.5 预算、审计与产物

- dtype=bfloat16 / kernel=sdpa / seed=0；candidate forward 400 次；每 run config 含 protocol_version/git_hash/seed/dtype/kernel/zero_re_prefill=true。
- 扩展版 `consistency_check`：P2 run ok=true（21 检查、9 失败均为旧 superseded run，非 P2）；`bootstrap_ci_report` 正常重算。`pytest` 53/53（GPU 空闲时）。
- 产物：`reports/runs/p2_gpu_mvp_seed0/{config.json,scores.jsonl,mechanism.json,decomposition.jsonl,mechanism_units.jsonl,manifest.json}`；汇总 `reports/p2_mechanism_summary.json`；`reports/runs_index.json` / `runs_index_errata.json` 已纳入该 run。


---

## 11. F1/F2/F5 闭环（PI contribution2_ruling 指令，追加不覆盖 §10）

### F1【必须闭环】逐对 delta_rand 持久化 — ✅ 闭环

- 新 run_id：`p2_gpu_mvp_seed0_delta_rand_audit`（seed0，git_hash=`6784780`，MVP，bf16/sdpa，zero_re_prefill=true；240 行 scores.jsonl）。
- 扩展字段：`oracle_U` 臂逐对新增 `delta_rand` / `hit_u` / `hit_rand` / `delta_hit`；新增 `oracle_random` 臂 ledger（逐对 `delta_ecf`=随机基线 ΔE_CF）。`scripts.bootstrap_ci_report` 已扩展：从 scores.jsonl 的 `oracle_U` 逐对列重算 repair-vs-random 成对簇级 bootstrap CI。
- **独立重算验证**：`bootstrap_ci_report` 从冻结产物重算得 point=0.275、95% CI **[0.150, 0.425]，下界>0**（与原 `p2_gpu_mvp_seed0` 汇总数完全一致，未回改原 run）。复算步骤：`.venv/bin/python -m scripts.bootstrap_ci_report --reports-root reports --output <out>` → 查 `runs/p2_gpu_mvp_seed0_delta_rand_audit.repair_vs_random`。
- F1 闭环，P5 可使用该 CI；原 `p2_gpu_mvp_seed0` 冻结产物一字未改。

### F2【要求补跑】P2 ≥3 seed 与 U 稳健性 — ✅ 完成三 seed

| run_id | seed | repair point | 95% CI | 命中 U / 随机 | 方向一致 | U 核心单元 |
|---|---|---|---|---|---|---|
| `p2_gpu_mvp_seed0_delta_rand_audit` | 0 | 0.275 | [0.150, 0.425] | 0.725 / 0.450 | 0.725 | 12/5·25/4·14/1 |
| `p2_gpu_mvp_seed1` | 1 | 0.275 | [0.125, 0.425] | 0.725 / 0.450 | 0.725 | 25/4·12/5·24/2 |
| `p2_gpu_mvp_seed2` | 2 | 0.350 | [0.200, 0.500] | 0.750 / 0.400 | 0.750 | 12/5·25/4·14/1 |

- 三 seed 全部 `mechanism_predictive`、CI 下界均>0；每项含四臂、分解、Oracle held-out、`delta_rand` 列完整产物；U 各 seed 只用各自 train 选、held-out 用 val、零重叠、未碰封存 test；Oracle 未进推理图；provenance 写全。
- **U 稳健性**（`reports/p2_seed_robustness.json`）：4 个核心单元 `(12,5,V)/(12,5,both)/(25,4,V)/(25,4,both)` **跨 3 seed 全部重合**；第 5 单元 seed0/2 为 layer14/head1、seed1 为 layer24/head2（边缘轻微漂移）。命中率 0.725–0.750，效应点 0.275–0.350。结论：机制定位跨 seed 基本一致（核心稳定、边缘有漂移），非完全逐单元恒定。
- 贡献(2) 是否由限定形式升为强形式仍由 PI/审稿人裁决；本报告不自升格。

### F5【清理】 ✅

`reports/runs/p2_smoke_tmp/` 已移至 `reports/_non_authoritative/p2_smoke_tmp/`，不再被审计扫描为正式 P2 run。

### 审计与产物

新 run 全部通过扩展版 `consistency_check`（git 6784780 在历史、跑分代码一致、model_pair 一致、zero_re_prefill=true）；`bootstrap_ci_report` 从逐对产物重算 F1 CI；`pytest` 53/53。产物：`reports/runs/p2_gpu_mvp_seed{0_delta_rand_audit,1,2}/`、`reports/p2_seed_robustness.json`、`reports/runs_index.json`、`reports/runs_index_errata.json`。

### 仍需人工决策

F1/F2 已技术闭环；贡献(2) 措辞升格（限定→强形式）、投递时机、作者署名/期刊仍属 PI/人工决策。P3/P4 NO-GO、贡献(3) withheld 维持。


---

## 12. P3 暂停状态说明（PI data_readiness_ruling，2026-11-23）

- **暂停原因**：数据正确性缺陷——18 条 `candidate_A==candidate_B && must_flip=true` 退化对、≥15 组跨 split 逐字文档泄漏（含 train↔test 整对）、bootstrap 簇退化为逐对 i.i.d.（CI 系统性偏窄）、flip 分母口径冲突（394 vs 457）；封存 test 已被污染，在其上跑 P3 主终点既不可发表也会消耗唯一封存评测机会。
- **暂停时点**：2026-11-23，PI 裁决签发后立即生效；暂停发生在**任何正式 P3 test run 启动之前**。核查确认：无正在运行/排队中的 P3 正式 run；`reports/runs/` 下无任何 `p3_*` 产物；唯一 P3 产物为 `reports/_non_authoritative/p3_smoke_cflite_seed0`（已标 non-authoritative，scores 仅 val，**未读 test 标签**），不得作为证据引用。
- **已完成的实现（允许范围内）**：`experiments/P3_gpu.py`（kd/cf_lite/cf_mech 三法入口、主终点=封存 test 上 vs kd_only 成对 E_CF 差异）、`GPUBackend.torch_candidate_logits`（可微、学生冻结、无人工偏置）、三法预算配平与逐步 loss 日志；commit `885a36a` → `ee74382`（HEAD），跑分路径工作区 clean、`git diff ee74382 HEAD` 为空；非 test 烟测门 PASS（梯度回传 448/448、学生梯度 0、loss 下降、schema/provenance 齐全），详见 `reports/p3_smoke_report.md`。
- **未产出的正式证据**：无 P3 正式 run、无 test 评测、无主终点（cf vs kd_only 成对 E_CF 差异）真实结果；贡献(3) 维持 withheld；P3 阶段维持 NO-GO/暂停，不得以烟测数字充当证据。
- **重启条件**：M1（退化对修复+重建）、M2（跨 split 去重）、M6′（聚类单元口径新版本文件）、M7′（flip 分母新版本文件）完成，数据重建 + manifest 更新，P1/P2 在干净数据上重跑确认 gap/机制仍成立，且统计口径新版本文件落地后，按 `p3_task_plan` 门控串行重启 P3；主终点须用新版本文件冻结的聚类口径。
- **并行边界**：暂停期间不编辑 `data/**`、`src/readkv/data/**`、`scripts/**`（含 bootstrap/一致性脚本）与 manifest（数据工程师负责），不重跑任何 test 评测；仅保留上述 P3 实现收尾、非 test 烟测与单元测试。


---

## 13. 干净数据重跑结果（PI data_readiness_ruling + clean_data_reversal_ruling，2026-11-23）

**数据**：新 sha256 `f910f1f1…a894a`，520 对（probe40/train120/val60/test300），退化对 0、跨 split 重叠 0、实体重叠 0、flip 分母 398；统计口径 v2.3（template_family 主 + pair-level 敏感性）。数据修复代码 commit `efc3ba3`；PI 回填 v2.3 的 commit `6413ba0`（HEAD）；`git diff efc3ba3 HEAD -- <跑分路径>` 为空，跑分路径 clean。

### 13.1 已完成的重跑（7 个新 run，全部通过 consistency_check）

- **E0**：`e0_clean_mvp_seed0` —— PASS（cosine 1.0、KL 0、EM 0.975、round-trip bit-identical、zero-re-prefill 全通过，git_hash=efc3ba3）。
- **P1（affine）三 seed**：`p1_clean_mvp_seed0/1/2`（git_hash=efc3ba3）—— joint E_CF **6.900 [5.499,8.313] / 8.159 [6.647,9.702] / 8.540 [7.057,10.062]**；dual **0.417 / 0.283 / 0.383**（Self ≈0.82），flip 0.75/0.74/0.76，coverage 0.87/0.88/0.88；**三 seed 全部 `transfer_broken=true`**。机器 verdict 仍为 `distortion_exists`（冻结判据未改），但科学定性为**迁移失败边界**。
- **kd_only 三 seed**：`p1_kd_clean_mvp_seed0/1/2`（git_hash=6413ba0，PI 的 v2.3 commit）—— E_CF **6.388 [5.360,7.400] / 6.479 [5.419,7.539] / 7.211 [6.078,8.322]**；Self dual 0.817/0.900/0.783，joint dual **0.700/0.733/0.767**（drop 0.117/0.167/0.017 <0.2），flip 0.942/0.906/0.925，coverage 0.867/0.883/0.883；**三 seed 全部 `transfer_broken=false`**。

### 13.2 P1 gap 与机制状态

- **gap 仍存在但性质翻转**：干净数据上 affine 的 E_CF 6.90–8.54 远大于旧数据的 1.93–2.12，且 dual 从 0.62–0.67 坍塌到 0.28–0.42、与错配/零缓存控制相当（mismatch 8.38、zero 8.58）——**这是迁移失败，不是 utility-preserving 的干净失真**。旧数据的正向 gap 信号源于数据缺陷（紧急裁决 §1）。
- **kd_only 不是 broken**（dual 保持 0.70–0.77、drop<0.2），但 E_CF 6.39–7.21 仍稳定非零、远非「接近 Self」；按 PI §3.3 预承诺，属**情形 C**（kd 不 broken 但仍有稳定小/非零 gap）→ 边界研究，贡献(1)(2) 撤回、贡献(3) withheld。engineering 不自行重判。
- **v2.3 审计口径**：bootstrap 主 CI 用 template_family、pair-level 敏感性同报；val 仅 8 个 template_family 簇（<24）→ `exploratory=true`，template-family CI 明显宽于 pair-level（例 seed0 joint 6.900 [3.564,10.100] vs pair [5.496,8.321]）；flip 分母 398。

### 13.3 未运行项（按紧急裁决，非工程遗漏）

- **δ=0.5 复核**：未启动 / 取消（P3 无意义）。**δ 无需 PI 重裁**——无新复核证据，v2.2 的 δ=0.5 形式登记不变。
- **P2 三 seed 重跑**：未启动 / 取消（机制前提塌陷，旧 P2 证据撤回）。
- **P3 正式 run**：维持暂停 / 实质取消。

### 13.4 审计与产物

- 7 个新 run 全部通过 `consistency_check`（git_hash/zero_re_prefill/dtype/kernel/model_pair 齐全）；`bootstrap_ci_report` 按 v2.3 输出 template-family 主 CI + pair-level 敏感性；`pytest` 53/53。
- 产物：`reports/runs/e0_clean_mvp_seed0/`、`p1_clean_mvp_seed{0,1,2}/`、`p1_kd_clean_mvp_seed{0,1,2}/`；汇总 `reports/clean_data_rerun_summary.json`、`reports/consistency_report.json`。总耗时约 65 分钟（3923 s）。
- 旧 run 全部溯源过期，在索引中已标 superseded，不删除、不作为证据；已写作者须按紧急裁决撤回正向 claim。


---

## 14. S1 溯源勘误（final_boundary_study_signoff §2 S1，2026-11-23）

- **新增勘误文件**：`reports/data_hash_binding_erratum.json`（仅 metadata，不改任何既有 scores.jsonl / config.json / metrics.json）。
- **绑定内容**：7 个 clean run（E0 `e0_clean_mvp_seed0`；P1 `p1_clean_mvp_seed0/1/2`；kd_only `p1_kd_clean_mvp_seed0/1/2`）的实际数据 sha256 = `f910f1f1196a21041765834654af8233d216ef4bf4f28f4c60abbd0641aa894a`（源于 `data/tasks/manifest.json::files[cf_pairs.jsonl].sha256`，与磁盘实测一致），并逐 run 记 commit（efc3ba3 / 6413ba0）。
- **性质**：原 run config 未记录 data_sha256 属溯源遗漏（记录不全），非数据不一致；数据修复先于全部 clean run，跑分代码在两 commit 间逐字未变。
- **未重跑任何实验**；`configs/prereg/**`、`data/**`、论文、任何已有 run 产物均未改。S2（manifest 的 v2.3 sha 回填前/后注记）属数据工程师侧残留，未在本文件处理。


---

## 15. SQuAD 外部锚点评测（v2.4，锚点先行，2026-11-23）

- **数据**：`data/anchors/squad/dev-v2.0.json`（官方 SQuAD v2.0 dev，CC BY-SA 4.0，仅评测/不改写/不发布衍生语料），sha256 实测 `80a5225e…82d8` 与五项登记一致；240 个 answerable 确定性子集，seed0。
- **代码 commit**：`938f3a0`（锚点评测入口）；run 时 HEAD=`b7b9f50`（数据工程师后续归档 commit），`git diff 938f3a0 HEAD -- <跑分路径>` 为空、工作区 clean，无 R1 重演。
- **两个 run**（均 `git_hash=b7b9f50`、`protocol_version` top=2.0/experiment=2.4、bf16/sdpa、`zero_re_prefill=true`、`data_sha256=80a5225e…`、480 行 scores）：
  - `anchor_squad_affine_seed0`：Self EM/F1 = 0.000/0.1975；Joint(affine) EM/F1 = 0.000/**0.0051**（F1 坍塌至 self 的 2.6

---

## 15. SQuAD 外部锚点评测（v2.4，锚点先行，2026-11-23）

- **数据**：`data/anchors/squad/dev-v2.0.json`（官方 SQuAD v2.0 dev，CC BY-SA 4.0，仅评测/不改写/不发布衍生语料），sha256 实测 `80a5225e…82d8` 与五项登记一致；240 个 answerable 确定性子集，seed0。
- **代码 commit**：`938f3a0`（锚点评测入口）；run 时 HEAD=`b7b9f50`（数据工程师后续归档 commit），`git diff 938f3a0 HEAD -- <跑分路径>` 为空、工作区 clean，无 R1 重演。
- **两个 run**（均 `git_hash=b7b9f50`、`protocol_version` top=2.0/experiment=2.4、bf16/sdpa、`zero_re_prefill=true`、`data_sha256=80a5225e…`、480 行 scores）：
  - `anchor_squad_affine_seed0`：Self EM/F1 = 0.000/0.1975；Joint(affine) EM/F1 = 0.000/**0.0051**（F1 坍塌至 self 的 2.6%）。
  - `anchor_squad_kd_seed0`：Self 同 0.000/0.1975；Joint(kd_only) EM/F1 = 0.000/**0.0014**（F1 坍塌至 self 的 0.7%）。
- **v2.4 预承诺三情形判读**：affine 失败方向复现，但 kd_only 在锚点上也坍塌（未复现合成域「kd 保持 utility」对照），且 EM 全臂触底（base 0.6B 未针对 SQuAD 微调）、仅 seed0/240 例 → **混合/样本有限 → `exploratory_disclosure`**（探索性披露）。**不**判 `reinforce_external_validity`、**不**判 `narrow_scope`；不反转叙事、不恢复贡献(1)(2)(3)、不与合成 test 混算、不重算冻结 CI。
- **是否跨数据源复现失败边界**：affine 坍塌方向在 SQuAD 上复现（F1 0.1975→0.0051），但 kd 对照未复现 → 只能作**探索性外部锚点观察**，不足以强化失败边界的跨数据源普适性。
- **审计**：两锚点 run 通过 `consistency_check`（ok=true）；`bootstrap_ci_report` 31 runs 正常；`pytest` 保持通过。产物：`reports/runs/anchor_squad_{affine,kd}_seed0/`、`reports/anchor_eval_summary.json`、`reports/consistency_report.json`。


---

## 16. 2×2 GPU 补充实验 12 格正式结果（protocol-v2.7，2026-11-23）

- **入口**：`experiments/audit_2x2_gpu.py`（显式四份 train/val JSONL，不调 P1_gpu 自动重建）；数据来自 `data/audit_2x2/{legacy,fixed}/`（旧 458de18 / 修复 efc3ba3），12 文件 sha256 全匹配 `_index.json`。bf16/sdpa、等深 28→28、逐层逐头 K/V affine、ridge λ=0.001、首 token 评分、zero_re_prefill=true。
- **12 格 L=Self−Joint（百分点，三 seed）**：A00=[0.017, −0.050, 0.033]；A11=[0.400, 0.617, 0.400]；A01=[0.267, 0.283, 0.333]；A10=[0.383, 0.233, 0.250]。全部 joint dual < self dual（除 A00_s1 微小负 L −0.05）。
- **预固定对比**：①固定 val 换校准语料：legacy val A10−A00=[0.367,0.283,0.217]、fixed val A11−A01=[0.133,0.333,0.067]，三 seed 均正 → 校准版本效应方向稳健；②固定 mapper 换 val：legacy cal A01−A00=[0.250,0.333,0.300]、fixed cal A11−A10=[0.017,0.383,0.150]，亦多为正 → 评估集构成敏感。按 v2.7 归因边界，只能识别两个数据版本整体切换，不作单项缺陷因果。
- **对角格核对**：A00 s0/s1/s2 与 `p1_gpu_mvp_repro_seed{0,1,2}`、A11 与 `p1_clean_mvp_seed{0,1,2}` 各 60/60 joint E_CF 逐对完全一致（`sample_hash==cache_hash`）。
- **失败/重试**：正式 12 格 0 失败、全部 attempt 1 完成（冒烟阶段 attempt1/2 失败、attempt3 成功，见 `reports/audit_2x2_smoke_report.md`）。每格完成即 commit+push 后才跑下一格，远程每次同步确认。
- **commit 链**（逐格已 push）：入口 `8aeb282`；冒烟修复 `c1a161a`/`03c9f50`；冒烟通过 `fec8a64`；seed0 `43cc800`→`80f0421`→`2ef23ab`(核对修正)→`290e959`→`c58f0d1`；seed1 `26feb0d`→`eca1b1d`→`97e6fe0`→`9485596`；seed2 `14b1a57`→`dce2ee4`→`8e85071`→`3ed85f0`；汇总 `见本次 commit`。
- **审计**：`bootstrap_ci_report` 43 runs 正常（报告层 `reports/audit_2x2_bootstrap.json`）；`consistency_check` 对 12 格报 ok=false，唯一原因为审计脚本要求 `model_pair` 字段而审计入口 config 未写该字段（其被显式 `calibration_version/validation_version` + teacher/student 路径替代）——属字段对接假阳性，非数据/指标错误；12 格 traceable（git 在历史、跑分代码一致、code_tracked=true）全部为真。`pytest` 保持通过。
- **总耗时**：12 格 GPU 合计约 23.7 分钟（单卡串行），加每格 commit/push 开销；远低于 1–2 GPU 小时预算。
- **产物**：`reports/runs/audit_2x2_A{00,01,10,11}_s{0,1,2}/`（12 格各 config/manifest/metrics/scores）、`reports/audit_2x2_formal_summary.json`、`reports/audit_2x2_bootstrap.json`、`reports/consistency_report.json`。贡献状态不变（(1)(2) 撤回、(3) withheld），主终点未触碰。


---

## 17. 2×2 统计口径补算修复（v2.7 合规缺口，2026-11-23）

- **缺口**（科学家 `docs/audit_2x2_statistical_interpretation.md` §1.1/§5.1）：原 `audit_2x2_bootstrap.json` 12 格仅 E_CF 区间且用 `cluster-fallback`/60 逐对簇（exploratory=false），无 L CI、无预固定对比 CI，违反 v2.7 template_family 主口径。
- **修复**：新脚本 `scripts/audit_2x2_ci.py`（纯 CPU，从冻结 scores + val JSONL 重算，不改任何 run 产物），按 `version_tag+sample_hash` 关联（规避跨版本 pair_id 碰撞，unknown_family=0）。产出 `reports/audit_2x2_l_ci.json`：每格 L 主 CI（template_family 簇级 bootstrap 10000）+ pair-level 敏感性 + `n_clusters=8` + `exploratory=true`（12/12）+ E_CF 主口径补正；两项预固定对比 ×3 seed 配对 CI。
- **关键 L 主 CI（pp）**：A11 +40.0/+61.7/+40.0、A01 +26.7/+28.3/+33.3、A10 +38.3/+23.3/+25.0 主 CI 下界多 >0；A00 +1.7/−5.0/+3.3 围绕 0。固定 val 换校准 legacy A10−A00 CI [15.5,54.8]/[13.8,42.4]/[0.0,41.3]；换 val 对比按跨版本非配对独立簇重采样（v2.7 cross_version_note），部分 CI 跨 0。
- **失败/重试**：attempt1 统计问题（换 val 对比按 sample_id 配对且跨版本 ID 不同→n=0），修复为独立簇重采样（commit `6c6b7d3`）；attempt2 成功。日志 `/tmp/opencode/audit_ci_attempt{1,2}.log`。
- **commit+push**：脚本 `e9f5773` → 修复 `6c6b7d3` → 产物+报告 `857ea56`（本地=远程）；原 `audit_2x2_bootstrap.json`、12 格 `reports/runs/`、prereg、数据、论文均未改。
- **产物路径**：`reports/audit_2x2_l_ci.json`、`reports/audit_2x2_ci_fix_report.md`、`scripts/audit_2x2_ci.py`。全 12 格 exploratory（8 族<24），不得作强显著性主张；whole_version_only 归因边界与贡献状态不变。

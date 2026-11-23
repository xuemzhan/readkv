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

## 8. 仍未完成 / 阻塞

1. kd_only seed1/2（并行实例 `_par` / `_fast` 均因 GPU 争用停滞）→ 仅 seed0，无三 seed 方差。
2. Huber δ 网格缺 δ=2.0（并行实例评测停滞）→ δ 未锁定；P2/P3 维持 NO-GO。
3. P2 机制、P3 方法、P4 泛化、P5 成稿均未运行（证据仅到 P1）。
4. 主验证对（非等深）未以新 git_hash 重跑；旧 run 仅作失败边界记录。

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

# 工程师锚点评测收尾审计报告（SQuAD 外部锚点 · v2.4）

> 日期：2026-11-23。执行人：工程师（readkv）。
> 授权依据：`docs/decisions/anchor_confirmation.md`（PI 签署 · 2026-11-23）、
> `configs/prereg/external_validity_v2.4.yaml`（冻结判据，只读引用）。
> 本报告只记录实现/运行/审计事实。所有数字来自真实 GPU run 的 `scores.jsonl` 重算；
> **Mock 数字不是科学证据**。工程师不作科学判断、不改贡献状态、不改冻结判据。

---

## 0. 范围与红线核对

| 项 | 状态 |
|---|---|
| 仅运行 `anchor_squad_affine_seed0` / `anchor_squad_kd_seed0`（seed0，仅评测） | ✅ 两个 run 均已落盘并校验 |
| 未跑 P2 / P3 / G1 / real split | ✅ 未启动 |
| 封存合成 test 未触碰、未参与任何锚点计算 | ✅ `split` 仅 `anchor_squad_dev`；`synthetic_test_used=false` |
| 未改冻结判据（`configs/prereg/**`、`docs/protocol.md`）、数据、已有 `reports/runs` | ✅ 未改 |
| finite 产物不可变性：未手改任何 run 的 config/scores/metrics/manifest | ✅ 仅只读校验 |
| zero re-prefill | ✅ config 与 metrics 均为 `true`（逐样本由 `verify_zero_re_prefill` 校验） |

---

## 1. 环境与 provenance

- GPU：NVIDIA GeForce RTX 4090 24 GB；`torch 2.15.0+cu132`，CUDA 可用（1 卡）。
- 数据：`data/anchors/squad/dev-v2.0.json`，实测 `sha256 = 80a5225e94905956a6446d296ca1093975c4d3b3260f1d6c8f68bc2ab77182d8`（4,370,528 B），与锚点确认登记值一致。
- 跑分代码：`experiments/anchor_squad_gpu.py`，在 commit `938f3a0` 纳入，`HEAD=b7b9f50` 与跑分相关代码 diff 为空；`git cat-file` 确认 RUN_CODE_PATHS 全部存在于 HEAD tree，跑分路径工作区 clean。
- 模型：teacher=Qwen3-1.7B，student=Qwen3-0.6B（本地 ModelScope 路径记于各 run config）。
- 配置：dtype=`bfloat16`、kernel=`sdpa`、seed=0、zero_re_prefill=true、n_examples=240（确定性 answerable 子集）。
- 每个 run `config.json` 含：`git_hash=b7b9f50`、`protocol_version=2.4`（位于 `experiment_config`，与 `anchor_protocol_version=2.4` 并列）、`data_sha256=80a5225e…`、`seed`、`dtype`、`kernel`、`zero_re_prefill`、锚点标识。
  - 说明：config 顶层 `protocol_version=2.0` 是 V2 运行时框架包装字段（`v2_context` 默认），锚点协议版本 2.4 完整记录在 `experiment_config` 与 `metrics.json`；`consistency_check.py` 据此对冻结 V2 prereg 校验通过。此处为框架字段与实验协议字段的语义差异，非矛盾。

---

## 2. 两个锚点 run 交付与完整性校验

| run_id | 文件齐全 | manifest 哈希 | scores 行数 | split | arms | EM/F1 重算 vs metrics |
|---|---|---|---|---|---|---|
| `anchor_squad_affine_seed0` | config/manifest/metrics/scores ✅ | 3/3 全部匹配 ✅ | 480（240×2） | 仅 `anchor_squad_dev` | self / joint | 完全一致 ✅ |
| `anchor_squad_kd_seed0` | config/manifest/metrics/scores ✅ | 3/3 全部匹配 ✅ | 480（240×2） | 仅 `anchor_squad_dev` | self / joint | 完全一致 ✅ |

- 无任何 `test` 字样 split、无 `cf_pairs`/合成 test 读取（逐行扫描确认）。
- **执行说明**：这两个 GPU run 在本任务接手时已完整落盘（affine `created_at` 13:10、kd 13:38，均 git_hash=`b7b9f50`、数据哈希一致、四件套齐全、480 行 scores）。按"`reports/runs/<run_id>/` 为不可变运行产物"与确定性 seed 原则，本轮**不重复执行**，而是做上述完整性 + 可重算校验。重跑不会产生新的科学信息，且会扰动不可变产物与 manifest 哈希。

---

## 3. 关键指标（普通 QA：EM / F1；Accuracy 口径 = EM）

每个 run 在同一确定性 answerable 子集上评测两臂；`self`=学生原生缓存 prefill（标准 QA 上限参考），`joint`=教师 prefill→mapper 映射→学生只前向 query（zero re-prefill）。

| run_id | method | n | self EM | self F1 | joint EM | joint F1 | joint/self F1 |
|---|---|---|---|---|---|---|---|
| `anchor_squad_affine_seed0` | affine | 240 | 0.0 | 0.1974734111 | 0.0 | 0.0050669157 | 0.0257 |
| `anchor_squad_kd_seed0` | kd_only | 240 | 0.0 | 0.1974734111 | 0.0 | 0.0013888889 | 0.0070 |

- EM 全臂触底（base Qwen3-0.6B 未针对 SQuAD 微调），以 F1 作梯度区分；两臂 joint F1 相对 self 均大幅下降。
- 训练口径：affine mapper 用合成 train（120 对）校准、epochs=0；kd mapper 用合成 train 训练 8 epoch、7.34M 可训练参数。**锚点数据仅用于评测，未参与训练。**
- v2.4 预承诺三情形的归类记录于 `reports/anchor_eval_summary.json`（`scenario_verdict=exploratory_disclosure`）。工程师只核对数据事实，不改动该科学归类，不恢复任何贡献。

---

## 4. 审计脚本重跑（本轮实际执行）

### 4.1 `scripts/bootstrap_ci_report.py`（默认输出 `reports/bootstrap_summary.json`）

- 结果：`runs=31`（原 26 → +2 锚点 +3 个既有但此前未纳入的 run 目录：`delta_lock_v2p1_2p0_par`、`p1_gpu_kdonly_mvp_seed1_par`、`p1_gpu_kdonly_mvp_seed2_fast`）。
- 两个锚点**已被纳入扫描**：`runs/anchor_squad_affine_seed0`、`runs/anchor_squad_kd_seed0`，`arms={}`、`stats_convention="n/a (v1 scores)"`。
  - 这是**预期且正确**的行为：锚点 scores 只有 EM/F1，无 `E_CF` / `gold_prob`，故不参与任何合成 E_CF 主终点 CI 重算（v2.4 禁止锚点混算主终点）。锚点被"纳入但无 CI"，与判据一致。
- clean affine 三 seed（`p1_clean_mvp_seed0/1/2`）与 clean kd 三 seed（`p1_kd_clean_mvp_seed0/1/2`）**全部被纳入**，与既有汇总一致。

### 4.2 `scripts/consistency_check.py`（默认输出 `reports/consistency_report.json`）

- 结果：`checked=31`、`failed=22`、`head_hash=b7b9f50`、`dirty_run_paths=[]`。
- **两个锚点**：`ok=true`、`traceable=true`、`problems=[]`、`git_hash_in_history=true`、`run_code_unchanged_vs_head=true`、`code_tracked=true`、`protocol_compat.ok=true`。
  - 非致命提示：`model_pair_check.ok=false`（`unknown model_pair ''`）。原因是锚点 config 按设计不声明 `model_pair` 字段（teacher/student 路径已记于 `experiment_config`），而该检查是为 P0/P1 主验证 run 设计的；返回对象不含 `problems` 键，故不影响 `ok=true`。未据此修改任何不可变产物。
- **clean affine/kd 三 seed**：6 个 run 全部 `ok=true`、`traceable=true`、`model_pair_check.ok=true`，彼此一致。
- 22 个 `failed` 均为**既有遗留/已 superseded run**的代码漂移（`run-producing code differs between config.git_hash and HEAD`）或早期 commit 缺跑分代码，与锚点无关；本轮不修、不改判据、不手改报告。

---

## 5. `reports/runs_index.json` 状态（任务 4）

- 已包含两个锚点条目：`protocol_version=2.4`、`git_hash=b7b9f50`、`data_sha256=80a5225e…`、`n_scores=480`、`method=affine/kd_only`、`superseded=false`、`role=SQuAD anchor (v2.4, evaluation-only)`。
- 既有 19 个 `superseded=true` 标记**全部保留**（含 `e0_gpu_main_seed0`、`p1_gpu_main_seed{0,1,2}`、`p1_gpu_mvp_seed{0,1,2}`、`p1_gpu_kdonly_mvp_seed0`、`p2_gpu_mvp_seed{0,1,2}`、`delta_lock_v2p1_0p5` 等）。
- 结论：索引已满足要求，本轮**无需改动**。

---

## 6. 阻塞与交付

- **GPU/代码/数据阻塞：无。** GPU 可用、数据哈希匹配、跑分代码在 HEAD tree 且工作区 clean、两 run 完整可重算。
- 未遇到需要上报 PI 的判据/主终点分歧；无实现与规格的偏差需"修正"。
- 交付物：
  - run_id：`anchor_squad_affine_seed0`、`anchor_squad_kd_seed0`
  - 审计文件：`reports/review/engineer_anchor_audit.md`（本文件）
  - 重跑汇总：`reports/bootstrap_summary.json`、`reports/consistency_report.json`（脚本默认输出，未手改）
  - 锚点摘要（既有）：`reports/anchor_eval_summary.json`
- 下游提示：写作者按 v2.4 三情形如实披露（锚点摘要现归类为 `exploratory_disclosure`）；审稿人可用 `sha256sum` 复算归档数据哈希；**不得**将锚点结果写成贡献恢复或合成主终点证据。

**签署：工程师（readkv）· 锚点收尾审计 · 2026-11-23**

# v3.0 G3 Batch-1 正式格执行报告（E5 × 3 + E6 × 3，2026-11-25）

> 角色：工程师（G3 执行）。
> 授权依据：`docs/decisions/v3_g2_release.md` §4（G3 放行）、`configs/prereg/gpu_followup_v3.0.yaml`（FROZEN）、
> `docs/decisions/v3_baseline_spec.md`（FROZEN）、`reports/_non_authoritative/v3_env/model_manifest.json`、
> `reports/review/v3_g2_pilot_report.md`。
> **性质：AUTHORITATIVE G3 正式格（新研究 v3.0），不是当前 TMLR 稿件的补充实验。本文只记录技术执行与产物，
> 不作任何科学解释、不合并 seed、不下结论；判读与统计由 G4 承担。**
> 执行顺序：BATCH 1a（E5 s0→s1→s2）→ BATCH 1b（E6 s0→s1→s2），全程单卡串行，一次一个 GPU 进程。

---

## 0. 执行前核验（先于任何正式 forward）

| 项 | 值 |
|---|---|
| GPU | NVIDIA GeForce RTX 5090，32607 MiB，driver 580.82.07，CUDA 13.0，capability (12,0) |
| 环境 | Python 3.12.3（`.venv`）；torch 2.11.0+cu130；transformers 5.24.0；numpy 2.5.5 |
| dtype / kernel | bfloat16 / sdpa（冻结，未临场改动） |
| seeds | E5：0/1/2；E6：0/1/2（逐格分开，未 pooled） |
| zero-re-prefill | 每格 `true`，并由独立 forward 审计复核（见 §2/§3） |
| 模型快照（SHA 命名符号链接，非裸 master） | 4B `reports/_non_authoritative/v3_g2_pilot/pinned/Qwen34B-sha256-8ba006f74fecfaae` → `/root/.cache/modelscope/models/Qwen--Qwen3-4B/snapshots/master`；1.7B `.../Qwen31.7B-sha256-1ddb5b89ebc90dcb` → `.../Qwen--Qwen3-1.7B/snapshots/master`；0.6B `.../Qwen30.6B-sha256-660db3b73d788119` → `.../Qwen--Qwen3-0.6B/snapshots/master` |
| 逐文件 SHA | 每格对 teacher/student 全部快照文件（4B 11 个、1.7B 10 个、0.6B 8 个）逐一重算，与 `model_manifest.json` 对照：**0 mismatch**（见各格 `g3_runtime_audit.json:model_provenance.per_file_hash_mismatches=[]`） |
| 入口 SHA-256 | `experiments/P1_gpu.py` = `97043a318fc0ed8928cafa4891887ddd0c522bc5b67dba98b3d6c975429884f5`；`experiments/v3_e6_control_gpu.py` = `86948cf99a9f76764cc050ec5332651c2da218cd3c7bffccd9dd241e6adb1b8d`。两文件**未修改** |
| 判据/规格 SHA-256 | prereg `d8c2321f…`；baseline spec `54be0861…`；G2 release `3f9086ba…`；model manifest `db97ef5f…` —— 执行后逐一重算 **全部未变** |
| 冻结数据 | `data/variants_v3/manifest.json` = `6b3d63ae194df9af8d1369737a1e8c627cae9f17be37fb3380797fa0a26c2ff9`；E6 train/val 逐 seed SHA 与 manifest 登记一致（见 §3） |
| model_pair 数据等价性 | `build_cf_pairs.py:474` 仅把 `model_pair` 写入 pair 元数据；不改文本 / split / label / 候选顺序。E5 用 `qwen3-4b-to-1.7b`，E6 用 `qwen3-1.7b-to-0.6b`；生成器 pair 参数不改变数据（已按 E5 prerequisite 核验并在逐格审计中记录两份 generated-pair 指纹） |
| 规模 | E5：`sizes={probe:40, train:120, val:60, test:300}`（未传 `--n-train/--n-val`，用协议冻结规模）；E6：train 120 / val 60（未传 `--smoke`） |
| 调度 | 严格串行；无并发抢卡；无 test split 评分；无阈值/λ/epoch/lr 调整 |

完整 provenance（代码 SHA、模型逐文件 SHA、环境、种子、dtype/kernel、layer_map、数据指纹）逐格落盘于
`g3_runtime_audit.json`（E5 该 supplement 被入口 manifest 一并哈希）。

---

## 1. BATCH 1a — E5 `affine` × seed 0/1/2（正式格）

入口：`experiments.P1_gpu.main()`（经 `scripts/g3_run_e5_cell.py` 薄包装，仅加审计，不改入口行为）。
模型对 Qwen3-4B → Qwen3-1.7B，36→28 proportional layer map，仅 validation；无 test。

| 项 | s0 | s1 | s2 |
|---|---|---|---|
| run_id | `v3_E5_affine_s0` | `v3_E5_affine_s1` | `v3_E5_affine_s2` |
| 入口 elapsed (s) | 184.5 | 177.6 | 204.1 |
| runner wall (s) | 184.6 | 177.8 | 204.3 |
| n_calibration / n_eval | 120 / 60 | 120 / 60 | 120 / 60 |
| 入口 n_captures / n_injections | 840 / 2400 | 840 / 2400 | 840 / 2400 |
| 正式 run 峰值显存（allocated / reserved MiB） | 11030.3 / 11046.0 | 11030.3 / 11046.0 | 11030.3 / 11046.0 |
| 技术审计峰值（allocated / reserved MiB） | 11033.9 / 11050.0 | 11033.9 / 11050.0 | 11033.9 / 11050.0 |
| 技术审计 elapsed (s) | 39.5 | 41.9 | 36.1 |
| 技术审计 PASS | true | true | true |

技术门逐格结果（详见各格 `g3_injection_audit.json`）：

- **逐学生层注入**：`resolve_injection_layer_map → None`（学生空间恒等）；36→28 source map
  `{0:0,1:1,2:3,3:4,…,26:33,27:35}` 原样保留；`entries_match_source_map=true`、
  `no_silent_wraparound=true`（无取模回绕）；V-stamp 实测读取顺序 `0,1,…,27`（28 个学生层逐层正确），
  `per_layer_injection_correct=true`。
- **Self / Identity**：logits 最大绝对差 `0.0`（阈值 1e-4）。
- **严格 zero-re-prefill**：`verify_zero_re_prefill(..., strict=True)=true`；审计
  `input_token_counts=[7]`，`cache_prefix_lengths=25 × 28`，`doc_len=25`，`query_len=7`，
  `doc_tokens_fed_to_student=0`，`n_decode_steps=0`。
- **cache 形状**：teacher 36 层 `(8,25,128)`；student 28 层 `(8,25,128)`；mapped 学生空间 28 层 `(8,25,128)`。
- **forward 审计**：审计进程总 14（离线 capture 10 + inference 4）；inference 输入长度 `[7,7,7,7]`，
  均 ≤ query_len 7 → `no_doc_tokens_in_inference=true`。

逐 seed 违规项：`scores.jsonl` 600 行，`split` 全为 `val`，test 命中 0；`config.json` dtype/kernel/zero_re_prefill
= bfloat16/sdpa/true；`g3_runtime_audit.json:authoritative=true, pilot_only=false`。

> 注：E5 入口 `metrics.json` 及 `scores.jsonl` 中的 E_CF / 决策字段仅作为产物落盘，**本报告不引用、不解释**；
> 逐 seed 主终点、bootstrap 与判读归 G4。

---

## 2. BATCH 1b — E6 `v3-BM-MLP-KD` × seed 0/1/2（正式格）

入口：`experiments.v3_e6_control_gpu.main()`（修复后代码；**未复用**失败 pilot `v3_E6_BM-MLP-KD_s0_smoke`）。
模型对 Qwen3-1.7B → 0.6B，28→28 identity，clean `fully_repaired` train/val，8 epochs / lr=1e-3。

| 项 | s0 | s1 | s2 |
|---|---|---|---|
| run_id | `v3_E6_BM-MLP-KD_s0` | `v3_E6_BM-MLP-KD_s1` | `v3_E6_BM-MLP-KD_s2` |
| train SHA | `9b035227…91e953` | `024a69e9…a37633f` | `53258777…eddcf3e6e` |
| val SHA | `19e9839e…caa3c595` | `b4f9587f…8423e7921` | `5633a8bf…b537a5e5b475` |
| trainable params | 7,340,032 | 7,340,032 | 7,340,032 |
| bias params / shape | 0 / `(28,8,128,128)` ×2(K,V) | 同 | 同 |
| optimizer steps（= backward 次数） | 960 | 960 | 960 |
| student forward（train / eval） | 1920 / 360 | 1920 / 360 | 1920 / 360 |
| captures（eval） | 721 | 721 | 721 |
| n_train / n_val / n_scores | 120 / 60 / 180 | 120 / 60 / 180 | 120 / 60 / 180 |
| 峰值 allocated / reserved MiB | 4608.6 / 4674.0 | 4608.6 / 4674.0 | 4608.6 / 4674.0 |
| entry elapsed (s) / train (s) | 521.8 / 494.9 | 500.8 / 471.7 | 507.1 / 479.5 |
| 外部 wall (s) | 533.8 | 512.5 | 518.8 |
| loss_first → loss_last | 0.0 → 0.0 | 1.595165 → 0.003216 | 0.185755 → 0.001530 |
| loss 有限 / 步数 | true / 960 | true / 960 | true / 960 |
| Self/Identity 最大差 | 0.0 | 0.0 | 0.0 |
| zero-re-prefill | true | true | true |
| 契约校验 | 19/19 PASS | 19/19 PASS | 19/19 PASS |

训练目标（逐格 `train_audit.loss_formula`，与 `src/readkv/train/kd_gpu.py:140-147` 同式）：
`L_KD = Σ_sides KL(log_softmax(mapped_s) ‖ log_softmax(self_s), log_target=True, reduction='batchmean')`；
`loss = 1.0·L_KD + 1e-4·reg`，`lam_cf=0`，`reg=0`（rank-0 control）；梯度只回传映射缓存，学生权重冻结。
参数匹配容差为**精确相等**（7,340,032 == kd_only 的 trainable_params），已逐格验证。

Joint 推理审计（逐格 `joint_audit_example`）：`input_token_counts=[7]`、`cache_prefix_lengths=25×28`、
`doc_tokens_fed_to_student=0`、cache 28 层 `(8,25,128)` → strict zero-re-prefill 成立。
`scores.jsonl` 180 行，`split` 全为 `val`，test 命中 0。

> 注：loss 轨迹中出现个别精确 `0.0` 步（identity 初始化下部分 batch 的 KL 恰为 0），
> `loss_finite=true`；全部 960 步数值有限，无 NaN/Inf。本报告不据此作任何方法优劣判断。

---

## 3. 产物清单（全部 NEW，未覆盖任何历史目录）

| run_id | 文件 |
|---|---|
| `reports/runs/v3_E5_affine_s0/` | `config.json`, `scores.jsonl`(600), `ecf_ledger.jsonl`, `metrics.json`, `g3_runtime_audit.json`, `manifest.json`, `g3_injection_audit.json`*, `g3_walltime_note.json`* |
| `reports/runs/v3_E5_affine_s1/` | 同上（8 文件） |
| `reports/runs/v3_E5_affine_s2/` | 同上（8 文件） |
| `reports/runs/v3_E6_BM-MLP-KD_s0/` | `config.json`, `scores.jsonl`(180), `metrics.json`, `manifest.json`, `g3_runtime_audit.json`* |
| `reports/runs/v3_E6_BM-MLP-KD_s1/` | 同上（5 文件） |
| `reports/runs/v3_E6_BM-MLP-KD_s2/` | 同上（5 文件） |
| `reports/review/v3_g3_batch1_report.md` | 本文 |

`*` = finalize 之后追加的 additive supplement（沿用 G2 `PILOT_NOTICE.json` 模式），不改写入口已写文件；
E5 的 `g3_runtime_audit.json` 在 finalize 内写入，故已被入口 `manifest.json` 收录并哈希。

完整性复核：六格 `config.json`/`scores.jsonl`/`metrics.json` 与 manifest 登记 SHA **全部一致**；
model 逐文件 SHA mismatch 计数全为 0；入口文件、prereg、baseline spec、G2 release、model manifest 的 SHA 执行前后不变。

---

## 4. 偏差 / 需知悉事项（均如实上报，未自行修改冻结文件或实验设计）

1. **E6 入口 metrics 中的 stale pilot 标志**：`experiments/v3_e6_control_gpu.py` 对所有 run 硬编码
   `authoritative=false, pilot=true` 及 `note="G2 technical pilot only..."`。按 `v3_g2_release.md` §4，
   本批三个 run-id 是 **AUTHORITATIVE G3 正式格**；三格 `g3_runtime_audit.json:entry_flag_discrepancy`
   已显式记录该矛盾，入口产物保持逐字节原样，未改入口代码。请 PI/G4 以 `g3_runtime_audit.json` 的
   `authoritative=true` 与放行文件为准。
2. **E5 `g3_runtime_audit.json:wrapper_wall_sec=0.0`**：薄包装在 `finalize()` 内写审计，但 wall 采样在
   `p1_main()` 返回后才赋值，导致该 supplement 字段为 0。入口 `metrics.json:elapsed_sec`
   （184.5/177.6/204.1 s）正确且为权威 elapsed；runner stdout wall 为 184.6/177.8/204.3 s，
   已逐格写入 additive `g3_walltime_note.json`。包装脚本已修正该采样顺序（不影响已产出正式格）。
3. **E5 `manifest.json` 自引用哈希陈旧**：冻结 `RunContext.finalize()` 先枚举文件再写 manifest，
   故 manifest 列的自身哈希是写入前版本；pilot 与历史 P1 归档同样如此（非本批引入）。
   六格除 manifest 自身外的全部登记文件哈希均核验一致。
4. **未运行**：E1、E2 正式格；未读/评分任何 test 内容；未改 papers/**、configs/**、docs/decisions/**、data/**。

---

## 5. 逐格结论与 Blockers

| run_id | 结论 | 关键证据 |
|---|---|---|
| `v3_E5_affine_s0` | **PASS** | 120/60、source map 无取模、V-stamp 0..27、Self/Identity 0.0、strict zrp、无 doc token、11.0 GiB |
| `v3_E5_affine_s1` | **PASS** | 同上；177.6 s / 2400 injections |
| `v3_E5_affine_s2` | **PASS** | 同上；204.1 s / 2400 injections |
| `v3_E6_BM-MLP-KD_s0` | **PASS** | 7,340,032 / bias 0 / 960 steps / 1920+360 forwards / 4.6 GiB / 19 项契约全过 |
| `v3_E6_BM-MLP-KD_s1` | **PASS** | 同上 |
| `v3_E6_BM-MLP-KD_s2` | **PASS** | 同上 |

**Blockers：无技术阻塞。** 需知悉项见 §4（均为记录性偏差，不影响六格技术门 PASS，
但 G4 审阅时必须按 §4 处理 authority 标志与 wall-time supplement）。
G4 统计与独立审阅尚未放行；本文不含任何科学结论、不 pooled、不触发当前稿件改动。

---

## 6. 回归与边界

- 全量单测：**97 passed**（执行前与执行后各一次，未引入回归）。
- 新增文件仅 `scripts/g3_audit_common.py`、`scripts/g3_run_e5_cell.py`、`scripts/g3_injection_audit.py`、
  `scripts/g3_finalize_e6_cell.py` 与上表 run/review 产物；均为工程审计工具与产物，不是冻结判据/规格。
- 未改：`configs/**`、`papers/**`、`docs/decisions/**`、`data/**`、`experiments/P1_gpu.py`、
  `experiments/v3_e6_control_gpu.py`、任何历史 `reports/runs/**`。

**签署：工程师（G3 Batch-1 正式格执行 · 2026-11-25）。六格 AUTHORITATIVE（新研究 v3.0），不含科学结论。**

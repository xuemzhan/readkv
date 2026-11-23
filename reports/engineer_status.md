# 工程师执行状态报告（V2.0 · 反事实功能保真）

> 角色：工程师（readkv）。日期：2026-11-22。本报告只记录实现与真实运行事实；
> Mock 数字一律不构成科学证据。所有结论性统计须由 `reports/runs/<run_id>/scores.jsonl` 重算。

---

## 0. 环境与模型

| 项 | 状态 |
|---|---|
| Python/torch | `.venv/bin/python` = Python 3.13.11；torch 2.15.0+cu132；transformers 5.24.0；CUDA 可用 |
| GPU | NVIDIA RTX 4090 24GB（空闲约 23.3GB），空闲显存满足单卡口径 |
| 磁盘 | overlay 1.5T，可用约 354GB |
| 依赖 | PyPI / https://modelscope.cn/ 可访问；pytest 9.2.0 |
| 已下载模型 | `Qwen/Qwen3-0.6B` → `/root/.cache/modelscope/models/Qwen--Qwen3-0.6B/snapshots/master`（base，28 层 / 8 KV heads / head_dim=128 / rope_theta=1e6） |
| 已下载模型 | `Qwen/Qwen3-1.7B` → `/root/.cache/modelscope/models/Qwen--Qwen3-1.7B/snapshots/master`（base，28 层 / 8 KV heads / head_dim=128） |
| 已下载模型 | `Qwen/Qwen3-4B` → `/root/.cache/modelscope/models/Qwen--Qwen3-4B/snapshots/master`（base，36 层；权重完整；merges.txt/vocab.json 因网络速率下载失败，已从 Qwen3-0.6B 复制——Qwen3 全系列 tokenizer 相同，已实测 `get_vocab()` 一致） |
| 未下载 | 8B（离线压力）— 本轮未下载，相关阶段未运行 |

环境为任务方声明「已就绪、不要重复搭建」，本轮只复核未重装。

---

## 1. P0 / E0 实现门（已完成，PASS）

### 1.1 实现内容

- **`src/readkv/models/hooks.py`** 三函数真实 GPU 前向已实现（pinned transformers 5.24 / Qwen3）：
  - `capture_teacher_cache`：对一份文档独立 prefill 一次；从 `DynamicCache.layers[i].keys/values` 取 Qwen3 的 **post QK-Norm + post RoPE** K/V；用 fp32 做 de-RoPE 得到内容空间 key；返回 `KVCache`（H_kv,T,d，fp32 numpy），metadata 含 position_ids / RoPE / 层映射 / dtype / kernel。
  - `inject_and_generate`：re-RoPE 内容空间 K 到学生位置，显式 `position_offset`；用全新 `DynamicCache` 注入；首 token logits 取自 query 末位；全程学生只处理 query token，zero re-prefill。
  - `verify_zero_re_prefill`：forward pre-hook 记录每次学生 forward 的 input token 数，断言无文档 token 进入、forward 次数 = 1+解码步数，并回写 run 的 `zero_re_prefill=true`。
  - 适配 `loader.py::resolve_layers` 与 Qwen3 half-split RoPE（cat(freqs,freqs)+rotate_half），bf16 + sdpa 口径。
- **`scripts/gen_teacher_cache.py`**：`--backend gpu` 由占位 NotImplementedError 改为真实调用 `capture_teacher_cache`、按 `PairCacheStore` 落盘、教师卸载。
- 51 个原有单测 + 2 个新增 hooks 单测 → **53 passed**。

### 1.2 E0 真实测量（run_id = `e0_gpu_mvp_seed0`）

用 Qwen3-0.6B 本体既做 capture 又做 inject（identity Mapper），隔离纯实现残差；40 对探针（≥6 模板族），bf16 + sdpa。判据来自 `configs/prereg/phase3_loss_config_v2.1.yaml §e0_measurement_error_tolerance`：

| 指标 | 实测 | 冻结门槛 | 结论 |
|---|---|---|---|
| Self(原生缓存两步) vs Identity 首 token logit cosine（最小） | **1.000000** | ≥ 0.9998 | 通过 |
| Identity first-token KL（最大） | **0.000000** | ≤ 0.001 | 通过 |
| 首 token argmax 一致率 | **1.000 (80/80)** | ≥ 0.929 | 通过 |
| cache 落盘/加载 round-trip bit-identical | **True（80/80）** | 必须 True | 通过 |
| zero_re_prefill 断言 | **80/80 True** | 必须 True | 通过 |
| 测量误差上限 | **2.2e-16** | < 效应/3 = 6.95 | 通过 |
| 待研究效应估计（40 对探针 `|D_self|` 有效子集均值） | 20.86 | — | 已记录 |

**E0 判定：PASS，P0 放行门已满足。** 可进入 P1。

补充诊断：整段一次 full-prefill vs 注入路径的全词表 cosine 最小 0.9993（47/80 低于 0.9998），但**注入与学生原生缓存两步路径逐 bit 一致（cosine=1.0）**——该残差完全来自 sdpa 在「整段 prefill」与「缓存+query 两步」两种 kernel 路径的差异（`docs/gpu_handoff.md §2` 预告），不是实现错误。此量已作为 `one_shot_min_logit_cosine` 记入 run，不计入 E0 主锚点。

产物：`reports/runs/e0_gpu_mvp_seed0/{config.json,scores.jsonl,metrics.json,manifest.json,cache/}`。`scripts.consistency_check` 检查通过（0 problems）。

---

## 2. P1 基准（真实 GPU，已完成）

### 2.1 实现与口径

- `src/readkv/models/gpu_backend.py`：实现 `pair_side_cache` / `inject` / `candidate_logits` 的 GPU 契约；教师 1.7B 与学生 0.6B **各自独立 prefill**；g(C,q) 用真实 next-token 候选首 token logits（**无 mock 正确性偏置**）。
- `experiments/P1_gpu.py`：复用 `evaluate.cf_pipeline.run_cf_pipeline`，score schema 与 mock 接线完全一致；校准只用 train split 拟合 affine KV mapper（28→28 identity 层映射），评测只用 val split（封存 test 留给 P3），判据来自冻结的 `phase1_benchmark_decision.yaml`，τ=1.0 / self_threshold=0.1 / n_resamples=10000 来自冻结配置。
- 每次运行 `config.json` 含 protocol_version=2.0 / git_hash / seed / dtype=bfloat16 / kernel=sdpa / **zero_re_prefill=true**；≤3 seed 已跑满。

### 2.2 真实 run 与结果（MVP：1.7B→0.6B，等深）

| run_id | seed | decision | joint E_CF [95% CI] | identity E_CF | dual_correct | flip_consistency | coverage | normalized_E_CF |
|---|---|---|---|---|---|---|---|---|
| `p1_gpu_mvp_seed0` | 0 | distortion_exists | **1.968 [1.614, 2.324]** | 0.000 | 0.667 | 0.938 | 0.800 | 0.334 |
| `p1_gpu_mvp_seed1` | 1 | distortion_exists | **1.934 [1.569, 2.311]** | 0.000 | 0.650 | 0.898 | 0.817 | 0.290 |
| `p1_gpu_mvp_seed2` | 2 | distortion_exists | **2.123 [1.695, 2.571]** | 0.000 | 0.617 | 0.958 | 0.800 | 0.322 |

- 机制方向（诊断，非结论）：seed0 的 K-only E_CF=0.630、V-only=1.851、Joint=1.968 —— V-only 已接近 Joint，提示失真主要落在 Value 消费侧；H1 成立，可按决策树进入 P2 机制诊断。
- 信息归因（`info_attribution = 控制组 E_CF − joint E_CF`，seed0）：mismatch +4.134、random +2.249、zero +4.191，均为正，说明正确缓存携带了可辨识信息（非「无信息即可低误差」）。【R8 符号勘误：原表述误写为 joint 减控制组，数值本身未变】
- 每个 run 600 行 `scores.jsonl`（60 val 对 × 10 臂）；逐对 E_CF / g/D / dual_correct / flip 等由 `scripts.bootstrap_ci_report` 从 scores 独立重算，与 metrics.json 一致。
- `dual_correct≈0.62–0.67 < 0.7`：Self 锚点本身在合成模板上并非全对；这是真实模型行为，未用 mock 偏置掩盖。此项若进入 P3 方法比较会触发 `tradeoff` 审查，须如实报告。

### 2.3 主验证对（非等深 4B→1.7B，seed 0/1/2 全部完成）

- E0：`e0_gpu_main_seed0`（学生 1.7B 自注入）—— 与 MVP 同样 PASS：Self-vs-Identity cosine≈1.0、KL=0、EM=1.0、round-trip bit-identical、zero-re-prefill 80/80、误差上限 2.2e-16 ≪ 效应/3=6.66。
- P1（教师 4B 36 层 → 学生 1.7B 28 层，proportional layer_map）：

| run_id | seed | verdict | joint E_CF [95% CI] | Self dual | joint dual | flip | coverage | normalized E_CF |
|---|---|---|---|---|---|---|---|---|
| `p1_gpu_main_seed0` | 0 | distortion_exists | **6.044 [4.741, 7.365]** | 0.733 | 0.300 | 0.490 | 0.817 | 0.812 |
| `p1_gpu_main_seed1` | 1 | distortion_exists | **5.365 [4.156, 6.663]** | 0.650 | 0.283 | 0.562 | 0.800 | 0.827 |
| `p1_gpu_main_seed2` | 2 | distortion_exists | **6.080 [4.847, 7.395]** | 0.783 | 0.283 | 0.542 | 0.800 | 0.995 |

- info_attribution（控制组 E_CF − joint E_CF）：seed0 mismatch −0.488 / random +0.229 / zero −0.447；seed1 +1.414 / +0.441 / −0.040；seed2 −0.248 / −0.262 / −0.617 —— **多数为负或接近零**。
- **如实上报**：非等深 affine mapper 的迁移质量很差：Joint 的 E_CF 接近甚至高于错文档/零缓存控制组，joint dual_correct 从 Self 的 0.65–0.78 掉到约 0.28–0.30。三个 seed 一致，属真实 GPU 结果，不掩盖、不调参。按 `p0_direction.md §3.3` 决策树，这是「强基线未消除失真」但**伴随明显质量退化**，后续阶段必须如实报告权衡，不能宣称迁移成功。
- 修复记录：非等深路径曾发现两处实现缺陷（LayerMap 学生/教师层数赋值写反；AffineMapper.transform 不自动重排教师层），均已修正后重跑；修正只涉及实验脚本层，未改冻结判据与 hooks 契约。

### 2.4 审计

`scripts.consistency_check` 对全部真实 run 通过（0 problems）；`scripts.bootstrap_ci_report` 从 `scores.jsonl` 重算 V2 簇级 paired CI，与 metrics.json 一致（例：seed0 joint 1.968 [1.614, 2.324]）。

> 注：`info_gap` 在此管线中以 `info_attribution`（控制组 E_CF − joint E_CF，见上）形式联合报告；逐对 `info_gap` 字段仅当 PairCFRecord 收到 control_logits 时填充，当前编排把控制组作为独立臂，故 metrics 中该字段为 None，但 `info_attribution` 已提供等价的聚合口径。此偏差在此备案，未改任何冻结判据。

---

## 3. P2–P5（如实标注）

| 阶段 | 状态 | 说明 |
|---|---|---|
| P2 机制诊断（E2） | **未运行** | P1 已给出 V-only≈Joint 的方向性线索，但 Oracle 层/头/Token 修复与独立文档预测价值检验未执行；不得仅凭 P1 的 K/V 四臂 E_CF 声称机制层成立 |
| P3 方法（E3/E4） | **未运行** | CF-RCT-lite/mech 未训练；Huber δ 最终值未在验证集网格锁定；封存测试未运行；KD-only 主基线未跑 |
| P4 泛化（E4） | **未运行** | 未见模板 / 真实文档子集未跑；封存 test 未运行 |
| 8B 离线压力（E5 一部分） | **未运行** | 8B 未下载 |
| P5 成稿 | **未运行** | 无 |

按任务优先级已优先保证 P0/E0 与 P1 的真实 GPU 证据（共 8 个真实 run、4080 行 scores.jsonl）。上述阶段没有真实产物，**不代表任何科学结论**。

---

## 4. 产物清单与下游交接

- E0 证据（MVP 等深）：`reports/runs/e0_gpu_mvp_seed0/`
- E0 证据（主验证学生侧）：`reports/runs/e0_gpu_main_seed0/`
- P1 证据（MVP 等深）：`reports/runs/p1_gpu_mvp_seed{0,1,2}/`
- P1 证据（主验证非等深）：`reports/runs/p1_gpu_main_seed{0,1,2}/`
- 环境清单：`reports/environment.json`（python/torch/transformers/CUDA/GPU/dtype/kernel/模型路径/已装包）
- 交接给审稿人：上述 run 目录 + `scripts.bootstrap_ci_report` / `scripts.consistency_check` 可直接重算、审计
- 交接给写作者：E0 残差表（§1.2）与 E1 基准表（§2 回填）；所有数值均来自真实 GPU 后端

---

## 5. 问题与偏差上报

- 规格书 `docs/gpu_handoff.md §2.3` 规定 `answer_logits → (2,)`，故 E0 的 cosine/KL 锚点按**候选首 token 2 维 logits**计算（与 MockBackend `answer_logits` 返回维度一致）；整段一次 prefill 的全词表残差作为补充诊断单列，未混入锚点。此口径选择在此显式备案，未改动任何冻结判据。
- E0 效应估计用多 token 候选的序列 logprob D_self（尺度约 17–20），与主终点 g 的 2 维 logit 尺度不同；因测量误差上限为 2.2e-16，远小于任一合理效应估计，不影响 E0 判定。此差异在此显式备案。

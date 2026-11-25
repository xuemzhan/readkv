# readkv 权威证据可复现指南

> 目的：让外部人员从零复现本项目**当前权威证据**（失败边界 / 数据泄漏教训负面实证研究的 9 个干净 run）。
> 性质：说明性文档，只转抄冻结产物，**不改**代码、数据、`configs/prereg/**`、`docs/decisions/**`、`reports/runs/**`、论文，也不重算任何统计。
> 日期：2026-11-23。数值 / 版本唯一来源：`reports/environment.json`、`reports/runs/<run_id>/{config,metrics}.json`、`data/tasks/manifest.json`、`reports/data/**`、`docs/decisions/**`、`configs/*.yaml`、各 `experiments/*_gpu.py` 的 argparse。
>
> **可复现范围与边界（先读）**：本指南复现的是权威 run 的**产物格式与统计口径**。项目当前定位为失败边界 / 数据泄漏教训的负面实证研究：贡献(1)(2) 撤回、贡献(3) withheld、封存 test 未评测、主终点未评估、`real=0`、P2/P3/P4 正式取消。复现这些 run **不等于**恢复任何正向贡献。

---

## 1. 环境（转抄 `reports/environment.json`）

| 项 | 实测值 |
|---|---|
| OS / 可执行 | Linux（executable `/root/.local/share/uv/python/cpython-3.13.11-linux-x86_64-gnu/bin/python3.13`） |
| Python | 3.13.11 |
| torch | 2.15.0+cu132（installed_packages 同时记 `"torch": "2.15.0"`） |
| transformers | 5.24.0 |
| CUDA | available=true，version 13.2 |
| GPU | NVIDIA GeForce RTX 4090（24GB，见 `configs/eval.yaml::resource.single_gpu_24gb`） |
| 计算口径 | dtype=`bfloat16`（bf16）、kernel=`sdpa`、device=`cuda` |
| ModelScope | `modelscope` 1.40.3（`modelscope-hub` 0.7.1；`huggingface-hub` 2.4.0） |
| pytest | 9.2.0 |
| 关键其它包 | numpy 2.5.5、scipy 1.18.1、safetensors 0.8.0、tokenizers 0.23.3、pydantic 2.14.4、triton 3.9.0 |

**模型本地路径（environment.json 记录）与 revision**：

| 模型 | 本地 snapshot 路径 | revision 记录 |
|---|---|---|
| Qwen3-0.6B（学生 / E0 自注入） | `/root/.cache/modelscope/models/Qwen--Qwen3-0.6B/snapshots/master` | 仅 `master` 快照别名 |
| Qwen3-1.7B（教师，MVP 等深对） | `/root/.cache/modelscope/models/Qwen--Qwen3-1.7B/snapshots/master` | 仅 `master` 快照别名 |
| Qwen3-4B（主验证对 4B→1.7B，旧 run **已 superseded**） | `/root/.cache/modelscope/models/Qwen--Qwen3-4B/snapshots/master`（本机存在，见 §7 限制） | 仅 `master` 快照别名；**未写入 environment.json 的 models 字段** |

> ⚠ **已知限制**：`environment.json` 只记录到 `snapshots/master`，**未把 revision 钉到具体 commit hash**，也未记录 NVIDIA **驱动版本**与 **uv 版本**；模型权重字节级一致性因此无法仅凭本文件保证（见 §7）。权威 MVP 证据只需 0.6B + 1.7B；4B 仅服务于已 superseded 的主验证对，不必为复现权威证据下载。

模型结构参数（`configs/models.yaml`，仅作核对）：0.6B / 1.7B = 28 层、8 KV heads、head_dim 128；4B / 8B = 36 层、8 KV heads、head_dim 128。

---

## 2. 一键安装与网络（本机实测命令）

```bash
# 1) 建虚拟环境（uv 管理 Python 3.13.11）
uv venv .venv

# 2) 安装项目（editable，含 dev 测试依赖）+ ModelScope
uv pip install --python .venv/bin/python -e ".[dev]" modelscope

# 3) 单元测试（权威产物记录 53 passed）
.venv/bin/python -m pytest

# 4) 下载权威 MVP 证据所需模型（ModelScope）；4B 可省略
.venv/bin/modelscope download Qwen/Qwen3-0.6B
.venv/bin/modelscope download Qwen/Qwen3-1.7B
#.venv/bin/modelscope download Qwen/Qwen3-4B   # 仅旧主验证对需要
```

- `pyproject.toml`：Python `>=3.10`、`readkv` 0.2.0；依赖 numpy/scipy/PyYAML/torch/transformers/tqdm，`dev` = pytest；`pip install -e ".[dev]"` 即从 `src/` 安装 `readkv` 包。
- `.venv/bin/` 实含 `python` / `pytest` / `modelscope`（无 `uv`，uv 在系统 PATH）。
- **网络访问**：模型走 ModelScope（`modelscope download`，本机 2026-11-23 实测可用）；SQuAD 锚点走官方站点 `https://rajpurkar.github.io/SQuAD-explorer/dataset/dev-v2.0.json` 与 CC 许可 `https://creativecommons.org/licenses/by-sa/4.0/legalcode.txt`（归档时均 HTTP 200，见 §3）。锚点文件已归档在仓库内，仅当需要重新下载 / 核对哈希时才需外网。HuggingFace 依赖仅安装期由 transformers/tokenizers 拉取（本轮锚点数据本身来自官方站点，非 HF 下载）。

---

## 3. 数据准备

### 3.1 合成任务数据（权威 P0/P1 数据）

- 文件：`data/tasks/cf_pairs.jsonl`（520 行，probe40 / train120 / val60 / test300 / real0）。
- **sha256 `f910f1f1196a21041765834654af8233d216ef4bf4f28f4c60abbd0641aa894a`**（size 455900，lines 520；旧 v2.0 为 `6058fd6d…d1887`，已 superseded）。
- 生成 / 导出：`src/readkv/data/build_cf_pairs.py::build_cf_pairs`；导出脚本 `scripts/export_task_data.py`；manifest 记录的复现命令 `python scripts/export_task_data.py --seed 0`。
- manifest：`data/tasks/manifest.json`（`cf_pairs_v2.1`，`generator_commit=ee74382c…`，`config_fingerprint=a6bc08cc997ac17a`，CC0-1.0，无第三方内容）。
- 数据质量（`manifest.json::quality`）：退化对 0、跨 split 逐字重叠 0、实体池重叠 0、flip 分母 398（排除 F5+F6）、`quality_gate=pass`；独立验收 11/11（`reports/data/acceptance_checks.json`，`scripts/verify_data_fix.py`）。

### 3.2 SQuAD 外部锚点数据（v2.4，仅评测）

- 归档路径：`data/anchors/squad/dev-v2.0.json`、`data/anchors/squad/LICENSE-CC-BY-SA-4.0.txt`。
- **文件 sha256 `80a5225e94905956a6446d296ca1093975c4d3b3260f1d6c8f68bc2ab77182d8`**（4,370,528 字节）；许可文本 sha256 `28a9529c7d0bb4dc51f4bf5c116a3d16ef247a052f7591466768ddf563fd1cf5`（20,138 字节）。许可 **CC BY-SA 4.0，仅评测、不改写、不再发布衍生语料**（SA 不触发）。
- 五项登记见 `reports/data/squad_anchor_manifest.md`；许可核验见 `reports/data/anchor_license_check.md`；PI 授权见 `docs/decisions/anchor_confirmation.md`。锚点脚本在运行时**强制校验**该 sha256（`experiments/anchor_squad_gpu.py::ANCHOR_SHA256`），不符即报错。
- 如需重新获取（来自 `squad_anchor_manifest.md §4`）：

```bash
curl -fSL https://rajpurkar.github.io/SQuAD-explorer/dataset/dev-v2.0.json -o data/anchors/squad/dev-v2.0.json
curl -fSL https://creativecommons.org/licenses/by-sa/4.0/legalcode.txt -o data/anchors/squad/LICENSE-CC-BY-SA-4.0.txt
sha256sum data/anchors/squad/dev-v2.0.json data/anchors/squad/LICENSE-CC-BY-SA-4.0.txt
```

### 3.3 数据硬边界

- `real=0`：无真实反事实文档（`docs/decisions/m4_target_adjustment.md`，受阻披露）；外部效度**仅** SQuAD（必要时 ARC 顺位）锚点 + `real=0` 受阻披露。
- v2.6 AI 生成数据提案**已评估并撤回（not activated）**，v2.6 冻结但**无 `data/generated/` 遗留产物**（`docs/decisions/ai_dataset_final_ruling.md`）；外部效度不依赖任何 AI 生成数据。

---

## 4. 权威 run 复现命令（逐条，来自 argparse）

所有命令在仓库根执行；模型路径为 §1 的本地 snapshot；参数取自各 `experiments/*_gpu.py` 的 `argparse`（未编造）。**权威 9 个 run 的 `--seed` / `--dtype` / `--kernel` / `zero_re_prefill` 对应关系见 §4.5**。

### 4.1 E0 实现门（1 条）

```bash
.venv/bin/python -m experiments.P0_gpu --run-id e0_clean_mvp_seed0 \
  --model /root/.cache/modelscope/models/Qwen--Qwen3-0.6B/snapshots/master \
  --n-probes 40 --seed 0 --dtype bfloat16 --kernel sdpa --device cuda \
  --model-pair qwen3-1.7b-to-0.6b
```
- `P0_gpu.py` argparse：`--run-id`(必填)、`--model`(必填)、`--n-probes`(默认40)、`--seed`(默认0)、`--dtype`(默认bfloat16)、`--kernel`(默认sdpa)、`--device`(默认cuda)、`--model-pair`(默认 qwen3-1.7b-to-0.6b)。config 记录 `git_hash=efc3ba3`。

### 4.2 P1 affine 三 seed（3 条）

```bash
# seed 0
.venv/bin/python -m experiments.P1_gpu --run-id p1_clean_mvp_seed0 \
  --teacher /root/.cache/modelscope/models/Qwen--Qwen3-1.7B/snapshots/master \
  --student /root/.cache/modelscope/models/Qwen--Qwen3-0.6B/snapshots/master \
  --seed 0 --dtype bfloat16 --kernel sdpa --device cuda \
  --mapper affine --n-resamples 10000 --model-pair qwen3-1.7b-to-0.6b

# seed 1（仅改 --run-id 与 --seed）
.venv/bin/python -m experiments.P1_gpu --run-id p1_clean_mvp_seed1 \
  --teacher /root/.cache/modelscope/models/Qwen--Qwen3-1.7B/snapshots/master \
  --student /root/.cache/modelscope/models/Qwen--Qwen3-0.6B/snapshots/master \
  --seed 1 --dtype bfloat16 --kernel sdpa --device cuda \
  --mapper affine --n-resamples 10000 --model-pair qwen3-1.7b-to-0.6b

# seed 2
.venv/bin/python -m experiments.P1_gpu --run-id p1_clean_mvp_seed2 \
  --teacher /root/.cache/modelscope/models/Qwen--Qwen3-1.7B/snapshots/master \
  --student /root/.cache/modelscope/models/Qwen--Qwen3-0.6B/snapshots/master \
  --seed 2 --dtype bfloat16 --kernel sdpa --device cuda \
  --mapper affine --n-resamples 10000 --model-pair qwen3-1.7b-to-0.6b
```
- `P1_gpu.py` argparse：`--run-id`、`--teacher`、`--student`(必填)，`--model-pair`(默认 MVP)、`--seed`(0)、`--dtype`、`--kernel`、`--device`、`--mapper`(affine/ridge，默认 affine)、`--n-resamples`(10000)、`--n-train`(**默认 None=用协议冻结规模 120**)、`--n-val`(**默认 None=60**)。权威 config 均为 `bootstrap_seed=seed`、`sizes={probe40,train120,val60,test300,real0}`、`eval_splits=["val"]`、`git_hash=efc3ba3`。**不要传 `--n-train/--n-val` 缩小值**（那会脱离冻结规模）。

### 4.3 P1 kd_only 三 seed（3 条）

```bash
# seed 0
.venv/bin/python -m experiments.P1_kd_gpu --run-id p1_kd_clean_mvp_seed0 \
  --teacher /root/.cache/modelscope/models/Qwen--Qwen3-1.7B/snapshots/master \
  --student /root/.cache/modelscope/models/Qwen--Qwen3-0.6B/snapshots/master \
  --seed 0 --dtype bfloat16 --kernel sdpa --device cuda \
  --method kd --epochs 8 --lr 1e-3 --n-resamples 10000 --eval-splits val

# seed 1
.venv/bin/python -m experiments.P1_kd_gpu --run-id p1_kd_clean_mvp_seed1 \
  --teacher /root/.cache/modelscope/models/Qwen--Qwen3-1.7B/snapshots/master \
  --student /root/.cache/modelscope/models/Qwen--Qwen3-0.6B/snapshots/master \
  --seed 1 --dtype bfloat16 --kernel sdpa --device cuda \
  --method kd --epochs 8 --lr 1e-3 --n-resamples 10000 --eval-splits val

# seed 2
.venv/bin/python -m experiments.P1_kd_gpu --run-id p1_kd_clean_mvp_seed2 \
  --teacher /root/.cache/modelscope/models/Qwen--Qwen3-1.7B/snapshots/master \
  --student /root/.cache/modelscope/models/Qwen--Qwen3-0.6B/snapshots/master \
  --seed 2 --dtype bfloat16 --kernel sdpa --device cuda \
  --method kd --epochs 8 --lr 1e-3 --n-resamples 10000 --eval-splits val
```
- `P1_kd_gpu.py` argparse：`--run-id`、`--teacher`、`--student`(必填)，`--model-pair`(默认 MVP)、`--seed`、`--dtype`、`--kernel`、`--device`、`--method`(kd/cf_lite，默认 kd)、`--huber-delta`(默认1.0，**仅 cf_lite 用**，权威 kd run 的 metrics `huber_delta=null`)、`--epochs`(8)、`--lr`(1e-3)、`--n-train`(None)、`--n-val`(None)、`--n-resamples`(10000)、`--eval-splits`(val)、`--skip-pipeline`。权威 config 记 `mapper=kd`、`bootstrap_seed=seed`、training `{epochs:8, lr:0.001, n_train_pairs:120, trainable_params:7340032}`、`git_hash=6413ba0`。

### 4.4 SQuAD 锚点两 run（2 条）

```bash
# affine 臂
.venv/bin/python -m experiments.anchor_squad_gpu --run-id anchor_squad_affine_seed0 \
  --teacher /root/.cache/modelscope/models/Qwen--Qwen3-1.7B/snapshots/master \
  --student /root/.cache/modelscope/models/Qwen--Qwen3-0.6B/snapshots/master \
  --method affine --seed 0 --dtype bfloat16 --kernel sdpa --device cuda \
  --n-examples 240 --max-new-tokens 16

# kd_only 臂
.venv/bin/python -m experiments.anchor_squad_gpu --run-id anchor_squad_kd_seed0 \
  --teacher /root/.cache/modelscope/models/Qwen--Qwen3-1.7B/snapshots/master \
  --student /root/.cache/modelscope/models/Qwen--Qwen3-0.6B/snapshots/master \
  --method kd --seed 0 --dtype bfloat16 --kernel sdpa --device cuda \
  --n-examples 240 --max-new-tokens 16
```
- `anchor_squad_gpu.py` argparse：`--run-id`、`--teacher`、`--student`、`--method`(affine/kd，必填)、`--seed`(0)、`--dtype`、`--kernel`、`--device`、`--n-examples`(240，answerable 确定性子集)、`--max-new-tokens`(16)、`--smoke`(non-authoritative，**权威 run 不加**)。锚点文件 hardcoded 为 `/root/readkv/data/anchors/squad/dev-v2.0.json`（相对路径不可用，须在 `/root/readkv` 运行）；权威 config `git_hash=b7b9f50`、`data_sha256=80a5225e…`、**`seed` 仅 0**（锚点非主终点，不要求 ≥3 seed）。

### 4.5 权威 run 参数 / 产物对照表（转抄 config）

| run_id | 脚本 | seed | dtype/kernel | zero_re_prefill | git_hash | scores 行数 |
|---|---|---|---|---|---|---|
| `e0_clean_mvp_seed0` | P0_gpu | 0 | bfloat16/sdpa | true | efc3ba3 | 80（40 探针 × 2 侧） |
| `p1_clean_mvp_seed0/1/2` | P1_gpu | 0/1/2 | bfloat16/sdpa | true | efc3ba3 | 各 600（60 val × 10 臂） |
| `p1_kd_clean_mvp_seed0/1/2` | P1_kd_gpu | 0/1/2 | bfloat16/sdpa | true | 6413ba0 | 各 600 |
| `anchor_squad_affine_seed0` | anchor_squad_gpu | 0 | bfloat16/sdpa | true | b7b9f50 | 480（240 例 × 2 臂） |
| `anchor_squad_kd_seed0` | anchor_squad_gpu | 0 | bfloat16/sdpa | true | b7b9f50 | 480 |

> **关于参数名的诚实说明**：权威 P0/P1/kd/锚点脚本**没有** `--n-select` / `--n-heldout` / `--zero-re-prefill` 这类 CLI 开关（那是 P2/P3 历史入口的概念）。`zero_re_prefill` 是 Joint 臂的固定性质，由代码写进每个 run 的 `config.json`（权威 run 均为 `true`），不是可切换命令行参数；`n-train/n-val` 仅 P1_gpu / P1_kd_gpu 暴露（默认 None = 冻结规模）。不要为权威 run 编造这些开关。

### 4.6 执行纪律

- **串行执行**：并发会因 GPU 争用放大 **3–7×**（见 `docs/p3_resource_estimate.md`）；上面 9 条逐条运行。
- **provenance**：每个 run 写 `config.json`（`git_hash`/`protocol_version`/`seed`/`dtype`/`kernel`/`zero_re_prefill`/`bootstrap_seed`，锚点另含 `data_sha256`）、`scores.jsonl`、`metrics.json`、`manifest.json`。
- **git_hash 必须与 run config 一致、工作区 clean**：官方产物由含跑分代码的 commit 产出（E0/P1 affine `efc3ba3`、kd `6413ba0`、锚点 `b7b9f50`）。`scripts.consistency_check` 用「ancestry + 跑分代码 `git diff` 为空」判定 traceable；若本地 HEAD 与 run config 的 `git_hash` 不同，**重跑产物会带新的 `git_hash`**，应视为新一轮而非覆盖原 run（见 §7 限制）。

---

## 5. 验证产物（核对与审计）

### 5.1 三个哈希 / config / scores 自检

```bash
# (a) 合成数据哈希：应等于 f910f1f1…a894a（manifest.json::files[cf_pairs.jsonl].sha256）
sha256sum data/tasks/cf_pairs.jsonl

# (b) manifest 自身哈希 sidecar：应等于 874826e9…c23a
sha256sum data/tasks/manifest.json
cat data/tasks/manifest.json.sha256

# (c) v2.3 统计口径哈希：回填后 e44c6acb…（回填前 5200940c…，commit 6413ba0）
sha256sum configs/prereg/stats_convention_v2.3.yaml

# (d) 锚点文件哈希：应等于 80a5225e…82d8
sha256sum data/anchors/squad/dev-v2.0.json

# (e) 每个 run 的 scores 行数（期望见 §4.5）
wc -l reports/runs/e0_clean_mvp_seed0/scores.jsonl \
      reports/runs/p1_clean_mvp_seed0/scores.jsonl \
      reports/runs/p1_kd_clean_mvp_seed0/scores.jsonl \
      reports/runs/anchor_squad_affine_seed0/scores.jsonl
```

逐 run 用文本查看 `config.json` 的 `git_hash`/`protocol_version`/`seed`/`dtype`/`kernel`/`zero_re_prefill`（锚点再加 `data_sha256`），与 §4.5 对照；`metrics.json` 的权威数值转抄示例：

- `e0_clean_mvp_seed0`：`gate.passed=true`、`measurement_error_ceiling=2.220446049250313e-16`、`em_agreement=0.975`、`min_logit_cosine=1.0`、`zero_re_prefill_all=true`。
- `p1_clean_mvp_seed{0,1,2}`：joint E_CF `6.8996 / 8.1590 / 8.5402`，joint dual `0.4167 / 0.2833 / 0.3833`，三 seed `transfer_broken=true`。
- `p1_kd_clean_mvp_seed{0,1,2}`：joint E_CF `6.3880 / 6.4789 / 7.2105`，joint dual `0.700 / 0.7333 / 0.7667`，三 seed `transfer_broken=false`。
- `anchor_squad_{affine,kd}_seed0`：self F1 `0.19747`，joint F1 `0.00507` / `0.00139`，self EM 与 joint EM 均为 `0.0`（原因见 §7）。

### 5.2 审计脚本（只读重算）

```bash
# 一致性审计（默认输出 reports/consistency_report.json）
.venv/bin/python -m scripts.consistency_check

# CI 重算（默认输出 reports/bootstrap_summary.json）
.venv/bin/python -m scripts.bootstrap_ci_report
```

两者 argparse：`consistency_check` 有 `--reports-root`（默认 `reports`）、`--output`（默认 `reports/consistency_report.json`）；`bootstrap_ci_report` 有 `--reports-root`、`--n-resamples`(默认 10000)、`--epsilon`(默认 0.02)、`--output`(默认 `reports/bootstrap_summary.json`)。`bootstrap_ci_report` 按 v2.3 以 `template_family` 为主聚类簇、同报 pair-level 敏感性、族数 < 24 标 `exploratory=true`，**不加载模型、不回写冻结文件**。

**期望结果（转抄当前冻结报告）**：

- `reports/consistency_report.json`：当前列表共 **31 项，`ok=true` 9 项、`ok=false` 22 项**。`ok=true` 的 9 项 = **7 个 clean run（E0 + P1 affine×3 + kd×3）+ 2 个锚点 run**，均 `traceable=true`。
- **「22 failed」的历史 superseded 语义**：这 22 项**不是**当前权威证据失败，而是旧 run（pre-fix 数据、`git_hash=458de18/53e9bc5` 等）、δ 网格 run、`superseded` 项，其 `run_code_unchanged_vs_head=false` / `traceable=false` / `superseded=true`；按裁决它们已被标 `superseded`，仅作历史 / 翻转对照，不计入结论。重跑审计时若本地 HEAD 前进，也可能因「跑分代码相对 HEAD 有差异」把更多项标 false——判定应以 **7 clean + 2 锚点 ok=true 且 traceable=true** 为准。
- `reports/bootstrap_summary.json` 当前 **31 项**，已包含 7 个 clean run + 2 个锚点 run（均按 v2.3 输出 template-family 主 CI + pair-level 敏感性）。注：`reports/review/meta_review/current_task_meta_review.md` §3.1 曾指出「26 项、kd clean 未纳入、C 表用 pair-level CI」为投稿前审计收尾项；就当前冻结产物而言 kd/锚点已入汇总，但 **kd 情形 C 表的 CI 口径（pair-level vs v2.3 template-family 主口径）仍须统一标注、不得混用**，该事项须由 PI 解释，写作者不得私下改表。

---

## 6. 整理数据（报告级整理包）

- 目标路径：`reports/data/gpu_experiments/v1/raw`（字节级源副本）与 `reports/data/gpu_experiments/v1/processed`（tidy 表）。
- **当前状态：待补**。截至 2026-11-23，`reports/data/gpu_experiments/` 尚未产出（目录不存在 / 为空）；本指南暂不给出该包的 sha256/inventory 数字，避免编造。数据工程师产出后应补充：raw 相对 `reports/runs/**` 源文件的 sha256 对照、processed 表的字段字典与行数、以及 `inventory.json`（逐文件 sha256 + 字节数）的核对命令，再更新本节。
- 在此之前，权威证据的唯一来源是 §5 的 `reports/runs/<run_id>/` 冻结产物 + `data/tasks/` 合成数据 + `data/anchors/squad/` 锚点文件。**整理数据即便产出，也只能辅助核对，不得用于恢复贡献或重算已冻结统计。**

---

## 7. 已知不可复现 / 限制（如实披露）

1. **封存 test 未评测、主终点未评估**：所有干净证据只评 `val`（`eval_splits=["val"]`）；CF 方法 vs kd_only 在封存 test 上的成对 E_CF 差异（95% CI 上界 < 0）从未计算；P3 取消后方法层不适用。
2. **单 MVP 等深对 + 合成域 + 8 族 exploratory**：仅 Qwen3-1.7B→0.6B、纯合成模板；v2.3 下 val 仅 8 个 template_family（< 24）→ `exploratory=true`，CI 宽、非强推断；不得声称跨模型 / 跨对泛化或强显著性。
3. **SQuAD 锚点 EM 全 0 的原因**：base 0.6B 未针对 SQuAD 微调，精确匹配（EM）全臂触底；F1 也大幅坍塌（self 0.1975 → joint 0.0051 / 0.0014）。kd 对照在锚点上也坍塌（未复现合成域「kd 保持 utility」），v2.4 三情形归为 `exploratory_disclosure`，不强化外部效度、不恢复贡献。仅 seed0 / 240 例。
4. **cache npz 未随包发布但可再生**：离线 teacher/student 缓存的 `.npz` 不作为不可变产物随仓库发布；可由固定模型 + `scripts/gen_teacher_cache.py` + 相同配置指纹再生（复现时以 run 的 `config.json` 参数为准）。
5. **模型 revision 未钉 commit**：`environment.json` 仅记录 `snapshots/master`，未钉具体权重 commit / 文件哈希；环境升级后同 alias 可能指向不同权重 → 无法仅凭本文件保证字节级一致；Qwen3-4B 路径甚至未进 environment.json 的 models 字段。
6. **驱动 / uv 版本未记录**：`environment.json` 无 NVIDIA 驱动版本、无 uv 版本号（只有 uv 管理的 Python 可执行路径），跨机器复现需自行补齐。
7. **git_hash 与 HEAD 一致性**：权威 run 由历史 commit 产出；当前 HEAD 已前进，重跑产物会带新 `git_hash`，需按 §4.6 的 ancestry + 跑分代码 `git diff` 口径判定 traceable，不能要求严格 `hash==HEAD` 相等。
8. **章节级引用未全文核验**：外部文献（KV-Lingo arXiv:2609.32610、CacheLink arXiv:2610.15509、SQuAD 两篇及新增 N1–N9）只到标题 / 作者 / 摘要 / 日期级核验；章节级细节须投递前按 `docs/protocol.md §9` 全文核验（`research_scope_update.md` §6）。
9. **kd 审计口径未统一**：kd 三 seed 的 v2.3 簇级 CI 与 pair-level CI 尚需统一标注 / 纳入 bootstrap 汇总（§5.2），属投稿前收尾项。

---

## 8. 禁止事项（硬约束）

- **mock / smoke / `_non_authoritative` 非科学证据**：`--backend mock`、`reports/_non_authoritative/**`、`--smoke` 只做接线 / 报告格式回归，不进入任何结论。
- **不得重跑 P2 / P3 / P4 / G1**：P2/P3/P4 正式取消且永久放弃（真实 PI 决策 8）；G1 仅可选低优先级、非核心，未经 PI 排期不得启动。历史入口 `experiments/P2_gpu.py`、`P3_gpu.py` 不是复现目标。
- **不得碰封存 test**：不为「救原研究」提前评测；所有证据限 `val` + 已授权锚点。
- **不得用整理数据恢复贡献**：`reports/data/gpu_experiments/v1/`（产出后）只作核对；贡献(1)(2) 撤回、贡献(3) withheld 不变；不得声称 utility-preserving gap / V 消费机制定位 / 方法改善 / 跨模型泛化。
- **不重算冻结统计、不挑 seed、不改冻结判据**：`configs/prereg/**`、`docs/protocol.md`、`reports/runs/**` 只读；统计只能由 `scores.jsonl` 经 `bootstrap_ci_report` 重算；seed 固定 0/1/2（锚点仅 0）。

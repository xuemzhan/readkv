# GPU 实验数据导出 v1（raw + processed，只转抄不重算）

> 生成日期：2026-11-23 · 生成脚本：`scripts/gpu_export_dataset.py` · schema：`gpu_experiments_v1`
> 性质：**只读导出**。源 `reports/runs/**`、`data/tasks/**`、冻结判据、评分逻辑、论文、`docs/decisions` 均未改动；未执行任何 GPU、未重算任何统计量、未改任何数值。

---

## 1. 目录结构

```
reports/data/gpu_experiments/v1/
├── README.md                     # 本文件
├── manifest.json                 # 生成日期、源哈希、raw 总数/总 sha256、processed 文件与行数、schema、排除项、校验
├── file_inventory.json           # 逐文件清单（JSONL）：copied_files + excluded_cache_npz
├── raw/<run_id>/                 # 28 个 run 的 byte-exact 原始副本
│   ├── config.json               #   每个 run 必有
│   ├── manifest.json             #   每个 run 必有
│   ├── scores.jsonl              #   每个 run 必有
│   ├── metrics.json              #   存在才复制（P2 四个 run 无此文件）
│   └── ecf_ledger.jsonl          #   存在才复制
└── processed/
    ├── runs_summary.csv                 # 28 行，每 run 一行
    ├── pair_scores_tidy.jsonl           # 12,040 行（26 个合成 run 的全部 score 记录，原字段 + 上下文字段）
    ├── anchor_scores_tidy.jsonl         # 960 行（2 个 SQuAD 锚点 run 的全部 score 记录）
    ├── data_quality_before_after.csv    # 16 行（数据修复前后关键对照，逐字转抄）
    └── cluster_map.csv                  # 1,400 行（run_id × pair_id → 聚类字段）
```

`raw/` 下 **126 个复制文件 / 28 个 run**；`excluded_cache_npz` 记录 **320 个 `.npz`（1,236,406,365 B）**，未复制。

---

## 2. 字段口径（全部为转抄/重命名，无重算）

### 2.1 `runs_summary.csv`
| 列 | 来源 |
|---|---|
| `run_id`, `stage`, `gate`, `seed`, `git_hash`, `protocol_version`, `n_scores`, `superseded_reason` | `reports/runs_index.json`（28 run 权威清单） |
| `status` / `authoritative` | 由 `runs_index.superseded` 派生：`authoritative = not superseded` |
| `method` | `config.experiment_config.mapper` → `.method` → `metrics.method`（取第一个非空），**不臆造**；同时保留 `mapper_raw`、`metrics_method_raw` 原值 |
| `data_sha256` | `runs_index.data_sha256` → `config.experiment_config.data_sha256` → `metrics.data_sha256` |
| `zero_re_prefill`, `eval_splits` | `runs_index` / `config.experiment_config.eval_splits`（列表以 `|` 连接） |
| `primary_endpoint_point`, `primary_ci_template_family`, `primary_ci_pair_level` | `reports/bootstrap_summary.json` → `runs["runs/<run_id>"].primary_endpoint`：`.point`、`.ci`、`.pair_level_sensitivity.ci`（**主 CI = template_family 簇级；第二类 = pair-level 敏感性**） |
| `transfer_broken` | `metrics.transfer_broken`（冻结正交标注）→ 回退 `runs_index.transfer_broken` |
| `verdict` | `metrics.decision.verdict` → 回退 `runs_index.mechanism_verdict`（P2） |
| `source_raw_dir` | 指向 `raw/<run_id>/` |

> 缺字段按原始缺值留空（如 E0 无 `primary_endpoint`、P2 无 `metrics.json`、锚点无 `eval_splits`）。**空 ≠ 0，勿补值。**

### 2.2 `pair_scores_tidy.jsonl`
逐条复制 `scores.jsonl` 的**全部原字段与原值**（数值零改动），再附加上下文列：`run_id`、`status`/`authoritative`、`method`、`seed`、`arm_dual_correct`/`arm_coverage`/`arm_info_gap`（来自 `metrics.arms[arm]`；P2 无 metrics 则留空）、`transfer_broken`、`data_sha256`、`git_hash`、`source_raw_dir`。原始 `dual_correct`、`flip_consistency` 保持原名原值；F5 `must_flip=false` 不进翻转分母的语义不变。

### 2.3 `anchor_scores_tidy.jsonl`
两条 SQuAD 锚点 run 的全部 score 原字段 + `n`（`anchor_eval_summary.runs[rid].n`=240）、`method`、`zero_re_prefill`、`data_sha256`、`git_hash`、`anchor`、`anchor_scenario`（v2.4 预承诺三情形之一）。

### 2.4 `data_quality_before_after.csv`
逐字转抄 `reports/data/data_fix_report.md §2`（并由 `data_readiness_audit.md §1–§3` 佐证）：sha、字节/行数、切片计数、退化对、跨 split 泄漏、实体重叠、模板结构、flip 分母、length_mismatch 等。**未重算。**

### 2.5 `cluster_map.csv`
`(run_id, pair_id)` 唯一键 → `template_family` / `cluster` / `split` / `slice_id` / `must_flip` / `authoritative`；字段来自各 run 的 `scores.jsonl`，用于复核 v2.3「主聚类单元 = template_family」口径。同一 pair 的这些字段在各 arm 间不变，取首次出现。

---

## 3. 排除项与理由
- **`cache/*.npz`**：320 个可再生 KV 缓存（1.24 GB），不复制；仅在 `file_inventory.json.excluded_cache_npz` 记录路径/大小/哈希登记状态。**无任何 run 的 `manifest.json` 登记过 `.npz` 的 sha256**（故 `registered_in_manifest_sha256=false`）。
- **`runs_index.json` 之外的 3 个 run 目录**：`delta_lock_v2p1_2p0_par`、`p1_gpu_kdonly_mvp_seed1_par`、`p1_gpu_kdonly_mvp_seed2_fast`（git `a04990d`）不在 28-run 权威清单，未纳入。
- **`reports/_non_authoritative/**`（smoke）**：mock/smoke/非正式产物，禁止作为正式数据。

---

## 4. 如何使用与禁令
1. 需要原始字节 → 用 `raw/<run_id>/`；`file_inventory.json` 的 `sha256` 与 `sha256sum raw/<...>` 必须一致。
2. 需要表格化分析 → 用 `processed/`；**只用 `status=authoritative` 的行作科学证据**，`superseded` 行仅作审计溯源（pre-clean-data / 缺 run code），**不得当作科学证据或并入主终点**。
3. **SQuAD/ARC 锚点仅作外部效度探针**：`anchor_scores_tidy.jsonl` 与合成 `pair_scores_tidy.jsonl` **不得混算**；锚点不并入合成 test 主终点 CI、不重算冻结 CI、不恢复任何贡献。
4. `real=0` 不变；贡献(1)(2) 撤回、贡献(3) withheld；v2.6 not-activated，无生成数据。
5. 不得据本导出重算统计量或改数值；需复核统计请用冻结的 `scripts/bootstrap_ci_report.py` 与 `scripts/consistency_check.py`。

---

## 5. 复现与校验
```
python3 scripts/gpu_export_dataset.py        # 幂等：仅写 reports/data/gpu_experiments/v1/**
sha256sum reports/data/gpu_experiments/v1/raw/<run_id>/config.json   # 与 inventory 比对
```
`manifest.json.validation` 记录：raw 副本 sha256 与源一致（126/126）、scores 行数与 `runs_index.n_scores` 一致（28/28）、tidy 行数与源一致（12,040/12,040 与 960/960）。全部通过方视为交付完成；任一不一致即停止并上报。

**签署：数据工程师（GPU 实验数据导出 v1 · 2026-11-23）**

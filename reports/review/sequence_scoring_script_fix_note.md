# 序列评分合规脚本修复说明（R1–R3）

> 日期：2026-11-24。范围：仅 `scripts/consistency_check.py`、`scripts/bootstrap_ci_report.py`、
> `tests/**`、本说明。未改判据/数据/论文/运行产物；未改 git；未重判任何结果；未跑 GPU。

## R2 — consistency_check.py

- `scripts/consistency_check.py:215` 新增 `PROTOCOL_WHITELIST = ("2.0","2.1","2.7","2.8")`；
  `:288` `_check_protocol_compat()` 用该白名单（原仅 2.0/2.1），2.7/2.8 不再报
  `incompatible with frozen V2 prereg`。
- `scripts/consistency_check.py:225` 新增 `_check_v28_fields()`；`:305` 当 `protocol_version=="2.8"`
  时并入 `protocol_compat.v28_fields`。校验项：
  `protocol_version=2.8`、`version_tag` 非空且与 `calibration_version` 一致、
  `calibration_version==validation_version`（对角格）、顶层与 `experiment_config.seed` 一致、
  `input_sha256.train/val` 为 64-hex、`zero_re_prefill=true`（顶层与 experiment_config）、
  `sealed_test_read=false`、`tokenizer_fingerprint.sha256` 为 64-hex 且不是
  `unavailable:*`、tokenizer/teacher/student 路径齐全、`scoring` 声明三读数。
- **dirty 不改**：`gpu_backend.py` 未提交导致的 `dirty_run_paths` / `run code paths have
  uncommitted changes` 是真实待提交状态，不是误报逻辑；按要求由主会话统一 commit 后自然消失。
  本轮修复后对 6 个正式 2.8 run 的实测：`protocol_compat.ok=true`、`v28_fields.ok=true`，
  唯一残留 problem 为 dirty（待提交）。

### 需主会话注意的残留（未由本任务处理）

`_run_code_unchanged()` 比较 `config.git_hash` 与 HEAD 的**产出代码**差异。6 个正式 run 的
`git_hash=a05e9b3` 记录于代码提交之前；主会话 commit 后 HEAD 前进且 `gpu_backend.py` /
新评分入口发生变化，因此该检查会对这些 run 报 `run-producing code differs between
config.git_hash and HEAD`。这是「以未提交工作树跑分」的真实可追溯性缺口，**不应静默放宽**；
请主会话在重跑审计脚本后按既有治理规则裁量（如如实记为已知限制），本任务未改该语义。

## R3 — bootstrap_ci_report.py

- `scripts/bootstrap_ci_report.py:28` 新增 `V28_READINGS`；`:31` `_sequence_readings()` 检测
  dict 型 `E_CF` 并按 `[first, full, length_normalized]` 固定顺序返回；`:45` `_ecf_value()`
  安全取值，**绝不 `float(dict)`**。
- `:128` 识别序列评分 run 后，`summarize_run()` 对**每个 arm、每个 reading 分别**计算
  `template_family` 主 CI + `pair_id` 敏感性 CI，写 `arms[arm].readings[reading]`；
  protocol/stats_convention 标 `v2.8`，顶层 `sequence_scoring=true` 与
  `sequence_scoring_note="sequence-scoring runs handled separately by reading ...;
  no cross-reading E_CF comparison"`。
- 非数值/缺失行不静默丢弃：`:163` 记 `n_excluded_non_numeric_per_reading` 与
  `n_excluded_non_numeric_total`。`:189` `paired_endpoint()` 对普通 float 与 dict 三读数
  均按 reading 成对重算；无 `new_joint` arm 时 `primary_endpoint=null`，不臆造主终点。
- 普通 `float E_CF` 老 run 路径保持原 v2.0 输出结构（单测覆盖）。
- 实测：49 个 run 全部处理完成、无崩溃；6 个正式 2.8 run 均产出三读数 CI（例：A11_s0
  joint `first` = 6.900 [3.577, 10.107]，pair 敏感性 [5.457, 8.194]），排除数 0。

## R1 — 待主会话统一提交的路径清单

本任务**未执行任何 git 操作**。按当前 `git status --short`，需一并提交：

**判据 / 决策（PI 所有，原文不改，仅纳入版本控制）**
- `configs/prereg/full_candidate_scoring_v2.8.yaml`
- `docs/decisions/full_candidate_scoring_ruling.md`

**代码 / 审计脚本 / 单测**
- `src/readkv/models/gpu_backend.py`（M，显式评分模式）
- `experiments/sequence_scoring_gpu.py`（新入口）
- `scripts/consistency_check.py`（M，R2）
- `scripts/bootstrap_ci_report.py`（M，R3）
- `tests/test_sequence_scoring.py`（新，7 项）
- `tests/test_sequence_scoring_scripts.py`（新，9 项）
- `refine-logs/GPU_SEQUENCE_SCORING_TRACKER.md`（M，状态更新）

**数据侧 CPU 产物（data-engineer 所有，不改动）**
- `data/audit_2x2/sequence/`（6 个 `A{00,11}_seed{0,1,2}.jsonl` + `manifest.json` + `build_sequence_index.py`）
- `reports/data/sequence_scoring_data_audit.md`

**运行产物（不可变，8 个新 run + 1 个失败产物）**
- `reports/runs/audit_seq_A11_s0/`、`audit_seq_A00_s0/`、`audit_seq_A11_s1/`、
  `audit_seq_A00_s1/`、`audit_seq_A11_s2/`、`audit_seq_A00_s2/`
- `reports/_non_authoritative/audit_seq_smoke_A11_s0_v2/`、
  `reports/_non_authoritative/audit_seq_smoke_A00_s0_v2/`
- `reports/_non_authoritative/audit_seq_smoke_A11_s0/`（原失败产物，按要求保留）

**文档（新增）**
- `reports/review/sequence_scoring_implementation_note.md`
- `reports/review/sequence_scoring_run_report.md`
- `reports/review/sequence_scoring_script_fix_note.md`（本文件）
- `reports/review/sequence_scoring_compliance_note.md`（reviewer 产物，非本任务生成，勿覆盖）

## 验证记录

- `CUDA_VISIBLE_DEVICES="" pytest`：**74 passed**（原 65 + 本任务新增 9）；未跑 GPU。
- `consistency_check.py` 与 `bootstrap_ci_report.py` 均用临时输出路径实测，未改动
  `reports/consistency_report.json` / `reports/bootstrap_summary.json` 或任何 run 产物。
- commit 后需由主会话重跑两个审计脚本；本任务不再执行 GPU 或重判结果。

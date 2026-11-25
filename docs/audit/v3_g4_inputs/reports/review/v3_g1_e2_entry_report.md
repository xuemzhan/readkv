# v3 G1 · E2 dedicated one-shot evaluator 实现交付报告（engineer-2 · CPU-only）

**日期：** 2026-11-25。**性质：** 工程实现 + CPU-only 自检报告。**本轮未运行 GPU、未读取/评测 test 条目内容、未产生任何 test 指标或 `scores.jsonl`、未修改任何冻结判据、未写入 `reports/runs/**`。**

**依据（只读）：** `configs/prereg/gpu_followup_v3.0.yaml` §2/§4/§8（FROZEN）、`docs/decisions/gpu_v3_scope_ruling.md` §1（PI 解锁 E2）、`reports/data/v3_e2_test_lock.md`（数据哈希 + 锁清单）、`docs/audit/GPU_experiment_plan_2026-11-25.md` §4。

---

## 1. 本轮写入文件（仅三个）

| 文件 | 内容 |
|---|---|
| `experiments/e2_test_evaluator.py` | E2 dedicated ONE-SHOT test-only evaluator；全部拒绝门、固定 6 格计划、产物 schema 校验、CPU 自检模式；GPU 路径为 lazy-import（torch/transformers/readkv 仅在 GPU 函数内部导入） |
| `tests/test_v3_entries.py` | 纯 stdlib CPU-only 测试：哈希不符 abort、test/val 路径拒绝、调参/返修标记拒绝、锁解锁证据、产物 schema；使用 synthetic 临时对象，不打开真实 test 内容、不加载模型 |
| `reports/review/v3_g1_e2_entry_report.md` | 本报告 |

未写入 `configs/**`、`papers/**`、`docs/decisions/**`、`reports/runs/**`、`data/**`、`src/**`。

## 2. 已实现的安全门（全部在模型加载 / test 内容读取之前）

1. **显式必需参数**：`--run-id` + `--test-path` + `--test-sha256` + `--lock-file` + `--eval-config-hash`；缺任一即 REFUSED（exit 2）。
2. **锁文件绑定**：`--lock-file` 必须解析为 `reports/data/v3_e2_test_lock.md`；解析锁 markdown 提取整文件 SHA-256 与 test-split SHA-256 两个不同值（真实锁解析得到两条与锁文件一致的 64-hex 值），并要求 `gpu_v3_scope_ruling.md` + `§1` + PI + 解锁措辞齐备；缺任一项即 REFUSED。可选 `--lock-file-sha256` 再绑定锁字节。
3. **三重哈希核验**：`sha256(test 文件字节) == --test-sha256`，且该值必须等于锁中两个数据哈希之一（记录 `binding_kind = whole_file | test_split`）；`sha256(configs/prereg/gpu_followup_v3.0.yaml 字节) == --eval-config-hash`。任一不符即 REFUSED。哈希计算是字节元数据操作，不解释任何条目内容。
4. **拒绝 val 混跑**：`--test-path` 路径分量/文件名出现 `val` / `validation` 即拒绝；`--val-path`、`--eval-splits` 等 val 风格 flag 显式拒绝；calibration 路径强制 train-only（禁止 test 分量）。
5. **拒绝调参/阈值选择/错误返修**：denylist 覆盖 `tune / threshold / select / rework / grid / sweep / search / huber / delta / resample / epoch / tau / lambda / --lr / n-train / n-test / cf-distortion / multi-round / rerun / peek`；命中即 REFUSED。CLI 不暴露 `tau`、`self_threshold`、`n_resamples`、`epochs`、`lr`、`huber_delta` 等旋钮——它们从冻结配置/常量读取。
6. **one-shot**：run-id 必须匹配 `v3_E2_*`；smoke 必须带 `_smoke` 后缀并写入 `reports/_non_authoritative/`，正式 run 写入**新** `reports/runs/<run_id>/`；输出目录已存在即拒绝覆盖（`RunContext` 再以 `exist_ok=False` 兜底）。
7. **命名诚实**：产物写 `criteria_source="configs/prereg/gpu_followup_v3.0.yaml"`、`split_designation="previously_unevaluated_held_out_split"`、`sealed_test_read=false`；schema 校验拒绝 `pooled_inference=true`、`sealed_test_read=true`、缺字段、错误 flip 分母或多份 pair fingerprint。

## 3. 固定设计与产物契约（已编码，未执行）

- 6 格 = `affine`/`kd_only` × seeds `0/1/2`；同一固定 300 对 test set（以 `pair_set_fingerprint` 强制所有格一致），16 个 template family，`exploratory=true`；三个 seed 是 mapper/calibration seed，**不是** 3 份独立 test replicate，`pooled_inference=false`。
- 逐格报告 Self/Joint dual、`L = Self − Joint`、`E_CF`（含 template-family 簇级 CI，10000 次）、coverage、flip（方向一致率 + 实际分母，排除 F5+F6）、pair-level 敏感性区间；`zero_re_prefill=true` 由 `v2_context` 记录并在写盘前 `require_zero_re_prefill()`。
- GPU 路径使用显式 hash-bound train JSONL + pin 的 teacher/student snapshot；不调用 `build_cf_pairs` / `run_cf_pipeline`（避免自动重建），不等深直接 REFUSED（指向 E5 层映射 blocker，不得当作 E2 结果）。
- 自检模式下**不打开真实 test 文件、不加载模型、不写 repo 文件**：全部用 `tempfile` synthetic 文件与 in-memory schema skeleton（占位符字符串，无任何数值结果）。

## 4. 测试结果（CPU-only / stdlib，实际运行）

| 检查 | 结果 |
|---|---|
| `python3 tests/test_v3_entries.py` | **7/7 PASS**（哈希不符 abort、eval-config 哈希不符 abort、val 路径拒绝、val flag 拒绝、调参/返修 flag 拒绝、锁无 PI 解锁拒绝、合法 synthetic 门链 + schema 通过且 corrupted schema 被拒） |
| `python3 -m experiments.e2_test_evaluator --cpu-selfcheck` | **10/10 PASS**（含真实锁 markdown 结构解析：两条数据哈希 + PI 解锁 + designation；全程未打开 `data/tasks/cf_pairs.jsonl`） |
| `python3 -m py_compile ...` | 通过（生成的 `__pycache__` 已清理，未留下额外文件） |

测试在 `python3 3.12.3` 下以纯 stdlib 执行；未使用 pytest/numpy/torch。

## 5. Pending（因环境缺依赖，按指令延后，不伪造通过）

- 当前 `.venv` 与系统 Python 均**无 torch / transformers / numpy / pytest**。`run_gpu_cells` 的 torch 依赖检查与任何 GPU 前向验证 **pending**，未执行；因此本轮**无任何 GPU 结果**。
- 仓库既有 51 个单元测试（含 V2 新增）依赖 numpy/pytest，**本轮未运行**，状态 pending；没有以本轮 stdlib 测试冒充它们通过。
- 真实一次性评测需授权者补齐并冻结：模型/tokenizer snapshot + 文件哈希、实际入口哈希、train 显式路径与哈希；本实现只提供入口与门禁，不代替授权。

## 6. Blockers / 边界

- **未越门**：G1 尚未放行；本交付只完成 E2 入口实现与 CPU 自检，不构成 G2 pilot 或 G3 正式格的执行授权。
- **E5 层映射 blocker 仍在**（见 `v3_g1_feasibility_audit.md` §1.4）：非等深路径的注入端二次映射问题未在本轮修复；E2 evaluator 对等深 MVP 强制 identity，遇到非等深直接拒绝，避免把该缺陷结果误记为 E2。
- **无结果**：未产出 `scores.jsonl` / `metrics.json`，未运行任何 test 评分，未报告任何 test 性能数字；mock/synthetic 数值只用于门控回归，不作科学证据。
- **不可变产物**：未写入 `reports/runs/**`；后续正式 run 由授权者在锁全部补齐后一次性执行，目录不得覆盖。

**签署：** engineer-2（实现 + CPU-only 自检，2026-11-25）。

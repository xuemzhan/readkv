# v3.0 G3 batch 2（E2 ONE-SHOT dedicated 评测）执行报告

> 角色：工程师（subagent）。日期：2026-11-25。
> 依据（只读）：`docs/decisions/v3_e2_argument_ruling.md`（PI 参数口径裁定，本次先行读取）、
> `docs/decisions/v3_g2_release.md` §4（G3 放行）、`configs/prereg/gpu_followup_v3.0.yaml` §4（FROZEN）、
> `docs/decisions/gpu_v3_scope_ruling.md` §1（真实 PI test 解锁）、`reports/data/v3_e2_test_lock.md`、
> `reports/_non_authoritative/v3_env/model_manifest.json`、`experiments/e2_test_evaluator.py`。
> **性质：两次 0 调用 preflight 停止 + 一次 pre-scoring REFUSED 调用 + 一次权威调用（COMPLETED）。
> 权威评分 pass = 1；产出 `reports/runs/v3_E2_heldout_s0s1s2/`（config/scores/metrics/manifest）。
> 未修改任何冻结判据/稿件。本文不含任何 test 性能数字。**

---

## 1. 结论（最终）

> **PASS（权威执行层）— 唯一一次权威调用 COMPLETED（exit 0），产出完整四件套产物；所有可从产物核验的结构/绑定门全部 PASS。**
> **evaluator 进程调用 = 2（1 次 pre-scoring REFUSED + 1 次权威）；权威评分 pass = 1；无重试、无重跑、无返修。**

历史失败均已由 PI 裁定关闭：
- 第 1 次 preflight STOP：`--test-sha256` 误用 test-split 派生哈希 → 由 `v3_e2_argument_ruling.md` 修正为整文件哈希（0 调用）。
- 第 2 次 preflight STOP：入口无法表达 3 份逐 seed 校准 → 由 `v3_e2_interface_ruling.md` 授权最小 per-seed 扩展（0 调用）。
- 第 3 次调用 pre-scoring REFUSED：整文件含 probe/train/val 行触发 test-only 行门 → 由 `v3_e2_rows_ruling.md`
  裁定不消耗科学 one-shot，授权最小 filter 修正（1 次调用，未加载模型/未评分）。
- 第 4 次（本次）权威调用：**COMPLETED**，入口 SHA `da80afdc…b8f6f`。

**gate 状态（权威产物可核验部分）= PASS**：见 §9；**不可从冻结入口产物核验的技术门**（峰值显存、耗时、forward 计数、
cache 形状、Self/Identity 差分、逐 forward 审计明细）在 §5/§9 如实标为「未记录，无法独立核验」，不伪造。

**权威产物：`reports/runs/v3_E2_heldout_s0s1s2/` 含 `config.json` / `scores.jsonl` / `metrics.json` / `manifest.json`。**
结果仅属新研究，不进入当前 TMLR 稿件；统计判读在 G4。

---

## 2. 时间线（两次 preflight STOP → 接口裁定 → 冻结 → 单次运行）

| 阶段 | 触发 | 停止点 / 动作 | evaluator 调用数 | 产物 |
|---|---|---|---:|---|
| 第 1 次派发 | 首次任务把 `--test-sha256` 误设为 test split 派生哈希 `c545…769a7a2`（且缺 train 绑定） | preflight 哈希门试算即 REFUSED；未调用主流程 | **0** | 仅本报告（第一版） |
| 参数口径裁定 | `docs/decisions/v3_e2_argument_ruling.md`：确认首轮停止正确、0 次调用、one-shot INTACT；修正 `--test-sha256` = 整文件哈希，冻结三份逐 seed train 哈希 | — | 0 | — |
| 第 2 次派发 | 按裁定核对全部修正绑定（全部一致，见 §3），随后检查入口能否在一条命令中绑定 3 份逐 seed train | 入口检查发现**无法表达**，按指令 STOP；未调用主流程 | **0** | 仅本报告 |
| 接口扩展裁定 | `docs/decisions/v3_e2_interface_ruling.md` §1–§2：采用 per-seed 校准（否决单一共享捷径），授权最小接口扩展并冻结入口 SHA | — | 0 | — |
| 实现 + 冻结 | 扩展 `experiments/e2_test_evaluator.py`；自检；冻结入口 SHA（见 §2b） | — | 0 | 本报告 + 代码/测试改动 |
| 第 3 次派发 | 以冻结入口、修正参数、SHA 命名模型链接单次调用 | test-only 行门 REFUSED（非 test 行 `probe-F1-0000`），exit 2；未加载模型、未评分 | **1** | 无 run 目录 |
| test-row 裁定 | `docs/decisions/v3_e2_rows_ruling.md`：pre-scoring REFUSED 不消耗科学 one-shot；授权最小 filter 修正 + 唯一权威调用 | — | 0 | — |
| filter 修正 + 冻结 | 仅 test 行评分 + 规范 SHA 绑定；自检 18/18、单测 13/13、pytest 103；冻结新入口 SHA（§2c） | — | 0 | 本报告 + 代码/测试改动 |
| 第 4 次（权威）派发 | 以新冻结入口单次权威调用 | 见 §9 | **1（唯一权威 pass）** | 见 §9 |

**累计 evaluator 进程调用 = 2（1 次 pre-scoring REFUSED + 1 次权威）；权威评分 pass = 1；前两次 preflight 为 0。全程无重试、无重跑、无多轮查看结果。**

---

## 2b. 接口扩展裁定落实与入口冻结（PI 裁定 §2）

- **只读先读**：`docs/decisions/v3_e2_interface_ruling.md` 与 `docs/decisions/v3_e2_argument_ruling.md` 均已在实现前读取。
- **实现（仅 `experiments/e2_test_evaluator.py`，最小改动）**：
  - 新增 `--train-path-s0/--train-sha256-s0`、`-s1`、`-s2` 六参数；原单组 `--train-path/--train-sha256` 仅保留给 `--cpu-selfcheck` 兼容，正式 GPU 模式**不接受**其为回退。
  - `verify_per_seed_trains()`：逐 seed `check_train_path()` → 重算文件字节 SHA → 与传入值严格比对（不符即 `E2Refusal`，沿用既有拒绝契约，**不写任何部分产物**，保持 one-shot 目录纯净）→ 仅加载该 seed 的 train 行。
  - `run_gpu_cells()`：按 seed 用各自 `train_rows` 构造 `tstack/sstack`（`stacks_by_seed`），6 格按 `(mapper, seed)` 取对应校准栈；test 仍是同一固定 300 对，`pair_set_fingerprint` 强制一致，不按 seed 拆分。
  - `config.json` 与 `metrics.json` 记录 `entry_sha256` 与三组 `per_seed_train`（路径 + SHA）。
- **安全门未削弱**：test 整文件哈希 `f910…aa894a`、锁 `c2d629…c9d5e`、eval-config `d8c232…116e6`、val 路径/调参 flag 拒绝、one-shot run-id、16 family exploratory、no pooled inference、strict zero-re-prefill 审计全部原样保留。
- **验证**：`--cpu-selfcheck` **15/15 PASS**（新增 5 项 per-seed 检查）；`tests/test_v3_entries.py` 扩展至 **11/11 PASS**（新增 per-seed 哈希不符 abort、legacy 回退拒绝、val 路径拒绝、正常加载）；全量 `.venv/bin/python -m pytest -q` **101 passed**；`py_compile` 通过。
- **实现偏差显式上报**：接口裁定 §2.2 提到「写失败 config」；实现沿用冻结入口既有拒绝契约（`E2Refusal` 时不写任何产物），以免污染 one-shot 目录。本次三部 train 哈希预检全部一致，该分支不会触发；如需失败 config 落盘，请 PI 另行明确。
- **冻结入口 SHA-256（该阶段身份，后被 §2c 的 row 修正取代）**：
  `04605192716f09105be88ce4981d49f615e12ef0d654a67f8d505ec8f50ff451`

---

## 2c. test-row 门冲突裁定落实（PI `docs/decisions/v3_e2_rows_ruling.md` §3）

- **只读先读**：`docs/decisions/v3_e2_rows_ruling.md` 已先读取；裁定明确 pre-scoring REFUSED **不消耗科学 one-shot**
  （权威评分 pass 仍为 0），授权修正后**唯一一次权威调用**。
- **最小修正（仅 `experiments/e2_test_evaluator.py`）**：
  - `_load_jsonl_pairs(path, "test")` 对整文件输入**跳过**所有非 `split=="test"` 行（probe/train/val 永不参与评分）；
    train 校准文件仍保持严格逐行检查（非 train 行即 REFUSED）。
  - 新增 `canonical_split_sha256()`（逐行 `json.dumps(ensure_ascii=False)+LF`，与锁 §2 一致）与
    `load_bound_test_rows()`：筛出的 test 行必须 300 行且规范 SHA == `c5450013…769a7a2`，不符即 abort；
    同时校验锁中 `test_split_sha256` 与冻结常量一致。
  - 既有全部门保持：整文件哈希 `f910…aa894a`、锁 `c2d629…c9d5e`、eval-config `d8c232…116e6`、
    per-seed 三组 train 哈希、val/调参拒绝、one-shot、16-family exploratory、no pooled inference、strict zero-re-prefill。
- **验证**：`--cpu-selfcheck` **18/18 PASS**（新增 3 项：整文件含非 test 行只筛 test 且规范哈希绑定、
  规范哈希不符 abort、train 文件仍严格）；`tests/test_v3_entries.py` **13/13 PASS**；全量 pytest **103 passed**；
  纯元数据预检确认真实整文件筛出 300 test 行 / 16 family / 规范 SHA `c545…769a7a2` 匹配、全部 gate PASS、
  目标 run 目录不存在、无禁止 flag。
- **冻结入口 SHA-256（本次权威调用的入口身份，写入 run `config.json`）**：
  `da80afdc35f433c65c22938a0bde516927feaef5dac0a6ae59d60e07d72b8f6f`

---

## 3. 修正后 preflight 证据（第二次派发，全部为元数据/静态检查）

| # | 检查 | 结果 | 证据 |
|---|---|---|---|
| 1 | 已先读 PI 裁定 | **PASS** | `docs/decisions/v3_e2_argument_ruling.md` §1–§3 已读；未改 v3.0 / 锁 / evaluator |
| 2 | `--test-path` = `data/tasks/cf_pairs.jsonl`；`--test-sha256` = 整文件字节哈希 `f910…aa894a` | **PASS** | 实算 `sha256` = `f910f1f1196a21041765834654af8233d216ef4bf4f28f4c60abbd0641aa894a`，与裁定 §1 一致；不再用 `c545…`（锁中派生值仅描述性元数据） |
| 3 | `--eval-config-hash` | **PASS** | `sha256(configs/prereg/gpu_followup_v3.0.yaml)` = `d8c2321fc4ba6abeda80e6f581d3f7ef6c592c9173de757aad1a40120ae811e6` |
| 4 | `--lock-file` = `reports/data/v3_e2_test_lock.md`，SHA = `c2d629b5…c9d5e` | **PASS** | 实算 `c2d629b5f928d03c106a2b4b6e8e3e7059af11f34c12bd5ace019d5c9b9c9d5e`；含 PI 解锁 + `previously unevaluated held-out split`；`parse_lock` 提取两条数据哈希 |
| 5 | 三份逐 seed clean v2.1 train 字节哈希 == 裁定 §2 | **PASS** | seed0 `9b03522746825f3fe0794c7f62ec7b1fb430f46734bb175b90a55a788d91e953`；seed1 `024a69e9f35c777ad1030227eed37ef8f3dd43a82fb0a905a569e9150a37633f`；seed2 `53258777ab214fb9226b85389673672c9c4b1b17c8cb9d07cf1a97beddcf3e6e` —— 三者实算全部一致 |
| 6 | **单次调用能否绑定 3 份逐 seed train** | **FAIL（阻塞项）** | `parse_args()` 仅一个 `--train-path`/`--train-sha256`；`run_gpu_cells()` 一次读 `train_rows`（`:722`）并构造单一 `tstack`/`sstack`（`:759–760`），6 格共用（`:768`）；无 per-seed 模板/哈希绑定接口 |
| 7 | evaluator 拒绝 val 路径 / 调参 / 返修 flag | **PASS（首轮实测，未削弱）** | `--cpu-selfcheck` 10/10 PASS：`val_path_rejected` / `val_flag_rejected` / `tuning_flags_rejected` 等全 PASS |
| 8 | 模型快照钉扎 + 逐文件 SHA 对 manifest | **PASS** | 1.7B 10/10、0.6B 8/8 文件 SHA+字节一致（`ALL_MODEL_HASHES_OK=TRUE`）；SHA 命名链接存在；未重新解析 `master`、未再下载 |
| 9 | 无既有 v3_E2 权威 run 目录 | **PASS** | `find reports/runs -maxdepth 1 -name 'v3_E2*'` 为空；目标 `v3_E2_heldout_s0s1s2/` 不存在 |
| 10 | 环境 | **PASS（信息项）** | RTX 5090 / 32607 MiB / driver 580.82.07；Python 3.12.3；bf16/sdpa 为冻结常量；6 格固定、16 family → `exploratory=true`、`pooled_inference=false`（entry 静态核对） |

### 关键哈希汇总（全部实算一致）

| 对象 | SHA-256 |
|---|---|
| `configs/prereg/gpu_followup_v3.0.yaml`（`--eval-config-hash`） | `d8c2321fc4ba6abeda80e6f581d3f7ef6c592c9173de757aad1a40120ae811e6` |
| `data/tasks/cf_pairs.jsonl` 整文件（`--test-sha256`，裁定修正值） | `f910f1f1196a21041765834654af8233d216ef4bf4f28f4c60abbd0641aa894a` |
| test split（300 对，锁中派生值，**非** `--test-sha256`） | `c5450013bc9fc9b84dec286a653207f2dde8168d0df74a24896218d32769a7a2` |
| `reports/data/v3_e2_test_lock.md` | `c2d629b5f928d03c106a2b4b6e8e3e7059af11f34c12bd5ace019d5c9b9c9d5e` |
| `fully_repaired/train_seed0.jsonl` | `9b03522746825f3fe0794c7f62ec7b1fb430f46734bb175b90a55a788d91e953` |
| `fully_repaired/train_seed1.jsonl` | `024a69e9f35c777ad1030227eed37ef8f3dd43a82fb0a905a569e9150a37633f` |
| `fully_repaired/train_seed2.jsonl` | `53258777ab214fb9226b85389673672c9c4b1b17c8cb9d07cf1a97beddcf3e6e` |

---

## 4. 历史阻塞项（第 2 次 preflight STOP；已由接口扩展裁定解决）

> 以下描述的是**扩展前**冻结入口的静态状态，仅作历史记录；扩展实现见 §2b。

PI 裁定 §2 冻结：seed `k ∈ {0,1,2}` 的校准集为 `fully_repaired/train_seed{k}.jsonl`（三份不同哈希）；
同一固定 300 对 test split 不按 seed 拆分；三个 seed 是 mapper/calibration seed，不是三份独立 test replicate。

冻结 evaluator 的实际行为（静态读取，未运行）：
- `parse_args()`（`:931–952`）仅定义 `--train-path`、`--train-sha256` 各一个标量参数；无 train 目录/模板/列表，
  `parse_args` 中也没有 docstring `:38` 示例里的 `--seed-set`。
- `run_gpu_cells()`（`:719–722`）对这一个 train 文件做一次哈希校验并读取 `train_rows`；
- `:752–760` 由该 `train_rows` 构造唯一一份 `cal_docs` → `tstack` / `sstack`；
- `:764–768` 的 6 格循环对**所有** affine/kd_only × seed 复用同一 `tstack` / `sstack`（affine 每 seed 完全同 mapper，
  kd_only 仅注入随机种子），没有按 seed 重新绑定校准数据。

因此，若只传 `train_seed0.jsonl`（或任一份），seed 1/2 就会在 seed 0 的校准集上评分，直接违背裁定 §2；
若传三份则 CLI 无法表达。按当时的 STOP 条件，工程师**未**调用 evaluator，也未发明 `--train-dir` / `{seed}`
模板 / 多次调用 / 拆分 6 格等接口或流程。

**已由 PI 接口扩展裁定解决**：采用方案 1（per-seed 校准），否决单一共享校准捷径；授权最小接口扩展并冻结入口 SHA
（见 §2b）。该历史阻塞不再存在，也不再需要第二种裁决选项。

---

## 5. Per-cell 技术门结果（6 格，权威调用后）

| cell | mapper / seed | 执行 | 可核验结构门 | 未记录的技术量 |
|---|---|---|---|---|
| 1 | affine / 0 | 权威执行 | zero-re-prefill 标志 true；300 test 对；16 family；fingerprint 一致 | 峰值显存/耗时/forward 计数/cache 形状/Self-Identity 差分/逐 forward 审计 |
| 2 | affine / 1 | 权威执行 | 同上 | 同上 |
| 3 | affine / 2 | 权威执行 | 同上 | 同上 |
| 4 | kd_only / 0 | 权威执行 | 同上 | 同上 |
| 5 | kd_only / 1 | 权威执行 | 同上 | 同上 |
| 6 | kd_only / 2 | 权威执行 | 同上 | 同上 |

- **已核验**：`config.zero_re_prefill=true`（写盘前调用 `require_zero_re_prefill()`）、`metrics.zero_re_prefill=true`、
  16 family → `exploratory=true`、`pooled_inference=false`、`sealed_test_read=false`、每格 300 对、同一 pair fingerprint；
  1800 条 score 行全部 `split=="test"`。
- **未记录、无法从产物独立核验**：冻结入口未持久化峰值显存、耗时、forward 计数、cache 形状、Self/Identity 差分或
  逐 forward 审计明细（已核对：产物与源码均无这些字段）。依 one-shot 纪律不得重跑补采，故如实标为不可核验；
  **不以 pilot 数字或占位值代替**。若 PI/G4 需要这些量，须另行授权一次带 instrumentation 的新入口与新的单次调用。

---

## 6. One-shot attestation（覆盖全部阶段）

- **evaluator 进程调用 = 2**：两次 preflight STOP 各 0 次 + 第 3 次 pre-scoring REFUSED 1 次 + 第 4 次权威 1 次。
  **权威评分 pass = 1**；REFUSED 后未重试，权威调用后未重跑、未再调用。
- **无调参、无阈值选择、无错误返修、无多轮查看**：pre-scoring REFUSED 阶段未观察到任何 test 结果；
  未读取 test 条目内容（仅做整文件/规范 split 的字节哈希与筛行，均为 evaluator 自身门逻辑）。
- **无 seed pooling**：未合并任何评分；6 格设计未在运行时改动。
- **无测试性能数字**：本报告不含 `E_CF`、Self/Joint、coverage、flip、L、CI 等任何性能数值。
- **未改冻结判据/稿件**：`configs/**`、`configs/prereg/**`、`docs/decisions/**`、`papers/**`、`data/**` 均未修改。
  仅按三份 PI 裁定修改实现文件 `experiments/e2_test_evaluator.py` 与测试 `tests/test_v3_entries.py`，每次修改均先冻结入口 SHA。
- **权威产物已落盘且不可变**：`reports/runs/v3_E2_heldout_s0s1s2/` 四件套齐全；未覆盖任何历史 run。
- **结果去向**：权威结果仅属**新研究**，不进入当前 TMLR 稿件；统计判读在 G4。

---

## 7. 移交

- → **PI / main agent**：权威调用已完成（见 §9），工程师**不再调用、不重跑、不改哈希/阈值/样本**。
  请按 G3 放行规则进入 G4：由 scientist + reviewer 从 `scores.jsonl` 重算 family bootstrap + pair 敏感性、
  判读分支对号入座、所有失败/REFUSED 调用入账。
- → **写作者 / 审稿人 / 科学家**：`reports/runs/v3_E2_heldout_s0s1s2/scores.jsonl` 为唯一权威逐对记录来源；
  本报告不含任何性能数值。技术量（显存/耗时/forward/cache 形状/Self-Identity）未被冻结入口记录，
  请勿从 pilot 或本报告推断这些量。

---

## 8. 第 3 次调用：pre-scoring REFUSED（完整历史记录）

**入口**：冻结后的 `experiments/e2_test_evaluator.py`，SHA-256 =
`04605192716f09105be88ce4981d49f615e12ef0d654a67f8d505ec8f50ff451`（调用前后复核一致）。
**调用命令行**（单次，`NO --smoke`、无调参/阈值/selection/rework flag，`scan_forbidden_flags([])` 为空）：

```
.venv/bin/python -m experiments.e2_test_evaluator \
  --run-id v3_E2_heldout_s0s1s2 \
  --test-path data/tasks/cf_pairs.jsonl \
  --test-sha256 f910f1f1196a21041765834654af8233d216ef4bf4f28f4c60abbd0641aa894a \
  --lock-file reports/data/v3_e2_test_lock.md \
  --eval-config-hash d8c2321fc4ba6abeda80e6f581d3f7ef6c592c9173de757aad1a40120ae811e6 \
  --train-path-s0 data/variants_v3/fully_repaired/train_seed0.jsonl \
  --train-sha256-s0 9b03522746825f3fe0794c7f62ec7b1fb430f46734bb175b90a55a788d91e953 \
  --train-path-s1 data/variants_v3/fully_repaired/train_seed1.jsonl \
  --train-sha256-s1 024a69e9f35c777ad1030227eed37ef8f3dd43a82fb0a905a569e9150a37633f \
  --train-path-s2 data/variants_v3/fully_repaired/train_seed2.jsonl \
  --train-sha256-s2 53258777ab214fb9226b85389673672c9c4b1b17c8cb9d07cf1a97beddcf3e6e \
  --teacher reports/_non_authoritative/v3_g2_pilot/pinned/Qwen31.7B-sha256-1ddb5b89ebc90dcb \
  --student reports/_non_authoritative/v3_g2_pilot/pinned/Qwen30.6B-sha256-660db3b73d788119 \
  --device cuda
```

**调用前纯门试算（不计调用）**：`verify_gates()` PASS、`binding_kind=whole_file`、`out_dir` 不存在、
`smoke=false`；模型逐文件 SHA 对 manifest 全部 OK；三组 train 哈希逐一匹配裁定 §2。

**调用结果（stdout 原文）**：
```
{"status": "REFUSED", "reason": "data/tasks/cf_pairs.jsonl contains a non-test row: 'probe-F1-0000'; val/test mixing is forbidden"}
exit = 2
```

**失败位置**：`run_gpu_cells()` 的 `_load_jsonl_pairs(args.test_path, "test")` 逐行门禁，在模型加载、cache capture、
任何前向或评分之前。整文件哈希门已通过；失败源于该文件按锁定义含有 probe/train/val 行，而入口要求整个文件全为
test 行。未产生 `reports/runs/v3_E2_heldout_s0s1s2/`，未产生任何分数或技术门测量值。依 one-shot 纪律**未重试**。

---

## 9. 第 4 次调用：唯一权威评分（PASS）

**入口**：冻结 SHA `da80afdc35f433c65c22938a0bde516927feaef5dac0a6ae59d60e07d72b8f6f`；
命令行与 §8 相同（`--run-id v3_E2_heldout_s0s1s2`、整文件哈希 `f910…aa894a`、锁 `c2d629…`、eval-config `d8c232…`、
三组 per-seed train、SHA 命名模型链接、`NO --smoke`、无禁止 flag），调用前 `verify_gates()` PASS、
规范 split SHA `c545…769a7a2`（300 行 / 16 family）预检匹配、run 目录不存在。

**结果**：`{"status": "COMPLETED", "run_id": "v3_E2_heldout_s0s1s2", "authoritative": true, "out_dir": "/root/readkv/reports/runs/v3_E2_heldout_s0s1s2"}`；exit 0。
为单次后台进程（前台 3600 s 窗口到期后自动转后台，**未启动第二份**）。

**产物结构核验（全部 PASS，无性能数值）**：

| 检查 | 结果 |
|---|---|
| 入口 SHA 写入 config / metrics | PASS（= `da80afdc…b8f6f`） |
| `zero_re_prefill`：config + metrics | PASS（均为 true；写盘前 `require_zero_re_prefill()`） |
| authoritative=true / one_shot=true / smoke=false / backend=gpu | PASS |
| 整文件 test 哈希 / 锁哈希 / eval-config 哈希 / binding=whole_file | PASS（四值与冻结值逐一相同） |
| 三组 per-seed train 哈希 | PASS（与 `v3_e2_argument_ruling.md` §2 一致） |
| designation / sealed_test_read=false / exploratory=true / pooled_inference=false | PASS |
| 6 格 = affine/kd_only × 0/1/2；每格 300 对 / 16 family | PASS |
| 所有格共享单一 `pair_set_fingerprint`（`9dad7c5c6786bfa9…`） | PASS |
| scores.jsonl 1800 行、全 `split=="test"`、300 个唯一 pair_id、cell 覆盖一致 | PASS |
| flip 分母排除 F5+F6；family CI unit=template_family / exploratory / 10000 resamples | PASS |
| manifest 三条文件 SHA-256 与字节数逐项比对 | PASS |

**产物哈希（供复核）**：

| 文件 | SHA-256 |
|---|---|
| `config.json` | `985c71f1d632e9152e994d288cd671afb787cde438306c0994dc5384c73186b2` |
| `metrics.json` | `42b78d5d2d74fa66384c7dc637fac5b6637d2b4865f94da4468d7fdff352cb68` |
| `scores.jsonl` | `15fb742067184bad7504c3f71206e0b1a0be30c43b2a48b2239615fe9c00dd26` |
| `manifest.json` | `af23c1d3ee65976fe33f4bdd377efb77f8292a2c54f9f87f93d7a9e30cfc02bf` |

**签署：工程师（G3 batch 2 / E2 ONE-SHOT；两次 0 调用 preflight STOP + 1 次 pre-scoring REFUSED + 1 次权威 COMPLETED；2026-11-25）。**

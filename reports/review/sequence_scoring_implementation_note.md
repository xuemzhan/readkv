# 完整候选答案评分独立 GPU 入口：实现说明（protocol-v2.8）

> 作者：engineer（readkv）。日期：2026-11-24。
> 状态：**已实现 + CPU 自检通过；本轮未启动任何 GPU 正式/冒烟 run**，等待 PI 在
> data-engineer CPU 审计完成后下达 GPU 运行指令。本文件不含任何科学结论或 GPU 数字。

---

## 1. 本轮交付与边界

| 项 | 内容 |
| --- | --- |
| 新增入口 | `experiments/sequence_scoring_gpu.py` |
| 新增显式评分模式 | `src/readkv/models/gpu_backend.py`（追加 `score_candidate_sequence` + 纯函数；**不改** `GPUBackend` 贪解码路径） |
| 新增单测 | `tests/test_sequence_scoring.py`（7 项，强制 CPU） |
| 本说明 | `reports/review/sequence_scoring_implementation_note.md` |
| 未触碰 | `configs/prereg/*`、`docs/protocol.md`、`reports/runs/**`、数据、论文、封存 test |
| GPU run | **0 个**（未执行 `--smoke`，未执行任何正式格；未加载 Qwen3 大模型） |

`--cpu-selfcheck` 不加载模型、不创建 run 目录、不调用 cuda；微型 Qwen3 单测显式
`device="cpu"` / `dtype=float32`。全套 `pytest`（GPU 屏蔽 `CUDA_VISIBLE_DEVICES=""`）
**64 passed**。

---

## 2. 设计

### 2.1 独立入口

- 显式接收 `--version legacy|fixed` 与 `--seed k`；路径只从
  `data/audit_2x2/{legacy,fixed}/{train,val}_seed{k}.jsonl` 派生（可用
  `--train-path/--val-path` 覆盖，但校验必须落在对应版本目录内）。
- `derive_paths()` 硬拒绝任何含 `test` 的路径、非 `train/val_seed{k}` 文件名、跨版本目录。
- **不调用** `P1_gpu.py` / `run_cf_pipeline`，不重建数据、不过质量门；只读 JSONL。
- `--version legacy → A00`（旧/旧），`--version fixed → A11`（修复/修复）；
  **A01/A10 无入口**（`cell` 仅允许 A00/A11，显式断言）。

### 2.2 每格一次 mapper

- `fit_mapper_once()`：用该格 train 的全部 CFPair 两侧上下文，teacher/student 各独立
  prefill，`AffineMapper(lam=0.001, channel="both")`，28→28 `LayerMap(kind="identity")`。
  **每格拟合一次**，同一 mapper 服务 Self/Joint/Identity 与三种读数。
- 固定 `bfloat16` + `sdpa`；等深断言（teacher/student 层数不等即拒绝）。

### 2.3 显式 teacher-forcing 评分（非贪解码）

新增 `score_candidate_sequence(model, cache, query_tokens, candidate_token_ids, ...)`：

1. 对每条候选分支，从**同一份已映射内容空间 KVCache** 新建**全新** `DynamicCache`
   （从 numpy 源数组重建张量，不共享可变状态；每次调用分配单调 `branch_cache_id`）。
2. query prefill（`position_ids = offset..offset+Q-1`，`offset=doc_len`）→ 首 token 分布；
   `first = FP32 log-softmax(logits)[cand[0]]`。
3. 依次 teacher-force 真实候选前缀：喂 `cand[i]`（位置 `offset+Q+i`）预测 `cand[i+1]`，
   累加 FP32 条件 logprob；**不追加 EOS**，`full = Σ_{i=0..m-1} log P(cand[i]|...)`。
4. `length_normalized = full / m`。
5. 全程 `inference_mode`，学生权重冻结；**文档 token 从不进入学生显式输入**，
   文档长度只经注入缓存与位置偏移。

`inject_and_generate(max_new_tokens=...)` 贪解码路径**语义未改**；`GPUBackend` 的
`candidate_logits/torch_candidate_logits` 保持原样。首 token 读数与归档同口径
（同一 query 末位 logits 取候选首 token，FP32 log-softmax 归一化在两候选间对消）。

### 2.4 逐次输入审计（硬门）

每次 forward 用 pre-hook 记录：输入 token 数、输入 token id 指纹、position 起点；
主循环记录注入缓存前缀长度。`audit_sequence_forwards()`（纯函数）断言：

- 输入长度序列严格 `[Q, 1 × (m−1)]`，forward 次数 `m`；
- 首次位置 `offset`，第二个为 `offset+Q`，之后每次 +1；
- 喂进学生的 token 总数 `Q+(m−1)`，所有位置 ≥ `offset ≥ doc_len`
  → **zero re-prefill 无文档 token 进显式输入**；
- 注入缓存前缀每步只增长对应输入长度（每分支从 `doc_len` 初始状态开始）；
- 候选 token id / 指纹齐全。

`strict_audit=True` 下任一断言失败即 `AssertionError` → 入口捕获后中止该格，写
`forward_audit.jsonl`（已完成的审计）+ `metrics.json`（`status=ABORTED` + `reason`），
不静默通过。入口额外断言四个分支（2 doc side × 2 candidate）`branch_cache_id` 互异。

### 2.5 三读数与统计

- 每（pair, arm）一行：双侧×两候选×三读数分数、`g=logP(A)−logP(B)`（双侧）、
  `D=g(docA)−g(docB)`、`E_CF=|D_joint−D_self|`、`dual_correct`、`evaluable`、
  `flip_consistency`、gold/预测、`template_family`、token 长度、token 边界报告、失败标记。
- `L = dual_correct(Self) − dual_correct(Joint)`，三读数并列；配对
  `L_full − L_first` 用 `template_family` 簇级 bootstrap（10000 resamples，
  <24 族标 `exploratory=true`）；`τ=1.0`、`self_threshold=0.1` 沿用归档 2x2，未按结果调整。
- 只输出指标事实，**不做判读分支归类**（由 scientist 按 v2.8 §7 对号入座）。

---

## 3. CLI 参数

| 参数 | 含义 |
| --- | --- |
| `--run-id` | 新 run id（不可覆盖已有目录） |
| `--version {legacy,fixed}` | 版本 → A00 / A11（A01/A10 不做） |
| `--seed {0,1,2}` | 对应 `_seed{k}.jsonl` |
| `--out-dir` | 产物父目录，写入 `<out-dir>/<run-id>/`；默认 `reports/runs`（冒烟默认 `reports/_non_authoritative`） |
| `--smoke` / `--smoke-n-val` | 技术门小样本；含 Identity 臂、首 token 历史回放（只读归档）、单 token 一致性、A/B 顺序说明 |
| `--cpu-selfcheck` | 纯函数 CPU 自检，零模型/零 GPU/零产物 |
| `--train-path/--val-path` | 可选显式数据路径（强制落在版本目录、禁 test） |
| `--teacher/--student/--dtype/--kernel/--device` | 模型与运行配置 |
| `--swap-ab` | 额外一轮 B→A 顺序，按候选身份核验分数一致 |
| `--n-resamples`, `--first-token-tol` | bootstrap 次数 / 冒烟首 token 回放容差 |

`config.json`（`RunContext`，`protocol_version=2.8`）含 `git_hash`、seed、版本标签、
train/val SHA-256、dtype/kernel/zero_re_prefill、模型路径、tokenizer 指纹、mapper/层映射、
判据来源。产物：`config.json`/`scores.jsonl`/`forward_audit.jsonl`/`metrics.json`/`manifest.json`。

---

## 4. 与 v2.8 对齐项

| v2.8 冻结条款 | 实现 |
| --- | --- |
| §2 只 A00/A11，8 run，不读 test | `--version` 仅两项；路径硬禁 test；未跑 A01/A10 |
| §3 显式 train/val 版本 + SHA-256 | `derive_paths` + `sha256_file` 写 config |
| §4 fit_once / affine λ=0.001 / 28→28 / bf16/sdpa | `fit_mapper_once` + `LayerMap(identity)` + 等深断言 |
| §4 三读数（首/full/归一化），FP32 log-softmax，不追加 EOS | `score_candidate_sequence` + `log_softmax_fp32` |
| §4 teacher-forcing 独立入口，不复用贪解码 | 新增显式模式，`GPUBackend` 贪解码未改 |
| §4 token 边界一致 + 互为前缀计数 | `tokenize_candidate`/`token_boundary_report`/`prefix_relation` |
| §4 同分沿用固定候选顺序 | `_pred_from_g`：`g>0→A`，`g≤0→B`（含同分） |
| §5 输入长度 `[Q,1×(m−1)]`、位置偏移、缓存独立、zero re-prefill、失败即中止 | `audit_sequence_forwards` + 单调 `branch_cache_id` + `ABORTED` 路径 |
| §6 L、L_full−L_first、簇级 bootstrap、<24 族 exploratory | `summarize()` |
| §8 冒烟门（首 token 回放、单 token 一致、A/B 顺序、逐次审计） | `--smoke` 检查块 |
| 不重算主终点 / 不恢复贡献 / 不碰封存 test | 入口无相关代码路径；metrics note 明示 |

---

## 5. CPU 自检结果（本轮实际执行）

- `python -m experiments.sequence_scoring_gpu --cpu-selfcheck` → `PASSED`：
  token 边界一致/不一致/互为前缀、长度序列 `[7]`/`[7,1,1]`、首 token=单 token 整串、
  审计 pass/fail 两类、token id 指纹确定。
- `CUDA_VISIBLE_DEVICES="" python -m pytest -q` → **65 passed**（含新增 7 项）。
  新增微型 Qwen3 CPU 前向测试验证：m=1 整串=首 token；m=3 输入序列 `[5,1,1]`、
  位置 `[12,17,18]`、缓存前缀 `[12,17,18]`、归一化=full/3；首 token 与
  `inject_and_generate` 对齐（abs≤1e-4）；两分支实例号互异且分数一致。
- **未**加载 Qwen3-1.7B/0.6B 大模型，**未**调用 cuda，**未**写 `reports/runs/**`。

---

## 6. 已知限制与待确认

1. **模型 revision / 旧快照身份**：默认路径为 `snapshots/master` 可变别名。config 只记录
   路径 + tokenizer 指纹，不哈希多 GB 权重。若归档 run 仅记可变 snapshot 别名，按 v2.8 §4
   以首 token 逐对一致性（`--smoke` 的 `first_token_replay`，只读归档、按 `sample_id`+arm 对齐）
   确认数值复现，并明示可核验身份范围；不可恢复的旧快照差异须如实记录，不静默通过。
2. **首 token 回放为冒烟只读锚点**：`_archived_first_token_dself()` 只读
   `reports/runs/audit_2x2_A{00,11}_s0/scores.jsonl`，不参与正式格评分；归档缺失时
   `passed=None`（记为 skipped），不伪造一致性。
3. **A/B 顺序交换**：`--swap-ab` 以独立一轮 B→A 审计体现；smoke 默认仅记录说明，正式核验在
   PI 下达指令后按门控执行并写入产物。
4. **统计解释未越界**：`metrics.json` 只给指标事实与区间；判读三分支、A11−A00 跨版本差
   由 scientist 在独立分析文档完成，本入口不做事后择支。
5. **身份/分母**：样本以 `version_tag|sample_hash[:16]` 标识（pair_id 跨版本会碰撞）；
   主分析 F1–F4 分母由 scientist/reviewer 在统计阶段核对，本入口对全部 val 行输出。
6. **与 data-engineer CPU 审计的一致性**：入口只读 `data/audit_2x2/{legacy,fixed}/`
   的 train/val JSONL，不依赖 `data/audit_2x2/sequence/**` 索引。候选 token id 一律在
   运行时用学生 tokenizer（Qwen3-0.6B）按固定边界 `add_special_tokens=False` 现算，
   **不读取源 JSONL 中作为文档长度代理的 `token_count_A/B`**（data-engineer 已警示该字段
   不是候选 token 数）。边界指纹写入 `forward_audit.jsonl` / `scores.jsonl`，可与索引的
   `candidate_*_token_count` 事后核对。
7. **本轮无科学结论**：以上均为实现与 CPU 自检事实；任何 GPU 数字须待 PI 指令后由真实 run 产出。

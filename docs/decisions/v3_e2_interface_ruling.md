# E2 evaluator 接口扩展裁定（2026-11-25）

> 裁决人：PI / 课题组长（本会话由真实 PI 授权 main agent 执行）。
> 背景：G3 batch 2 两次 preflight 停止，`experiments/e2_test_evaluator` 累计调用次数 = **0**；无 run 目录、无 test 内容评分。第二次停止原因：冻结 evaluator 只接受单组 `--train-path/--train-sha256`，`run_gpu_cells()` 用同一 `train_rows` 构造一个 `tstack/sstack` 供 6 格复用（`e2_test_evaluator.py:722,752-760,768`），无法表达 v3.0 §4「各 mapper seed 在同一固定 test 集上分别评分」所需的 per-seed 校准。
> 性质：**实现接口扩展授权 + 冻结裁定**。不改 v3.0、不改锁文件、不改科学设计；扩展后须冻结入口哈希再运行。one-shot 锚点仍为首次成功调用，前两次 preflight 停止不计入。

---

## 1. 裁定：采用 per-seed 校准（方案 1），不采用单一共享校准

- v3.0 §4 规定「affine 与 kd_only 各 seed」在同一固定 300 对 test 集上评估；seed 决定校准/训练 split 的生成（v2.1 协议 train_seed{k}），故 3 个 seed 必须各自使用 `fully_repaired/train_seed{k}.jsonl`。
- 若退化为单一共享校准集，seed 1/2 不再对应其各自的训练数据，违背预注册设计且会把 mapper-seed 误读为重复评分；**明确否决**该捷径。
- 不因此改 v3.0、不改判读分支、不改 test 锁、不改论文。

## 2. 授权的最小接口扩展（仅 `experiments/e2_test_evaluator.py`）

授权工程师对**实现文件**做最小扩展，要求：

1. 新增三组显式参数：`--train-path-s0` / `--train-sha256-s0`、`--train-path-s1` / `--train-sha256-s1`、`--train-path-s2` / `--train-sha256-s2`；保留原单组 `--train-path/--train-sha256` 仅用于 `--cpu-selfcheck` 兼容，正式模式必须提供三组。
2. 对三组路径逐一重算 SHA-256 并与传入值比对；任一不符即 abort，写失败 config。三组哈希须分别等于 `docs/decisions/v3_e2_argument_ruling.md` §2 的三个值。
3. `run_gpu_cells()` 改为按 seed 取对应 train_rows 构造该 seed 的 `tstack/sstack`；test 集仍为同一固定 300 对，按 pair fingerprint 强制一致；不得按 seed 拆分 test。
4. 所有既有安全门保持不变：test 整文件哈希绑定、锁文件与 PI 解锁解析、eval-config 哈希、val 路径/调参 flag 拒绝、one-shot run-id、16 family exploratory、no pooled inference、strict zero-re-prefill 审计。
5. 扩展后运行 `.venv/bin/python -m experiments.e2_test_evaluator --cpu-selfcheck`（应 10/10 PASS，必要时新增 per-seed 检查项），并新增/扩展 `tests/test_v3_entries.py` 覆盖 per-seed 哈希不符 abort。
6. **冻结扩展后入口文件的 SHA-256**，写入 `reports/review/v3_g3_batch2_report.md` 与本次运行的 `config.json`；此哈希是后续复核的入口身份。

## 3. one-shot 纪律

- 前两次均为 preflight 停止、evaluator 调用次数 0；本裁定仅修正实现接口。
- 扩展完成后只允许**一次** evaluator 调用；任何失败立即停止上报，不得改阈值/样本/哈希/重跑/分多次查看。
- 结果仅属新研究，不进入当前 TMLR 稿件。

---

**签署：PI / 课题组长（E2 接口扩展裁定 · 2026-11-25）**

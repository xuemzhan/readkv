# E2 one-shot 参数口径裁定（2026-11-25）

> 裁决人：PI / 课题组长（本会话由真实 PI 授权 main agent 执行）。
> 背景：G3 batch 2 首次派发在 preflight 停止，`experiments/e2_test_evaluator` **0 次调用**、无 run 目录、无 test 内容评分。停止原因是我方派发参数把「test split 派生哈希」误当 `--test-sha256` 传入，且缺 `--train-path/--train-sha256`。这不是冻结判据或 evaluator 的缺陷。
> 性质：派发参数口径裁定；不改 v3.0、不改锁文件、不改 evaluator。one-shot 锚点仍为**首次成功调用**；本次为失败 preflight 后的唯一一次派发，不构成重试/返修/多轮查看。

---

## 1. `--test-sha256` 的绑定语义（冻结）

- `experiments/e2_test_evaluator` 对 `--test-path` 指向的**磁盘整文件字节**计算 SHA-256，并要求与 `--test-sha256` 相等，且该值须出现在锁文件的两个记录值之一。
- 因此 `--test-sha256` = **`f910f1f1196a21041765834654af8233d216ef4bf4f28f4c60abbd0641aa894a`**（`data/tasks/cf_pairs.jsonl` 全文件 520 行字节哈希）。
- `c5450013bc9fc9b84dec286a653207f2dde8168d0df74a24896218d32769a7a2` 是锁文件中记录的 **test split（300 对）派生哈希**，仅作描述性元数据，**不是** `--test-path` 的字节哈希，不得填入 `--test-sha256`。
- 锁文件 `reports/data/v3_e2_test_lock.md` 两值并存、PI 解锁与设计ation 已解析通过，无需改动。

## 2. calibration train 绑定（冻结）

按 G2 release §1 的 clean v2.1 裁定（`fully_repaired` 为规范 clean 版本），E2 各 mapper seed 的校准集为 `data/variants_v3/fully_repaired/train_seed{k}.jsonl`，字节哈希：

| seed | train 路径 | SHA-256 | 行数 |
|---:|---|---|---:|
| 0 | `data/variants_v3/fully_repaired/train_seed0.jsonl` | `9b03522746825f3fe0794c7f62ec7b1fb430f46734bb175b90a55a788d91e953` | 120 |
| 1 | `data/variants_v3/fully_repaired/train_seed1.jsonl` | `024a69e9f35c777ad1030227eed37ef8f3dd43a82fb0a905a569e9150a37633f` | 120 |
| 2 | `data/variants_v3/fully_repaired/train_seed2.jsonl` | `53258777ab214fb9226b85389673672c9c4b1b17c8cb9d07cf1a97beddcf3e6e` | 120 |

评测固定使用同一份 300 对 held-out split（不按 seed 拆分）；三个 seed 是 mapper/calibration seeds，不是三份独立 test replicate。

## 3. one-shot 纪律重申

- 首轮因派发参数错误在 preflight 停止：evaluator 调用次数 = 0，无 `reports/runs/v3_E2_*` 目录，无 test 内容读取/评分。
- 本裁定仅修正派发参数；重新派发后必须**单次成功运行即止**；任何失败一律停止并上报，**不得**改阈值、改样本、改哈希、重跑或分多次查看。
- 结果仅属新研究，不进入当前 TMLR 稿件。

---

**签署：PI / 课题组长（E2 参数口径裁定 · 2026-11-25）**

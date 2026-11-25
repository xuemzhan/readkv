# E2 test-row 门冲突裁定（2026-11-25）

> 裁决人：PI / 课题组长（本会话由真实 PI 授权 main agent 执行）。
> 背景：G3 batch 2 累计 evaluator 调用 1 次，该次在 `_load_jsonl_pairs(path,"test")` 的 test-row 门被 REFUSED（`data/tasks/cf_pairs.jsonl` 含 probe/train/val 行），**未加载模型、未前向、未评分、未产出任何 test 数字**。此前两次为 0 调用的 preflight 停止。
> 性质：**one-shot 语义裁定 + 最终接口修正授权**。不改 v3.0、不改锁文件、不改科学设计。

---

## 1. one-shot 语义裁定

- prereg §4 / G0 的「一次性 dedicated test evaluator」目的是防止**看到 test 结果后**调参、返修、多轮查看或择支。
- 本次唯一一次调用在**评分前**被 test-row 门拒绝：权威评分次数仍为 **0**，未观察到任何 test 结果，不存在事后择支或调参的可能。
- **裁定：pre-scoring 的契约拒绝不消耗科学 one-shot。** 授权在修正接口后执行**唯一一次权威评分调用**；该调用之后无论结果如何均不得重跑、调参或分多次查看。累计 evaluator 进程调用数为 2（1 次 REFUSED + 1 次权威），但权威评分 pass 恰为 1。

## 2. 数据绑定语义（与锁文件一致）

- `--test-path` 仍为整文件 `data/tasks/cf_pairs.jsonl`，`--test-sha256` 仍绑定整文件字节 `f910f1f1196a21041765834654af8233d216ef4bf4f28f4c60abbd0641aa894a`。
- 评测集是其中 `split=="test"` 的 300 行，按 `json.dumps(ensure_ascii=False)+LF` 规范序列化后字节 SHA-256 = `c5450013bc9fc9b84dec286a653207f2dde8168d0df74a24896218d32769a7a2`（与 `reports/data/v3_e2_test_lock.md` §2 一致）。
- **禁止**把整文件当 test 行逐行评测；**禁止**引入未锁定的新 test 文件。

## 3. 授权的最小接口修正（仅 `experiments/e2_test_evaluator.py`）

授权工程师做以下最小修正并重新冻结入口 SHA：

1. `_load_jsonl_pairs(path, "test")` 在整文件哈希绑定通过后，只保留 `split=="test"` 的行；不得按 probe/train/val 行评分。
2. 对筛选出的 300 行按锁文件 §2 的规范序列化重算 SHA-256，须等于 `c5450013…769a7a2`；不符即 abort。
3. 保留所有既有门：整文件哈希、锁文件与 PI 解锁、eval-config 哈希、per-seed 校准三组哈希、val 路径/调参 flag 拒绝、one-shot run-id、16 family exploratory、no pooled inference、strict zero-re-prefill。
4. 修正后重跑 `--cpu-selfcheck`（含新增的「整文件含非 test 行时只筛 test 且哈希匹配」检查）与 `tests/test_v3_entries.py`；记录新入口 SHA-256 于报告与 run config。
5. 然后执行**唯一一次**权威调用；任何失败立即停止上报，不得再修再跑。

## 4. 结果边界

权威结果仅属新研究，不进入当前 TMLR 稿件；不 pooled、不称 sealed、不称普遍泛化。统计与判读在 G4。

---

**签署：PI / 课题组长（E2 test-row 裁定 · 2026-11-25）**

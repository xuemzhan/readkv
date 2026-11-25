# E1 单缺陷干预变体 — CPU 数据与审计清单（G1）

**性质：** CPU-only 数据准备与审计；**无 GPU 运行、无模型推理、无 test 评分**。本文件不修改任何冻结判据，不是运行授权。

**日期：** 2026-11-25　**角色：** data-engineer　**状态：** G1 数据产物已生成并独立复核；下游 GPU 门（G2/G3）未启动。

## 1. 权威依据与数据来源

- `docs/audit/GPU_experiment_plan_2026-11-25.md` §3（E1 设计与边界）；§3.1 明确退化对不进入 ridge 监督拟合。
- `docs/decisions/gpu_v3_scope_ruling.md`（G0 授权 E1；结果另立新研究）。
- `configs/prereg/gpu_followup_v3.0.yaml`（FROZEN，只读；E1 变体登记与判读分支）。
- 基线：`data/audit_2x2/legacy/{train,val}_seed{0,1,2}.jsonl`（generator commit `458de18`）。
- 全修复：`data/audit_2x2/fixed/{train,val}_seed{0,1,2}.jsonl`（generator commit `efc3ba3`，v2.1 M1/M2/M3）。
- 序列化：`json.dumps(..., ensure_ascii=False) + LF`，文件末尾 LF；SHA-256 作用于文件字节（规范 LF，无 CR）。

## 2. 六变体定义（只改一个声明属性）

| 变体 | 唯一改动属性 | 作用域 | 精确规则 |
|---|---|---|---|
| `legacy_bundle` | NONE (baseline) | verbatim legacy copy | Byte-for-byte copy of the legacy generator export (commit 458de18). No attribute changed; historical reference only. |
| `dedup_only` | in-train duplicate texts only | TRAIN only; VAL verbatim; declared as IN-TRAIN DEDUP (NOT train-val overlap cleanup) | IN-TRAIN DEDUP ONLY: remove train rows whose (context_A, context_B, query, edited_span) duplicates an earlier row in the SAME train split; keep first by file order. VAL is verbatim. train-val overlap cleanup is NOT applied and is never conflated with this variant. |
| `degenerate_only` | must-flip degenerate pairs (candidate_A==candidate_B) only | TRAIN and VAL | Remove rows with must_flip==true AND candidate_A==candidate_B (M1 degenerate must-flip defect) from BOTH train and val. F5 same-candidate rows with must_flip==false are by design and retained. |
| `entity_disjoint_only` | entity-pool overlap across train/val only | VAL only; TRAIN verbatim | VAL only: replace every entity string (name/project/city/date/number) occurring in val text with an injective, rule-generated substitute absent from train text, consistently across context_A/context_B/query/candidate_A/candidate_B/edited_span; recompute sample_hash and sample_id. TRAIN verbatim; row count, family labels, correctness labels and token counts unchanged. Substitutes are produced by this CPU prep script, NOT emitted by the original generator. |
| `template_disjoint_only` | query skeleton overlap across train/val only | VAL only; TRAIN verbatim | VAL only: rewrite each val query into a structurally different skeleton (deterministic paraphrase); context documents, candidates, correctness labels and family labels unchanged; recompute sample_hash and sample_id. TRAIN verbatim; row count unchanged. |
| `fully_repaired` | ALL defects (M1+M2+M3) | full v2.1 repaired version | Verbatim copy of the v2.1 fully repaired generator export (commit efc3ba3, M1+M2+M3). DIFFERENT generator commit and RNG stream than legacy; per-row sample_hash differs on all rows. VERSION DIFFERENCE, not a pure single-defect effect. |

**声明 1（dedup，不得混称）：** `dedup_only` = **训练集内去重（in-train dedup）**；**未做 train–validation overlap 清理**。两者是不同缺陷，本变体不混称；train–val 重叠属于另一缺陷维度，未在此变体中处理。
**声明 2（degenerate）：** must-flip 退化对是 **标签/任务有效性缺陷**，**不进入 ridge 监督拟合**；因此**不声称对 mapper 拟合有任何因果效应**。对旧 logits 的重算应优先 CPU replay；只有候选文本/输入上下文改变才追加 GPU 前向，并单列为「数据任务改变」。
**声明 3（版本差异）：** 任何样本数或 template-family 计数变化均标记为 **版本差异**，不作为「纯单缺陷效应」。`fully_repaired` 来自不同 commit/RNG，全部样本重生成，属版本差异。

## 3. 文件清单（36 文件；哈希/样本数/族数）

| 变体 | 文件 | seed | split | 行数 | 族数 | 退化行 | SHA-256 |
|---|---|---:|---|---:|---:|---:|---|
| `legacy_bundle` | `train_seed0.jsonl` | 0 | train | 120 | 16 | 5 | `81da04a041a4e7757caa02e502c10ca9a9236d7f98da5419fb226ca95a02b00a` |
| `legacy_bundle` | `val_seed0.jsonl` | 0 | val | 60 | 8 | 4 | `24a5077bec11657c70d8eeddeed6fbe4871253d6d141daf16989903d1ebccaaa` |
| `legacy_bundle` | `train_seed1.jsonl` | 1 | train | 120 | 16 | 3 | `7385245c6b2db4e4f78abc837aaa31817cd7025eaa23dc099b2dc92c9f4a793e` |
| `legacy_bundle` | `val_seed1.jsonl` | 1 | val | 60 | 8 | 4 | `6f5c2b553832bdb2e03dd56ab39a7e6b2a6e4b5ec726448692f9fae1ebb849ff` |
| `legacy_bundle` | `train_seed2.jsonl` | 2 | train | 120 | 16 | 4 | `3ad49eea2a41ff0e0ffd516b0fb1b8dc5282dce9a8336d7f371bf28adc97bb11` |
| `legacy_bundle` | `val_seed2.jsonl` | 2 | val | 60 | 8 | 5 | `df24f7cf9d6fae8ce2e8a7af9b2a68aefe040a447534d30119aed99cd7f0c759` |
| `dedup_only` | `train_seed0.jsonl` | 0 | train | 120 | 16 | 5 | `81da04a041a4e7757caa02e502c10ca9a9236d7f98da5419fb226ca95a02b00a` |
| `dedup_only` | `val_seed0.jsonl` | 0 | val | 60 | 8 | 4 | `24a5077bec11657c70d8eeddeed6fbe4871253d6d141daf16989903d1ebccaaa` |
| `dedup_only` | `train_seed1.jsonl` | 1 | train | 119 | 16 | 3 | `94fc68b17b1a25ab3fc51ef7d62279a19a2265fa0342e910338c4e91a79d6e46` |
| `dedup_only` | `val_seed1.jsonl` | 1 | val | 60 | 8 | 4 | `6f5c2b553832bdb2e03dd56ab39a7e6b2a6e4b5ec726448692f9fae1ebb849ff` |
| `dedup_only` | `train_seed2.jsonl` | 2 | train | 120 | 16 | 4 | `3ad49eea2a41ff0e0ffd516b0fb1b8dc5282dce9a8336d7f371bf28adc97bb11` |
| `dedup_only` | `val_seed2.jsonl` | 2 | val | 60 | 8 | 5 | `df24f7cf9d6fae8ce2e8a7af9b2a68aefe040a447534d30119aed99cd7f0c759` |
| `degenerate_only` | `train_seed0.jsonl` | 0 | train | 115 | 16 | 0 | `547e036369cea9f3d9cb39a84ecb53bc4ec786808789a205a4bb888c3a408d4d` |
| `degenerate_only` | `val_seed0.jsonl` | 0 | val | 56 | 8 | 0 | `1b8331470b4ea9aafab6420eab2fac2c3bc64ffc17f7ff6fca81bdaa8489b7dc` |
| `degenerate_only` | `train_seed1.jsonl` | 1 | train | 117 | 16 | 0 | `1eff31623ef7f3292976e8fed2b4804446ec4926db69eaa5ce8642a6e86911ef` |
| `degenerate_only` | `val_seed1.jsonl` | 1 | val | 56 | 8 | 0 | `88123c3b2620283f8b077b0a5fe4a0e183550fce8f1db65cb2fcf37d1b5c2bfb` |
| `degenerate_only` | `train_seed2.jsonl` | 2 | train | 116 | 16 | 0 | `c99d065d96c3ebbc5258258b7283ffd74285b2dc1c468aeed174c71f1607c8e0` |
| `degenerate_only` | `val_seed2.jsonl` | 2 | val | 55 | 8 | 0 | `63773014d340b699868ad921a58b69d80af38d37352a8fc4810629cba54d6fd8` |
| `entity_disjoint_only` | `train_seed0.jsonl` | 0 | train | 120 | 16 | 5 | `81da04a041a4e7757caa02e502c10ca9a9236d7f98da5419fb226ca95a02b00a` |
| `entity_disjoint_only` | `val_seed0.jsonl` | 0 | val | 60 | 8 | 4 | `1f0fdae041261fa7c79a0ce71b7724eeef0b65783cbe79fbef210714004af254` |
| `entity_disjoint_only` | `train_seed1.jsonl` | 1 | train | 120 | 16 | 3 | `7385245c6b2db4e4f78abc837aaa31817cd7025eaa23dc099b2dc92c9f4a793e` |
| `entity_disjoint_only` | `val_seed1.jsonl` | 1 | val | 60 | 8 | 4 | `4c60f81d49501bc2e330ef7d50ad27b5748cd950c033a50f36fd9513f5e75cc9` |
| `entity_disjoint_only` | `train_seed2.jsonl` | 2 | train | 120 | 16 | 4 | `3ad49eea2a41ff0e0ffd516b0fb1b8dc5282dce9a8336d7f371bf28adc97bb11` |
| `entity_disjoint_only` | `val_seed2.jsonl` | 2 | val | 60 | 8 | 5 | `9f87de4f6eddb9cdb959740dec3acf4b5afbfd34f3ec705c286510baeb49c3bd` |
| `template_disjoint_only` | `train_seed0.jsonl` | 0 | train | 120 | 16 | 5 | `81da04a041a4e7757caa02e502c10ca9a9236d7f98da5419fb226ca95a02b00a` |
| `template_disjoint_only` | `val_seed0.jsonl` | 0 | val | 60 | 8 | 4 | `d92225e4eddd40ea949ce59e33a941488f6e732172e33719ad34e2d5afd03a63` |
| `template_disjoint_only` | `train_seed1.jsonl` | 1 | train | 120 | 16 | 3 | `7385245c6b2db4e4f78abc837aaa31817cd7025eaa23dc099b2dc92c9f4a793e` |
| `template_disjoint_only` | `val_seed1.jsonl` | 1 | val | 60 | 8 | 4 | `008c9da6817fd463a2898b4a0e44e410e5598eb62b662cf2e48c5172b7b50920` |
| `template_disjoint_only` | `train_seed2.jsonl` | 2 | train | 120 | 16 | 4 | `3ad49eea2a41ff0e0ffd516b0fb1b8dc5282dce9a8336d7f371bf28adc97bb11` |
| `template_disjoint_only` | `val_seed2.jsonl` | 2 | val | 60 | 8 | 5 | `0e7875a5e9fa78b4372ab942dfe9e4b813fc232e8418bbd017e173d12ab37257` |
| `fully_repaired` | `train_seed0.jsonl` | 0 | train | 120 | 16 | 0 | `9b03522746825f3fe0794c7f62ec7b1fb430f46734bb175b90a55a788d91e953` |
| `fully_repaired` | `val_seed0.jsonl` | 0 | val | 60 | 8 | 0 | `19e9839e4e27b584c53d30242411ab14a659ac5cc487849b205928f5caa3c595` |
| `fully_repaired` | `train_seed1.jsonl` | 1 | train | 120 | 16 | 0 | `024a69e9f35c777ad1030227eed37ef8f3dd43a82fb0a905a569e9150a37633f` |
| `fully_repaired` | `val_seed1.jsonl` | 1 | val | 60 | 8 | 0 | `b4f9587fc7e28a780b923c7e4a3e1aec96ddf6cde3c63a50fd0cc4b8423e7921` |
| `fully_repaired` | `train_seed2.jsonl` | 2 | train | 120 | 16 | 0 | `53258777ab214fb9226b85389673672c9c4b1b17c8cb9d07cf1a97beddcf3e6e` |
| `fully_repaired` | `val_seed2.jsonl` | 2 | val | 60 | 8 | 0 | `5633a8bf052f33c44ec694704baef64c96898a1548fc313abc2fb537a5e5b475` |

每文件的 template-family 全量列表、slice 计数、逐 seed 变更记录（removed_pair_ids / text_hash_changed / substitution_map / query_rewrites）见 `data/variants_v3/manifest.json`（逐文件字段 `template_families`、`slice_counts`、`changes`）。

## 4. 构成变化与版本差异审计

| 变体 | train 行数 (s0/s1/s2) | val 行数 (s0/s1/s2) | 族数 (train/val) | 构成变化判定 |
|---|---|---|---|---|
| `legacy_bundle` | 120/120/120 | 60/60/60 | 16/8 | 基线；无构成变化（保留全部已知缺陷） |
| `dedup_only` | 120/119/120 | 60/60/60 | 16/8 | s1 减 1 行（训练集内去重）；**构成变化 → 版本差异标记**；s0/s2 为 no-op |
| `degenerate_only` | 115/117/116 | 56/56/55 | 16/8 | 剔除退化对致行数变化；**构成变化 → 版本差异标记**；族集合未变 |
| `entity_disjoint_only` | 120/120/120 | 60/60/60 | 16/8 | 行数/族数不变；val 实体串替换 → **数据任务改变**（非纯标签修复） |
| `template_disjoint_only` | 120/120/120 | 60/60/60 | 16/8 | 行数/族数不变；val query 改写 → **数据任务改变** |
| `fully_repaired` | 120/120/120 | 60/60/60 | 16/8 | 行数/族数表面相同但全部样本由不同 commit/RNG 重生成 → **版本差异** |

逐变体质量审计说明：

- **`legacy_bundle`**：Baseline reference. Retains all known defects (degenerate must-flip rows, cross-split entity overlap, query-skeleton overlap, in-train duplicates).
- **`dedup_only`**：Declared explicitly as IN-TRAIN DEDUP (NOT train-val overlap cleanup). Seeds 0 and 2 had 0 in-train duplicates -> no-op (120 rows); seed 1 had 1 duplicate (train-F3-0062) -> 119 rows. This ≤1-row composition change is flagged; do not read as a pure matched-sample effect.
- **`degenerate_only`**：Must-flip degenerate pairs are a LABEL / TASK-VALIDITY defect. In the canonical pipeline these rows do NOT enter ridge supervised fitting; therefore NO causal effect on mapper fitting is claimed. Any effect on predictions must be recomputed by CPU replay on stored logits/per-pair scores; only a change to candidate text or input context would require extra GPU forward (declared separately as a data-task change). Row/composition changes are flagged as version differences: train 115/117/116, val 56/56/55.
- **`entity_disjoint_only`**：Row count 120/60 unchanged, family labels unchanged; 40/39/39 entity substitutions per seed; no old entity strings remain in val; correctness labels, must_flip flags and token counts preserved. Val text content changed -> Panel B would need a GPU forward (CPU replay on original logits is not valid for text changes). This is a declared data-task change, not label-only.
- **`template_disjoint_only`**：Row count 120/60 unchanged; 60 query rewrites per seed; only query text and derived sample_hash/sample_id changed; family labels, candidates, correctness and context preserved. Query input changed -> Panel B requires GPU forward; CPU replay on original logits is NOT valid. Data-task change.
- **`fully_repaired`**：Different commit (efc3ba3) and RNG stream than legacy -> VERSION DIFFERENCE (all rows re-generated, not a one-attribute A/B vs legacy). Use as the v2.1 endpoint anchor only.

## 5. 独立复核结果（CPU）

以 `data/audit_2x2` 原始导出为参照，对 36 文件逐项复核：

- 逐文件 SHA-256、字节数、行数、族集合、族数、slice 计数、退化行数与 manifest 记录**全部一致**；无 CR 字节、末尾 LF、规范 JSON-LF 序列化。
- 规则重算：legacy/fully_repaired 逐字节等于来源导出；dedup_only 等于「按 key 保留首次出现」的去重结果且 val 逐字节不变；degenerate_only 等于「剔除 must_flip∧candidate_A==candidate_B」结果；entity_disjoint_only / template_disjoint_only 的 train 逐字节等于 legacy、val 保留 pair_id 顺序与全部正确性/族标签。
- 实体互斥质量：val 中旧实体串残留 0；token_count_A/B 逐行未变；正确性标签与 must_flip 不变。
- 全部复核脚本：`data/variants_v3/verify_variants_v3.py`（CPU-only，可重跑）。

## 6. 边界与阻断项

- 本轮 GPU run = 0；模型推理 = 0；test 内容未读取用于评分、未产生任何预测；未写 `configs/**`、`papers/**`、`docs/decisions/**`、`reports/runs/**`、`src/**`、`experiments/**`。
- **阻断项（下游必须解决后才可进 G2/G3）：** 变体运行入口尚不存在——`experiments/audit_2x2_gpu.py` 只接受 legacy/fixed 两套 train/val，**不能直接执行单缺陷变体**；需工程师实现显式文件输入 + 版本哈希绑定入口，且不得调用自动重建数据的 `P1_gpu.py`。
- Panel B 中 `template_disjoint_only` / `entity_disjoint_only` 改变了输入文本，须走 GPU 前向，不能对原 logits 做 CPU replay；`degenerate_only` 的指标变化优先 CPU replay，因为退化对不进入 ridge 拟合。
- 由于多变体存在构成/族计数变化与不同 commit/RNG，**不得把本 6 条件筛查称为因果贡献分解或缺陷交互定量分解**（冻结判据 §3 interpretation）。

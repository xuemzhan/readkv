# S2 哈希一致性标注：stats_convention_v2.3.yaml 的版本过程

> 处理角色：数据工程师 · 日期：2026-11-23
> 依据：`docs/decisions/final_boundary_study_signoff.md` §2 S2
> 性质：溯源层标注，非改判据、非重跑实验。

## 1. 背景

`configs/prereg/stats_convention_v2.3.yaml` 是 PI 为消除 flip 分母口径冲突而新增的版本文件（冻结标识 `protocol-v2.3`），用于澄清：

- 主终点聚类单元 = `template_family`（附 pair-level 敏感性）；
- `flip_denominator_convention.excludes = [F5, F6]`。

数据重建后，flip 分母在干净数据上重算为 **398**。本数据工程角色当时无该文件写权限，只在 `data/tasks/manifest.json` 中登记了初版哈希，并在 `reports/data/data_fix_report.md` §4 记录"待 PI 回填"。此后 PI 完成回填并锁定。

## 2. 版本过程（两次均属同一冻结版本的内容补全）

| 阶段 | `recomputed_value` | sha256 | commit | 说明 |
|---|---|---|---|---|
| 初版（回填前） | `null` | `5200940c0ad466af000aab74689a6f1101d5c486e7358d2fdd3c87afd4776603` | 未提交（PI 工作区创建的未跟踪文件） | 数据工程当时登记到 manifest / acceptance_checks |
| 最终（回填后，现生效） | `398` | `e44c6acb79649ae55e4880696a00cb406636f5958f3d2053f7e1504c3d39bce0` | `6413ba0`（PI 锁定，该文件首次且唯一提交） | 现文件系统哈希，已核验一致 |

**两阶段同属冻结版本 `protocol-v2.3`**，差异仅为 `flip_denominator_convention.recomputed_value` 从 `null` 填为 `398`——这是对既有字段的**内容补全**（把数据侧实测值写入预留字段），不是改动判据、主终点定义、`τ`、聚类单元规则或统计门槛，也未回写 `configs/protocol.yaml` 或其它已冻结文件。commit `6413ba0` 已锁定最终内容。

## 3. 本次同步的文件与字段

| 文件 | 字段 | 处理 |
|---|---|---|
| `data/tasks/manifest.json` | `stats_convention.sha256` | 更新为 `e44c6acb…`（最终值） |
| `data/tasks/manifest.json` | `stats_convention.sha256_before_398_backfill` | 新增，保留旧值 `5200940c…` 作历史 |
| `data/tasks/manifest.json` | `stats_convention.locked_by_commit` / `version_process_note` | 新增，注明 `6413ba0` 与版本过程 |
| `data/tasks/manifest.json.sha256` | manifest 自身哈希 sidecar | 因 manifest 内容变更同步更新为 `874826e9…f8cc23a` |
| `reports/data/acceptance_checks.json` | `stats_convention_v2_3_sha256` | 更新为 `e44c6acb…`（最终值） |
| `reports/data/acceptance_checks.json` | `stats_convention_v2_3_sha256_before_398_backfill` / `stats_convention_hash_annotation` | 新增，保留旧值并注明版本过程 |
| `docs/data/data_card.md` | §1 统计口径引用、§6 flip 分母口径 | 同步为最终值并标注版本过程 |

## 4. 明确未变的内容

- `data/tasks/cf_pairs.jsonl` **未改**：sha256 仍为 `f910f1f1196a21041765834654af8233d216ef4bf4f28f4c60abbd0641aa894a`（manifest `files[0].sha256` 与 sidecar 无关，保持一致）。
- `configs/prereg/**`（含 v2.3）、`docs/protocol.md`、`reports/runs/**`、论文、代码：**未改**；未重跑任何实验。
- `manifest_stats_convention_sha_match` 仍为 `true`：因 manifest 与 acceptance_checks 的 v2.3 哈希均已同步为当前文件系统实际值 `e44c6acb…`。

## 5. 下游审计提示

- 旧值 `5200940c…` 仅作为历史记录保留在标注字段中，**不是**当前 v2.3 的哈希；任何一致性检查应以 `stats_convention.sha256` / `stats_convention_v2_3_sha256` 为准。
- `reports/data/acceptance_checks.json` 原由 `scripts/verify_data_fix.py` 生成；本次为 S2 溯源收尾手工加注历史字段。若日后重跑该脚本，它会用当前哈希 `e44c6acb…` 重写 `stats_convention_v2_3_sha256`（与 manifest 仍一致），但不会保留 `*_before_398_backfill` 历史字段，届时以本文件为准恢复标注。
- `manifest_stats_convention_sha_match` 在manifest v2.3 哈希同步后仍成立；验证方式：`sha256sum configs/prereg/stats_convention_v2.3.yaml` 与 manifest 字段比对。

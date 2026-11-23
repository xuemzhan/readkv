# 数据修复执行报告（M1–M5 / M7′，M4 计划）

- 执行角色：数据工程师 · 日期：2026-11-23
- 依据：`docs/decisions/data_readiness_ruling.md`、`configs/prereg/stats_convention_v2.3.yaml`（只读引用）
- 写入边界：仅 `data/**`、`src/readkv/data/**`、`scripts/**`、`reports/data/**`、`docs/data/**`
- **未改**：`configs/prereg/**`（含 v2.3）、`docs/protocol.md`、`reports/runs/**`、论文、其它 `src/**`

## 0. 执行摘要

| 任务 | 状态 | 关键结果 |
|---|---|---|
| M1 退化对归零 | ✅ 完成 | 强制候选相异 + must_flip 断言；退化对 18 → **0** |
| M2 跨 split 去重与实体隔离 | ✅ 完成 | 逐字重叠 ≥15 组 → **0**；实体池重叠 → **0** |
| M3 结构未见模板 | ✅ 完成 | 新增 16 个结构不同模板；基础结构 8 → **24**；train/test 骨架交集 → ∅ |
| M5 manifest/数据卡规范化 | ✅ 完成 | license/source/commit hash/配置指纹/分层报告 + `docs/data/data_card.md` + manifest 哈希 sidecar |
| M7′ 统计口径实现 | ✅ 完成 | 主聚类单元改 template_family + pair-level 敏感性；flip 排除 [F5,F6]，重算 **398** |
| M4 真实文档 | ⏸ 仅出计划 | `reports/data/real_doc_acquisition_plan.md`，需 PI/人工决策，未引入任何真实文档 |

数据已重建：`data/tasks/cf_pairs.jsonl` 新 sha256 = `f910f1f1196a21041765834654af8233d216ef4bf4f28f4c60abbd0641aa894a`（旧 `6058fd6d…d1887`），质量门 `pass`。独立验收 **11/11 项全通过**（`reports/data/acceptance_checks.json`）。

---

## 1. 逐项执行说明

### M1 退化对归零（✅）
- 文件：`src/readkv/data/build_cf_pairs.py`
- 改动：F1/F2/F3/F4/F6 的候选/被替换实体统一走 `_distinct`；F2 还强制团队相异、F4 强制干扰项与两候选相异；每个 `must_flip=true` 样本生成后断言 `candidate_A != candidate_B`、`correct_A != correct_B`、`context_A != context_B`。F5 保留相同候选（`must_flip=false`，非翻转负控）。
- 结果：全量 520 对中退化对 = **0**（旧 18 条，含 test 7 条）。

### M2 跨 split 去重与实体隔离（✅）
- 实体池按 split 不相交分配：姓名/项目/城市/日期/编号/角色/策略/团队 8 类，每 split 独占一段（团队带甲/乙/丙/丁/戊前缀）。
- 生成期以 `(context_A, context_B, query, edited_span)` 为全局签名做确定性重试，保证无重复。
- 结果：跨 split 逐字重叠 context_A/B/query/edited_span 全部为 **0**（旧 ≥15 组，含 `train-F3-0014 ≡ test-F3-0015` 整对泄漏）；实体与候选姓名跨 split 重叠 **0**（旧 8 姓名全共享）。

### M3 结构未见模板（✅）
- 新增 `UNSEEN_TEMPLATES` 16 个**句式结构不同**的模板（U-F1×3 / U-F2×3 / U-F3×3 / U-F4×3 / U-F5×2 / U-F6×2），专供 test/probe；原 8 个标记为 `SEEN_TEMPLATES`（S-*）供 train/val。
- 为使 "未见" 名副其实，所有 query 与 edited_span 均含 split 专属实体；train/test 的 context 与 query 骨架交集均为 ∅。
- 模板族：基础结构 8 → **24**（≥24 目标达成）；带变体后缀的总族数 **56**；`unseen_template_subset` = probe 16 + test 16 = **32 族**（结构 16），已写入 manifest.quality。

### M5 manifest/数据卡规范化（✅）
- `scripts/export_task_data.py` 重写：manifest 新增 `revision`、`generator_commit`、`config_fingerprint`、`stats_convention`（含 v2.3 sha256）、`license`（CC0-1.0）、`source`（synthetic/external_download=false）、`reproduce`、`length_mismatch` 分层、`flip_denominator_excludes`、全部隔离检查结果。
- 新增 `data/tasks/manifest.json.sha256`（manifest 自身哈希 sidecar）。
- 新增数据卡 `docs/data/data_card.md`：来源、生成方式、隔离证明、length_mismatch 分层、flip 分母口径、已知限制、复现命令。

### M7′ 统计口径实现（✅）
- `scripts/bootstrap_ci_report.py` 按 v2.3 改造：
  - 主 CI 一律以 **template_family** 为聚类单元（新增 `_fill_template_family` 从同文件其它 arm 按 pair_id 补齐缺失字段，旧产物无法补齐时显式标记 `cluster-fallback` 而非冒充合规）；
  - 每个终点同时输出 **pair-level 敏感性 CI**；
  - 模板族数 < 24 标记 `exploratory=true`；
  - 顶层 `flip_denominator` 块从重建后的 manifest 读取 excludes 与重算值，附说明 "PI 负责回填 v2.3"。
- 冒烟验证：旧 run 每 run 仅 8 个模板族 → `exploratory=true`，template-family CI 明显宽于 pair-level（例：`delta_lock_v2p1_0p5` new_joint E_CF 2.750 [1.413, 4.160] vs pair [2.084, 3.359]），符合 v2.3 对"不得只报较窄一套"的要求。
- **未回写** `configs/protocol.yaml` 或任何冻结文件；统计脚本默认输出路径保持原样（本次冒烟测试输出定向到 /tmp，未触碰 `reports/**` 既有产物）。

### M4 真实文档（⏸ 仅计划）
- 已写 `reports/data/real_doc_acquisition_plan.md`：候选来源类别（百科/公共领域/学术基准/内部语料）、逐项许可风险、人工核验 7 步流程、80—150 对采集量级与 5—10 人日估计、风险与待决策事项。
- **未抓取、未编造、未引入**任何真实文档；real split 仍为 0。

---

## 2. 重建前后关键指标对比

| 指标 | 重建前（v2.0） | 重建后（v2.1） |
|---|---|---|
| 数据 sha256 | `6058fd6d…d1887` | `f910f1f1…a894a` |
| 文件字节 / 行数 | 439734 / 520 | 455900 / 520 |
| split 规模 | probe40/train120/val60/test300 | 不变（满足 protocol.yaml） |
| 切片计数 | F1 130/F2 67/F3 130/F4 67/F5 63/F6 63 | F1 111/F2 90/F3 110/F4 87/F5 61/F6 61（M3 模板分布变化，如实记录） |
| 退化对（must_flip） | 18（test 7） | **0** |
| 跨 split 逐字重叠 | ≥15 组（含 train↔test 整对泄漏） | **0** |
| 实体跨 split 重叠 | 8 姓名全共享 | **0**（8 类实体全隔离） |
| 模板基础结构数 | 8（F1 与 F5 骨架还重复） | **24** |
| template_family 族数 | probe8/train16/val8/test8（共 40） | probe16/train16/val8/test16（共 56） |
| unseen 子集 | 仅后缀 D，无结构未见 | **32 族 / 16 结构真正未见** |
| train/test 模板骨架 | 100% 重合 | **∅** |
| length_mismatch | 39（全 F5） | 61（全 F5，probe4/train14/val7/test36） |
| F5 负控数 | 63 | 61 |
| flip 分母（排除 F5+F6） | 394（含 18 退化对） | **398**（干净数据重算） |
| quality_gate | pass（但门禁未检查泄漏/退化） | pass（门禁新增 6 项正确性检查） |
| manifest 溯源字段 | 无 license/source/commit hash | 全部具备 + 哈希 sidecar |

> 说明：flip 分母由 394 变为 398，并非"修复使分母变大"，而是 M3 引入 16 个新模板后切片分布变化（F1—F4 合计 398）所致；仅做 M1 修复时 394−18=376。两种效应已在数据卡 §6 中说明。

## 3. 验收检查结果（独立复核）

`scripts/verify_data_fix.py` 直接从文件重算（不复用质量门判定逻辑），结果写入 `reports/data/acceptance_checks.json`，11 项全通过：

- manifest sha256 / size / lines 与文件一致 ✅
- split 规模 = protocol.yaml ✅
- 跨 split 逐字重叠（context_A/B/query/edited_span）= 0 ✅
- 退化对 = 0 ✅
- 模板骨架 train∩test（context 与 query）= ∅ ✅
- 候选实体跨 split 重叠 = 0 ✅
- 重算 flip 分母 = manifest 值 = 398 ✅
- seed=0 重建字节一致 ✅
- v2.3 sha256 与 manifest 记录一致（冻结文件未改）✅
- 既有测试套件 `pytest tests/ -q` 全部通过（53 passed，无回归）✅

## 4. flip 分母重算值（供 PI 回填）

- **recomputed flip denominator = 398**（F1 111 + F2 90 + F3 110 + F4 87）
- 口径：`excludes = [F5, F6]`（`stats_convention_v2.3.yaml`）
- 待 PI 动作：把 `398` 写入 `configs/prereg/stats_convention_v2.3.yaml` 的 `flip_denominator_convention.recomputed_value`（当前 null）。本角色无该文件写权限，**未修改**。

## 5. 需 PI / 人工决策事项

1. 将 flip 分母 `398` 回填 v2.3 版本文件（§4）。
2. 数据已变 → 旧 run 溯源过期：按裁决 §3.4 在干净数据上重跑 P1（≥3 seed）、P2（三 seed），E0 快速复验；是否重启 P3 由 PI 决定。本角色未触碰 `reports/runs/**`。
3. M4 真实文档（5—10 人日）是否投入、来源与许可类型，见 `reports/data/real_doc_acquisition_plan.md` §6。
4. 模板族数已达 24，bootstrap 主终点可脱离 `exploratory` 标记；但旧 run 自身只有 8 族，重跑前其统计结论仍须按探索性措辞。
5. 数据卡 `docs/data/data_card.md` 的 known limitations 需在正文/notes 同步披露（合成域、real=0、单 MVP 对、F5 长度分层、修复前后口径）。

## 6. 交付物清单

- 代码：`src/readkv/data/build_cf_pairs.py`、`scripts/export_task_data.py`、`scripts/bootstrap_ci_report.py`、`scripts/verify_data_fix.py`
- 数据：`data/tasks/cf_pairs.jsonl`、`data/tasks/manifest.json`、`data/tasks/manifest.json.sha256`
- 文档：`docs/data/data_card.md`、`reports/data/data_fix_report.md`、`reports/data/real_doc_acquisition_plan.md`、`reports/data/acceptance_checks.json`、`reports/data/data_readiness_audit.md`（前次审计）

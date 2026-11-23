# 数据卡：cf_pairs_v2.1（反事实文档对数据集）

> 版本：v2.1-corrected（M1/M2/M3 修复版） · 生成日期：2026-11-23 · 状态：可复现、质量门通过
> 对应文件：`data/tasks/cf_pairs.jsonl`、`data/tasks/manifest.json`、`data/tasks/manifest.json.sha256`

## 1. 数据集身份

| 项 | 值 |
|---|---|
| 名称 | `cf_pairs_v2.1` |
| 规模 | 520 对（probe 40 / train 120 / val 60 / test 300 / real 0） |
| 切片 | F1 111 / F2 90 / F3 110 / F4 87 / F5 61 / F6 61 |
| schema | 29 字段（pair_id, split, template_family, source_doc_id, context_A/B, query, candidate_A/B, correct_A/B, edited_span, token_count_A/B, position_gap, model_pair, ..., slice_id, cluster, swap_candidates, must_flip, length_matched, token_count_A/B） |
| 数据文件 sha256 | `f910f1f1196a21041765834654af8233d216ef4bf4f28f4c60abbd0641aa894a` |
| 行数 / 字节 | 520 / 455900 |
| 生成种子 | 0 |
| 生成器 | `src/readkv/data/build_cf_pairs.py::build_cf_pairs` |
| 导出脚本 | `scripts/export_task_data.py` |
| 生成时 git HEAD | `ee74382c0eac6fde5e7cd0af6db28ffc819c97d5` |
| 协议配置指纹 | `a6bc08cc997ac17a`（`configs/protocol.yaml` sha256 前 16 位） |
| 统计口径引用 | `configs/prereg/stats_convention_v2.3.yaml`（只读；最终 sha256 `e44c6acb…c3d39bce0`，commit `6413ba0`；回填前 `5200940c…4776603`） |

复现命令：`python scripts/export_task_data.py --seed 0`（seed=0 时逐字节重建，见 §6）。

## 2. 数据来源与许可

- **来源类型**：合成（synthetic）。全部文本由本项目模板与自建实体池生成。
- **外部下载**：无。未使用 HellaSwag / ARC / SQuAD 或任何第三方语料、个人数据或受限内容。
- **许可**：`CC0-1.0`（本项目自生成合成数据，无第三方内容需授权）。
- **real split**：空（0 对）。真实文档采集计划见 `reports/data/real_doc_acquisition_plan.md`，属需 PI/人工决策事项，未执行。

## 3. 生成方式

1. **模板分组（M3）**：8 个已见模板 `S-*`（train/val） + 16 个**句式结构不同**的未见模板 `U-*`（test/probe）；基础结构共 24 个、带 split 变体后缀后共 56 个模板族。未见子集：test 16 族 + probe 16 族。
2. **实体池隔离（M2）**：姓名/项目/城市/日期/编号/角色/团队/策略八类实体池按 split 不相交分配（probe=甲/train=乙/val=丙/test=丁/real=戊 前缀），跨 split 实体重叠 = 0。
3. **候选相异（M1）**：F1—F4/F6 强制 `candidate_A != candidate_B`；对每个 `must_flip=true` 样本断言候选不同、答案位不同、两文档不同。F5 的相同候选是非翻转负控的设计使然（`must_flip=false`），保留。
4. **去重**：生成期以 `(context_A, context_B, query, edited_span)` 为全局签名做确定性重试，保证无重复签名。
5. **位置偏差控制**：候选 A/B 顺序按 seed 随机交换并记录 `swap_candidates`。

## 4. split 隔离证明（独立验收）

来源：`reports/data/acceptance_checks.json`（`scripts/verify_data_fix.py` 独立重算）。

| 检查 | 结果 |
|---|---|
| 跨 split 逐字重叠（context_A / context_B / query / edited_span） | 0 / 0 / 0 / 0 |
| 实体池跨 split 重叠（8 类） | 全 0 |
| 候选姓名跨 split 重叠 | 0 |
| `template_overlap_train_eval` | `[]` |
| 模板骨架 train ∩ test（context） | ∅ |
| 模板骨架 train ∩ test（query） | ∅ |
| 退化对（`must_flip=true` 且候选/文档/答案位相同） | 0 |
| seed=0 重建字节一致 | 是 |

## 5. length_mismatch 分层

length_mismatch 共 **61** 对，**全部落在 F5**（表层同义改写替换了不同字数的角色词）。F5 为非翻转负控、不计入 flip 分母，因此长度差异不污染主翻转指标；仍单独分层报告。

| split | F5 长度不匹配数 |
|---|---|
| probe | 4 |
| train | 14 |
| val | 7 |
| test | 36 |
| 合计 | 61 |

每个 split 的 6 个角色词长度互不相同（2—7 字），同义改写必然产生 token 长度差，`position_gap > 0` 被显式记录。

## 6. flip 分母口径（M7′）

- 口径来源：`configs/prereg/stats_convention_v2.3.yaml`（`flip_denominator_convention.excludes = [F5, F6]`）。
- 语义：F5 = 非翻转负控；F6 = 长度/位置控制，语义上答案不应翻转。两者均不计入“必须翻转”分母。
- **重建后重算值：398**（F1 111 + F2 90 + F3 110 + F4 87 = 398）。
- 对照：旧数据口径 394（排除 F5+F6 但含 18 条退化对）；冻结配置字面口径 457（仅排除 F5）。修复退化对并引入 M3 模板后，切片分布变化，最终为 398。
- **v2.3 版本过程（S2 已闭环）**：初版 `recomputed_value=null`（sha `5200940c…`）→ PI 回填 `398` 并以 commit `6413ba0` 锁定最终内容（sha `e44c6acb…`）。两次均属同一冻结版本 `protocol-v2.3` 的内容补全，非改判据。`manifest.json` 与 `acceptance_checks.json` 中的 v2.3 哈希已同步为最终值并保留回填前值作历史；详见 `reports/data/s2_hash_annotation.md`。

## 7. 已知限制

1. 合成域数据；模板多样性有限（24 个基础结构），虽 test/probe 有结构未见模板，仍不能代表真实世界分布。
2. `real=0`，无外部基准锚点；外部效度缺口需作为 limitation 披露。
3. F5 长度不匹配 61 对，须分层报告（见 §5）。
4. 实体为 8 个姓名/项目等的有限池（每 split 8 个），语义覆盖面窄。
5. 旧 run（`reports/runs/**`）基于 v2.0 数据，其溯源已过期，须由 PI 决定是否重跑；本角色未改动这些产物。
6. 统计聚类口径已按 v2.3 改为 template_family 主 + pair-level 敏感性；对旧数据（每 run 仅 8 个模板族）bootstrap 汇总会标记 `exploratory=true`。

## 8. 质量门

`manifest.json::quality.quality_gate = "pass"`。门禁条件：总数>0、train/eval 模板族无重叠、train/test 模板与 query 骨架无重叠、退化对=0、跨 split 逐字重叠=0、实体池重叠=0。

## 9. M4 真实文档状态（2026-11-23，阻塞中）

- 本数据卡当前**仅描述合成 `cf_pairs_v2.1`**。`real` split **尚未生成、不可用**（PI 二次签off前不得标记可用）。
- PI 已签署第一阶段合规签off（来源 A/B/C 授权抓取核验、D 不入库、E/F/G 仅评测）；锚点许可核验见 `reports/data/anchor_license_check.md`（SQuAD/ARC=CC BY-SA 4.0，HellaSwag=MIT，评测用途合规）。
- 抓取阶段阻塞：授权文档源（census/bls/wikidata/wikipedia）在本环境返回 403/超时，未取得任何原始文件字节，故无法完成五项登记中的「原始文件 sha256」；人工双人校验/第三人抽检资源未落实。**不伪造来源/哈希/人工抽检记录**，因此未生成 `cf_pairs_real.jsonl`、未更新 manifest 的 real 条目。
- 详见 `reports/data/m4_fetch_attempt_log.md` 与 `reports/data/m4_acceptance_checklist.md`（0/7 通过，未申请二次签off）。待 PI 解决出网通道与人工标注资源后再继续。


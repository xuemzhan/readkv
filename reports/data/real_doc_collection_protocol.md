# M4 真实文档采集 SOP（80–150 对，独立 real split）

> 执行角色：数据工程师 · 日期：2026-11-23
> 依据：`docs/decisions/human_decisions.md`、`docs/decisions/m4_anchor_execution_plan.md` §1.3/§4.2、`docs/protocol.md` §4.3/§9、`reports/data/m4_source_license_assessment.md`
> 状态：**SOP 草案，尚未执行**。本轮未抓取、未入库任何真实文档；不修改 `data/tasks/cf_pairs.jsonl` 或 manifest，不写代码，不改 `configs/prereg/**`，不跑实验。
> 前置门槛：PI 合规签off（来源与待决项，见许可预评估 §6）+ PI 新增 `configs/prereg/external_validity_v2.4.yaml` 冻结（先冻后跑）**之前**，不得执行本 SOP 中任何抓取/入库动作，不得启动 real/锚点 run。

---

## 1. 范围与隔离不变量

- **规模**：80–150 对，目标 **100 对**（留 ≥20% 抽检返工余量）。
- **独立文件与 split**：真实文档写入 `data/tasks/cf_pairs_real.jsonl` 或等价文件，`split="real"`；与合成 probe/train/val/test **完全物理隔离**。
- **绝不污染封存**：real 文档不得并入合成 test，不得参与任何已冻结主终点、bootstrap CI 或 flip 分母口径；v2.3 的 `[F5,F6]` 排除与 `template_family` 聚类仅对合成数据生效，real 由 v2.4 定义。
- **不恢复贡献**：real/锚点仅作外部效度观察，按 PI 执行计划 §3 预承诺，不得据此恢复贡献(1)(2)(3) 状态或改论文定位。

---

## 2. 端到端流程（七步）

### 步骤 0：前置检查（Gate 0）
- 确认 PI 已对许可预评估 §6 的来源清单与待决项签off；
- 确认 v2.4 版本文件已冻结；
- 确认本 SOP 依赖的字段与 schema 已与工程师对齐（real schema = 合成 schema + 来源/许可/标注扩展字段）。
- **未过 Gate 0 → 停止，不得抓取。**

### 步骤 1：来源登记（五项登记齐全方可继续）
对每份来源文档建立登记条目（字段定义见许可预评估 §4）：
- `source_id`、`source_url`（永久链接/oldid）、`source_title`、`publisher`；
- `version`、`source_date`、`retrieval_date`；
- `license_id`、`license_url`、`license_text_sha256`（许可原文快照哈希）；
- `raw_file_sha256`（下载原文件字节哈希）、`processing_commit`；
- `attribution_record`（署名文本）、`pi_signoff_ref`。
- 许可原文与原始文件**先落盘再算哈希**；许可不属白名单或登记不全 → 整批剔除（不凑数）。

### 步骤 2：事实抽取
- 从原文抽取可核验事实句（实体 / 关系 / 时间 / 数值），逐条保留 `fact_span` 原文与出处定位；
- 优先覆盖 F1（直接事实替换）、F3（关系方向）、F6（长度/位置）等结构；F5（表层等价）与 F6 按语义标注，遵循 v2.3 的 flip 排除口径；
- 含未脱敏个人数据的句子一律剔除（待决项 5 建议"剔除"）。
- 抽取产出的每条事实登记其 `source_doc_id`（同一原文的所有事实共享该 ID，供分组隔离）。

### 步骤 3：反事实编辑
- 按 F1—F6 编辑类型构造 `d_A`/`d_B`：仅关键事实位点不同，逻辑一致（`d_A` 答 a、`d_B` 答 b），候选互斥；
- **复用 M1 退化对断言**：对每个 `must_flip=true` 样本断言 `candidate_A != candidate_B`、`correct_A != correct_B`、`context_A != context_B`；F5 相同候选 + `must_flip=false` 为设计使然；
- 候选顺序随机交换并记录 `swap_candidates`；
- 编辑类型记入 `edit_type` 与 `edited_span`，编辑脚本 commit 记入 `processing_commit`。

### 步骤 4：双人标签校验
- 两名标注者**独立**核对：候选互斥性、答案正确性、`must_flip` 语义（F5 非翻转、F6 条件扰动）、事实一致性、是否有无意的第二处改动；
- 两人一致 → `label_check_pass=true`；不一致 → 交科学家裁定或剔除；
- 记录 `annotator_A`、`annotator_B`、`label_check_note`、`label_check_date`。

### 步骤 5：≥20% 人工抽检
- 按来源文档/主题簇**分层抽取 ≥20%** 样本，由第三人（抽检员）复核事实抽取与编辑正确性；
- 记录 `sampling_reviewer`、`sampling_result`、`sampling_date`、`sampling_note`；
- 抽检未通过：该来源簇返工；两次未通过 → 整簇剔除。100 对目标下抽检 ≥20 对，留返工余量。

### 步骤 6：泄漏与隔离检查
- **分组隔离**：以 `source_doc_id`（同一原文）为最小不可分簇；同一原文的所有派生对必须落在同一 real 内部子集，禁止跨子集；
- **主题簇隔离**：对来源主题/实体域打 `real_topic_cluster`，同一主题簇不跨 real 内部评测子集（供 v2.4 聚类口径）；
- 检查项（全部须为 0）：同一 `fact_span` 跨子集、同一 `source_doc_id` 跨子集、同一原文 `raw_file_sha256` 重复、候选实体跨子集泄漏；
- 合成 test 与 real 之间不得有任何共享 source_doc / 原文哈希 / 逐字 context。

### 步骤 7：入库
- 写入 `data/tasks/cf_pairs_real.jsonl`，仅 `split="real"`；
- 更新 manifest：新增 real 的 sizes / by_slice / 文件 sha256 / 来源与许可汇总（**不改合成 cf_pairs.jsonl 的哈希与任何冻结字段**）；
- 更新数据卡 `docs/data/`：真实来源清单、许可义务、五项登记摘要、隔离证明、抽检结论；
- **PI 合规签off 后方可进入主实验**（Gate 7）。

---

## 3. real schema（合成字段 + 扩展字段）

沿用 `CFPair.as_record()` 的合成字段（`pair_id`, `split`, `slice_id`, `template_family`/`real` 标记, `source_doc_id`, `context_A/B`, `query`, `candidate_A/B`, `correct_A/B`, `edited_span`, `token_count_A/B`, `position_gap`, `must_flip`, `length_matched`, `swap_candidates`, `seed` 等），并新增：

| 字段组 | 字段 | 说明 |
|---|---|---|
| 来源 | `source_id`, `source_url`, `source_title`, `publisher`, `fact_span` | 来源标识与原文事实定位 |
| 版本/日期 | `version`, `source_date`, `retrieval_date` | 固定来源版本 |
| 许可 | `license_id`, `license_url`, `license_text_sha256`, `attribution_record`, `pi_signoff_ref` | 许可与署名登记 |
| 溯源 | `raw_file_sha256`, `processing_commit` | 五项登记中的哈希与脚本 commit |
| 编辑 | `edit_type`, `edited_span` | 反事实编辑类型 |
| 标注 | `annotator_A`, `annotator_B`, `label_check_pass`, `label_check_note`, `label_check_date` | 双人校验痕迹 |
| 抽检 | `sampling_reviewer`, `sampling_result`, `sampling_date`, `sampling_note` | ≥20% 抽检痕迹 |
| 隔离 | `real_topic_cluster`, `real_source_hash` | 供 v2.4 按来源文档/主题簇聚类 |

说明：真实文档"模板族"概念不适用（PI 执行计划 §4.2）——主聚类单元由 v2.4 冻结为 `source_doc_id` / `real_topic_cluster`；`template_family` 在 real 中仅记为来源类别/编辑类型标记，**不参与合成域的模板隔离检查**。

---

## 4. 分组隔离与 v2.4 聚类口径衔接

- **不可分簇**：`source_doc_id`（同一原文）与 `real_topic_cluster`（同主题/实体域）为两级隔离单位；
- **real 内部子集**：若 real 未来划分评测子集，按簇整体分配（GroupSplit），禁止簇内样本跨子集；
- **聚类 bootstrap**：real 臂按 `source_doc_id` / `real_topic_cluster` 聚类（v2.4 冻结具体定义），附 pair-level 敏感性，簇数 <24 标 `exploratory=true`（沿用 v2.3 原则）；
- **flip 分母**：按 real 实际切片重算（v2.4 明确），不套用合成数据的 398。

---

## 5. 验收清单（入库前全部满足）

| # | 条件 | 检查方式 |
|---|---|---|
| 1 | 80–150 对（目标 100），独立 `real` split | 行数与 split 统计 |
| 2 | 每对来源五项登记齐全、许可属白名单、无个人数据 | 逐条字段检查 |
| 3 | `must_flip` 语义正确、候选相异（F5 除外）、F5/F6 标注正确 | 复用 M1 断言脚本逻辑（**本轮不写码**） |
| 4 | 双人标签校验 + ≥20% 抽检通过并留痕 | 标注字段完整性 |
| 5 | 泄漏/隔离检查全 0（来源/主题簇/实体/原文哈希） | 分组重叠扫描 |
| 6 | manifest 和数据卡已更新（real sizes/by_slice/hash/来源许可） | 文件差异检查 |
| 7 | **PI 合规签off** | 签off记录引用（无则禁止入库） |

---

## 6. 本轮明确不做的事

- 不抓取、不下载、不入库任何真实文档；
- 不修改 `data/tasks/cf_pairs.jsonl`、`data/tasks/manifest.json` 及其哈希；
- 不写代码（含采集/编辑/校验脚本）；
- 不改 `configs/prereg/**`（PI 正在起草 v2.4）、`docs/protocol.md`；
- 不启动任何 GPU run（real/锚点均不跑）；
- 不改写或再发布任何学术基准语料（锚点仅限按各自 license 评测）。

---

## 7. 下一步（依赖链）

1. PI 签off `reports/data/m4_source_license_assessment.md` §6 来源清单与待决项（尤其 CC BY-SA 的 SA 义务）；
2. PI 冻结 `configs/prereg/external_validity_v2.4.yaml`（real/锚点口径、聚类定义、预承诺）；
3. 获双重授权后，按本 SOP 步骤 1—2 抓取与抽取，建立五项登记；
4. 步骤 3—6 构造与质检；
5. 步骤 7 入库 + PI 合规签off；
6. 此后才由工程师启动 real/锚点评测 run（另案）。

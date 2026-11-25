# M4 入库申请验收清单（SOP §5 七项）—— 未通过，申请二次签off暂缓

> 执行角色：数据工程师 · 日期：2026-11-23
> 依据：`reports/data/real_doc_collection_protocol.md` §5、`docs/decisions/m4_compliance_signoff.md` §3/§4
> 结论：**七项验收均未满足，不申请入库二次签off**；real split 未写入、未标记可用、未启动 real/锚点 run。

## 1. SOP §5 七项验收逐项状态

| # | 验收条件 | 状态 | 证据 / 阻塞原因 |
|---|---|---|---|
| 1 | 80–150 对（目标 100），独立 `real` split | ❌ **未满足** | 未生成任何 real 对；`data/tasks/` 下无 `cf_pairs_real.jsonl`。原因见 `m4_fetch_attempt_log.md`：A/B/C 原始文件全部 403/超时，无字节流可抽取事实。 |
| 2 | 每对来源五项登记齐全、许可白名单、无个人数据 | ❌ **未满足** | 五项登记第③（许可原文快照）④（原始文件 sha256）无法完成——未下载到原始文件。无登记条目，故 `pi_signoff_ref` 全空，按红线不得入库。 |
| 3 | `must_flip` 语义正确、候选相异（F5 除外）、F5/F6 标注正确 | ⚠️ **无对象可检** | 未构造任何对，无法执行 M1 断言。校验逻辑就绪（cf_pairs_real 若生成将复用），但当前无数据。 |
| 4 | 双人标签校验 + ≥20% 抽检通过并留痕 | ❌ **未满足** | 本执行体为单一自动化 agent，无第二名独立标注者与第三人抽检；不能编造 `annotator_A/annotator_B/sampling_reviewer` 留痕（硬约束：不伪造人工抽检记录）。 |
| 5 | 泄漏/隔离检查全 0（来源/主题簇/实体/原文哈希） | ⚠️ **无对象可检** | 无 real 数据，隔离检查（`source_doc_id` / `real_topic_cluster` 两级 GroupSplit、与合成 test 零重叠）待 real 数据存在后执行。 |
| 6 | manifest 和数据卡已更新（real sizes/by_slice/hash/来源许可） | ❌ **未执行** | 因数据未入库，刻意不更新 manifest 的 real 条目（避免把不可用数据标记为正式）。数据卡可追加“M4 进行中/阻塞”状态说明。 |
| 7 | **PI 合规签off（二次签off）** | ⏸ **未申请** | 本清单为申请前自检；因 1–6 未过，**不提交入库签off申请**。 |

**总判定：0/7 通过（3 项无对象可检、4 项明确未满足）。不得入库、不得标记可用、不得启动 real/锚点 run。**

## 2. 已诚实完成的部分（与阻塞项区分）

| 交付物 | 状态 |
|---|---|
| `reports/data/m4_source_license_assessment.md`（来源筛选与许可预评估） | ✅ 完成（PI 已据此签off） |
| `reports/data/real_doc_collection_protocol.md`（采集 SOP） | ✅ 完成 |
| `configs/prereg/external_validity_v2.4.yaml`（由 PI 冻结，非本角色） | ✅ 已冻结（签off依据） |
| `reports/data/anchor_license_check.md`（E/F/G 许可核验） | ✅ 完成：SQuAD=CC BY-SA 4.0、ARC=CC BY-SA 4.0、HellaSwag=MIT，评测用途合规 |
| `reports/data/m4_fetch_attempt_log.md`（A/B/C/D 抓取真实日志） | ✅ 完成：全部失败，无原始文件字节 |
| `cf_pairs_real.jsonl` / manifest real 条目 | ❌ 未生成（诚实：无真实源则不应生成） |

## 3. 需 PI 裁决的阻塞项（升级）

1. **出网/抓取通道**：本执行环境对 census.gov、api/www2.bls.gov、download.bls.gov、wikidata.org、wikipedia.org、raw.githubusercontent.com 均返回 403/超时；B（.gov.cn）无可用出网。请 PI 提供可用通道（如受控下载代理、预先下载并校验的原始文件、或具备出网的执行节点），否则 A/B/C 采集无法进行。
2. **人工标注资源**：PI 签off §3 要求“两名标注者独立核对”+“第三人 ≥20% 抽检”。本角色无人工标注者。请 PI 明确：(a) 提供人工标注资源/外包，或 (b) 以新版判据文件授权“自动化双重校验 + 自动化分层抽检”替代人工留痕（需新版本文件，不得回写冻结判据）。在明确前，不得伪造人工留痕。
3. **Census 使用条款冲突（重要合规发现）**：Census 官方页明确 “You may not modify or falsely represent content accessed through the API and still claim the source is the Census Bureau”（来源：census.gov 开发者 ToS，web 抓取原文）。反事实编辑（改写事实位点）与“不得修改内容仍称来源为 Census”存在张力。建议按 PI 待决②“仅允许引用不等于允许改写发布”从严处理：将 Census API/数据内容判为**仅可引用、不用于改写为 real 文档**，real 源以 Wikidata（CC0）为主，政府源仅取明确允许改写/再分发者。请 PI 确认。
4. **D（Wikipedia 正文）**：PI 已裁定不入库；本轮抓取核验也失败（ECONNRESET/超时），无入库动作，符合裁定。

## 4. 下一步（待 PI 裁决后）

- 获得可用抓取通道 → 按 SOP 步骤 1–2 对 A/B/C 逐份完成五项登记（含真实 sha256）→ 步骤 3–6 构造/校验/抽检/隔离 → 回填本清单 → 提交二次签off申请。
- 获得人工/自动化替代授权 → 完成步骤 4 留痕。
- 上述全部满足前，real split 保持不存在/不可用状态，锚点 run 亦不启动。

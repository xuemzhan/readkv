# M4 A/B/C/D 抓取与五项登记尝试日志（真实失败记录）

> 执行角色：数据工程师 · 日期：2026-11-23
> 依据：`docs/decisions/m4_compliance_signoff.md` §1（A/B/C 授权抓取核验、D 条件授权、E/F/G 评测授权）、§3 入库红线
> 性质：对**实际发生的**抓取尝试与结果的可审计记录。所有 URL 与返回状态均为本轮真实观测；**未获得任何可下载的原始文件字节，因此未产生任何 raw_file_sha256**。

## 1. 红线复述

- 五项登记：①来源 URL/标识 ②版本/日期 ③许可原文 ④**原始文件 sha256** ⑤处理脚本 commit。
- `pi_signoff_ref` 为空的条目一律不得入库；许可不清整批剔除；个人信息句子统一剔除。
- **二次签off前**：real 数据不得标记为可用/正式入库，不得启动 real/锚点 run。

## 2. 实际抓取尝试与结果（逐条真实）

| # | 来源类别 | 授权 | 尝试 URL | 方法 | 结果（真实） |
|---|---|---|---|---|---|
| 1 | A 美国联邦政府 | ✅ | `https://www.census.gov/about/policies/privacy.html` | GET/text | **403** |
| 2 | A 美国联邦政府 | ✅ | `https://www.census.gov/quickfacts/fact/table/California/PST045224` | GET/html | **403** |
| 3 | A 美国联邦政府 | ✅ | `https://api.census.gov/data/2020/dec/pl?get=NAME,P1_001N&for=state:06` | GET/text | **403** |
| 4 | A 美国联邦政府 | ✅ | `https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/state/totals/NST-EST2024-ALLDATA.csv` | GET/text | **403** |
| 5 | A 美国联邦政府 | ✅ | `https://download.bls.gov/pub/time.series/cu/cu.data.1.AllItems` | GET/text | **403** |
| 6 | A 美国联邦政府 | ✅ | `https://www.bls.gov/news.release/cpi.nr0.htm` | GET/text | **403** |
| 7 | A 美国联邦政府 | ✅ | `https://catalog.data.gov/api/3/action/package_search?q=population&rows=1` | GET/text | **404** |
| 8 | A 美国联邦政府 | ✅ | `https://www.data.gov/` | GET/text | **成功**（仅门户导航页，无可哈希的原始事实文件） |
| 9 | C Wikidata（CC0） | ✅ | `https://www.wikidata.org/w/api.php?action=wbgetentities&ids=Q64&...` | GET/text | **超时** |
| 10 | C Wikidata（CC0） | ✅ | `https://www.wikidata.org/wiki/Special:EntityData/Q64.json` | GET/text | **超时** |
| 11 | D Wikipedia（不入库） | ⚠️ | `https://en.wikipedia.org/w/api.php?action=query&prop=revisions&titles=Berlin&...` | GET/text | **ECONNRESET** |
| 12 | D Wikipedia（不入库） | ⚠️ | `https://en.wikipedia.org/api/rest_v1/page/summary/Berlin` | GET/text | **超时** |
| 13 | —（探测器） | — | `https://dbpedia.org/data/Berlin.json` | GET/text | **超时** |
| 14 | —（探测器） | — | `https://raw.githubusercontent.com/rajpurkar/SQuAD-explorer/master/README.md` | GET/text | **Transport error** |
| 15 | B 中国政府/统计 | ✅ | （本环境对中国 .gov.cn 域无可用出网；未取得任何可下载原始文件字节） | — | **未获取到原始文件** |

补充说明：web **搜索**接口可返回页面摘要文本（如 census 许可政策、data.gov、NASA、HF dataset card 的文本片段），但**搜索引擎返回的摘要不是原始文件字节流**，无法作为 `raw_file_sha256` 的哈希对象；本日志中的成功项（#8）仅为门户导航页，**不含可核验的事实段落**，不能作为 real 文档来源。

## 3. 由此产生的硬约束

1. **无法完成五项登记的第④项**：本轮未下载到任何 A/B/C 原始文件字节 → 无法计算真实 `raw_file_sha256`。任何“伪造一个看起来合理的哈希”都违反硬约束（不伪造哈希）。
2. **无法完成第③项的原文快照**：仅拿到搜索摘要/政策页文本，未固定具体事实文档的许可原文与版本。
3. **无法执行双人校验与 ≥20% 人工抽检**：本 agent 为单一自动化执行体，无第二名独立标注者、无第三人抽检；若编造 `annotator_A/annotator_B/sampling_reviewer` 留痕，即为“伪造人工抽检记录”，违反硬约束。
4. **个人信息剔除**：尚无实际文档，剔除计数为 0（无从剔除），不能凭空记录剔除数。

## 4. 结论

- A/B/C/D **均未取得可入库的真实原始文件**；五项登记链条在第③④项即中断。
- 依 PI 红线（“五项登记齐全 + 双人校验 + ≥20% 抽检 + 二次签off，缺一不得入库”）与我在角色硬约束（不伪造来源/许可/哈希/人工抽检），**本轮不生成 `cf_pairs_real.jsonl`，不写入 real split，不更新 manifest 的 real 条目**。
- 已完成的、可诚实交付的部分：E/F/G 锚点许可核验（`anchor_license_check.md`）、SOP（既有）、来源筛选与许可预评估（既有）、本抓取日志、验收清单（诚实标注阻塞）。
- 需 PI 裁决：见 `m4_acceptance_checklist.md` 与最终报告“需 PI 决策事项”。

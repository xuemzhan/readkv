# ModelScope real 候选源探查报告（仅探查，不入库）

> 执行角色：数据工程师 · 日期：2026-11-23
> 依据：`docs/decisions/m4_blocker_ruling.md` §1/§3（授权探查 ModelScope 可合法改写事实文本作 real 候选；探查≠入库）、§4（白名单：公共领域/CC0/CC BY；排除 SA/仅研究/ToS 冲突）
> 性质：**探查与许可核验**。未批量下载、未入库、未生成 `cf_pairs_real.jsonl`、无人工作留痕字段。

## 0. 探查方式

- ModelScope SDK 1.40.3（`HubApi.list_repos(repo_type='dataset', search=...)`, `get_dataset_detail`, `get_dataset_files`）。
- 对候选逐一读取 `license` 元数据 + README/LICENSE 原文（仅取小文本文件，未取数据主体），用 `sha256sum` 等价方式对实际字节算哈希。
- 关键词：cc0 / public domain / wikipedia / 事实 / 百科 / trivia / baike。

## 1. 候选清单与许可核验

| 数据集 ID | 元数据 license | 原文/描述证据 | 事实文本适配 | 白名单判定 |
|---|---|---|---|---|
| `rootsautomation/SciTSR-pd` | `cc0-1.0` | README 原文：“A public-domain subset of SciTSR … only tables whose source papers carry a **CC0 or equivalent public domain dedication** — no attribution required, no restrictions on commercial or derivative use”；列 `paper_license`。README 实字节 4,136 B，sha256 `6f3f867a…40da0650` | 中（科学**表格**结构，非连续事实句；需评估能否支撑 F1/F3/F6） | ✅ **白名单内（CC0/公共领域，可改写再分发）** —— 当前最合规候选 |
| `common-pile/public_domain_review` | `Apache License 2.0`（打包层） | README 原文：“We collect all articles published in the Public Domain Review under a **CC BY-SA license**”；“License Issues … license laundering … erroneously assign incorrect license” | 高（文章/散文事实文本） | ❌ **排除**：底层 CC BY-SA（SA 义务，PI 待决①不接受 SA）；元数据 Apache 与原文冲突，按原文从严 |
| `TeraflopAI/wikicommons-cc-0` | `other` | README 仅 `license: other`（实字节 393 B，sha256 `99fdab77…4b5d7c`），无可核验 CC0 原文 | 低（Wikimedia Commons 多为图片） | ❌ **排除**：许可不清，整批剔除 |
| `alfredplpl/image-text-pairs-ja-cc0` | `cc0-1.0` | LICENSE.txt 实字节 235 B，sha256 `a66d5e31…c1064489` | 低（日文图文对，非事实文本） | ⚠️ 许可合规但不适配 real 事实源 |
| `raaa337/kelizi-oc-cc0` | `CC0-1.0` | 描述：“图片为原创OC 可丽子，CC0 1.0 …允许二次创作/商用，无需署名”（仅图片） | 无（图片） | ❌ 不适配 |
| `wikimedia/wikipedia` | `Apache License 2.0`（打包层） | Wikipedia 镜像；底层文本 CC BY-SA（已知事实） | 高 | ❌ **排除**：SA 义务 + 元数据与底层许可冲突 |
| `AI-ModelScope/wikipedia-cn-20230720-filtered` | `cc-by-sa-3.0` | 元数据明确 SA | 高 | ❌ **排除**：SA |
| `SkyContact/TheCompleteWorksOfLuXun` | `apache-2.0` | 鲁迅全集（公版作品打包） | 中（文学文本，非事实句） | ⚠️ 许可合规（打包 Apache-2.0，内容公版）但适配低 |
| ZJUNLP/FactCHD 等 | `MIT` | 事实核查数据（非文档事实源） | 低 | ⚠️ 许可合规但不适配 |

## 2. 关键发现（合规）

1. **ModelScope 的 `license` 元数据不可直接采信**：多处“Apache License 2.0”是**打包/镜像层**许可，与底层内容许可（CC BY-SA）冲突——`common-pile/public_domain_review`、`wikimedia/wikipedia` 均属此列。按 PI“许可不清整批剔除”“原文从严”原则，**须读 README 原文核验**，不能仅凭元数据入库。
2. **唯一明确 CC0 且可下载真实字节的事实文本候选**：`rootsautomation/SciTSR-pd`（CC0/公共领域、无署名、允许商用/衍生）。但其内容是**科学表格结构识别**数据，非连续事实句——能否支撑 F1/F3/F6 反事实编辑**需科学家评估语义适配性**。
3. **无大量连续事实句的 CC0 文本源被确认**：高适配的 Wikipedia 镜像均为 CC BY-SA（PI 已排除 SA）；public_domain_review 原文亦为 CC BY-SA。
4. **sha256 可计算性**：ModelScope 数据集文件可通过 `get_dataset_file_url` / repo API 取得真实字节流 → sha256 **可实际计算**；本轮仅对小文本（README/LICENSE）计算了真实 sha256（见上表），未下载数据主体。

## 3. 结论

- **real 唯一路径部分打通**：ModelScope 上存在 1 个明确 CC0/公共领域、可下载、可算哈希的事实文本候选（`rootsautomation/SciTSR-pd`），但其为表格结构数据，**事实句适配性存疑**，需 PI/科学家裁定是否用作 real 改写源。
- **高适配文本源仍不可得**：Wikipedia/Public Domain Review 均为 SA（已排除）；gov.cn/Wikidata 网络不可达；Census ToS 冲突永久剔除；Wikipedia 正文按待决①不入库。
- **未入库**：本轮未下载数据主体、未生成 `cf_pairs_real.jsonl`、未登记 `annotator_*`/`sampling_*`（人力待真实 PI 提供）。
- 按 PI §2 结局表：若 SciTSR-pd 语义不适配或人力不到位 → real 走“受阻披露”（real=0，正文诚实披露），不伪造 real。

## 4. 需 PI / 真实 PI 决策

1. 是否将 `rootsautomation/SciTSR-pd`（CC0 表格数据）认定为可用 real 改写源（需先做语义适配评估：表格能否构造 F1/F3/F6 反事实对）。
2. 真实 PI 提供 2 名标注者 + 1 名抽检员人力（入库前必需）。
3. 若上述任一不满足 → 确认 real=0 受阻披露路径。

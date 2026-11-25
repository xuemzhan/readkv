# M4 三项阻塞裁决（V2.0 · 抓取通道 / 人工标注 / Census 冲突）

> 裁决人：PI / 课题组长。日期：2026-11-23。
> 性质：紧急执行阻塞裁决。数据工程师如实拒绝伪造数据（`m4_fetch_attempt_log.md`、`m4_acceptance_checklist.md` 0/7、不申请二次签off）——**该行为完全正确，予以确认与表扬**。
> 依据：`reports/data/{m4_fetch_attempt_log,m4_acceptance_checklist,anchor_license_check}.md`、`docs/decisions/{m4_compliance_signoff,m4_anchor_execution_plan,external_validity_v2.4,human_decisions}.md`、PI 本轮独立网络实测。
> 本裁决只写决策文档，不改任何已冻结文件（含 v2.4）、`src/**`、`reports/runs/**`、数据或论文；不写代码、不跑实验。

---

## 0. PI 独立网络核验（本轮实测，作为裁决依据）

| 目标 | 实测结果 | 含义 |
|---|---|---|
| `rajpurkar.github.io/SQuAD-explorer/dataset/dev-v2.0.json` | **HTTP 200，返回完整真实 JSON 字节流**（`{"version":"v2.0","data":[...]}` 含段落/问题/答案） | **锚点通道打通**：可下载真实字节 → 可算真实 `raw_file_sha256` |
| `rajpurkar.github.io/SQuAD-explorer/` | 200，明示 CC BY-SA 4.0、Dev v2.0 4MB / Train v2.0 40MB 下载 | 许可与版本可固定归档 |
| `www.modelscope.cn`（域名） | 有 HTTP 响应（JSON 错误体，非连接失败） | 域名可达；具体数据集 API 路径需数据工程师核验 |
| census.gov / api.census.gov | 403（与工程师日志一致） | A 来源仍不可达 |
| Wikidata API / EntityData | 超时（与日志一致） | C 来源仍不可达 |

**关键新事实**：SQuAD 官方数据**可直接下载真实字节流并计算哈希**——锚点（意图 4b）的通道是通的，与 real 文档抓取阻塞应**分开处理**。

---

## 1. 三项阻塞逐项裁定

### 阻塞 1 — 抓取通道（A/B/C 无原始文件字节）

> **裁定：改由可达的官方源下载锚点数据（SQuAD 官方页为主），并授权数据工程师探查 ModelScope 上可合法改写的事实文本镜像作为 real 候选；A/B/C 原渠道暂缓，不要求真实 PI 立即提供代理。若 ModelScope 仍无合规可改写的 real 源，则 real 目标按 §4 调整。**

- **锚点（立即可行）**：授权从 `rajpurkar.github.io` 直接下载 SQuAD dev-v2.0（PI 已实测 200 + 真实字节），ARC/HellaSwag 若 HuggingFace 不可达则查 ModelScope 镜像或 AWS 公开桶（ARC 在 `ai2-public-datasets` 公开 S3）；按 `anchor_license_check.md` 的许可结论与五项登记（版本+文件 sha256+URL+日期+处理 commit）归档。**许可核验仍须齐全，不得绕过"许可不清不入库"红线**；锚点数据仅评测、不改写发布（v2.4 待决④）。
- **real 源（M4）**：授权数据工程师在 **ModelScope** 探查可合法改写/再分发的事实文本数据集（CC0/公共领域/CC BY，排除 SA 与仅研究用途），核验其许可原文与五项登记。**这是探查授权，不是入库授权**——入库仍须五项登记齐全 + 二次签off。
- **不要求真实 PI 立即提供代理/预下载**：因已有可达通道（SQuAD 官方、ModelScope），先穷尽可行通道；仅在 ModelScope 亦无合规 real 源时，才上报真实 PI 请求预下载文件或受控代理（§6）。
- 红线不变：任何来源**无原始文件字节 → 不得计算/编造 sha256**；许可不清 → 整批剔除；不得绕过 v2.4 红线。

### 阻塞 2 — 人工标注缺失（无 annotator_A/B/sampling_reviewer）

> **裁定：不新增 v2.5 授权"自动化校验"替代人工留痕；人工标注必须由真实 PI 提供人力或明确豁免。本执行体不得伪造任何人工记录。**

理由：签off §3 的"两名标注者独立核对 + 第三人 ≥20% 抽检"是**真实人力留痕**要求；自动化双重校验（如脚本比对候选相异、答案一致）可以**补充**但不能**替代**人工语义判断（事实是否正确、改写是否引入第二处改动、逻辑是否一致）。若以 v2.5 把自动化伪装成"人工双人留痕"属伪造，触碰硬约束。

- **即时指令**：向真实 PI 上报——M4 入库需要至少 2 名标注者 + 1 名抽检员（可为真实 PI 本人或指定人员）提供真实留痕；**在人力到位前，real 数据不得入库**。
- 工程侧可做（不算伪造）：脚本化的候选相异断言（M1）、三项语义自检、分层抽样**名单生成**——但 `annotator_*`/`sampling_*` 字段必须由真人填写，不得由 agent 代填。
- **锚点不受此阻塞**：锚点是标准 QA 评测（EM/Accuracy），不要求人工双人标注；阻塞 2 仅影响 M4 real 入库。故锚点可先行（见 §4b）。

### 阻塞 3 — Census ToS 冲突

> **裁定：确认剔除 Census（来源 A）作为 real 改写源，按待决②从严执行；real 改以 ModelScope 上的 CC0/公共领域事实文本为主。**

- Census ToS 原文"You may not modify or falsely represent content accessed through the API and still claim the source is the Census Bureau"——反事实改写 + 保留来源声明与之**直接冲突**；即便网络可达也不可用。**来源 A 从 real 候选永久剔除**（锚点也不用，因其 ToS 同样约束 API 内容）。
- **real 来源调整**：鉴于 Wikidata（C）网络超时、gov.cn（B）无出网、Wikipedia 正文（D）已按待决①排除、Census（A）ToS 冲突，**A/B/C/D 原授权源全部不可用**。real 唯一可行路径是 **ModelScope 上的 CC0/公共领域事实文本**（需数据工程师探查并核验许可）；若探查失败，执行 §4 的 M4 目标调整。

---

## 2. M4 目标调整裁定

> **裁定：维持 80–150 对目标为"首选"，但设置明确降级路径——若 ModelScope 无合规可改写 real 源或人力不到位，则 M4 记为"已尽力但受网络/许可/人力限制"，real=0，在正文如实披露，不无限期阻塞投递。**

分三种结局（预承诺，防反复）：

| 结局 | 触发条件 | 处理 |
|---|---|---|
| **M4 完成** | ModelScope 找到合规 real 源 + 五项登记齐全 + 人力到位（2 标注+1 抽检）+ 二次签off | 100 对入 real split，增强外部效度 |
| **M4 部分/延后** | 找到源但人力未到位 | real 数据暂存 `reports/_non_authoritative/` 或草稿区，不入库；待真实 PI 人力到位再续 |
| **M4 受阻披露** | ModelScope 无合规源，或真实 PI 决定不投入人力 | **real=0**，正文/notes 明确披露"已尽力但受网络/许可/人力限制"；按决策 B 的定位，以锚点 + 合成域负面结果投稿（不伪造 real） |

**给写作者的即时指令**：在真实文档到位前，**不得**在论文中写任何 real split 结果；正文可先写"real=0，外部效度受限"的诚实 limitation，待 M4 有结论后再更新。

---

## 3. 锚点先行裁定（4b）

> **裁定：允许锚点独立于 M4 先行——先归档 SQuAD（主）真实字节与许可，完成五项登记后启动锚点评测 run；不受 real 阻塞与人工标注缺失影响。**

- **可行性**：SQuAD 官方页可直接下载（PI 实测 200 + 真实字节），许可 CC BY-SA 4.0（仅评测不触发 SA），无需人工双人标注。
- **执行顺序**：数据工程师下载 SQuAD dev-v2.0（或 train 子集）→ 归档版本 + 原始文件 sha256 + URL + 日期 + 处理 commit（五项登记）→ PI 确认锚点登记合规 → 工程师启动锚点评测 run。ARC/HellaSwag 按可达性与许可顺位跟进。
- **run 纪律（受 v2.4 约束）**：锚点臂 `anchor_{squad|arc}_{affine|kd}_seed0`（seed0 即可）、bf16/sdpa、`zero_re_prefill=true`、provenance 齐全、串行；新评测代码纳入新 commit 避免 R1；**v2.4 的预承诺三情形与"不恢复贡献"规则全部适用**。
- **明确**：锚点评测**不是**主终点、不构成贡献(3) 证据；结果按 v2.4 预承诺归类（复现→强化外部效度 / 相反→收窄边界不反转叙事 / 混合→探索性披露）。

---

## 4. 授权矩阵（本次裁定汇总）

| 事项 | 裁定 |
|---|---|
| SQuAD 官方下载 | ✅ 授权（锚点，五项登记齐全后评测） |
| ModelScope 探查 real 源 | ✅ 授权探查 + 许可核验（探查≠入库） |
| ARC/HellaSwag 锚点 | ✅ 授权（按可达性/许可顺位，仅评测） |
| A/B/C/D 原 real 源 | ❌ 暂缓/剔除（403/超时/无出网/ToS 冲突/SA 排除）；A（Census）永久剔除 |
| 自动化替代人工标注 | ❌ 否决（不得 v2.5 伪装人工留痕） |
| 人工标注人力 | ⏳ 上报真实 PI 提供（2 标注+1 抽检） |
| real 入库 | ⛔ 二次签off前禁止；本次所有授权均不含入库 |

---

## 5. 上报真实 PI 的事项

1. **人力**：M4 real 入库需 2 名标注者 + 1 名抽检员的真实留痕——请真实 PI 提供人员或明确豁免/降级（豁免则 real=0 披露）。
2. **受控代理/预下载（条件性）**：若 ModelScope 探查仍无合规可改写 real 源，请真实 PI 提供预下载并校验的原始文件或受控网络代理。
3. **venue**（既有未决）：M4 完成后指定。

---

## 6. 结论与给各角色的即时指令

**给数据工程师**：
1. 立即下载 SQuAD dev-v2.0（官方页，PI 已验证可达），完成五项登记（版本 sha256/URL/日期/commit），提交 PI 锚点登记确认；ARC/HellaSwag 顺位跟进。
2. 在 ModelScope 探查 CC0/公共领域可改写事实文本作为 real 候选，核验许可原文（白名单：公共领域/CC0/CC BY；排除 SA/仅研究/ToS 冲突），**仅探查核验，不入库**；结果如实报告。
3. 生成候选相异断言、语义自检、分层抽样**名单**（工程辅助），但 `annotator_*`/`sampling_*` 留空等待真人。
4. 不得编造任何哈希或人工记录；无原始字节不入库。

**给工程师**：待数据工程师完成锚点五项登记并经 PI 确认后，按 v2.4 启动锚点评测 run（seed0、bf16/sdpa、zero_re_prefill、新 commit）；不启动 real run（人力/入库未就绪）。

**给写作者**：real 结果未到位前不得写入论文；先保持 real=0 的诚实 limitation；锚点有结果后按 v2.4 预承诺归类更新，贡献状态不变。

**给真实 PI（上报）**：人力（2+1）、条件性代理/预下载、venue。

**冻结文件**：本裁决不改 v2.4 或任何已冻结文件；若后续要以自动化辅助校验正式入规则，须另立 v2.5 且**不得**将其表述为人工留痕的替代。

**签署：PI / 课题组长（M4 阻塞裁决 · 2026-11-23）**

# 外部锚点许可核验报告（E/F/G，仅评测用途）

> 执行角色：数据工程师 · 日期：2026-11-23
> 依据：`docs/decisions/m4_compliance_signoff.md` §1（E/F/G 授权）、§2 待决④（仅合规评测、不改编、不再发布、如实披露引用）、`docs/decisions/m4_anchor_execution_plan.md` §2
> 性质：**许可核验**（web 检索，引用一手/权威来源）；本轮不下载数据集正文、不启动任何锚点评测 run。
> 结论摘要：SQuAD 与 ARC 为 **CC BY-SA 4.0**，HellaSwag 为 **MIT**；三者均**允许用于评测**，本项目用途（仅评测、不改编语料、不再发布衍生语料、如实署名引用）在其条款内。**注意**：SA 义务仅在我们**再发布衍生语料**时触发——本项目明确不再发布其语料，故不触发 SA 传导；但必须在论文/报告中披露基准名称、版本、许可与引用。

## 0. 核验方式与证据等级

- 通过 web 搜索读取一手/权威页面：官方数据集主页、Hugging Face 官方 dataset card（metadata license 标签 + Licensing Information 段）、发布论文、AWS Open Data Registry、官方 GitHub。
- 每条给出可复核 URL 与页面原文关键句、核验日期（2026-11-23）。
- 对存在镜像/聚合站口径不一致者，以**一手来源**为准并标注分歧。

---

## 1. SQuAD（主锚点）— 许可：CC BY-SA 4.0

| 项 | 内容 |
|---|---|
| 许可 | **CC BY-SA 4.0**（署名-相同方式共享 4.0 国际） |
| 一手证据 1 | 官方主页 rajpurkar.github.io/SQuAD-explorer：原文 “Download a copy of the dataset (distributed under the **CC BY-SA 4.0** license)” |
| 一手证据 2 | Hugging Face 官方卡 huggingface.co/datasets/rajpurkar/squad：metadata `license: cc-by-sa-4.0`；Licensing Information: “The dataset is distributed under the **CC BY-SA 4.0** license.” |
| 一手证据 3 | SQuAD 2.0 论文（ACL 2018, nlp.stanford.edu/pubs/rajpurkar2018squad.pdf）脚注：“we release SQuAD 2.0 under the **CC BY-SA 4.0** license.” |
| 版本 | SQuAD 1.1（100,000+ QA / 500+ 篇）与 SQuAD 2.0（+50,000 不可答问题）；主锚点建议 dev 子集（v1.1 或 v2.0，需写作者与工程师定版本并归档版本哈希） |
| 义务 | 署名（作者、标题、来源、许可、修改说明）；**SA 仅在再发布改编材料时触发** |
| 本项目用途合规 | ✅ 仅评测（EM/答案对编辑的响应），不改写、不再发布其语料 → 不触发 SA；按引用披露 |
| 必引 | Rajpurkar et al., “SQuAD: 100,000+ Questions for Machine Comprehension of Text,” EMNLP 2016, doi:10.18653/v1/D16-1264；若用 2.0 加引 Rajpurkar & Jia et al., ACL 2018, doi:10.18653/v1/P18-2124 |
| 风险 | 低（评测用途无 SA 传导）；须核实所下载具体版本的哈希与引用版本一致 |

## 2. ARC（辅锚点）— 许可：CC BY-SA 4.0

| 项 | 内容 |
|---|---|
| 许可 | **CC BY-SA 4.0** |
| 一手证据 1 | Hugging Face 官方卡 huggingface.co/datasets/allenai/ai2_arc：metadata `license: cc-by-sa-4.0`（卡正文 Licensing Information 字段显示 “More Information Needed”，但 **metadata 许可标签为 cc-by-sa-4.0**，为一手机器可读声明） |
| 一手证据 2 | AWS Open Data Registry registry.opendata.aws/allenai-arc/：License = **CC BY-SA**；Documentation = allenai.org/data/arc；数据位于公开 S3 桶 `ai2-public-datasets`（无需 AWS 账户） |
| 一手证据 3 | ai2 GitHub open-data-registry `datasets/allenai-arc.yaml`：`License: '[CC BY-SA](creativecommons.org/licenses/by-sa/4.0/)'` |
| 版本 | ARC-Challenge（2,590）/ ARC-Easy（5,197），共 7,787 道；辅锚点建议 ARC-Challenge validation/test |
| 义务 | 署名；SA 仅在再发布改编材料时触发 |
| 本项目用途合规 | ✅ 仅评测（候选结构与本项目 A/B 口径相近），不改编、不再发布 → 不触发 SA；按引用披露 |
| 必引 | Clark et al., “Think you have Solved Question Answering? Try ARC, the AI2 Reasoning Challenge,” arXiv:1803.05457 (2018) |
| 风险 | 低—中：卡正文 “Licensing Information: More Information Needed” 与 metadata 许可标签不一致；以 metadata + AWS registry + 官方 YAML 为准，落引用时注明“license per HF metadata & AWS registry: CC BY-SA 4.0” |

## 3. HellaSwag（可选锚点，优先级最低）— 许可：MIT

| 项 | 内容 |
|---|---|
| 许可 | **MIT** |
| 一手证据 1 | Hugging Face 官方卡 huggingface.co/datasets/Rowan/hellaswag：Licensing Information = “**MIT** github.com/rowanz/hellaswag/blob/master/LICENSE” |
| 一手证据 2 | 官方 GitHub github.com/rowanz/hellaswag：License = **MIT license**，仓库含 `LICENSE` 文件 |
| 一手证据 3 | 发布页 rowanzellers.com/hellaswag（ACL 2019）+ 论文 arXiv:1905.07830；evalport 一手核验表亦记 HellaSwag = MIT |
| 口径分歧 | 部分镜像/聚合站显示 “Not stated by the source” 或 “Apache-2.0”（如 ModelScope evalscope 镜像）→ **以一手 HF 卡 + 官方 GitHub LICENSE 为准：MIT**；若启用，须固定并归档官方 LICENSE 文件哈希 |
| 版本 | 59,950 条（train 39,905 / validation 10,042 / test 10,003） |
| 义务 | MIT：保留版权/许可声明；无 SA |
| 本项目用途合规 | ✅ 仅评测（通用语言理解旁证），可比性较低（非文档事实编辑），优先级最低 |
| 必引 | Zellers et al., “HellaSwag: Can a Machine Really Finish Your Sentence?,” ACL 2019 |
| 风险 | 低（MIT，无 SA）；镜像口径不一致 → 必须固定一手 LICENSE 文件 |

---

## 4. 汇总判定与执行约束

| 基准 | 许可 | 评测用途合规 | SA 是否触发（本项目） | 优先级 | 固定/披露要求 |
|---|---|---|---|---|---|
| SQuAD | CC BY-SA 4.0 | ✅ | 否（不再发布衍生语料） | 主锚点 | 归档版本+文件哈希；署名+引用+许可披露 |
| ARC | CC BY-SA 4.0 | ✅ | 否 | 辅锚点 | 同上；注明许可来源（HF metadata/AWS registry） |
| HellaSwag | MIT | ✅ | 否（MIT 无 SA） | 可选 | 固定官方 LICENSE 哈希；署名+引用 |

统一执行约束（承接 PI 待决④）：
1. 三者**仅评测**，不改写、不作为 real 文档源、不再发布其语料；
2. 评测前由数据工程师下载所选版本并归档**版本标识 + 原始文件 sha256 + 下载 URL + 日期**，写入锚点数据登记（本轮未下载，尚未完成）；
3. 论文/报告如实披露：基准名称、版本、许可、引用、评测用途与“未再发布语料”声明；
4. 若任一口径在本项目实际下载时与本报告不符 → 按 SQuAD→ARC→HellaSwag 顺序调整，不强用；
5. 本轮**未启动任何锚点评测 run**（符合 PI “先核许可、不跑 run” 指令）。

## 5. 需注意的一个合规联动（重要）

SQuAD/ARC 均为 CC BY-SA，虽然本项目“仅评测不发布衍生语料”不触发 SA 传导，但若将来把锚点上的**评测结果/派生分析表**作为数据集发布，需由 PI 合规再评估 SA 义务是否适用于该派生材料。本报告按当前用途判定为不触发。

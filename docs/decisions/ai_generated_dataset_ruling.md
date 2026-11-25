# AI 生成数据集提议裁决：human-seeded, model-generated 反事实对（V2.0）

> 裁决人：PI / 课题组长。日期：2026-11-23。
> 触发：真实 PI 新提议——"让 AI 基于真实人类行为数据生成对应的数据，构建数据集并说明，在项目中公开；这样总比不做好"。
> 依据：`docs/decisions/{m4_target_adjustment,final_boundary_study_signoff,agent_crosscheck_ruling}.md`、`configs/prereg/{external_validity_v2.4,annotation_convention_v2.5,ai_generated_data_v2.6}.yaml`、`reports/data/anchor_license_check.md`；HellaSwag 许可经本轮 websearch 一手核实（HF 官方卡 + GitHub LICENSE），数据卡框架参考 Gebru et al., *Datasheets for Datasets*, CACM 2021。
> 本裁决 + v2.6 只写决策/冻结文档；不改任何旧冻结文件（含 v2.4/v2.5）、`src/**`、`reports/runs/**`、数据或论文；不写代码、不跑实验。

---

## 1. 可行性结论：有条件 GO

> **裁定：GO（有条件）——可以构建并公开一个以 HellaSwag（MIT，真人撰写常识句）为种子、由 AI 生成的反事实对数据集，但只能定性为 "human-seeded, model-generated counterfactual pairs"，并按 v2.6 先冻后跑。**

理由：
1. **种子许可干净**：HellaSwag = MIT（HF 官方卡 "Licensing Information: MIT" + github.com/rowanz/hellaswag/LICENSE，本轮 websearch 一手核实），允许衍生与再发布、无 SA 义务，只需保留版权/许可声明并署名 Zellers et al. ACL 2019——这使"生成并公开衍生集"在许可上可行。
2. **不伪造红线可守**：种子是真实可下载字节（可算真实 sha256），生成过程可完整留痕（模型版本/seed/prompt/脚本 commit），质量审计沿用 v2.5 的 agent 交叉校验口径——不触碰"伪造人类标注/哈希"红线（数据工程师此前拒绝伪造的做法被表扬并延续）。
3. **有真实价值，但有限**：作为"额外探针"和公开资产，它比"什么都不做"提供了可复现的生成协议与一个公开数据集；但**不是**真实人类行为数据，不能补 real=0 的外部效度缺口。

**限制前提**：种子**只能**用 HellaSwag；SQuAD/ARC（CC BY-SA，发布衍生触发 SA）**禁止**作种子；generator 须与 teacher/student 不同；全程按 v2.6；结果不恢复贡献、不重算主终点。

---

## 2. 命名与定性（强制）

- **唯一正式名称**：`human-seeded, model-generated counterfactual pairs`（真人种子、模型生成的反事实对）。
- **禁止名称**："真实人类行为数据"、"real split / real 文档"、"human-annotated / human-verified"、"真实文档外部效度已验证"。
- **声明**：数据卡与论文须写明"本集由模型生成，以 HellaSwag 真人常识句为种子；生成文本非人类撰写或标注"。
- **real=0 不变**：M4 受阻披露 real=0 的结论不变；本工作包不是 real 的替代，不声称真实文档外部效度。
- **不恢复贡献**：贡献(1)(2) 撤回、贡献(3) withheld 维持；P2/P3/P4 永久放弃——本工作包是**新数据构建**，不是 P3 重启。

---

## 3. 许可与合规

1. **种子仅 HellaSwag MIT**：下载实际文件（HF `Rowan/hellaswag` 或官方 GitHub），用 `sha256sum` 算真实哈希；归档官方 LICENSE 原文（算哈希）与引用原文（Zellers et al., ACL 2019）。
2. **底层来源披露**：HellaSwag 文本源自 ActivityNet + WikiHow；数据卡须如实披露，MIT 适用于 HellaSwag 作者的整理/标注；含可识别第三方内容或个人信息的种子句剔除。
3. **衍生集许可**：以 **MIT**（或项目现有 CC0 许可，取更宽松者）发布，随附 HellaSwag MIT 声明与 Zellers et al. 2019 署名；数据卡声明"AI 生成、非真实人类标注"。
4. **禁用 SQuAD/ARC 派生内容**：CC BY-SA 衍生发布会触发 SA，禁止进入公开集或作生成种子。
5. **五项登记齐全**：URL/版本/许可原文/sha256/处理脚本 commit；无原始字节不得算哈希（不编造）。

---

## 4. 科学有效性约束（已写入 v2.6，先写后跑）

- 冻结 generator 模型与版本（Qwen3-0.6B/1.7B/4B 中选一固定），**须与 teacher/student 不同**以避免循环自生成；固定 seed 与 prompt 模板全文。
- 规模 80–150 对（建议 100），目标覆盖 F1–F6；不可构造的切片如实标注，不强行填充。
- 复用 M1 退化对断言；双人 agent 交叉校验 + ≥20% 抽检（v2.5 口径）；按 seed document 分簇、簇级 bootstrap + pair 敏感性、簇<24 标 exploratory。
- **不得按评测结果回改生成器/prompt/种子/筛选**（p-hacking 禁令）。
- **仅作额外探针**：不并入合成 test、不重算主终点、不恢复贡献、不与合成域/锚点混算。

---

## 5. 执行分工、排期与验收

| 环节 | 负责角色 | 验收标准 |
|---|---|---|
| 种子下载/归档/五项登记 | 数据工程师 | HellaSwag 真实字节 + sha256 + LICENSE + 引用 + 五项登记齐全 |
| 生成脚本实现（v2.6 协议） | 工程师 | 固定模型/seed/prompt，纳入新 commit，产物可复现 |
| 生成运行 | 工程师 | 80–150 对，F1–F6 覆盖如实，退化对断言通过 |
| 质量审计 | 审稿人 | v2.5 交叉校验 + ≥20% 抽检、去重、个人信息剔除、exploratory 标记 |
| 数据卡/论文披露/数据卡 | 文档工程师 + 写作者 | Datasheets 风格、非人类声明、MIT+署名、底层来源披露 |
| 协议合规 | PI | 全链条符合 v2.6，未改旧判据 |

**工作量量级（估计，非承诺）**：种子归档 0.5 人日；生成脚本实现 0.5–1 人日；生成运行 GPU 约 0.5–1 h（0.6B/1.7B，80–150 对短生成）；质量审计 1–2 人日；数据卡/披露 0.5–1 人日。合计约 **3–5 人日 + <2 h GPU**。

---

## 6. 对外发布内容

- 生成对数据文件（含种子 ID、generator 版本、seed、prompt 版本字段）；
- manifest（文件 sha256、规模、切片覆盖、五项种子登记）；
- 数据卡（Datasheets for Datasets 风格：动机/组成/采集/用途 + "AI 生成、非真实人类标注"声明 + MIT 许可与 Zellers 2019 署名 + HellaSwag 底层来源）；
- 生成脚本与 commit、质量报告；
- 发布位置 `data/generated/`，并更新 README 增加条目与定性说明。

---

## 7. 论文表述边界

**可写**：
- "We release a human-seeded, model-generated counterfactual probe built from HellaSwag (MIT), with a fully documented generation protocol."
- "As an additional probe, model-generated pairs show [探索性结果]；exploratory, single-generator, not real-world validation."
- 数据审计方法论警示（贡献(1)(2) 撤回的前因）、SQuAD 锚点的有限外部效度。

**禁写**：
- "real documents / real-world validation / human-annotated / human-verified / 真实人类行为数据"；
- "真实文档外部效度已验证 / cross-source generalization"；
- 任何用生成集恢复贡献(1)(2) 或声称贡献(3) 方法增益的表述；
- 把生成集结果与合成 test / 锚点混算或当主终点。

**venue**：仍待真实 PI 指定（见 venue_recommendation.md，首选 TMLR）；本工作包不改变 venue 未定前"投递就绪、不最终签 off"的状态。

---

## 8. 结论与第一步

- **可行性**：有条件 GO；种子仅 HellaSwag MIT，产物定性为 human-seeded model-generated，按 v2.6 先写后跑。
- **v2.6 已冻结**（`configs/prereg/ai_generated_data_v2.6.yaml`），不回写旧文件；real=0 与贡献状态不变；不是 P3 重启。
- **第一步执行动作**：数据工程师从 HF `Rowan/hellaswag` / 官方 GitHub 下载 HellaSwag 实际文件与 LICENSE，算真实 sha256、归档引用原文，完成五项种子登记并提交 PI 确认；PI 确认后工程师按 v2.6 实现生成脚本并纳入新 commit。**v2.6 冻结 + PI 种子确认前，不启动任何生成 run、不写数据文件。**

**签署：PI / 课题组长（AI 生成数据集裁决 · 2026-11-23）**

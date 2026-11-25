# AI 生成数据集最终裁定：撤回 GO，维持 real=0 + 锚点路径（V2.0）

> 裁决人：PI / 课题组长。日期：2026-11-23。
> 触发：科学家的独立评估（`docs/data/hellaswag_seed_semantic_assessment.md`）与我此前 `ai_generated_dataset_ruling.md`（有条件 GO）冲突，要求最终裁定。
> 依据：科学家评估全文、`configs/prereg/ai_generated_data_v2.6.yaml`、`configs/prereg/external_validity_v2.4.yaml`、`docs/decisions/{m4_compliance_signoff,ai_generated_dataset_ruling,agent_crosscheck_ruling,m4_target_adjustment}.md`、`reports/data/anchor_license_check.md`；HellaSwag 论文一手核实（arXiv:1905.07830 摘要，本轮 webfetch）。
> 本裁决只写决策文档；不改任何已冻结文件、`src/**`、`reports/runs/**`、数据或论文；不写代码、不跑实验。

---

## 1. 复核结论：科学家的反驳成立，撤回「有条件 GO」

> **最终裁定：撤回 `ai_generated_dataset_ruling.md` 的「有条件 GO」。v2.6 保持冻结但标注「无适用对象（not activated）」，不启动生成。维持 `m4_target_adjustment.md` 的 real=0 受阻披露 + SQuAD/ARC 锚点路径。不新增 v2.7（无需覆盖"锚点仅评测不发布"口径，因为不做生成发布）。**

我逐条复核科学家的五点，全部成立：

1. **语义不适配（成立，且比 SciTSR 更弱）**：HellaSwag 的形态是"情境 + 4 候选结尾的续写合理性（plausibility）"，不是可编辑的事实命题（belief）。F1 实体替换、F2 推理链、F3 方向/否定**不可作为真人派生**——AI 要写出含事实的 d_A/d_B，事实/关系/极性全是模型发明，种子只提供场景骨架。仅 F4（抗捷径结构）、F5（表层负控）、F6（表层位置）有部分结构价值。我此前 GO 低估了这一形态鸿沟。
2. **"human-seeded"名存实亡（成立）**：对 F1/F2/F3，所谓"真人种子"只剩题材骨架，本质是"合成数据 v2"；若论文声称"基于真人行为数据生成事实反事实对"属误导性表述。
3. **循环论证高风险（成立）**：本机只有 Qwen3 系列，若 generator 与 teacher/student 同家族，评测得到的是"模型偏好镜像"而非独立真实性检验；缓解需跨家族模型（本机没有）+ 真人分层抽样核验——**后者正是 real 人力阻塞的同一个绑定条件**，并未因换方案而解除。
4. **合规口径冲突（成立，但我选择不覆盖）**：`m4_compliance_signoff` 待决④与 v2.4 明令锚点"仅评测、不改写、不再发布其语料"；我此前 GO 未处理这一冲突。MIT 无 SA 义务，但与冻结口径语义冲突。本裁定**不以新增版本文件覆盖该口径**——因为不做生成发布，冲突自然消解。
5. **第6点我独立核实属实（关键）**：HellaSwag 论文摘要原文——"a series of discriminators iteratively select an **adversarial set of machine-generated wrong answers**"——**干扰结尾是机器生成的**。这意味着"真人撰写"只对 context 与正确结尾成立；用"含机器生成干扰的种子"去生成更多机器数据，循环论证证据更强，"human-seeded"表述在干扰维度上根本不成立。这进一步削弱了 GO 的基础。

---

## 2. 直接回应真实 PI 的原话"总比不做好"

> **科学判断：不成立。在这个具体案例里，"做"比"不做"更糟。**

- "总比不做好"隐含前提是"产物至少是中性的、不会伤害论证"。但本产物：① **无法回答目标问题**（F1/F2/F3 核心语义切片全为模型发明，不是真人事实证据）；② **引入同源偏置**（同家族 generator/evaluator 循环论证）；③ **制造概念混淆**（"human-seeded"实为合成数据 v2，干扰项本身还是机器生成的）；④ **与已冻结的"锚点仅评测不发布"口径冲突**。
- 这样的产物会稀释证据强度，并招致审稿人"概念混淆 + 循环论证"的致命意见——比诚实披露 `real=0` 更有害。诚实的 `real=0` + 已授权 SQuAD/ARC 锚点，是合规、证据、成本三者都最稳的方案。
- 这不是"不做科学研究"，而是"不做伪装成外部效度补救的低科学价值数据"。PI 建议的真实目标（外部效度旁证）已由 SQuAD（人写维基事实文本，比 HellaSwag 更贴近文档事实编辑）覆盖——用已授权锚点即可，无需生成新数据集。

---

## 3. 若「仍坚持做」的处置说明（本次不采用，仅备查）

科学家 §5.2 给出了"若 PI 仍坚持"的最低条件（仅 F4/F5/F6、≥24 独立 seed 簇、60–100 对、跨家族 generator、真人核验、独立非权威轨道）。但本次**不采用**，因为：
- 本机无跨家族 generator（仅 Qwen3）；
- 真人核验人力阻塞未解除（与 real 同一绑定条件）；
- 即使只做 F4/F5/F6，其科学定位也只是"对数据构造敏感的探索性旁证"，不填补 real=0 缺口——不足以构成"做"的理由。
- 若未来真实 PI 以新证据/新资源重启，须另立新版本 prereg（覆盖 v2.6 的 not-activated 状态）并重新裁决；不得直接启用 v2.6。

---

## 4. v2.6 处理

- **v2.6 保持冻结，状态标注为"无适用对象 / not activated"**（类似 v2.5 无 real 对象的处理）。
- 严禁"为了用上 v2.6"而做低科学价值数据；v2.6 的协议条款在 not-activated 状态下不产生任何生成授权。
- 不新增 v2.7：因不做生成发布，"锚点仅评测不发布"口径无需覆盖，v2.4 保持原样。
- 不改 `ai_generated_dataset_ruling.md` 原文（历史裁决保留），本裁决为其最终覆写；两者并存时以本裁决为准。

---

## 5. 给各角色的指令

- **数据工程师**：不启动任何 HellaSwag 生成数据下载/生成；`data/generated/` 不创建；维持 SQuAD 锚点归档现状。
- **工程师**：不实现 v2.6 生成脚本；锚点评测（`anchor_squad_{affine,kd}_seed0`，依 anchor_confirmation.md）按计划继续，不受本裁决影响。
- **审稿人**：无需为生成数据做质量审计（未启动）；P5 合规意见中注明"AI 生成集提案已评估并撤回（not activated），无遗留产物"。
- **写作者/文档工程师**：论文不写任何 human-seeded/model-generated 数据集及其结果；维持 real=0 受阻披露 + SQuAD/ARC 锚点有限外部效度；贡献(1)(2) 撤回、贡献(3) withheld 不变；venue 仍待真实 PI 指定（首选 TMLR，见 venue_recommendation.md）。

---

## 6. 结论

- **最终裁定**：撤回有条件 GO；v2.6 冻结但 not-activated；维持 real=0 + SQuAD/ARC 锚点路径；不新增 v2.7。
- **对真实 PI**："总比不做好"在此不成立——该产物无法回答目标问题、引入循环论证与概念混淆、与冻结口径冲突，比诚实披露 real=0 更有害；外部效度旁证由已授权的 SQuAD 锚点覆盖。
- **论文/阶段**：定位与贡献状态不变；venue 仍待真实 PI 指定；venue 未定前维持"投递就绪、不最终签 off"。

**签署：PI / 课题组长（AI 生成数据集最终裁定 · 2026-11-23）**

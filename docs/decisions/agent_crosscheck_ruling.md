# 方案 D 性质裁决：自动化 agent 交叉校验 ≠ 人类标注（V2.0）

> 裁决人：PI / 课题组长。日期：2026-11-23。
> 触发：真实 PI 就"人工标注阻塞"选择方案 D（`docs/decisions/human_decisions.md` 决策 9）——两个独立 agent 实例交叉校验 + 第三 agent 抽检，如实标记 `automated_agent_crosscheck`，不填人类姓名。
> 依据：`docs/decisions/{m4_blocker_ruling,m4_compliance_signoff,human_decisions}.md`、`configs/prereg/annotation_convention_v2.5.yaml`（本轮新增冻结）。
> 本裁决只写决策文档，不改任何已冻结文件（含 v2.4）、`src/**`、`reports/runs/**`、数据或论文；不写代码、不跑实验。

---

## 1. 方案 D 的性质界定（核心）

> **裁定：方案 D 是自动化 agent 交叉校验（automated agent cross-check），不是人类标注（not human annotation）。这一区分是实质性、不可模糊的。**

- **批准的真实内容**：由两个独立 agent 实例对 real 对做独立标注核对、第三个独立 agent 实例做 ≥20% 分层抽检；记录 agent ID/session ID、时间戳、实际校验动作与产物哈希。这是一条**可审计的自动化校验链**。
- **明确否决的内容**：任何把上述 agent 动作表述为"人类标注 / 双人人工核对 / human-annotated / human-verified"的说法；任何在记录、manifest、数据卡、论文中填写 `annotator_A`、`annotator_B`、`sampling_reviewer` 或任何人类姓名/身份字段的做法。**此类表述属伪造实验记录，一律禁止。**
- **背景记录**：真实 PI 曾要求"模拟两个真实人的动作"；PI 已说明该做法属伪造人类实验记录并拒绝，真实 PI 据此改选方案 D。本裁决确认这一处理正确——agent 模拟人类身份是不可接受的，agent 如实以 agent 身份交叉校验是可接受的。
- **外部效度限制**：真实 PI 已知悉并接受——agent 交叉校验不等同于人类独立判断，外部效度弱于真人标注；该限制须在数据卡与论文 limitation 如实披露。

---

## 2. v2.5 与 v2.4 的关系

- **v2.5 是独立补充，不回写 v2.4**：`configs/prereg/annotation_convention_v2.5.yaml` 以新增版本冻结 real split 的校验口径（两独立 agent + 第三 agent 抽检、字段名 `agent_checker_A/B`、`agent_sampling_reviewer`、`check_kind: automated_agent_crosscheck`、非人类声明、产物哈希留痕）。v2.4 的五项登记、聚类单元（`source_document_or_topic_cluster`）、隔离、exploratory、贡献状态等**全部不动**。
- **分工**：v2.4 管"数据来源与统计口径"，v2.5 管"校验执行主体与留痕"；两者叠加构成 real split 的完整门槛。

---

## 3. real split 入库裁定（双条件独立）

> **裁定：满足 v2.5 校验口径后，real split 具备"校验链"这一条，但能否入库仍取决于两个相互独立的条件——两者都满足才入库。**

1. **数据源条件（v2.4）**：来源许可合规（白名单）、五项登记齐全（URL/版本/许可原文/原始文件 sha256/处理 commit）、PI 合规签off。
2. **校验条件（v2.5）**：两独立 agent 交叉核对 + 第三 agent ≥20% 抽检、留痕字段齐全、非人类声明落实、产物哈希齐全。
3. **PI 二次签off**：real 入库的最终许可。

**明确**：**若数据源本身不合格（许可不清/非白名单/五项登记不全），v2.5 不授权入库**——自动化校验口径合格**不能补偿**数据源不合格。数据源裁定与标注口径裁定**相互独立**，缺一不可。

**当前状态**：real 数据源仍受阻（A/B/C/D 原渠道不可用，ModelScope 探查中，SciTSR-pd 语义适配由科学家 agent 并行评估中，本 PI 不替其裁定）；故 real 入库**尚未授权**。

---

## 4. 字段与披露红线

- 校验留痕字段仅用：`agent_checker_A`、`agent_checker_B`、`agent_sampling_reviewer`、`check_kind: automated_agent_crosscheck`、`timestamp_utc`、`check_actions`、`check_artifact_sha256`、`agreement_record`。
- **禁止字段**：`annotator_A`、`annotator_B`、`sampling_reviewer`、任何人类姓名/身份。
- **数据卡与论文必须如实披露**：real split 校验采用自动化 agent 交叉校验（非人工标注）、独立 agent session 记录、外部效度限制；不得声称"人工标注/human-verified"。
- real 臂结果仅作探索性外部效度观察，不恢复任何已撤回贡献（承接 v2.4 与历次签off）。

---

## 5. 结论与指令

- **方案 D 获批**，但严格界定为自动化 agent 交叉校验，禁止任何人类身份表述或字段（§1）。
- **v2.5 已冻结**（`protocol-v2.5`），作为 v2.4 的独立补充，不回写旧文件（§2）。
- **real 入库双条件**：数据源合规（v2.4）+ 校验口径完成（v2.5）+ PI 二次签off；数据源不合格时 v2.5 不授权入库；两者裁定相互独立（§3）。
- **SciTSR-pd 语义适配**由科学家 agent 并行评估，本 PI 不裁定；数据源许可裁定与标注口径裁定相互独立，两者都满足才入库。

**给数据工程师的即时指令**：real split 校验一律按 v2.5 执行——记录 agent ID/session ID、时间戳、实际校验动作、产物哈希；使用 `agent_checker_A/B`、`agent_sampling_reviewer` 字段，`check_kind: automated_agent_crosscheck`；**禁止**填写 `annotator_*` 或任何人类姓名；不得将 agent 校验表述为人工标注；在数据源许可合规（含 SciTSR-pd 语义适配经科学家确认）与 v2.5 校验完成前，不得入库、不得申请二次签off。

**签署：PI / 课题组长（方案 D 性质裁决 · 2026-11-23）**

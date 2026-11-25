# 干净数据方向性翻转紧急裁决（P1 · broken transfer · V2.0）

> 裁决人：PI / 课题组长。日期：2026-11-23。
> 性质：**紧急科学裁决**，不等待正在运行的 GPU 重跑结束；根据新证据冻结贡献措辞并调整阶段门控。
> 依据：`reports/runs/p1_clean_mvp_seed{0,1,2}/metrics.json`（实测，git_hash=`efc3ba3`）、`configs/prereg/phase1_benchmark_decision.yaml`（冻结）、`docs/protocol.md` §1.2/§8/§10、`docs/decisions/{data_readiness_ruling,final_signoff,contribution2_final_form,contribution2_ruling}.md`、`reports/data/data_readiness_audit.md`、`docs/data_readiness_scientist.md`。
> 本裁决只写决策文档，不改 `src/**`、`reports/runs/**`、冻结判据、数据或论文；不写代码、不跑实验。

---

## 0. 事实核验（先确认翻转属实）

PI 独立读取干净数据 P1 产物，确认上报属实：

| seed | joint E_CF [CI] | dual_correct | flip | coverage | transfer_broken | joint_dual_drop_vs_self |
|---|---|---|---|---|---|---|
| 0 | 6.900 [5.499, 8.313] | 0.417 | 0.750 | 0.867 | **true** | 0.4 |
| 1 | 8.159 [6.647, 9.702] | 0.283 | 0.736 | 0.883 | **true** | — |
| 2 | 8.540 [7.057, 10.062] | 0.383 | 0.755 | 0.883 | **true** | — |

- **数据修复生效**：`degenerate_must_flip_pairs=0`、`cross_split_overlap`（context_A/B/query/edited_span/source_doc/cluster）全 0、`entity_pool_overlap` 全 0、flip 分母口径已改为排除 F5+F6（398）——旧数据的退化对与泄漏确已消除。
- **provenance**：git_hash=`efc3ba3`、`zero_re_prefill=true`、`protocol_version=2.0`，三 seed 齐全。
- **质量坍塌**：joint dual 0.283–0.417 vs Self ≈0.82，drop≈0.4（远超 0.2 阈值）；`transfer_broken=true` 由正交字段标注（`quality_pass` 仍仅指数据质量门，冻结 verdict=`distortion_exists` 未改）。
- 对照旧（已 superseded）数据：E_CF 1.93–2.12、dual 0.617–0.667、flip 0.90–0.96、`transfer_broken=false`。**方向性翻转属实**。

---

## 1. 科学判定：贡献(1)(2) 是否还成立

### 1.1 贡献(1)（评价层 gap）——立即冻结并降级，不再成立为原措辞

> **裁定：原贡献(1)"可复现的、未被强基线消除的 utility-preserving 反事实失真"在干净数据上不再成立，立即冻结，不得再以该强度表述。**

理由：

1. 贡献(1) 的 §10 模板是 "gap between standard **transfer utility** and counterfactual response fidelity"——它预设**迁移 utility 基本保持而 fidelity 失真**。干净数据上 joint dual 坍塌到 0.28–0.42（Self ≈0.82）、E_CF 达到 6.9–8.5 且与错配/零缓存控制相当（`joint_ecf_vs_controls`: mismatch 8.38、zero 8.58），这是**迁移整体失败（broken transfer）**，不是 utility-preserving 的干净失真。
2. 旧数据上"H1 成立、distortion_present、transfer_broken=false"的正向信号，经独立审计证实源于**数据泄漏/退化对/模板重合**（见 data_readiness_audit §2）——修复后这些信号反转为失败边界。换言之，**贡献(1) 的正向证据基础已不存在**。
3. 这是**证据基础的塌陷**，不是"强度保留"问题。按 `protocol.md §8`，"效果仅在合成域成立/迁移失败"须明确适用边界，不得声称普遍 gap。

### 1.2 贡献(2)（机制层）——立即冻结 withheld，不等 P2 重跑

> **裁定：贡献(2) 立即撤回至 withheld，不等待 P2 三 seed 重跑结果。**

理由：

1. 贡献(2) 的逻辑前提是贡献(1)——机制定位的对象是"utility-preserving 的失真"。前提塌陷后，"定位 V 消费侧的失真机制"失去意义：在一个迁移整体坏掉的系统上做 Oracle 修复，定位的是"如何修一个坏 mapper"，不是"解释干净的失真现象"。
2. 旧 P2 证据（repair 0.275–0.350、4/5 核心单元稳定）本身建立在被污染数据上——审计报告 §2.3 已指出"held-out 与 train 间文档泄漏可能抬高机制预测的表观成绩"。该证据不可信。
3. 因此**不采用"等 P2 重跑再定"的路线**——那会浪费算力在一个前提已塌的实验上，且旧证据必须在论文中撤回。

### 1.3 立即冻结的含义

- 从本裁决签发起，`final_signoff.md`、`contribution2_final_form.md` 中"贡献(1) 全 claim + 贡献(2) 强形式解禁"的签 off **对新数据不再适用**；以本裁决为准。
- 写作者不得再以任何形式引用旧数据的正向数值作为贡献证据；旧 run 已标 superseded，须彻底移出论文主表。

---

## 2. 剩余重跑：分项指令

> **总原则：停止一切服务于"正向贡献"的实验；保留具有失败边界诊断价值的实验。**

| 在跑/待跑 | 指令 | 理由 |
|---|---|---|
| **kd_only 三 seed（进行中）** | **继续完成**，但目的改为"失败边界确认"而非"验证失真未被消除" | 它对择支至关重要（§3）：若 kd_only 也不 broken → 所有 mapper 都失败，纯失败边界；若 kd_only 反而不 broken 且接近 Self → 触发"强基线接近 Self"分支。结果无论哪向都提供决定性信息。 |
| **δ=0.5 验证集复核** | **暂停/取消**（P3 已无意义，δ 只服务方法层） | 方法层前提塌陷；δ 复核不再有投递价值，省 GPU。 |
| **P2 三 seed（待启动）** | **不启动**（取消） | 机制诊断前提（干净失真）已塌；旧 P2 证据撤回；继续跑是纯浪费。若日后重新构造出干净失真数据再重启。 |
| **P3** | **维持暂停，实质取消**（除非人工要求重定义为"修复 broken transfer"的另一个问题） | 方法层"减少 gap"失去目标——没有可修复的干净失真；三 δ 负值预警 + 当前翻转使 P3 无科学意义。 |

**即时执行**：工程师收到本裁决后立即停 δ 复核、不启 P2；kd_only 三 seed 跑完即停，不再开新 run。

---

## 3. H1 / 决策树重新择支

### 3.1 冻结判据的机器 verdict 与科学定性的分离

- `phase1_benchmark_decision.yaml` 冻结规则：`distortion_present=true ∧ quality_pass=true → distortion_exists`。干净数据上 `distortion_present=true`（joint E_CF 显著>0）、`quality_pass=true`（数据质量门）→ **机器 verdict 仍返回 `distortion_exists`**。
- 但该判据把 `distortion_present` 操作化为"joint E_CF > 0"，**无法区分"utility-preserving 失真"与"迁移失败"**——这正是此前 R4 指出的口径缺陷。科学定性必须以正交字段 `transfer_broken=true` 为准：**这是失败边界，不是 H1 的正向证据**。
- PI 不修改冻结判据；机器 verdict 与 `transfer_broken` 的并存须在论文/报告中如实披露，禁止下游只看 verdict 判"干净失真"。

### 3.2 §8 决策树分支判断

| 分支 | 当前状态 |
|---|---|
| "强基线接近 Self → 转边界研究" | **待 kd_only 结果**：若 kd_only 不 broken 且接近 Self → 触发；若 kd_only 也 broken → 不触发（见下）。 |
| "强基线有失真但机制无预测价值 → 报告现象" | 不适用（机制前提已塌）。 |
| "CF 改善 E_CF 但常规退化 → 报告权衡" | 不适用（无 CF 方法结果）。 |
| "效果仅在合成域成立 → 明确边界" | 部分适用（数据全合成），但当前主问题是迁移失败。 |
| "机制与方法均稳定优于强基线 → 投稿" | 未触发（无机制/方法）。 |

> **PI 择支（kd_only 出来前的暂定）**：MVP 对从"干净失真"翻转为"迁移失败"，已使**任何正向失真证据消失**。当前应走**失败边界研究**路线（§8 "失败条件研究 / 优先真实任务或非等深场景"的精神）。

### 3.3 kd_only 结果出来后的判读规则（预承诺，防事后择支）

- **情形 A：kd_only 也 broken（dual 坍塌、transfer_broken=true）** → 所有 tested mapper（affine/kd_only）在干净数据上都迁移失败 → **纯失败边界结论**；贡献(1)(2) 全部撤回，论文为"迁移失败边界 + 数据泄漏教训"的负面/实证结果论文。
- **情形 B：kd_only 不 broken、E_CF 小且接近 Self** → 触发 §8 第一条"强基线接近 Self → 转边界研究"；结论为"强行为基线可保持迁移效用，先前观察到的 gap 是数据缺陷导致的假象"——这是**重要的方法学负面结果**（数据泄漏如何制造虚假科学发现），贡献(1)(2) 同样撤回。
- **情形 C：kd_only 不 broken 但仍有稳定小 gap** → 唯一可能的正向证据回到 kd_only 自身（基线而非方法），仍不足以支撑贡献(1) 的"强基线未消除 gap"主张；按边界研究处理。
- **无论 A/B/C，贡献(3) 与方法层路线均不成立。**

---

## 4. 论文与投稿紧急指令

### 4.1 写作者立即执行

1. **撤回贡献(1)(2)**：删除所有"reproducible gap / utility-preserving distortion / V-consumption mechanism localization"的正向 claim；旧数据数值仅可作为"被数据缺陷推翻的历史结果"在披露段落提及，不得进入结论。
2. **主表切换**：用干净数据 `p1_clean_mvp_seed{0,1,2}` 的新数值（E_CF 6.9–8.5、dual 0.28–0.42、`transfer_broken=true`）；明确标注这是**失败边界**而非失真证据。
3. **论文重定位**：改写为**"跨模型 KV 迁移的失败边界 + 数据泄漏如何制造虚假科学发现"的实证/负面结果论文**——核心叙事变为：① 在修复泄漏/退化对/模板重合后，此前报告的 gap 反转为迁移失败；② 数据质量审计对 KV 迁移基准结论的决定性影响（方法学教训）；③ 失败边界的条件刻画（等深 MVP 对上 affine mapper 的迁移坍塌）。
4. **新增核心披露**：数据修复前后方向性翻转的完整对照表（旧 E_CF 1.93–2.12/dual 0.62–0.67/broken=false ↔ 新 E_CF 6.9–8.5/dual 0.28–0.42/broken=true）；冻结 verdict=`distortion_exists` 与 `transfer_broken=true` 的口径分离说明。
5. **主终点与 P3**：明确"主终点（成对 E_CF vs kd_only，CI 上界<0）未评估、方法层完全缺位"——并说明在当前 broken transfer 前提下方法层无意义，P3 已取消。**贡献(3) 维持 withheld**。
6. **边界/实证定位**：仍为 empirical/boundary study，但**内涵从"发现 gap + 机制定位"改为"失败边界 + 数据教训"**；任何残留的正向机制/方法措辞一律删除。

### 4.2 投稿时机

**继续暂缓**（承接 data_readiness_ruling），且现在的原因更强：核心贡献已被推翻，须完成论文重写 + kd_only 择支 + 审稿复核后方可考虑投递。

### 4.3 对外主张强度边界

- 可主张：数据质量对基准结论的决定性影响（有前后对照实证）；干净数据上 affine mapper 在 MVP 对的迁移失败边界。
- 不可主张：任何"反事实失真普遍存在""V 消费侧机制定位""方法改善 gap""跨模型/真实世界泛化"。
- 引用核验（§9）仍为投递前必做。

---

## 5. 审稿人立即介入指令

> **裁定：立即触发审稿人对抗性复核（可并行、不阻塞正在跑的 kd_only）。**

复核重点（"是否真为 broken transfer 而非实现 bug"）：

1. **实现 bug 排除**：核对干净数据重建后 mapper 训练/缓存注入路径是否与旧数据一致（commit `efc3ba3` 跑分代码与 HEAD 一致性、`git diff`、worktree clean）；确认 E_CF 升高/dual 坍塌不是数据重建引入的实现回归（如模板/实体变化导致 tokenization 或候选位置错乱）。
2. **broken transfer 判定稳健性**：独立重算 joint dual drop（0.4）、E_CF vs 控制组；特别核实 `info_attribution` 符号不一致现象（mismatch +1.48、zero +1.68 为正，random −0.13 为负，而 dual 坍塌）——判断 `transfer_broken` 标注是否稳健，是否存在"E_CF 方向保留但双文档答对率坍塌"的混合信号需更细致表述。
3. **统计合规**：bootstrap（seed/cluster 口径）、≥3 seed、联合报告、transfer_broken 正交字段与冻结 verdict 并存的披露；prereg（v2.1/v2.2 + 新统计口径文件）未篡改。
4. **冻结判据口径**：确认机器 verdict=`distortion_exists` 未被私自改动，仅正交字段标注；下游汇总须联合读取 `transfer_broken`。
5. **输出**：出具紧急复核报告，给出"broken transfer 判定可信度"结论（高/中/低）与是否需工程修复的判定，上报 PI。

若审稿判定为**实现 bug** → 立即停所有结论冻结，工程修复后重跑；若判定**可信** → 维持本裁决全部裁定。

---

## 6. 不改冻结判据

本裁决不修改任何冻结判据（`phase1_benchmark_decision.yaml`、`phase3_*`、`v2.1/v2.2`、`configs/protocol.yaml`）；机器 verdict 与 `transfer_broken` 的口径分离以论文/报告披露与新增版本文件（统计口径）处理，由有权限角色执行，PI 不回写。

---

## 7. 结论与即时执行摘要

- **科学判定**：原贡献(1) 立即冻结降级、贡献(2) 立即撤回 withheld（不等 P2）——旧正向信号源于数据缺陷，修复后翻转为 broken transfer。
- **重跑**：kd_only 继续（失败边界确认）；δ 复核暂停；P2 不启动；P3 维持暂停/实质取消。
- **择支**：暂定失败边界研究；kd_only 结果按 §3.3 三情形预承诺判读。
- **论文**：改写为"迁移失败边界 + 数据泄漏教训"的负面/实证结果论文；贡献(1)(2) 撤回、贡献(3) withheld；投稿继续暂缓。
- **审稿**：立即介入复核 broken transfer 可信度（排除实现 bug）。

**签署：PI / 课题组长（干净数据翻转紧急裁决 · 2026-11-23）**

# 反事实审计与数据质量门禁诊断框架规格书（V3.0 · 失败边界 / 数据泄漏教训的负面结果实证研究）

> 状态：**设计产出（承接 PI 最终收口裁决）**。本文把原 V2.0「CF-RCT 方法增益 + 机制定位」的算法/机制叙事，重写为**负面结果与方法论审计**叙事：核心对象不再是"训练一个降低 E_CF 的 Mapper"，而是**用 E_CF 成对反事实审计 + 控制组 + 数据质量门禁刻画跨模型 KV 迁移的失败边界，并揭示数据缺陷如何制造虚假发现**。
> 依据：`reports/review/meta_review/current_task_meta_review.md`、`reports/review/research_advisor/third_round_online_addendum.md`、`docs/decisions/{final_boundary_study_signoff,clean_data_reversal_ruling,anchor_confirmation,ai_dataset_final_ruling,agent_crosscheck_ruling}.md`、`configs/prereg/{stats_convention_v2.3,external_validity_v2.4,annotation_convention_v2.5,ai_generated_data_v2.6}.yaml`、`docs/protocol.md §4/§7/§8/§10`。
> 边界：只写设计；不改 `configs/prereg/**`、不改代码、不改运行产物、不改论文、不改主终点定义；**不重算任何统计**（文中引用的数值均为已冻结产物的记录值，出处随文标注）。Mock 数字一律不构成证据。

---

## 0. 研究定位（V3.0 相对 V2.0 的根本变更）

### 0.1 已删除的研究目标（V2.0 → V3.0）

| V2.0 目标 | V3.0 处置 | 处置依据 |
|---|---|---|
| CF-RCT / CF-RCT-lite / CF-RCT-mech 方法增益（贡献 3） | **删除为研究目标**；P3 永久放弃、贡献(3) withheld | clean 数据上 affine 迁移坍塌、kd 稳定非零 gap 但无方法主终点；`final_boundary_study_signoff §1.2/§4` |
| `L_KD/L_CF/L_local/L_reg` 作为"要优化的损失" | **删除**（原设计服务于已撤回的方法层）；下文只在"历史记录"中提及 | 同上；Huber δ 冻结流程随 P3 取消而失效 |
| K/V 四臂 + Routing/Consumption 分解 + Oracle 层/头/Token 移植作为**机制定位贡献**（贡献 2） | **删除为贡献目标**；P2 永久放弃、贡献(2) 撤回 | 机制对象（干净失真）不存在、旧证据污染；`clean_data_reversal_ruling §1.2` |
| "可复现 utility-preserving gap"（贡献 1） | **删除为正式贡献**；降为 kd 三 seed 的**探索性观察** | 贡献(1) 撤回；`final_boundary_study_signoff §1.2` 情形 C 细化 |

> **不把"加一个 loss / 多做一套评测 / 换一个 Mapper"自动成立为贡献**（`protocol.md §10`）。V3.0 没有任何可训练 Mapper 作为研究对象；affine 与 kd_only 均为**固定的对照基线**，不是待优化方法。

### 0.2 V3.0 的三个研究问题（均为审计/实证问题，非方法优化问题）

- **RQ1（失败边界）**：在修复数据缺陷后的干净数据上，tested mapper（affine）在单一等深 MVP 对上是否发生**迁移失败**（dual 坍塌、`transfer_broken=true`），而非早期声称的"utility-preserving 失真"？
- **RQ2（数据泄漏教训，方法学核心）**：退化对、跨 split 文档/实体泄漏、模板骨架重合如何制造**虚假的正向发现**？修复前后结论如何从"gap 存在"翻转为"迁移失败"？
- **RQ3（基线对照 / 探索性观察）**：强行为基线 kd_only 保持迁移 utility（dual 0.70–0.77）却仍有稳定非零 `E_CF` gap（6.4–7.2）——这是 **v2.3 exploratory 口径下的探索性观察**，不是贡献(1) 的恢复，也不进方法主终点。

### 0.3 贡献与阶段状态（冻结结论，本文只引用不改动）

- 贡献(1) 撤回、贡献(2) 撤回、贡献(3) withheld（`final_boundary_study_signoff §1.2`）。
- P0/E0 GO（终局）、P1 GO（终局）；**P2 / P3 / P4 永久放弃**（不重启）；P5 投递暂缓；G1 仅可选低优先级确认，**不纳入必做**（`third_round_online_addendum §3.2/§3.3`）。
- 论文定位：**失败边界 + 数据泄漏教训的负面/实证结果研究（empirical / boundary study）**，不是方法论文。

---

## 1. 硬约束（贯穿全部设计）

1. **严格 zero re-prefill**：Joint 是唯一报告路径；K-only / V-only / Self / Oracle 均为离线诊断臂，带 `deployable=false`，不进 Joint 推理图；每条 run 写 `zero_re_prefill=true`。
2. **封存 test 不评**：当前全部证据为 `eval_splits=["val"]`；**封存 test 从不评测**，无方法主终点、无"成对 E_CF vs kd_only 的 CI 上界<0"检验。不得为"救原研究"提前碰 test。
3. **判据先写后跑 / 不改冻结判据**：主终点定义、τ=1.0、self_threshold=0.1、v2.3–v2.5 口径均已冻结；v2.6 已冻结但为 not-activated（提案撤回、无适用对象），本文只引用；禁止按结果改阈值/换聚类单元/挑种子。
4. **E_CF 联合报告**：`E_CF` 永远与 `dual_correct` / `flip_consistency` / `coverage` / `info_attribution` 同报；`E_CF` 单独变化不构成"成功"或"失败"的充分证据。
5. **Oracle 隔离**：局部 Oracle 信号只允许离线诊断，不得进入任何推理图；本文不鼓励任何新的 Oracle 移植实验（P2 已放弃）。
6. **反事实分别诊断**：在 `d_A`、`d_B` 上分别诊断再比较差值；不可用单文档注意力误差替代反事实误差。
7. **机器 verdict 与科学定性分离**：`phase1_benchmark_decision.yaml` 把 `distortion_present` 操作化为"joint E_CF>0"，冻结 verdict 仍返回 `distortion_exists`；但科学定性以正交字段 `transfer_broken=true` 为准，二者并存须如实披露（`clean_data_reversal_ruling §3.1`）。
8. **v2.6 AI 数据提案已撤回**：经最终裁定撤回有条件 GO、not-activated，**不生成、无产物、仅作历史记录**（见 §5.3）；外部效度只保留 SQuAD（必要时 ARC）锚点，`real=0` 维持。

---

## 2. 记号与审计量（E_CF 的用途从"优化目标"改为"审计度量"）

| 记号 | 含义 | V3.0 用途 |
|---|---|---|
| `T` / `S` | 教师 / 接收学生（S 主权重冻结） | 固定对象，无训练 |
| `C_T(d)` / `C_S(d)` | 教师缓存 / 学生原生缓存 | `C_S(d)` 仅离线锚点 |
| `Ĉ_S(d)` | 固定 affine 映射（或 kd_only 行为蒸馏）后的缓存 | **对照基线**，非待训练模型 |
| `u=(q,d_A,d_B,a,b,m)` | 反事实评测最小单元 | F1–F6 切片；F5 非翻转、F6 条件扰动 |
| `g(C,q)=log P(A\|C,q)−log P(B\|C,q)` | 响应强度差 | 同一生成位置取 logits |
| `D_self` / `D_trans` | 原生 / 迁移反事实响应差 | 审计量 |
| `E_CF=\|D_trans−D_self\|` | 主审计量 | **描述失败边界 gap，不作为要最小化的训练目标** |
| `normalized_E_CF` | `\|D_trans−D_self\|/(\|D_self\|+τ)`，`τ=1.0`（仅引用冻结值） | 跨量纲归一，仅报告 |
| Self 有效子集 | `\|D_self\| ≥ 0.1`（仅引用冻结值） | `flip_consistency` 在此子集计算 |
| `transfer_broken` | 正交标注字段（由 dual drop≈0.4 单信号触发） | 失败边界定性依据；与冻结 verdict 分离披露 |
| `info_attribution` | 错配 / zero / random 无信息控制下的 gap 符号 | 信息归因审计；当前为混合信号（2 正 1 负，见 S4） |

> 注：原 V2.0 的 `Q_S/A_S/V_S`、`L_local`、`rank_units_by_repair` 等机制单元记号随 P2 放弃而不再用于贡献产出；若仅需刻画失败边界，可保留 Self/K-only/V-only/Joint 四臂作为**诊断臂**（见 §4.3），但不得写成机制定位。

---

## 3. V3.0 核心诊断框架（替代原 CF-RCT 训练骨架）

### 3.1 反事实成对审计管线（Algorithm A · 唯一"算法"）

```
Algorithm A  COUNTERFACTUAL_AUDIT_PIPELINE        # 无训练；纯审计
Input : 干净 val 反事实对 {u_i}（已过数据质量门禁 §3.3）；
        固定基线集合 B = {affine, kd_only}；控制组集合 C（§3.2）；
        冻结统计口径 v2.3（template_family 主聚类 + pair-level 敏感性）
Output: 失败边界 verdict + 数据审计报告（无"方法增益"输出）

  for each baseline b in B:
    for each u_i:
      D_self   ← g(C_S(d_A),q) − g(C_S(d_B),q)          # 离线锚点
      D_trans  ← g(Ĉ_b(d_A),q) − g(Ĉ_b(d_B),q)          # Joint 路径
      E_CF_i   ← |D_trans − D_self|
      记录 dual_correct / flip_consistency / coverage / info_attribution（d_A、d_B 分别打分）
    # 与控制组对比（错配 / zero / random / shuffled-target / self-identity / receiver-only）
    gap_vs_controls ← E_CF(b) − E_CF(control)             # 不得据"接近控制"夸大（见 S4）
    bootstrap ← v2.3：template_family 主 CI + pair-level 敏感性；簇数<24 → exploratory=true
  failure_boundary ← (affine 迁移失败：dual 坍塌 + transfer_broken=true)
                     ∧ (kd 保 utility：dual 0.70–0.77 但 gap 稳定非零，exploratory)
  return 双 bar 对照 + 控制组表 + 证据强度边界（§6）
```

要点：
- **无 `L.backward()`、无可训练参数、无 δ / λ 调参**。原 `Algorithm 1/2/3`（训练骨架 / Joint 推理 / Oracle 排序）和 §5 Huber δ 冻结流程**随方法层放弃而整体删除**；如读者需要历史出处，见 V2.0 版文档（已被本文取代）。
- 每条 run 记录 `zero_re_prefill`、`protocol_version`、git hash、配置指纹、逐对 schema（`protocol.md` 附录 A）。

### 3.2 控制组（信息归因，沿用冻结口径）

七类最小控制（沿用 `protocol.md §4.4`）：`correct` / `mismatch derangement` / `random` / `zero` / `shuffled-target` / `self-identity` / `receiver-only adapted`。F5 为非翻转负控、不入翻转分母；flip 分母按 v2.3 排除 F5+F6 = 398（冻结值，仅引用）。当前记录在案的混合信号：seed0 `joint E_CF≈6.90` 仍低于 mismatch 8.38 / zero 8.58，**不得写"达到无信息水平"**（S4，`final_boundary_study_signoff §2`）。

### 3.3 数据质量门禁（方法学教训的核心，RQ2）

审计维度（修复前后对照的判据，数值均为已冻结审计产物记录，出处 `reports/data/{data_readiness_audit,data_fix_report,acceptance_checks}.json`）：

| 维度 | 旧数据（已 superseded） | 干净数据（权威） |
|---|---|---|
| 退化必须翻转对 | 18 | 0 |
| 跨 split 逐字泄漏（含 train↔test 整对） | ≥15 组 | 0 |
| 实体池重叠 | 全共享 | 0 |
| 模板骨架 | 重合、簇退化为逐对 i.i.d. | 已修复；flip 分母排除 F5+F6 = 398 |
| 结论方向 | "gap 存在 / H1 成立" | "迁移失败 / 失败边界" |

> 该前后对照是 RQ2 的**主证据**：它证明数据缺陷可以**制造**虚假科学发现，修复后结论发生方向性翻转（`clean_data_reversal_ruling §0/§4`）。本文不重算这些统计，只引用冻结审计产物。

### 3.4 证据强度边界（S4/S5，写作者必守）

- joint `E_CF` **大幅升高、接近但未超过**错配/零控制，伴随 dual 坍塌（不是"达到无信息"）。
- `transfer_broken` 由**单一信号（dual drop）**触发；info 归因 seed0 为 2 正 1 负（混合信号）。
- 所有 clean CI 在 v2.3 下为 **exploratory**（仅 8 个 `template_family` < 24）、**单一 MVP 等深对**、**纯合成域**、**封存 test 未评**。
- 禁止"强显著性 / 跨模型泛化 / 因果 / 真实世界 / 可复现 gap"等措辞。

---

## 4. 诊断臂（保留为失败边界刻画工具，非机制贡献；P2 已放弃）

- **K/V 四臂**：Self / K-only / V-only / Joint（带 `deployable` 标记）。用途：验证"K/V-only 近 Self、仅 Joint 坍塌"→ 支持"迁移失败而非跑分实现坏"（`clean_data_reversal_emergency_review`）。**这是稳健性诊断，不是 V-consumption 机制定位**。
- **Routing/Consumption 分解 `Ô−O_S=(Â−A_S)V_S W_O + Â(V̂−V_S)W_O`**：仅作**局部代数恒等式自检**，不得解释为全模型因果分解；不作为新实验目标（原 E2 随 P2 放弃）。
- **Oracle 层/头/Token 移植、对称 Key 四目标**：P2 永久放弃，不再启动；旧证据（repair 0.275–0.350 等）建立在污染数据上，须撤回，不得进论文主表。

---

## 5. 统计口径与外部效度（沿用冻结版本，不重算、不回写）

### 5.1 v2.3（主统计口径）
- `template_family` 为**主聚类单元**；**pair-level 敏感性必须同时报告**；`min_clusters_for_inference=24`，簇数<24 → `exploratory=true`（当前 8 族）。
- flip 分母排除 F5+F6 = 398（冻结值）；`forbidden_after_freeze`：不得按结果改聚类单元、不得只报 pair-level CI、不得回写旧文件。
- 当前全部证据为 val-only；kd 三 seed 的 C 类判读须统一为 v2.3 簇级口径（或明确标注 pair-level 为敏感性，见 meta_review §3.2 的口径混用提示），**由 PI/审稿人出说明，本文不重算**。

### 5.2 v2.4（锚点 / 真实文档外部效度）
- 主聚类单元 `source_document_or_topic_cluster` + pair-level 敏感性 + min 24 / exploratory；预承诺三情形：`reinforce_external_validity` / `narrow_scope` / `exploratory_disclosure`。
- **仅增强外部效度，不替换合成主实验、不重跑冻结主终点、不恢复任何已撤回贡献**。SQuAD 锚点仅 seed0、仅评测、不改写/再发布语料。

### 5.3 v2.5 / v2.6（校验主体与 AI 数据）
- v2.5：real split 校验一律为 `automated_agent_crosscheck`（两独立 agent + 第三 agent ≥20% 抽检），**不是人类标注**；禁用 `annotator_*` 等人类身份字段；外部效度弱于真人标注，须披露。
- v2.6：按 `ai_dataset_final_ruling.md`，HellaSwag 种子 AI 数据提案的**有条件 GO 已最终撤回**，状态 **not-activated / 无适用对象**——**不启动生成、无产物、仅作历史记录**。它不是探针、不是数据工作包、不填补 `real=0`、不恢复贡献。外部效度仅由 **SQuAD 主锚点（必要时 ARC 辅锚点）** 承担，`real=0` 维持受阻披露。

---

## 6. 图表规划（更新：保留前后对照，删除机制/方法图）

| 规划项 | V3.0 处置 | 来源 |
|---|---|---|
| 数据审计前后对照表 | **保留（核心方法学证据）** | §3.3 |
| 干净数据三 seed 表（affine 失败 + kd 情形 C） | **保留（主实证证据，标注 exploratory）** | P1 产物 |
| 控制组 / 信息归因表 | **保留** | §3.2 |
| 外部锚点表（SQuAD，必要时 ARC） | **保留（增强外部效度，不恢复贡献）** | §5.2 |
| 机制热图（原图 5：层/头反事实误差 + Oracle 修复） | **删除**（P2 永久放弃、证据污染） | §4 |
| 方法消融图（原图 6：KD/CF/机制约束） | **删除**（P3 永久放弃、贡献(3) withheld） | §0.1 |

---

## 7. 交接

- **给工程师**：本版无新训练/新 Mapper 任务；只执行配套 `docs/experiment_design_E0_E7.md` 中已授权的收尾与锚点评测（SQuAD，必要时 ARC）；v2.6 AI 数据提案已撤回、无产物，不实现任何生成脚本，不得碰封存 test。
- **给 PI / 审稿人**：v2.6 AI 数据提案已按 `ai_dataset_final_ruling.md` 最终撤回、not-activated、无产物、仅历史记录，外部效度只靠 SQuAD（必要时 ARC）锚点、`real=0` 维持——本设计与该裁定已一致，无残留处置项；kd 三 seed 的 v2.3 簇级口径由 PI/审稿人出说明，本文不重算。
- **给写作者**：方法/机制素材从本框架 §3–§5 取，贡献措辞严格按 `final_boundary_study_signoff §3.2` 可写/禁写清单；图表按 §6 取舍。

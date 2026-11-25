# 最终收口裁决：失败边界 / 数据泄漏教训研究（V2.0 · 终稿）

> 裁决人：PI / 课题组长。日期：2026-11-23。
> 性质：最终收口裁决（承接 `clean_data_reversal_ruling.md` 及其 §3.3 预承诺 A/B/C）。
> 依据：`reports/review/clean_data_reversal_emergency_review.md`（翻转可信，高）、`reports/clean_data_rerun_summary.json`、`reports/engineer_status.md §13`、`reports/runs_index.json`、`reports/runs/{p1_clean_mvp_seed*,p1_kd_clean_mvp_seed*,e0_clean_mvp_seed0}/metrics.json`、`configs/prereg/stats_convention_v2.3.yaml`、`papers/readkv_v2_draft/main.tex`（负面结果重写稿）。
> 本裁决只写决策文档，不改 `src/**`、`reports/runs/**`、冻结判据、数据或论文；不写代码、不跑实验。

---

## 1. 情形 C 确认与最终科学定性

### 1.1 情形 C 判读确认

审稿复核已确认翻转可信（高，跑分代码逐字未变、唯一变化为数据修复 + 一个 P1 不调用的 P3 readout、E0 干净复验 PASS、Self/Identity 锚点更健康）。kd_only 干净三 seed 结果：

| seed | E_CF [CI] | Self dual | joint dual | dual_drop | flip | transfer_broken |
|---|---|---|---|---|---|---|
| 0 | 6.388 [5.360, 7.400] | 0.817 | 0.700 | 0.117 | 0.942 | false |
| 1 | 6.479 [5.419, 7.539] | 0.900 | 0.733 | 0.167 | 0.906 | false |
| 2 | 7.211 [6.078, 8.322] | 0.783 | 0.767 | 0.017 | 0.925 | false |

对照 affine（p1_clean）：E_CF 6.9–8.5、joint dual 0.28–0.42、`transfer_broken=true`。据此逐条核对 PI §3.3 预承诺：

- **非 A**：kd 不 broken（`transfer_broken=false`、dual_drop 均<0.2）；
- **非 B**：kd 不接近 Self（E_CF 6.4–7.2，template-family 与 pair CI 下界均远离 0）；
- **是 C**：kd 不 broken 但仍有**稳定非零 gap** → **边界研究**。

> **PI 确认：最终定性 = 情形 C → 失败边界研究。** 完整科学结论为三条：(i) tested affine mapper 在干净数据上于等深 MVP 对发生迁移失败（dual 坍塌、broken transfer）；(ii) 强行为基线 kd_only 保持迁移效用（dual 0.70–0.77、broken=false）却仍有稳定非零反事实 gap；(iii) 旧数据的"gap/机制"正向信号是数据泄漏/退化对/模板重合造成的假象——**方法学教训**。

### 1.2 贡献状态（维持紧急裁决，含情形 C 细化）

| 贡献 | 最终状态 | 说明 |
|---|---|---|
| **贡献(1) 评价层** | **维持撤回**（针对原 affine/旧数据 "reproducible utility-preserving gap" 主张——已证伪） | 见下方情形 C 细化：kd 的干净 gap 作为**探索性观察**记录于边界研究，**不恢复为 §10 正式 claim**。 |
| **贡献(2) 机制层** | **维持撤回 withheld** | 机制对象（干净失真）不存在；旧 P2 证据建立在污染数据上；P2 未重跑。 |
| **贡献(3) 方法层** | **维持 withheld** | 主终点未评估、P3 取消、无新方法证据。 |

**情形 C 细化裁定（重要，防过度解读两个极端）**：kd 干净数据呈现的 "dual 保持 0.70–0.77 + E_CF 稳定非零 6.4–7.2" 是一个**与旧（虚假）信号不同的、干净的探索性观察**——它提示"在 utility 保持的强基线上，反事实功能保真仍有 gap"。但 PI **不据此恢复贡献(1) 的正式 claim**，理由：(i) v2.3 下 `exploratory=true`（仅 8 个 template_family < 24，template-family CI 宽、效力弱）；(ii) 单一 MVP 等深对、纯合成域；(iii) 属强基线相对 Self 的 gap，非"新方法与强基线成对对比"的主终点；(iv) P3 取消、无跨模型/真实文档佐证。处理：在失败边界论文中**如实报告为探索性观察**，不写成 "reproducible gap" 的正向贡献；若日后补足 (i)–(iv)，由 PI 在新证据上重新裁定是否恢复限定的评价层贡献。

---

## 2. 审稿收尾项 S1–S5 逐项处理

| 项 | 处理决定 | 执行方 | 是否阻塞方向/投递 |
|---|---|---|---|
| **S1** clean run 未记录数据哈希 | **必须补**：以 metadata 勘误方式把数据 sha `f910f1f1…a894a` 绑定至 7 个 clean run（新勘误文件/新 manifest 字段），不改冻结 `scores.jsonl`/`config.json` | 工程师 | 溯源收尾；投递前必须 |
| **S2** v2.3 哈希一致性 | **部分已闭环 + 一残留**：v2.3 已回填 `recomputed_value=398` 并由 PI commit `6413ba0` 锁定（现 sha `e44c6acb…`），解决"冻结后回改无版本记录"疑虑；**残留**：`data/tasks/manifest.json`/`acceptance_checks.json` 中 `stats_convention_v2_3_sha256` 仍为回填前 `5200940c…`，须同步为 `e44c6acb…` 或加注"回填前 5200940c → 回填后 e44c6acb，因 PI 回填 flip 分母 398，commit 6413ba0"，消除下游审计假阳性 | 数据工程师（manifest）+ PI 确认 | 溯源收尾；投递前必须，不阻塞方向 |
| **S3** runs_index 更新 | **采信已闭环**：采信工程师已更新至 26 run（旧 19 标 superseded、新 7 权威）；PI 复核以最终 `reports/runs_index.json` 为准——若 `consistency_check` 仍报 clean run 非权威或旧 run 未标 superseded，须再修 | 工程师（已完成）/ 审稿复核 | 投递前确认 |
| **S4** 措辞精度 | **必须在论文中修正**：改为"joint E_CF 大幅升高、**接近但尚未超过**错配/零缓存控制（seed0: joint 6.90 vs mismatch 8.38 / zero 8.58），伴随 dual 坍塌 0.4；info 归因 2 正 1 负"——不得写"E_CF 与控制相当/达到无信息水平"。broken transfer 定性仍由 dual 坍塌充分支撑 | 写作者 | 投递前必须（强制） |
| **S5** 单信号 + exploratory 强度边界 | **必须披露**：明确 `transfer_broken` 由单一信号（dual drop）触发、`exploratory=true`（8 族<24）、单一 MVP 等深对、合成域；禁止"强显著性/跨对泛化/跨模型"主张 | 写作者 | 投递前必须 |

S1–S5 均为溯源/披露层收尾，**不改变第 1 节方向裁定**；审稿侧"翻转可信（高）"结论维持。

---

## 3. 写作者最终定稿指令 + 贡献表述清单

### 3.1 定稿动作

1. **填 kd 三 seed**：把 PENDING 的 kd 结果补入（E_CF 6.388/6.479/7.211，joint dual 0.700/0.733/0.767，flip 0.942/0.906/0.925，`transfer_broken=false`，dual_drop 0.117/0.167/0.017）；明确与 affine 的对照（kd utility 保持 vs affine 坍塌）。
2. **修正 S4 措辞**（强制）：按 §2 S4 精确表述。
3. **情形 C 探索性观察**：按 §1.2 细化，把 kd 非零 gap 写为"utility 保持基线上的探索性 gap 观察"，**不**写成贡献(1) 的恢复或 "reproducible gap"。
4. **强度边界**（S5）：保留 exploratory（8 族<24、CI 宽、下界>0 但非强推断）、单 MVP 等深对、合成域、`transfer_broken` 单信号触发；机器 verdict=`distortion_exists` 与 `transfer_broken=true` 口径分离说明。
5. **维持定位与暂缓**：负面结果 / 失败边界 + 数据泄漏教训的 empirical study；贡献(1)(2) 撤回、贡献(3) withheld；投稿暂缓。
6. **引用核验**：KV-Lingo/CacheLink 按协议 §9 投递前核实版本/日期/口径。

### 3.2 贡献表述最终清单（可写 / 禁写）

**可写**：
- "On clean data, the tested affine mapper fails to transfer usefully on the equal-depth MVP pair (dual-side correctness collapses to 0.28–0.42; flagged `transfer_broken`)."
- "A data-quality audit (degenerate pairs, cross-split document/entity leakage, structural template overlap) reversed the earlier reported gap into a transfer failure — a methodological caution for KV-transfer benchmarks."
- "The strong kd_only baseline preserves transfer utility (dual 0.70–0.77) yet retains a stable, exploratory counterfactual E_CF gap (6.4–7.2); reported as an exploratory observation on a single synthetic pair."
- "All clean CIs are exploratory under the v2.3 convention (8 template_family clusters < 24); no strong-inference or cross-pair claim is made."

**禁写**：
- ✗ 任何 "reproducible gap / utility-preserving distortion" 作为**正式贡献**（贡献(1) 已撤回）；
- ✗ "localized mechanism / V-consumption cause"（贡献(2) 已撤回）；
- ✗ "method reduces the gap / improves over kd_only / without-target-re-prefill at inference"（贡献(3) withheld）；
- ✗ "E_CF reaches / matches no-information controls"（S4：实测仍低于控制）；
- ✗ "across model pairs / robust / causal / real-world / generalizable"（S5：单对、合成域、exploratory）；
- ✗ "strong statistical significance"（exploratory）。

---

## 4. P0–P5 最终阶段状态

| 阶段 | 最终状态 | 说明 |
|---|---|---|
| P0 / E0 | **GO（终局）** | 干净数据 E0 复验 PASS（cosine 1.0、KL 0、EM 0.975、round-trip、zero-re-prefill、2.2e-16≪效应/3）。 |
| P1 基准 | **GO（终局）** | 干净三 seed；定性为 affine 迁移失败边界 + kd 情形 C；机器 verdict 与 `transfer_broken` 分离披露。 |
| P2 机制 | **正式取消**（不重启） | 前提（干净失真）已塌，旧证据污染；审稿复核确认无需再投算力。 |
| P3 方法 | **正式取消**（非仅暂停） | 方法层无目标、三 δ 负值、翻转后无意义。 |
| P4 泛化 | **正式取消 / NO-GO** | 上游取消、无跨模型/真实文档证据。 |
| P5 投递 | **暂缓（Conditional，未签 off）** | 门槛见 §5。 |

**重启条件**（明确，避免模糊）：
- **P2 重启**：仅当重新构造出干净、utility-preserving 的失真数据（与当前 broken-transfer 数据不同）并经 PI 新裁决；当前无此计划。
- **P3 重启**：仅当人工明确把问题**重定义为"修复 broken transfer"**（这是与 V2.0 "反事实保真"不同的科学问题）并提供新资源/新判据（新增版本文件）；否则永久取消。
- 无上述条件，P2/P3/P4 不再启动。

---

## 5. 投递决策与暂缓条件清单

> **裁定：维持暂缓，不批准现在投递。**

**暂缓期间必须完成（全部）**：
1. S1 数据哈希绑定勘误（§2）；
2. S2 manifest 的 v2.3 sha 同步/加注（§2）；
3. S3 runs_index 26 run 最终确认（§2）；
4. S4 措辞精度修正（§2，强制）；
5. S5 强度边界披露（§2）；
6. kd 三 seed 数值填入 + PENDING 清零（§3）；
7. 贡献表述清单逐条核对（§3.2）；
8. 引用核验（协议 §9）。

**增强项（非当前边界研究硬门槛，但显著影响接收档位）**：
- M4 真实文档 80–150 对（来源/许可见 §6）；
- 外部锚点：标准 QA（HellaSwag/ARC 子集）上 Joint vs kd 常规质量对照，支撑"E_CF gap ≠ 常规退化"；
- 结构未见模板臂（M3 已部分修复至 56 族/24 结构，v2.3 仍标 exploratory，需在论文解释）。

**若现在投的风险**：核心贡献刚被推翻、kd 处仍 PENDING、S4 措辞夸大（"与控制相当"）、S1/S2 溯源缺口（数据哈希未绑定、v2.3 哈希不一致）、v2.3 exploratory 未披露——这些是可被审稿人逐条击穿的低级缺陷，且负面结果论文对强度边界要求极高，仓促投递会直接损害可信度与接收档位。

---

## 6. 人工决策事项（真实 PI）

1. **真实文档来源与许可（M4）**：80–150 对真实文档的采集渠道、授权合规、人工核验人日（5–10）；硬约束要求记录来源/许可并经 PI 裁决后方可进入主实验。
2. **额外人日投入**：S1–S5 收尾（低成本）+ 可选 M4/外部锚点（高成本）；是否批准。
3. **投递时机**：修复 S1–S5 即投"失败边界 + 数据教训"边界研究 ，还是连 M4/外部锚点一起补成更强实证版本再投；负面结果论文的 venue 定位。
4. **是否放弃 P3/方法层路线**：PI 已正式取消 P3；是否确认长期放弃 V2.0 方法论文，或转为以"修复 broken transfer"为新问题另立课题（需新判据/新资源）。

---

## 7. 结论与给各角色的最后指令

- **情形 C 确认**：affine 迁移失败边界 + kd 稳定非零 gap（探索性观察）+ 数据泄漏教训；贡献(1) 撤回、贡献(2) 撤回、贡献(3) withheld 全部维持；论文为**失败边界 / 数据泄漏教训的负面结果实证研究**。
- **工程师**：闭环 S1（数据哈希绑定）、S3 确认、S2 中 manifest 侧同步（数据工程师）；无新实验。
- **写作者**：填 kd 三 seed、强制修正 S4、按 §3.2 清单定稿、保留探索性/单对/合成域边界、投稿暂缓。
- **审稿人**：确认 S1–S5 闭环后在重开 P5 时出具最终合规意见。
- **阶段**：P0/P1 GO；P2/P3/P4 正式取消；P5 暂缓（8 项门槛清单）。
- **人工决策**：真实文档许可、额外人日、投递时机、是否放弃 P3 路线。

**签署：PI / 课题组长（失败边界研究最终收口裁决 · 2026-11-23）**

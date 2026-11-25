# P0/E0 + P1 阶段 Go/No-Go 最终裁决（反事实功能保真 V2.0）

> 裁决人：PI / 课题组长。日期：2026-11-23。
> 依据：审稿报告 `reports/review/stage_p1_review.md`（2026-11-23，第 1 轮）、`docs/decisions/p0_direction.md`（§3.2 / §3.3 / §4 / §7）、`docs/protocol.md` V2.0（§1.2 / §4.5 / §8 / §9 / §10）、`configs/prereg/*`（含 `phase3_loss_config_v2.1.yaml`）、`reports/engineer_status.md`、`papers/readkv_v2_draft/main.tex`。
> 本裁决只写决策文档，不修改任何代码、`reports/runs/**`、冻结判据或论文源文件。
> 证据边界：证据仅到 P0/E0 与 P1（MVP 等深 + 主验证非等深，共 8 个真实 GPU run）；P2–P5 无产物。

---

## 0. 风险编号映射（先澄清，避免误裁）

任务摘要的风险编号与审稿报告原始编号不一致，本裁决**以审稿报告编号为准**，并在每项前给出对照：

| 本裁决议题 | 审稿报告编号 | 任务摘要编号 |
|---|---|---|
| git_hash 不指向产出代码（可复现性阻塞） | R1 | R1 |
| consistency_check 盲点 / 审计假阳性 | R2 | R4 |
| kd_only 未跑，gap 未证"未被强基线消除" | R3 | R2 |
| quality_pass 含糊 / broken transfer 判为 distortion_exists | R4 | R3 |
| bootstrap 种子不一致 | R5 | R5 |
| 主验证 model_pair 误标 | R6 | R6 |
| E0 效应尺度 / one-shot 残差 | R7 | R7 |
| engineer_status 符号笔误 | R8 | R8 |

---

## 1. 阶段 Go/No-Go 决议总表

| 阶段 | 决议 | 性质与前置条件 |
|---|---|---|
| **P0 / E0 实现门** | **GO（确认）** | E0 数值判定成立（cosine 1.0、KL 0、round-trip bit-identical、zero-re-prefill 80/80、误差上限 2.2e-16 ≪ 效应/3）；R7 尺度 caveat 不改变判定。可复现来源（R1）为 P5 阻塞项，不推翻 E0 放行。 |
| **P1 基准 — 作为证据产出 / 边界定位** | **条件 GO（Conditional GO）** | 可记录、可用于论文边界定位：MVP affine/ridge mapper 存在稳定 gap；主验证非等深为迁移失败边界。条件见 §2–§5。 |
| **P1 基准 — 作为"进入 P2 的失真前提"** | **NO-GO** | 直至 kd_only 补跑并按冻结 `phase1_benchmark_decision` 重判、R1 可复现闭环、R4 verdict 口径勘误完成。当前 `distortion_exists` 不足以放行 P2。 |
| **P2 机制** | **NO-GO** | 依赖上述 P1 前提闭环；且 E2 未运行、Huber δ 最终值未按 v2.1 在验证集锁定。 |
| **P3 方法** | **NO-GO** | P2 未闭环；δ 未锁定；封存测试未运行；kd_only 主终点未评估。 |
| **P4 泛化** | **NO-GO** | P3 未闭环；未见模板 / 真实文档 / 封存 test 未运行。 |
| **P5 成稿 / 投递** | **NO-GO** | R1 未修复前贡献(1) 的 "reproducible" 措辞不成立；全部条件未闭环；贡献(2)(3) 维持 withheld。 |

一句话：**P0 GO；P1 条件 GO（仅证据/边界层）；P2–P5 NO-GO。**

---

## 2. R1（阻塞）裁决 — 可复现性

**事实认定**：8 个 run 的 `config.json` 记 `git_hash=53e9bc5`，该 commit tree 仅含文档/prompts；实际跑分代码 `experiments/P{0,1}_gpu.py`、`src/readkv/models/gpu_backend.py`、`hooks.py`、`cf_pipeline.py`、`scripts/gen_teacher_cache.py` 为 untracked 或仅有工作区修改。checkout 该 hash 无法复现。审稿人正确指出：**数字本身不失效**（真实 GPU 产物、可重算），失效的是来源可追溯性与 "reproducible" 措辞。

**PI 裁决（强制，最高优先级）**：

1. 工程师须将生成这 8 个 run 的**精确代码状态**提交为一个新的、可追溯的 commit（含上述全部跑分入口、GPU 后端、hooks、管线、缓存脚本与依赖清单），并确保该 commit 相对工作区在跑分路径上无未提交修改。
2. 在此 commit 之后二选一：
   - **方案 A（推荐）**：以**新 run_id** 重跑 P0/E0 与 P1，使每个 `config.json` 的 `git_hash` 指向真实产出该结果的代码且工作区 clean。新 run 作为论文主表唯一证据来源；旧 run 标注为 `superseded / provenance-unverified`，不得用于主结论。
   - **方案 B（备选，仅在重跑成本不可接受时）**：不重跑，但须以**新增 metadata 勘误文件**把 `git_hash` 更新为该新 commit，并附**逐文件哈希对照**，证明该 commit tree 与产出 run 时代码状态一致；仅当对照完整、可核验时方予接受。
3. **禁止**回改任何冻结 `reports/runs/**` 产物（含 `scores.jsonl`、`config.json`）——勘误只能以新 run_id 或新增勘误文件实现。
4. **R1 闭环前**：论文不得使用 "reproducible" 形容词（含摘要与贡献(1)）；P5 维持 NO-GO；P2 亦不得引用该词。
5. **是否支撑"可复现"措辞**：只有完成 1+2（A 或 B）且通过第 2 轮复审后，方可恢复 "reproducible" 表述；否则一律降为 "real-GPU benchmark on an as-run working tree（provenance under remediation）"。

---

## 3. kd_only 缺位（报告 R3 / 摘要 R2）裁决

**事实认定**：P1 映射臂为 affine（closed-form ridge 初始化，`mapper_trainable_params=0`），仅与 Self / Identity / 错配 / 随机 / 零缓存对照；`primary_baseline=kd_only` 未跑。`distortion_present=true` 由 "joint E_CF 显著 > 0（Self=0 锚点）" 触发，**不是**由"强行为基线仍有 gap"触发。协议 §1.1 RQ1 的证据要求明确是"**既有强 Mapper** 的反事实误差显著大于原生/Identity 数值残差"。

**PI 裁决（强制进 P2 前条件）**：

1. **kd_only 必须在进入 P2 前补齐。** 理由：现有 affine 零参数 mapper 不构成强行为基线，无法检验 H1 中"高常规任务分数不保证反事实保真"的"高分数"前提，因此 `phase1_benchmark_decision` 的 `distortion_present` 未被按设计意图检验；不放行 P2 主线。
2. 补跑范围：至少 **MVP 对 (1.7B→0.6B)** 跑 kd_only；理想再补 consumer / score（协议 §7 E1 的强基线族）。主验证对 (4B→1.7B) 建议一并跑 kd_only，以判定该对是"强基线仍失真"还是"迁移彻底失败"（见 §4）。补跑仅用 train/val，**不得触碰封存 test**；判据沿用已冻结的 `phase1_benchmark_decision.yaml`，不新设规则。
3. **按补跑结果走两条路**（与 §7 决策树联动）：
   - 若 kd_only 的相对 Self gap 消失/接近 Self → 触发 §8 第一条，**取消 P2/P3 主线**，转边界 / 失败条件研究；
   - 若 kd_only 仍有稳定 gap → 满足 RQ1 证据前提，方可进入 P2（同时仍须 R1 闭环 + δ 锁定）。
4. **若不补跑**：贡献(1) 与主终点必须降级表述为 "for the affine/ridge mapper tested here"，明确 "whether stronger behavioral baselines (kd_only, consumer, score, ridge) retain this gap is left to future work"；P1 不得作为进入 P2 的失真前提放行，仅作为"affine mapper 的边界现象报告"；P2/P3 保持 NO-GO。

---

## 4. quality_pass / distortion_exists 口径（报告 R4 / 摘要 R3）裁决

**事实认定**：主验证 3 seed 的 joint dual 从 Self 0.65–0.78 坍塌至 0.28–0.30、flip 0.49–0.56、joint E_CF 接近/高于错配与零缓存控制、info_attribution 多为负——这是迁移失败。但 pipeline 因 `data_quality.gate=pass` 置 `quality_pass=true`，冻结判据据 `{distortion_present:true, quality_pass:true}` 返回 `distortion_exists`；论文 §5.4 已正确定性为 broken transfer，但机器可读 `runs_index.json` 的 verdict 会误导下游自动汇总。

**PI 裁决**：

1. **不改冻结判据** `phase1_benchmark_decision.yaml`。冻结规则在给定输入下的输出 `distortion_exists` 本身无误；问题是 `quality_pass` 在实现层被绑定到"数据质量门"这一含义，与"模型迁移效用"混淆。
2. **口径澄清（写入新增说明，不回写冻结文件）**：明确 `quality_pass` 在本管线中 = **数据质量门 pass**（split 隔离、模板无重叠、注释一致），**不含**模型迁移效用门槛；它不构成对"失真是否为 utility-preserving"的判定。
3. **实现层勘误**：要求工程师在机器可读产物中**新增一个正交诊断字段**（如 `transfer_broken: true` 或 `quality_outcome: failure_boundary`），依据客观观测标注（例如：joint dual 较 Self 下降 ≥0.2、joint E_CF ≥ 错配/零缓存控制、info_attribution 多数为负）。该字段**仅作注释**，不得改写冻结 verdict 本身；下游汇总须联合读取该字段，禁止只看 verdict 就判定"存在干净失真"。
4. **是否新增 `broken_transfer` verdict 类别**：**不新增到冻结判据**（那属改判据）。仅在实现层 verdict 标签 / 新增版本说明中体现；若日后要提升为正式判据类别，须另立版本文件并说明理由。
5. **证据效力裁决**：主验证对的 P1 结果**不计入 H1"失真存在"的正向支持**——它是 broken transfer 的失败边界记录；高 E_CF 在此反映迁移失败，而非 utility-preserving 的反事实失真。候选失真证据目前仅 MVP 对，且仍受 §3 的 kd_only 补齐条件约束。
6. 写作者：论文 §5.4 的 broken-transfer 定性正确，保持；补一句"机器可读 verdict 与叙事的差异"说明。

---

## 5. consistency_check 与 model_pair 勘误（报告 R2 / R6；摘要 R4 / R6）裁决 + 审稿轮次

**事实认定**：`consistency_check` 仅查键存在与 `zero_re_prefill is True`，不校验 git hash 真实性、工作区 clean、`model_pair` 与 teacher/student 路径及 layer_map 一致性 → R1/R6 均假阳性通过。主验证三 run 的 `model_pair` 误标为 `qwen3-1.7b-to-0.6b`（实为 4B→1.7B，不影响任何指标，不阻塞）。

**PI 裁决**：

1. **consistency_check（R2）**：要求工程师扩展审计项——(a) 比对 `config.git_hash` 与 `git rev-parse HEAD` 并检测跑分路径工作区脏状态；(b) 校验 `model_pair` 与 teacher/student 路径、layer_map 层数一致；(c) 校验 `protocol_version` 与 prereg 版本兼容。此为审计代码增强，**不是改冻结判据**，允许。
2. **model_pair（R6）**：要求工程师以**新增 metadata 勘误文件或新 run_id 索引**写入 `model_pair_corrected="qwen3-4b-to-1.7b"` 并标注依据（路径 + 36→28 layer map）；**不动冻结 `scores.jsonl`**。写作者当前"正文按 4B→1.7B + §5.2 脚注披露"的过渡做法予以认可，勘误发布后更新脚注引用。
3. **是否触发审稿第 2 轮**：**是，触发第 2 轮**（`docs/agent_team.md §6.1`：每阶段写改审最多 2 轮，第 3 轮由 PI 直接裁决）。触发条件为"工程师完成 R1 + kd_only 补跑 + R4 口径勘误 + R2 审计增强 + R6 勘误"之后，对 P0/E0 与 P1 做**聚焦复审**：验证 R1 可复现、kd_only 重判结果、verdict 注释字段、扩展后的审计脚本、model_pair 勘误。第 2 轮仍未解决，则由 PI 直接裁决，不再进入第 3 轮。修复未完成时**不启动第 2 轮**，各阶段维持 §1 的 NO-GO 状态。

---

## 6. 次要风险 R5 / R7 / R8 裁决

- **R5（bootstrap seed）**：要求工程师统一 pipeline 与审计脚本的 bootstrap seed 并在 run config 记录；写作者补 "CI endpoints are bootstrap-seed dependent; point estimates are exact"。CI 差 ≤0.05、结论不变，不单独阻塞，但须在 P5 前闭环。
- **R7（E0 尺度 / one-shot 残差）**：披露充分，判定稳健，无需改判据或重跑；后续任何 one-shot 部署路径单独测量 kernel 差异。
- **R8（engineer_status §2.2 符号笔误）**：要求工程师更正文案为 `info_attribution = 控制组 E_CF − joint E_CF`，避免外部读者反向解读。

---

## 7. `docs/protocol.md §8` 决策树分支裁决

**结论：当前没有任何一条决策树分支被完整触发；证据仅到 P1 基准且强基线缺位，处于"证据不足 / 未定分支"状态。**

| 分支 | 是否触发 | 依据 |
|---|---|---|
| 强基线在反事实任务上已接近 Self → 边界研究 | **未触发** | kd_only 未跑，无法判断是否接近 Self（§3）。 |
| 强基线有失真，但机制诊断无跨样本预测 | **未触发** | P2 机制诊断未运行。 |
| 机制有效，CF 方法不优于 KD → 方法降级 | **未触发** | P2/P3 均未运行。 |
| CF 方法改善 E_CF 但降低真实任务质量 → 报告权衡 | **前提不成立** | 无 CF 方法；主验证的质量坍塌来自 affine 迁移失败（broken transfer），不是方法权衡（§4）。但"如实报告不利结果"的精神已满足并须保持。 |
| 效果仅在合成域成立 → 明确适用边界 | **未完整触发** | P4 泛化（未见模板/真实文档）未跑，无法判定；但当前全部为合成模板，须在定位中标注适用性边界。 |
| 机制与方法均稳定优于强基线 → 补齐投稿 | **未触发** | 无机制、无方法、无封存测试结果。 |

**当前应走的路径**：由于无实证分支可落地，按 `docs/protocol.md §1.2 / §10` 与 `p0_direction.md §3.3`，论文只能定位为**边界 / 实证研究**（评价层现象 + 失败边界），贡献(2)(3) withheld。**不得**声称走了"强基线失真→进 P2"分支，也不得声称"强基线接近 Self"分支——两者都缺 kd_only 证据。待 §3 的 kd_only 补跑结果出来后再正式择支：接近 Self→第一条边界研究线（取消方法主线）；仍有 gap→进入 P2 机制诊断（须 R1 闭环 + δ 锁定）。

---

## 8. 论文定位最终意见

1. **定位**：边界 / 实证研究论文（与当前草稿一致，予以确认）。标题、§Conclusion 的 "boundary / empirical study" 定性正确。
2. **贡献(1)**：可 claim，但必须（a）限定为 "for the affine/ridge mapper tested here"，补 "stronger behavioral baselines not yet evaluated for this gap"（R3）；（b）**R1 闭环前删除 "reproducible" 形容词**——§10 贡献(1) 模板含 "reproducible"，在来源不可追溯时不可批准使用该词；修复后方可恢复并附 commit 引用。
3. **贡献(2)(3)**：**withheld**；不得出现机制定位或方法改善措辞；V-only≈Joint 保持"方向性线索"，不得升格；CF-RCT 保持"设计待验证"。
4. **主验证对**：保持 broken transfer 定性，明确其不计入 H1 正向证据，作为失败边界呈现。
5. **通用性**：不得宣称跨家族 / 真实世界迁移；数据全为合成模板，须标注适用边界（§7 第五条）。
6. **统计纪律**：维持"主终点未评估、无改善声明、P>0.05 不作等效、CI 联合报告"的现状；补 R5 的 seed 脚注；图表 placeholders 不得伪造。

---

## 9. 给各角色的指令清单

### 给工程师（最高优先级排序）

1. **[R1·阻塞]** 提交生成 8 个 run 的精确代码为新 commit；按方案 A（新 run_id 重跑 P0/E0+P1）或方案 B（metadata 勘误 + 逐文件哈希证明）闭环可追溯性；旧 run 标注 superseded；不改冻结 `reports/runs/**`。
2. **[R3·进 P2 前必须]** 补跑 kd_only（至少 MVP；理想含 consumer/score；建议主验证对同跑），仅用 train/val，按冻结 `phase1_benchmark_decision` 重判并回报 verdict。
3. **[R4]** 不改冻结判据；在实现层/新增说明增加 `transfer_broken` 诊断字段与口径澄清，勘误主验证 verdict 注释；下游汇总须联合读取该字段。
4. **[R2]** 扩展 `consistency_check`：git hash vs HEAD / 工作区 clean、`model_pair` vs 路径与 layer_map、protocol/prereg 版本兼容。
5. **[R6]** 新增 `model_pair_corrected="qwen3-4b-to-1.7b"` 勘误（不碰 `scores.jsonl`）。
6. **[R5/R8]** 统一 bootstrap seed 并记录；修正 `engineer_status.md §2.2` 符号描述。
7. **[δ]** 进入 P3 前按 `phase3_loss_config_v2.1.yaml` 在验证集网格 {0.5,1.0,2.0} 锁定最终 δ，封存测试前完成，不得事后调整。

### 给写作者

1. 贡献(1)/摘要限定 gap 为 affine/ridge mapper，补"强基线未评估"说明；R1 闭环前删除所有 "reproducible" 形容词，闭环后附 commit 引用。
2. §5.4 保留 broken transfer 定性并补"机器可读 verdict 与叙事差异"说明（R4）。
3. 更新 model_pair 脚注引用至勘误文件（R6）；补 R5 的 CI seed 脚注。
4. 维持贡献(2)(3) withheld、主终点未评估、P>0.05 不作等效、图表不伪造。
5. 全文定位为边界 / 实证研究，标注合成域适用边界。

### 给审稿人（第 2 轮，修复完成后启动）

1. 对 P0/E0 + P1 做聚焦复审：R1 可复现、kd_only 重判、R4 verdict 注释、R2 扩展审计、R6 勘误。
2. 复审必跑 `bootstrap_ci_report` 与**扩展后**的 `consistency_check`；核对 `configs/prereg/**` 仍未被篡改。
3. 依据 kd_only 结果判定 §7 决策树择支，回报 PI。
4. 复核贡献(1) "reproducible" 措辞合规（R1 未闭环则必须已删除）。
5. 第 2 轮仍未解决直接上报 PI 裁决，不进第 3 轮。

---

## 10. 生效与复核触发

- 本裁决自签发生效；§1 的 Go/No-Go 状态维持至对应条件闭环并经第 2 轮复审确认。
- **P2 启动门槛（全部满足）**：R1 闭环 + kd_only 补跑重判（且未消除 gap）+ R4 口径勘误 + δ 按 v2.1 在验证集锁定。
- **P5 启动门槛（全部满足）**：上述 + R2/R5/R6/R8 闭环 + 第 2 轮复审通过 + 贡献(1) 措辞合规。
- 任何对冻结判据的变更须新增版本文件并说明理由；不得回改 `phase1_*`/`phase3_*`/`stage*_decision`、`configs/protocol.yaml`、`reports/runs/**`。

**签署：PI / 课题组长（P0/E0 + P1 Go/No-Go 最终裁决 · 2026-11-23）**

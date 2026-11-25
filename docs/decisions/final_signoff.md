# 最终裁决与投递签 off（反事实功能保真 V2.0 · P0–P1 阶段）

> 裁决人：PI / 课题组长。日期：2026-11-23。
> 依据：审稿第 1 轮 `reports/review/stage_p1_review.md`、第 2 轮 `reports/review/stage_p1_review_round2.md`、`docs/decisions/p1_go_no_go.md`、`docs/decisions/huber_delta_lock.md`、`configs/prereg/phase3_loss_config_v2.2.yaml`、`reports/engineer_status.md`（含 §9 并行实例 3、§8 seed2）、逐 run 产物核验（`p1_gpu_kdonly_mvp_seed{0,1,2}/metrics.json`）、论文定稿 `papers/readkv_v2_draft/main.tex`。
> 第 2 轮为协议最后复审轮；本裁决为 PI 直裁（`docs/agent_team.md §6.1`），不进第 3 轮。
> 本裁决只写决策文档，不改 `src/**`、`reports/runs/**`、冻结判据或论文源文件，不写代码、不跑实验。

---

## 1. 闭环事实逐项确认

| 项 | 事实核验 | PI 裁定 |
|---|---|---|
| **R1 可复现性** | 新 commit `458de18` 含全部 11 个跑分/实现文件；repro run（`e0_gpu_mvp_repro_seed0`、`p1_gpu_mvp_repro_seed{0,1,2}`）`git_hash=458de18`；8 个旧 run 标 `superseded` 且产物未改；第 2 轮判已闭环 | ✅ **闭环确认** |
| **R2 审计补盲** | 扩展 `consistency_check` 检出旧缺陷（4B→1.7B teacher path 不匹配、layer_map 28/36≠28/28、run-code diff）；7 个权威新 run 全 `ok=true`；第 2 轮判闭环 | ✅ **闭环确认**（`review/` 目录误列入属良性噪声，不改变判定） |
| **R3 kd_only 三 seed** | seed0 E_CF=0.7350 [0.5517,0.9344]/dual 0.700；seed1=1.0338 [0.7663,1.3279]/dual 0.633（已核验 `metrics.json:81` 真实产物）；seed2=1.5389 [1.1481,1.9588]/dual 0.683。三 seed CI 下界均 >0，`distortion_present=true`、`transfer_broken=false` | ✅ **闭环确认**（补齐 ≥3 seed，满足 `min_training_seeds=3`；此前"无产物"信息过时，产物实存） |
| **R4 verdict 口径** | `transfer_broken`/`verdict_note`/`quality_pass_scope` 正交字段落地，冻结 verdict 未改；第 2 轮判闭环 | ✅ **闭环确认** |
| **R5/R6/R7/R8** | bootstrap seed 统一、model_pair 勘误、E0 尺度披露、符号笔误更正均完成；第 2 轮判闭环 | ✅ **闭环确认** |
| **δ 锁定** | δ=0.5、硬护栏口径已裁决（`huber_delta_lock.md`），`phase3_loss_config_v2.2.yaml` 形式登记完成；δ=2.0 完整产物见 `engineer_status.md §9`（`delta_lock_v2p1_2p0_par`，E_CF 2.7625/dual 0.5333/flip 0.9583）。第 2 轮因当时 δ=2.0 未见判未闭环——**该新增事实经 PI 复核属实，网格已完整，δ 锁定闭环** | ✅ **闭环确认**（复核新增事实后解除第 2 轮遗留阻塞） |
| **审稿轮次** | 第 2 轮为最后复审轮；其遗留的两项（kd 三 seed、δ 网格）均已由新增产物补齐 | ✅ 具备 PI 直裁条件 |

**小结**：第 1 轮唯一阻塞 R1、三项主要（R2/R3/R4）、四项次要（R5–R8）及 δ 锁定、pytest 待验证项状态已核清。除 pytest 53/53 因 GPU 争用第 2 轮未能独立复核（次要、不作为放行依据也不否定）外，全部闭环。

---

## 2. 决策树分支判断（kd 三 seed 完成后）

依据 `docs/protocol.md §8` 决策树与 `p1_go_no_go.md §7`：

| 分支 | 是否触发 | 判据核对 |
|---|---|---|
| **① 强基线接近 Self → 转边界研究** | **未触发** | kd_only 三 seed E_CF 0.735/1.034/1.539，CI 下界 0.552/0.766/1.148 全部远离 0；`distortion_present=true`。gap 未归零、未接近 Self。 |
| **② 强基线仍有 gap（H1 前提成立）→ 进 P2** | **触发（方向性 + ≥3 seed 稳定性达标，但附强度保留）** | 三 seed ≥3、全部 `distortion_present=true`、`transfer_broken=false`、CI 下界>0，dual/flip 不退化、信息归因正向——满足 RQ1/H1 的"未被强基线消除的失真"证据要求，达到 `p1_go_no_go.md §10` 的 P2 启动门槛（R1 闭环 + kd 重判未消除 gap + R4 勘误 + δ 锁定）。 |
| **③ 机制有效但 CF 不优于 KD → 方法降级** | **未触发** | P2/P3 未运行，无机制/方法证据；δ 网格"三 δ 均不优于 kd_only"仅为风险预警，不构成本分支。 |
| **④ CF 改善 E_CF 但常规退化 → 报告权衡** | **未触发** | 无 CF 方法结果。 |
| **⑤ 效果仅在合成域 → 明确边界** | **未完整触发** | P4 泛化未跑；但数据全为合成模板，须在定位中标注适用边界。 |
| **⑥ 机制与方法均稳定优于强基线 → 投稿** | **未触发** | 无机制、无方法、无封存测试、主终点未评估。 |

**PI 择支裁决：走分支②（H1 前提成立 → 进 P2 机制诊断），并对分支①/⑤保留边界预警。**

理由与强度保留（如实写入论文与 P2 任务书）：

1. **gap 未归零但缩小**：kd_only 相对 affine≈1.968 缩小约 22%–63%（三 seed 0.735–1.539），但三 seed CI 下界全部 >0，统计学上"未被消除"稳健；这不是分支①的"接近 Self"。
2. **三 seed 不稳定**：gap 量级从 0.735 跨到 1.539（约翻倍），跨 seed 方差大。这**不否定 gap 的存在**（每个 seed 独立显著），但意味着 gap 的**幅度不可当作稳定点估计**；论文不得给出单一"gap 幅度"结论，须逐 seed 报告并标注方差。
3. **预算 caveat 仍在**：kd 网格 60 对/3 epoch vs kd_only 120 对/8 epoch，非劣比较仅供初筛；"未被消除"的结论由三 seed 显著性支撑，不依赖同预算非劣比较。
4. **与第 2 轮的分歧说明**：第 2 轮因"单 seed 不足"判不能放行 P2；现 seed1/2 产物已补齐（≥3 seed），该阻塞解除。PI 据此直裁放行 P2，但保留上述强度限制——这是新增事实驱动的合法裁决，非推翻审稿方法论。

---

## 3. P0–P5 最终 Go/No-Go 决议

| 阶段 | 最终决议 | 依据 |
|---|---|---|
| **P0 / E0** | **GO（最终）** | repro run E0 PASS，R1 闭环，可复现来源成立。 |
| **P1 基准** | **GO（最终）** | 权威 repro run + kd 三 seed，联合报告齐全、broken-transfer 边界正确标注、贡献(1) 证据成立。 |
| **P2 机制诊断** | **GO（有条件放行）** | 分支②触发，P2 启动门槛全部满足；任务书见 §3.1。**条件**：执行中遵守 Oracle 隔离、机制选择仅用训练/验证集、E2 预测判据按 v2.1/v2.2 冻结口径；若 E2 无 held-out 预测价值，按 §8 降级为现象报告，不得硬升格贡献(2)。 |
| **P3 方法** | **NO-GO（维持）** | P2 未闭环；封存测试未运行；主终点（成对 E_CF vs kd_only，CI 上界<0）未评估；三 δ 均不优于 kd_only 的风险未排除。须待 P2 机制单元结果 + δ=0.5 训练 + 封存测试后另裁。 |
| **P4 泛化** | **NO-GO（维持）** | P3 未闭环；未见模板 / 真实文档 / 封存 test 未运行。 |
| **P5 成稿/投递** | **有条件 GO —— 批准"边界/实证研究"定位投递（见 §4）** | 证据层与论文合规性达标；投递措辞门槛与残余事项见 §4。 |

### 3.1 P2 GO 后工程师下一步任务书（E2 机制诊断）

1. **K/V 四臂**：在 MVP repro 权威 run 基础上跑 Self / K-only / V-only / Joint，四臂带 `deployable` 标记（仅 Joint 可部署）；P1 已给出 V-only≈Joint 方向性线索，须用四臂定量确认。
2. **局部 Routing/Consumption 分解**：按冻结恒等式 `Ô−O_S=(Â−A_S)V_S W_O+Â(V̂−V_S)W_O` 在固定 Query 下分解，报告 routing/consumption 范数与残差≈0（数值自检）；不得解释为全模型因果分解。
3. **层/头/Token Oracle 移植**：按 Oracle Δ 在训练/验证集降序选候选单元集 U，在**独立验证文档**上检验 held-out 预测价值——严格按 `phase3_loss_config_v2.1.yaml e2_mechanism_prediction` 冻结判据：repair 命中率显著高于随机（簇级 paired bootstrap 95% CI 下界>0）、方向一致 ΔE_CF>0 占比>0.5、分解残差≈0。
4. **Oracle 隔离**：Oracle 只在离线诊断/训练期，不得进入 Joint 推理图；机制选择规则只用训练/验证集，不碰封存测试标签。
5. **判定纪律**：三项判据全达 → 产出候选机制公式、可支撑贡献(2)；仅事后热图相关 → 按 §8 降级现象报告，如实写入，不得硬升格。
6. **预算对齐**：P2 run 沿用 repro 权威代码（commit `458de18` 及其后继），同 dtype/kernel，写 `git_hash`、`zero_re_prefill=true`、`transfer_broken` 正交字段。

---

## 4. 论文投递签 off 与贡献措辞门槛

**裁决：批准当前稿件 `papers/readkv_v2_draft/main.tex` 以「边界 / 实证研究（boundary / empirical study）」定位投递——这是条件性签 off（Conditional GO），条件如下必须在投递前满足：**

1. **主终点如实标注**：论文已明确"成对 E_CF vs kd_only、CI 上界<0 的主终点未评估、不作改善声明"——保持，不得删除或弱化。§10 贡献(3) 维持 withheld。
2. **贡献(1) 措辞达标**：贡献(1) 已限定为评价层 gap 发现；须补入 kd 三 seed 结果（gap 缩小约 22%–63% 但未消除、CI 下界>0、跨 seed 幅度不稳定），并把"gap"限定在**已测的 affine/ridge/kd_only mapper 范围内**。`reproducible` 措辞在 R1 闭环后允许，须附 commit `458de18` 引用。
3. **贡献(2)(3) withheld**：机制层、方法层无证据，维持显式 withheld；V-only≈Joint 保持"方向性线索"；CF-RCT 保持"设计待验证"；不得出现 localized/reduces/improves 的已证实措辞。
4. **broken-transfer 边界**：主验证对（4B→1.7B）保持"迁移失败边界"定性，不计入 H1 正向证据；机器可读 verdict 与叙事差异说明保留。
5. **不利结果与 caveat 齐全**：δ 网格三值均不优于 kd_only、kd gap 跨 seed 不稳定、E0 尺度差异、one-shot 残差、model_pair 勘误、预算不对等——均须在稿中如实披露（定稿已覆盖大部分，投递前逐条核对）。
6. **P2/P3 状态同步**：论文已声明 P2–P5 未运行；**注意**：本裁决放行 P2，若 P2 在投递前产出机制证据，投稿版本可选择维持边界定位（保守）或待 P2 完成后重投含贡献(2) 的增强版——此为策略选择，见 §6 人工决策。
7. **引用核验**：`[PLACEHOLDER]` 引用按 `protocol.md §9` 在投递前核实正式版本/日期/口径。

**§10 门槛结论**：当前证据只满足贡献(1) 门槛，按协议必须定位为边界/实证研究并 withheld (2)(3)——定稿符合该门槛，予以签 off；**任何把贡献(2)(3) 写成已证实的版本一律不签 off**。

---

## 5. 给全体角色的最终指令清单

### 给工程师
1. **启动 P2 机制诊断**（§3.1 任务书六条）：K/V 四臂、Routing/Consumption 分解、层/头/Token Oracle held-out 检验；沿用 repro 权威代码，写全 provenance 字段。
2. 收尾次要项：`consistency_check` 扫描限定 `reports/runs/*`（排除 `review/` 目录）；GPU 空闲后重跑 pytest 复核 53/53（不改任何冻结判据）。
3. `reports/huber_delta_lock.json` 更新为 δ=0.5 已锁定的汇总去重状态（报告层，不碰冻结产物）。
4. P2 产物交审稿人做统计合规审计后再上报 PI 择支；不得自行升格贡献(2)。

### 给写作者
1. 按 §4 七条定稿：贡献(1) 补 kd 三 seed（缩小但未消除、跨 seed 不稳定）、附 commit `458de18`、恢复 `reproducible` 措辞；主表确保为 `*_repro_*` 权威 run。
2. 维持贡献(2)(3) withheld、主终点未评估、broken-transfer 边界、P2–P5 未运行声明、P>0.05 不作等效。
3. 投递前完成 `[PLACEHOLDER]` 引用核验（协议 §9）。
4. 在投稿 cover letter 中把论文明确定位为 boundary/empirical study，不夸大方法贡献。

### 给审稿人
1. P2 产出后执行阶段性对抗审阅（本协作协议下新一轮阶段审稿），必跑 `bootstrap_ci_report` + 扩展版 `consistency_check`，核对 Oracle 隔离与 E2 冻结判据未被篡改。
2. 复核论文定稿相对 §4 的合规性；重点查贡献(2)(3) 是否被误升格、kd 三 seed 是否如实披露。
3. 本阶段（P0/E0+P1）闭环审计已完成，无遗留阻塞项需第 3 轮。

### 给科学家
1. 备好 P2 机制公式候选与 E2 设计细节（held-out 判据已冻结于 v2.1/v2.2，不得改）。
2. 若 P2 产出机制证据，评估是否值得将投稿升级为含贡献(2) 的增强版（见 §6）。

---

## 6. 仍需人工（真实 PI）决策的事项

以下超出本 agent 授权或属策略判断，上报真实 PI：

1. **投递时机策略**：现在以边界/实证研究投递（保守、优先占先），还是等 P2 机制结果出来后评估升级为含贡献(2) 的增强版再投（更高贡献但延后且有 P2 失败风险）？本 agent 的裁决是"当前稿件已具备边界研究投递资格"，但投递 vs 等待的策略由真实 PI 拍板。
2. **P2 方向的资源承诺**：P2 机制诊断需 GPU 与 Oracle 离线诊断工时；kd seed 与 δ 网格已暴露 GPU 争用/停滞问题，真实 PI 需确认排期与算力。
3. **预算不对等的补救**：是否投入同预算（120 对/8 epoch）复核 kd 非劣比较，以强化 gap 幅度结论？本 agent 裁定"不影响 gap 存在性结论"，但若要发表"幅度"主张需人工决定是否补做。
4. **作者署名与投稿期刊**：`author list to be finalized` 与目标venue 属人工决策。

---

## 7. 最终结论

- **闭环**：R1–R8 及 δ 锁定、kd 三 seed 全部闭环（pytest 次要待验证，不阻塞）。
- **择支**：决策树分支②（H1 前提成立 → 进 P2），分支①/⑤ 保留边界预警；gap 未归零但缩小约 22%–63%、跨 seed 不稳定，须如实报告。
- **阶段**：P0/E0 GO；P1 GO；**P2 有条件 GO（附任务书）**；P3/P4 NO-GO；**P5 条件性 GO —— 批准边界/实证研究定位投递**。
- **贡献门槛**：仅贡献(1) 达标，贡献(2)(3) withheld；定位为边界/实证研究；任何升格措辞不予签 off。

**签署：PI / 课题组长（最终裁决与投递签 off · 2026-11-23）**

# P3（方法层）任务安排与阶段门控（反事实功能保真 V2.0）

> 裁决人：PI / 课题组长。日期：2026-11-23。
> 触发：人工（真实 PI）已下达"启动 P3"决策（见 `contribution2_final_form.md §5` 人工决策项）。
> 依据：`docs/p3_resource_estimate.md`（实测资源/耗时）、`docs/decisions/final_signoff.md`、`contribution2_final_form.md`、`configs/prereg/phase3_method_decision.yaml`（三分支，不可改）、`configs/prereg/phase3_loss_config_v2.2.yaml`（δ=0.5 已锁）、`docs/algorithm_spec.md` §2–§4、`docs/experiment_design_E0_E7.md` E3–E6、`reports/engineer_status.md`。
> 本文件只写任务安排，不改 `src/**`、`reports/runs/**`、冻结判据，不写代码、不跑实验。凡需新规则一律另立版本文件。

---

## 1. 范围与策略裁决

### 1.1 策略：分阶段门控 + 折中探路（不盲目全量）

> **裁定：采用"烟测门 → kd vs cf_lite 探路（2 方法 × 3 seed）→ 门控决定是否续跑 cf_mech"的分阶段方案；不一开始就全量 3×3。**

理由：

1. **负面信号强**：δ 网格三值（0.5/1.0/2.0）的 val joint E_CF（2.75/1.60/2.76）全部高于 kd_only（0.735）；`contribution2_final_form`/`final_signoff` 已多次记录该风险。P3 主终点（cf 方法 vs kd_only 的成对 E_CF 差异，CI 上界<0）**很可能为负**——全量 9 run（5–7h）有较高概率只是确认 `no_method_gain`。
2. **探路成本低、信息量高**：先跑 kd vs cf_lite（2×3 seed ≈ 2.5–3h）。若 cf_lite 相对 kd_only 方向为负/无增益，即可按冻结决策树降级，省下 cf_mech 的 1.3–1.8h；若方向为正，再续 cf_mech。
3. **门控符合协议纪律**：`phase3_method_decision.yaml` 的 `no_method_gain`（ecf_improved=false）与 `tradeoff`（ecf_improved 但 dual<0.7）分支都可在探路阶段判定；`method_contribution` 需 mech 对 lite 与最强基线均有增益——这本来就必须等 cf_mech，故门控顺序与判据逻辑一致。

### 1.2 若主终点为负是否继续 cf_mech

> **明确裁定：若探路阶段 cf_lite vs kd_only 的成对 E_CF 差异 CI 上界 ≥ 0（即 `ecf_improved=false`）或落入 `tradeoff`，则不继续 cf_mech，按冻结决策树降级收口。**

理由：cf_mech = cf_lite + `L_local`，其附加价值以 lite 有增益为前提；冻结判据 `method_contribution` 要求"mech 对 lite 与最强公共基线均有额外增益"。若 lite 本身不优于 kd_only，mech 缺乏成立基础，继续跑只是浪费算力，且易诱发"挑 seed 找 positive"的违规（`dropping_seeds`/`selecting_seeds_by_result` 明令禁止）。唯一例外：若探路显示 cf_lite 有**微弱正信号但 CI 跨 0**，可由 PI 在门控点权衡是否续 mech 以验证机制约束能否把效应推过阈值——此例外须在门控记录中写明理由，不得默许。

### 1.3 风险承受

- 接受 `no_method_gain` 为**合法且可接受的结论**：贡献(3) 维持 withheld，论文维持 empirical/boundary study 定位（贡献(1)(2) 已达标，投递不受阻）。
- 不接受以任何方式掩盖负结果（丢 seed、换指标、事后调 δ/λ、按测试结果选配置）。

---

## 2. 实现前置任务（给工程师，全部在跑任何正式 run 之前完成）

| # | 任务 | 验收标准 |
|---|---|---|
| **2.1** | 新建 `experiments/P3_gpu.py` 入口：`--backend gpu --method {kd,cf_lite,cf_mech} --seed {0,1,2}` | 复用 `train/cf_rct.py` 训练骨架与 `evaluate.cf_pipeline` 评测口径；score schema 与既有 run 一致；封存 test 只在最终评测读取 |
| **2.2** | GPU 后端实现可微 `torch_candidate_logits()`（冻结学生、可反传） | 返回形状与 `mock_backend.torch_candidate_logits` 一致（候选 logits 张量）；候选在同一生成位置取；`L_KD/L_CF/L_local` 可经其对 `gθ` 反传；不引入学生权重更新 |
| **2.3** | 预算配平：三法同 `epochs`/`lr`/LoRA-rank 或可训练参数量/学生 Forward 次数 | 记录每法 `trainable_params`、`student_forward_calls`、`train_sec`；`L_KD` 的 λ_KD=1.0 锚点；`δ=0.5` 从 v2.2 读取；`τ=1.0`/`self_threshold=0.1` 冻结引用 |
| **2.4** | 新 commit 纳入全部跑分代码（P3_gpu.py、可微 readout、训练入口、审计脚本改动） | **避免 R1 重演**：正式 run 的 `git_hash` 必须指向含全部跑分代码且工作区 clean 的 commit；`git diff <commit> HEAD -- <跑分路径>` 为空；provenance 字段齐全 |
| **2.5** | 烟测（单 seed 单方法）：先跑 1 个 smoke run 验证端到端接线 | 记为 `smoke/non-authoritative`，置于 `reports/_non_authoritative/`；确认可微 readout 反传正常、loss 下降、评测口径与 P1/P2 一致；**不得**把 smoke 数字当证据 |

---

## 3. Run 排期（串行）

**执行顺序理由**：`p3_resource_estimate §2` 实测并发 2–3 任务使 kd 训练放大 3×–7.3×、δ 网格放大 5×——**并发不省时间，全部串行**。

### 3.1 run_id 命名与配置

| 阶段 | run_id | 方法 | seed | 关键配置 |
|---|---|---|---|---|
| 烟测 | `p3_smoke_cflite_seed0`（non-authoritative） | cf_lite | 0 | 小规模接线验证，不入门控统计 |
| 探路 | `p3_gpu_kdonly_mvp_seed0/1/2` | kd_only（primary baseline） | 0/1/2 | 见 3.2 |
| 探路 | `p3_gpu_cflite_mvp_seed0/1/2` | cf_lite（L_KD+L_CF） | 0/1/2 | 见 3.2 |
| 续跑（门控后） | `p3_gpu_cfmech_mvp_seed0/1/2` | cf_mech（+L_local） | 0/1/2 | 见 3.2；仅探路门通过才启动 |

### 3.2 每 run 统一配置

- 模型对：MVP 等深 `qwen3-1.7b-to-0.6b`（与 P1/P2 权威口径一致）；
- 数据：train 120 / val 60 调参与早停；**封存 test 300** 仅最终主结果评测（≥24 模板/主题簇 + 未见模板子集）；F1–F6 全覆盖，F5 不入翻转分母；
- 训练：8 epoch（与 P1 kdonly 一致，确保配平）；lr 同三法；δ=0.5（v2.2）；τ=1.0；self_threshold=0.1；λ_KD=1.0；λ_CF/λ_local/λ_reg 由验证集网格同预算选定并记录搜索成本；
- 运行：dtype=bfloat16；kernel=sdpa；n_resamples=10000；簇级 paired bootstrap；≥3 seed（seed 0/1/2）；`zero_re_prefill=true`；
- 每 run 写 `config.json`（含 git_hash/protocol_version/seed/dtype/kernel/bootstrap_seed/zero_re_prefill/method/预算字段）。

### 3.3 耗时与 GPU 预算（按实测）

| 作业 | 单 run 实测估计 | 数量 | 小计 |
|---|---|---|---|
| 烟测 | ~10–15 min | 1 | ~0.25 h |
| kd_only | ~20 min | 3 | ~1.0 h |
| cf_lite | ~20–25 min | 3 | ~1.0–1.25 h |
| cf_mech（条件） | ~25–35 min | 3 | ~1.3–1.8 h |
| 聚合/bootstrap/审计 | — | — | ~0.5 h |
| **探路阶段合计（烟测+kd+cf_lite）** | | | **≈ 2.5–3 h** |
| **全量合计（含 cf_mech）** | | | **≈ 4–5 h GPU** |
| 实现前置（可微 readout + 入口 + 配平 + commit） | — | — | ~1–2 h |
| **总墙钟预算** | | | **探路 ≈ 4–5 h；全量 ≈ 5–7 h** |

- 显存：单训练 run ~7.8 GB（kd 实测），cf 略高；单卡串行无并发，24 GB 充裕。
- 磁盘：+约 60–100 MB run 产物；1.2 TB 可用；无需新增模型、无需联网。

---

## 4. 统计与判据纪律

1. **主终点**：封存 test 上 cf_lite/cf_mech 相对 `primary_baseline=kd_only` 的**成对 E_CF 差异**；模板/来源簇级 paired bootstrap（10000 resamples，bootstrap_seed 记入 config）；95% CI **上界 < 0** 才算稳健改善。P1/P2 的 E_CF 是"相对 Self 锚点"，**不是**主终点，不得混用。
2. **≥3 seed**：每法 seed 0/1/2 齐全，逐 seed 报点估计与 CI，报告方差；**任何 seed 缺失 → 该法不得支撑主结论，必须降级表述**（如只报 2 seed，须显式声明"不足 3 seed，结论降级为方向性"），严禁伪造或挑选 seed。
3. **联合报告**：E_CF 必须与 `dual_correct`/`flip_consistency`/`coverage`/`info_gap` 同报；单独 E_CF 下降不算改善（D_self≈0 时恒定输出可低误差）。
4. **普通 QA 同报**：反事实 QA 与普通 QA 一起报告，防止"新指标改善但常规任务退化"（`tradeoff` 判据依赖 dual_correct<0.7）。
5. **多重比较**：多方法/多终点比较用 Holm 调整；`P>0.05` 不作等效证明。
6. **不得按封存测试调参**：δ=0.5、λ、阈值已于验证集冻结（v2.2），封存 test 只读最终评测；违反 `forbidden_after_run`（changing_loss_weights_on_test/changing_tau_on_test/dropping_seeds）。
7. **预算对齐**：三法同 epoch/lr/参数量/Forward 次数；`L_local` 的 Oracle 训练信号只在训练期，不得进 Joint 推理图；`zero_re_prefill=true`。

---

## 5. 阶段门控与检查点

### 门 1：烟测门（实现完成后）

- **Go**：可微 readout 反传正常、loss 可下降、评测口径与 P1/P2 一致、provenance 字段齐全、smoke 已标 non-authoritative。
- **No-Go / 降级**：任一接线失败 → 修实现后重烟测，禁止进入正式 run；不得带病开跑。

### 门 2：方法探路门（kd + cf_lite 各 3 seed 完成后）

按 `phase3_method_decision.yaml` 三分支判定（cf_lite vs kd_only）：

| 探路结果 | 冻结分支 | 门控动作 |
|---|---|---|
| cf_lite 成对 E_CF 差 CI 上界<0，且 flip≥0.7、dual≥0.7、普通 QA 不退化 | 满足 `method_contribution` 的 lite 前提 | **GO**：续跑 cf_mech 3 seed，验证机制约束额外增益 |
| cf_lite E_CF 改善但 dual<0.7（常规退化） | `tradeoff` | **有条件 GO**：可续 cf_mech 探是否兼顾，但已预告"如实报告权衡、不省略退化"；若 mech 仍退化 → 降级收口 |
| cf_lite 无增益（CI 上界≥0） | `no_method_gain` | **NO-GO / 收口**：不续 cf_mech（§1.2），按 `method_downgraded` 降级，贡献(3) 维持 withheld |

- 唯一例外（§1.2）：微弱正信号但 CI 跨 0，PI 可在门控记录中写明理由后续 mech；不得默认。

### 门 3：全量门（cf_mech 完成后，或探路即收口）

- 按完整三分支与 §4 纪律判定最终 verdict；`method_contribution` 还须 mech 对 lite 与最强公共基线均有额外增益、普通 QA 不退化、≥3 seed、Holm。
- **No-Go 降级**：任一 seed 缺失 → 降级表述；负结果 → `method_downgraded`，不挑种子。

### 审稿介入点（门 3 之后、P5 之前）

- 必跑 `bootstrap_ci_report`（主终点重算）+ 扩展版 `consistency_check`（git_hash ancestry、跑分代码一致性、zero_re_prefill、model_pair、dtype/kernel）；
- 核对 `configs/prereg/**`（v2.0/v2.1/v2.2）未被篡改；
- 审计预算配平（三法 trainable_params/Forward/train_sec）、seed 完整性、联合报告、普通 QA；
- 审稿人出具 P3 阶段报告后上报 PI 最终择支与贡献(3) 措辞裁定。

---

## 6. 交接产物

### 6.1 每 run 必备文件

`config.json`、`scores.jsonl`（逐对，含 g/D/E_CF/dual/flip/control）、`metrics.json`、`ecf_ledger.jsonl`、`manifest.json`、训练 loss 日志（含 λ/δ/预算字段）；`config.json` 含 git_hash/protocol_version/seed/dtype/kernel/bootstrap_seed/zero_re_prefill/method/预算字段。

### 6.2 汇总 JSON

`reports/p3_method_summary.json`：三法 × 3 seed 的主终点（成对 E_CF 差 + CI）、联合报告指标、普通 QA、预算对照表、Holm 结果、最终 verdict 与 claim_boundary（贡献(3) 是否解禁由 PI/审稿人裁决，工程师不自行升格）。

### 6.3 下游路径

- 审稿人：`reports/runs/p3_gpu_*` + 汇总 JSON + 审计脚本输出；
- 写作者：汇总 JSON 与 E3 主表；**仅在 PI 裁定的条件下更新论文**（见 6.4）。

### 6.4 写作者更新条件（贡献(3) 解禁门槛）

- **解禁贡献(3) 完整措辞**（"We present a mechanism-constrained mapper that reduces this gap… without target-side re-prefill at inference"）须**同时**满足：
  1. P3 verdict = `method_contribution`（主终点 CI 上界<0、flip≥0.7、dual≥0.7、≥3 seed、Holm、mech 对 lite 与最强基线均有增益、普通 QA 不退化）；
  2. **E5 跨模型证据**（至少一组非等深方向增益稳定）——`contribution2_final_form`/`final_signoff` 明确贡献(3) 的"跨模型"需 P4/E5 支撑；
  3. **E6 成本证据**（Joint 端到端成本低于重 Prefill，阈值运行前冻结）——支撑 "without target-side re-prefill" 的系统侧措辞；
  4. 统计/公开代码/论文叙事补齐（冻结决策规则 action）。
  - 缺 2/3 时，即便 P3 主终点为正，贡献(3) 措辞仍须限定（如"on the MVP pair"）或维持 withheld，不得写跨模型/系统收益。
- **维持 withheld 的降级措辞**（`no_method_gain`/`tradeoff` 或 seed 缺失）：按冻结三分支如实写——"方法层未见稳健增益/存在常规任务权衡/seed 不足结论降级"，贡献(1)(2) 不动，论文维持 empirical/boundary study。

---

## 7. 时间/资源上限与熔断

1. **总墙钟上限**：探路阶段 ≤ 5 h、全量 ≤ 8 h（含实现与审计）；超时未完成须上报 PI，不擅自扩预算。
2. **单 run 熔断**：某 run 超过 **60 min** 无 `metrics.json` 产物即中止（实测干净单跑 ≤35 min，60 min 已含余量），如实记录停滞原因（GPU 争用/OOM），**不伪造产物、不隐藏失败**；中止的 run 不计入 seed 统计，缺失 seed 按 §4.2 降级。
3. **并发禁令**：全程串行；发现并发立即纠正（3–7× 惩罚）。
4. **显存/磁盘**：单卡串行，峰值 <12 GB；磁盘增量 <200 MB；不下载新模型、不联网、不跑 8B。
5. **判据变更禁令**：不得改 `phase3_method_decision.yaml`/v2.1/v2.2/protocol；如需新规则另立版本文件；不改 `reports/runs/**`（历史不可变），新 run 用新 id。

---

## 8. 仍需人工（真实 PI）决策的事项

1. **λ 网格成本**：若探路显示微弱正信号，是否投入 +1–2.5 h 做 λ_CF/λ_local 网格（3–6 run）；默认不做，除非门控点 PI 批准。
2. **E5/E6 投入**：P3 主终点为正时，是否追加跨模型（E5）与成本（E6）实验以解禁贡献(3) 完整措辞——这决定论文能否升级为 method paper。
3. **投递时机**：P3 进行中是否并行走 P5 投递（当前稿件已可投 empirical/boundary study），还是等 P3 结果定稿。
4. **署名与期刊**（沿用前次人工决策项）。

---

## 9. 第一个执行动作与时间预算摘要

- **总时间预算**：探路 ≈ 4–5 h、全量（探测为正）≈ 5–7 h 墙钟；实现 1–2 h 含在内；P3 不是投递硬门槛。
- **第一个执行动作**：工程师完成任务 2.1–2.4（新建 `P3_gpu.py`、可微 `torch_candidate_logits`、三法预算配平、纳入新 commit 确保 provenance），随即执行任务 2.5 烟测 `p3_smoke_cflite_seed0`；烟测门通过后，按 §3 串行启动探路 run `p3_gpu_kdonly_mvp_seed0`（kd_only 为 primary baseline，先行）。

**签署：PI / 课题组长（P3 任务安排 · 2026-11-23）**

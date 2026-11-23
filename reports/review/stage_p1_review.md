# 阶段审稿报告：P0/E0 + P1 交付点（反事实功能保真 V2.0）

> 审稿人：reviewer（对抗性审阅 / readkv）。日期：2026-11-23。
> 依据协议：`docs/protocol.md` V2.0、`configs/protocol.yaml` v2.0、`configs/prereg/*`（含 `phase3_loss_config_v2.1.yaml`）、`docs/decisions/p0_direction.md` §7。
> 审稿范围：E0 实现门、P1 基准（MVP 等深 + 主验证非等深）、论文初稿 `papers/readkv_v2_draft/{main.tex,notes.md}`。P2–P5 未运行，不在证据审查范围。
> 本审稿**未修改**任何代码、`scores.jsonl`、`configs/prereg/**` 或论文源文件；仅写本报告与统计脚本输出。

---

## 0. 统计合规动作（硬要求，已执行）

| 动作 | 命令 | 结果 | 落盘 |
|---|---|---|---|
| 从 scores.jsonl 重算 E_CF / 簇级 CI | `.venv/bin/python -m scripts.bootstrap_ci_report` | 成功，8 个 run | `reports/bootstrap_summary.json` |
| git hash / 协议版本 / zero_re_prefill / 哈希审计 | `.venv/bin/python -m scripts.consistency_check` | 8 checked, 0 failed | `reports/consistency_report.json` |

**核对结论**：
- `configs/prereg/` 未被动态篡改：4 个既有冻结文件 + `configs/protocol.yaml` + `configs/eval.yaml` 的 `git diff` 均为空；`phase3_loss_config_v2.1.yaml` 为 PI 于 2026-11-22 新增的 untracked 文件，符合 §7 冻结裁决，**非事后篡改**。
- mock 数字未混入正式结论：论文/笔记明确声明全部数值来自 `reports/runs/**`；README “51 passed” 未被当作当前证据。合规。
- `zero_re_prefill=true` 在全部 8 个 run config 中置位；`consistency_check` 仅校验键存在 + 标志为 true（见 §4 审计工具盲点）。
- **git hash 与 run config 表面一致，但与代码来源不一致——见发现 R1（阻塞级）。**
- 重算得到的主验证 joint E_CF 点估计与 `metrics.json` 完全一致（6.044 / 5.365 / 6.080）；CI 端点在 seed 1/2 与报告值有微小差异——见发现 R5（次要）。

---

## 1. 逐项发现与风险等级

### R1【阻塞 · 可复现性】run config 记录的 git hash 不指向产出结果的代码

- **事实**：全部 8 个 run 的 `config.json` 记录 `git_hash="53e9bc5"`，该 commit 为 HEAD（`Add multi-agent research team protocol and role prompts`），其 tree **仅含** `docs/agent_team.md` 与 `prompts/*.md`。而实际产出 E0/P1 结果的代码：
  - `experiments/P1_gpu.py`、`experiments/P0_gpu.py`、`src/readkv/models/gpu_backend.py` → **完全未纳入任何 commit（untracked）**；
  - `src/readkv/models/hooks.py`、`src/readkv/evaluate/cf_pipeline.py`、`scripts/gen_teacher_cache.py` → **工作区已修改但未提交**。
- **影响**：任何第三方 checkout `53e9bc5` 都**无法复现**这些 run（入口脚本不存在，hooks 为旧版）。论文摘要/引言声称 “reproducible benchmark / machine-precision gate”，与项目硬约束「可复现环境」冲突。`consistency_check` 因只检查键存在而给出 false-green（见 R2）。
- **判定数字本身是否失效**：不失效——`scores.jsonl` 为真实 GPU 产物，点估计可重算；失效的是**来源可追溯性与“可复现”措辞**。
- **建议（工程师）**：将生成 8 个 run 的精确代码状态提交为新 commit，并以**新增 run_id 或 metadata 勘误**把 `git_hash` 更新为该 commit（禁止回改冻结产物）。在修复前，论文不得使用 “reproducible”  adjectives，应改为 “real-GPU benchmark on a committed-but-unmerged working tree” 或删除该词。
- **等级**：P1 阶段=主要；P5 投递/贡献(1)措辞=**阻塞**。

### R2【主要 · 审计工具】`consistency_check` 存在盲点，0-problem 不能证明来源正确

- 脚本仅检查 `config.json` 中 6 个键是否存在、`zero_re_prefill is True`；**不校验** `git_hash` 是否等于 HEAD、工作区是否 clean、`model_pair` 是否与 teacher/student 路径一致。
- 因此 R1（git 来源错误）与 R4（model_pair 误标）均通过审计，形成“审计通过但元数据错误”的假阳性。
- **建议（工程师）**：扩展审计项——(a) 比对 config git_hash 与 `git rev-parse HEAD` 并检测工作区脏状态；(b) 校验 `model_pair` 与 teacher/student 路径、layer_map 层数一致；(c) 校验 `protocol_version` 与 prereg 版本兼容。**我不改脚本**，仅提出要求。

### R3【主要 · P1 证据边界】未运行指定强基线 `kd_only`，“强基线未消除失真”未被证实

- `configs/eval.yaml` 与协议规定 P1 应比较 `affine/consumer/kd_only/score/ridge` 等强行为基线，`primary_baseline=kd_only`。实际 P1 的映射臂是 **affine + closed-form ridge、`mapper_trainable_params=0`**，且仅与 Self / Identity / 错配 / 随机 / 零缓存对照。
- `phase1_benchmark_decision` 的 `distortion_present=true` 由 “joint E_CF 显著 > 0（Self 锚点）” 触发，**不是**由 “强行为基线仍有 gap” 触发。因此 contribution (1) 中「gap between standard transfer utility and counterfactual fidelity」在 P1 只对**该 affine mapper** 成立；对 kd_only/consumer/score/ridge/KV-Lingo 类强基线是否被消除，P1 无法回答，属 P3 未跑内容。
- 写作者已在 §5.5 “Baselines and fair alignment” 声明 “full matched-baseline comparison belongs to the unrun method stage”，措辞上未越界；但 `runs_index.json` 中 `result="distortion_exists"` 与摘要 “reproducible gap between standard transfer utility and …” 若脱离上下文阅读，会被理解为强基线检验已通过。
- **建议（写作者）**：在贡献(1)与摘要中把 gap 明确限定为 “for the affine/ridge mapper tested here”，并显式标注 “whether stronger behavioral baselines (kd_only, consumer, score, ridge) retain this gap is left to the method stage”。
- **等级**：主要（证据强度未达 RQ1/H1 完整口径，但已披露，不伪造）。

### R4【主要 · 判据口径】`quality_pass` 操作化含糊：broken transfer 被判为 `distortion_exists`

- 主验证对 3 个 seed 的 joint dual_correct 从 Self 0.65–0.78 坍塌到 0.28–0.30，flip 0.49–0.56，joint E_CF 接近/高于错文档与零缓存控制，info_attribution 多负——这是**迁移失败**，不是干净的反事实失真。
- 但 pipeline 因 `data_quality.gate=pass` 设 `quality_pass=true`，并经 `phase1_benchmark_decision` 对 3 seed 全部返回 `distortion_exists`。协议 §8 决策树要求「强基线有失真但伴随明显质量退化 → 如实报告权衡」且 `p0_direction.md §3.3` 要求「强基线已接近 Self → 边界研究」；写作者已在论文 §5.4 正确定性为 “broken transfer rather than a well-behaved counterfactual distortion”，**叙事合规**。
- 风险在机器可读产物：`runs_index.json` 对主验证 3 run 记 `result="distortion_exists"`，会被下游自动汇总误读为“主验证对存在干净失真”。
- **建议（PI 澄清口径 + 工程师勘误）**：明确 `quality_pass` 是否含模型效用门槛；若含，主验证对应为 `boundary_study`/失败边界；若仅指数据质量，需在机器可读结果中增加 `transfer_broken: true` 字段并在勘误中写明，避免单看 verdict 误读。**这是判据解释问题，不改冻结判据本身。**

### R5【次要 · 复现细节】bootstrap 随机种子不一致，重算 CI 端点与报告值有微小差异

- pipeline（`src/readkv/evaluate/counterfactual.py:221`）以 `seed=实验 seed` 调用 `cluster_bootstrap`；审计脚本 `bootstrap_ci_report.py:36` 固定 `seed=0`。故点估计一致、CI 端点不同：
  - 主验证 seed1：报告 `[4.156, 6.663]` vs 重算 `[4.131, 6.611]`；
  - 主验证 seed2：报告 `[4.847, 7.395]` vs 重算 `[4.794, 7.408]`；
  - MVP seed1/2 同样存在 ≤0.05 的差异。
- `engineer_status.md §2.4` 以 “例：seed0 joint 1.968…” 佐证“与 metrics.json 一致”，恰好选取了 seed=0 这一唯一完全吻合的示例（其余 seed 不吻合），存在透明度瑕疵。
- **无结论影响**：所有 CI 均远离 0，定性不变。**建议**：审计脚本与 pipeline 统一 bootstrap seed 并在 run config 记录；论文补一句 “CI endpoints are seed-dependent; point estimates are exact”。

### R6【次要 · 元数据误标专项】主验证 run 的 `model_pair` 字符串误标——已核实，不阻塞放行

- **核实结果（写作者发现属实）**：`p1_gpu_main_seed{0,1,2}` 的 `config.json` 与 `runs_index.json` 中 `model_pair="qwen3-1.7b-to-0.6b"`；但同一 config 的 `teacher` 指向 `Qwen--Qwen3-4B`、`student` 指向 `Qwen--Qwen3-1.7B`，`layer_map={kind: proportional, n_teacher_layers: 36, n_student_layers: 28}`。`e0_gpu_main_seed0` 的 `model_pair` 正确为 `qwen3-4b-to-1.7b`。三处主验证 config 已逐个确认。
- **严重性评估**：E_CF/CI/dual/flip/coverage 全部由真实 logits 与缓存计算，计算路径**不读取** `model_pair` 字符串，故**不影响任何计算指标**，也不影响决策 verdict。此为标签层错误。
- **是否阻塞**：**不阻塞 P0/E0 与 P1 放行**。若该字符串进入机器可读索引而不勘误，可能导致下游把主验证 run 错误归组为 MVP → 需在 P5 前修正。
- **修勘建议（工程师，我不自行改产物）**：不动冻结 `scores.jsonl`；以**新增 metadata 勘误文件或新 run_id 索引**写入 `model_pair_corrected="qwen3-4b-to-1.7b"`，并标注依据（teacher/student 路径 + 36→28 layer map）。写作者当前处理（正文按 4B→1.7B 报告 + §5.2 脚注披露）为正确的过渡做法，予以认可。

### R7【次要 · E0 尺度】“误差上限 ≪ 效应” 的效应估计与主终点不同尺度，已披露

- E0 `effect_estimate≈20.86`（MVP）/19.99（main）来自多 token 序列 logprob；主终点 g 为 2 维候选首 token logit。形式上 “测量误差上限 ≤ 效应/3（6.95/6.66）” 的效应侧与主终点不同量纲。因误差上限 2.2e-16 远低于任一合理效应，E0 判定稳健，不构成错误。
- **one-shot full-prefill cosine 0.9993（MVP）/ 0.99972（main），47/80 低于 0.9998**：已如实备案于 `engineer_status.md §1.2`、`main.tex §5.1`、`notes.md §4`，并正确排除于 E0 锚点之外（注入路径与原生两步 bit-identical，cosine=1.0）。披露充分，无隐瞒。建议后续任何 one-shot 部署路径单独测量该 kernel 差异。

### R8【次要 · 内部一致性】`engineer_status.md §2.2` info 归因的符号口径描述与 metrics/论文相反

- §2.2 把 “mismatch +4.134 / random +2.249 / zero +4.191” 描述为 “joint E_CF 减控制组 E_CF”，但数值实际为 **控制组 E_CF − joint E_CF**（6.103−1.968=+4.135）。§2.3、metrics.json、论文 §5.3 均按 `info_attribution = 控制组 E_CF − joint E_CF`，标签一致、仅 §2.2 描述笔误。建议工程师更正文案，避免外部读者反向解读。

### 合规通过项（无风险，简要记录）

- **E0 实现门**：Self/Identity cosine=1.0、KL=0、round-trip bit-identical 80/80、EM=1.0、zero_re_prefill 80/80、误差上限 2.2e-16 ≪ 效应/3——`metrics.json` 与初稿一致，PASS 可信（R7 尺度 caveat 不改变判定）。
- **联合报告**：P1 全部 run 同时报告 E_CF、dual_correct、flip_consistency、coverage、info_attribution（info_gap 逐对字段为 None 但聚合等价口径已备案）。合规。
- **V-only≈Joint 未被升格**：论文明确标为 “directional clue, not a mechanism finding (P2 not run)”。合规。
- **主终点未评估如实说明**：论文 §5.4/§5.5 明确“成对 E_CF vs kd_only、CI 上界<0 未跑，不作改善声明”。合规。
- **§10 贡献门槛**：仅贡献(1)被 claim；(2)(3) 显式 withheld；无未证实的 “reduces/improves” 措辞（scan 命中的 reduces/improves 均在 withheld 条目或否定句中）。P>0.05 未被写成等效。不利结果齐全。合规。
- **P2–P5 / Huber δ 仅规则冻结**：均被如实标注为“未运行、不支持科学结论”。合规。

---

## 2. 风险等级汇总

| 编号 | 发现 | 等级 |
|---|---|---|
| R1 | git hash 不指向产出代码，可复现性失效 | **阻塞（P5）/ 主要（P1）** |
| R2 | consistency_check 盲点导致假阳性 | 主要 |
| R3 | 未跑强基线 kd_only，gap 未证“未被强基线消除” | 主要 |
| R4 | quality_pass 含糊，broken transfer 判为 distortion_exists | 主要 |
| R5 | bootstrap seed 不一致，CI 端点有微小差异 | 次要 |
| R6 | 主验证 model_pair 误标（已核实，不影响指标） | 次要（不阻塞） |
| R7 | E0 效应估计尺度差异 + one-shot 残差（已披露） | 次要 |
| R8 | engineer_status info_attribution 符号笔误 | 次要 |

统计：阻塞×1（仅针对 P5/可复现措辞）、主要×3、次要×4。

---

## 3. 阶段放行建议

**P0/E0 实现门：放行（GO）。** 实现一致性、bit-identical、zero_re_prefill、误差上限均通过，one-shot 残差已披露。

**P1 基准：有条件放行（Conditional GO）。** 作为“affine/ridge mapper 在等深对上存在可复现 gap、非等深对发生迁移失败”的**证据产出**可放行；但以下问题须在进入 P2 前/进入 P5 前解决：
1. （进 P2 前）R1 修复 git 来源可追溯性；否则不得使用“reproducible”措辞。
2. （进 P2 前）R3 明确 gap 的基线范围，或补跑至少一个指定强基线（kd_only/consumer/score）以支撑“未被强基线消除”。
3. （进 P2 前）R4 由 PI 澄清 `quality_pass` 口径并勘误机器可读 verdict。
4. （进 P5 前）R6 model_pair 勘误；R2 审计脚本补盲；R5/R8 文案与种子对齐。

**P5 投递 / 贡献(1)措辞：NO-GO（当前）。** R1 未修复前，“reproducible gap” 主张不成立；按 §10，贡献(2)(3) 维持 withheld，论文维持边界/实证研究定位。

### 给 PI 的 Go/No-Go 建议
- P0：GO。
- P1：Conditional GO（附上述 1–3 条件）。
- P2/P3：维持 NO-GO，直至 E0/P1 条件闭环且 Huber δ 最终值按 v2.1 在验证集网格锁定。
- P5：NO-GO，直至 R1 修复 + 全条件闭环。
- 无发现判据被篡改或 zero-re-prefill 违规，无需触发“立即暂停阶段推进”的最高告警；但 R1 需在文献检索/投稿前解决。

---

## 4. 给写作者的修改清单（不改论文源文件，此处仅建议）

1. 贡献(1)与摘要把 gap 限定为 “for the affine/ridge mapper tested here”，补 “stronger behavioral baselines (kd_only/consumer/score/ridge) not yet evaluated for this gap”（R3）。
2. 在 R1 修复前，删除或改写所有 “reproducible” 形容词；修复后保留并补 git commit 引用。
3. 主验证表/§5.4 保留 broken-transfer 定性（已正确），并补一句机器可读 verdict 与叙事的差异说明（R4）。
4. 接受现有 model_pair 脚注披露（§5.2），在勘误发布后更新脚注引用（R6）。
5. 补 “CI endpoints are bootstrap-seed dependent; point estimates exact”（R5）。
6. 维持贡献(2)(3) withheld、P>0.05 不作等效、主终点未评估声明——现状合规，勿改弱。

## 5. 给工程师的修改清单（不改代码/产物，此处仅建议）

1. 提交生成 8 个 run 的精确代码为新 commit；以新 run_id 或 metadata 勘误同步 `git_hash`（R1，**最高优先**）。
2. 扩展 `consistency_check`：校验 git hash 与 HEAD/工作区 cleanliness、model_pair 与路径/layer_map 一致、protocol/prereg 版本兼容（R2）。
3. 统一 bootstrap seed（pipeline 与审计脚本），并在 run config 记录（R5）。
4. 以勘误文件/新索引修正主验证 `model_pair` 为 `qwen3-4b-to-1.7b`，不动冻结 `scores.jsonl`（R6）。
5. 澄清 pipeline 中 `quality_pass` 的语义并勘误主验证 verdict（R4）；修正 `engineer_status.md §2.2` info 归因符号描述（R8）。
6. E0/one-shot 残差备案维持现状（R7 已充分披露）。

---

## 6. 审稿结论

P0/E0 实现门与 P1 真实 GPU 证据在**数值层面可信、联合报告与不利结果披露充分、§10 贡献表述严格合规**，未发现 mock 混入、判据篡改或 zero-re-prefill 违规。**但存在一项阻塞级可复现性缺陷（git hash 不指向产出代码）与三项主要证据/口径问题（强基线缺位、quality_pass 含糊、审计工具盲点）**。据此：

- **阶段建议：P0 GO；P1 有条件 GO；P5 NO-GO。**
- 上报 PI：在 R1/R3/R4 闭环前不建议启动 P2；R1 在投稿前必须修复，否则“可复现”主张不成立。
- 本阶段改审循环计为第 1 轮；第 3 轮仍未解决由 PI 裁决（按角色协议）。

**签署：reviewer（对抗性审阅），2026-11-23。**

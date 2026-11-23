# 第 2 轮复审报告：P0/E0 + P1（聚焦闭环判定）

> 审稿人：reviewer（对抗性审阅 / readkv）。日期：2026-11-23。
> 轮次：第 2 轮（由 PI `docs/decisions/p1_go_no_go.md` §5.3 触发）；第 3 轮由 PI 直裁。
> 依据：第 1 轮报告 `reports/review/stage_p1_review.md`、`docs/decisions/p1_go_no_go.md`、`reports/engineer_status.md`（更新版）、`reports/runs_index.json`、`reports/runs_index_errata.json`、`reports/huber_delta_lock.json`、新 run 产物与 git 历史。
> **范围**：只判第 1 轮 R1–R8 的闭环状态，不重复第 1 轮已通过项的论证。本轮未改代码、`scores.jsonl`、`configs/prereg/**` 或论文源文件。

---

## 0. 复审执行的强制动作

| 动作 | 结果 |
|---|---|
| `.venv/bin/python -m scripts.bootstrap_ci_report` | 成功，15 runs → `reports/bootstrap_summary.json` |
| `.venv/bin/python -m scripts.consistency_check`（**扩展后**） | checked=17, failed=9, head=a04990d, dirty_run_paths=[] → `reports/consistency_report.json` |
| `git` 核验：commit 内容、ancestry、diff、worktree 状态 | 见 §1–§2 |
| prereg 完整性 | `git diff ff578b5 HEAD -- configs/prereg/ configs/protocol.yaml` = 空，未被篡改 |

**关于 failed=9 的解读（重要，避免误读）**：9 个失败项 = **8 个被正确标注 `superseded` 的旧 run**（审计按设计报错）+ **1 个 `reports/review/` 目录**（本审稿产物目录，被审计脚本按目录扫描误列入，非实验 run，属良性噪声）。**7 个权威新 run 全部 `ok=true / traceable=true`**。failed 计数不应被解读为「9 个 run 损坏」。

---

## 1. 逐项闭环判定

### R1 可复现性（第 1 轮：阻塞）→ **已闭环** ✅

- **commit 内容核实**：`git show --stat 458de18` 含全部 11 个跑分/实现文件：`experiments/P{0,1}_gpu.py`、`experiments/P1_kd_gpu.py`、`src/readkv/models/gpu_backend.py`、`src/readkv/models/hooks.py`、`src/readkv/evaluate/cf_pipeline.py`、`scripts/gen_teacher_cache.py`、`src/readkv/train/kd_gpu.py`、`scripts/bootstrap_ci_report.py`、`scripts/consistency_check.py`、`tests/test_hooks.py`。第 1 轮所指缺代码问题已消除。
- **新 run config 字段核实**（逐个读 `config.json`）：`e0_gpu_mvp_repro_seed0`、`p1_gpu_mvp_repro_seed{0,1,2}`、`p1_gpu_kdonly_mvp_seed0` 均为 `git_hash=458de18`、`zero_re_prefill=true`、`dtype=bfloat16`、`kernel=sdpa`、`protocol_version=2.0`、`bootstrap_seed`（在 `experiment_config` 内，=seed，R5）齐全。δ 网格 run 的 hash 为 `ff578b5`/`a04990d`，均为 458de18 的后继、在 HEAD ancestry 内。
- **代码一致性核实**：`git diff 458de18 HEAD -- <跑分路径>` 仅 `scripts/consistency_check.py` 不同（审计脚本自身，由 841d283 修正，已在审计中排除）；其余跑分代码与 HEAD 完全一致；`dirty_run_paths=[]`。「HEAD 因并行实例前进」的情形由 ancestry + run-code-identity 审计正确覆盖，方法学上成立。
- **旧 run 标注核实**：8 个旧 run 在 `runs_index.json` 与 `runs_index_errata.json` 中均标 `superseded=true` + `superseded_by` 说明；`git diff 9a26748 -- reports/runs/<旧run>` 为空 → **旧 scores/config 未被修改**，符合「不可变产物」约束。勘误仅在报告层。
- **选择**：方案 A（新 run_id 重跑）落实，符合 PI §2 推荐路径。结论：R1 已闭环，贡献(1) 的 "reproducible" 措辞可按 PI §2.5 恢复，但须附 commit `458de18` 引用，且论文主表应改用 `*_repro_*` 权威 run（见 §4 写作者遗留项）。

### R3 kd_only 补跑（第 1 轮：主要 / 进 P2 前必须）→ **部分闭环** ⚠️

- **数字核实**：`p1_gpu_kdonly_mvp_seed0/metrics.json` joint E_CF=**0.735 [0.552, 0.934]**（bootstrap 重算一致）、dual=0.700、flip=1.000、coverage=0.800、info_attribution 全正（mismatch +5.528 / random +4.751 / zero +5.424）；affine=1.968、Identity=0。缩小幅度 (1.968−0.735)/1.968≈**62.7%**，CI 下界 0.552>0 → **gap 未消除**。数据如实，无 mock。
- **未闭环部分**：
  1. **单 seed**：kd seed1/2 无 run 目录、无 `metrics.json`（GPU 争用停滞），仅 seed0。协议 `configs/protocol.yaml statistics.min_training_seeds=3` 与 §4.5 要求 ≥3 seed 报方差；**单 seed 不足以支撑「稳定 gap」的强结论**，只能作为方向性证据。这与第 1 轮对主验证对的审慎标准应一致。
  2. **预算不对等**：δ/kd 网格用 60 对/3 epoch，kd_only 用 120 对/8 epoch（工程师 §6 budget_caveat 已如实记录）；非劣比较仅为初步筛查，不满足「同预算配平」的公平比较最低要求（协议 §7）。
  3. **只补 MVP**：主验证对（4B→1.7B）未补 kd_only， PI §3.2「建议一并跑」未落实；该对仍为 broken-transfer 失败边界，不计 H1 正向证据（PI §4.5）。
- **决策树判断（PI §7 择支）**：见 §3。核心：0.735 相对 Self 的 0 **并非「接近 Self」**（CI 下界 0.552 远离 0），故**决策树第一条「强基线接近 Self → 转边界研究」未被触发**；方向上支持 H1 前提（强基线仍有 gap），但因单 seed + 预算不对等，**不能作为强结论**，更不能单凭它放行 P2。

### R4 verdict 口径（第 1 轮：主要）→ **已闭环** ✅

- `src/readkv/evaluate/cf_pipeline.py` 新增正交注释字段：`transfer_broken`、`verdict_note`、`quality_pass_scope="data_quality_gate_only"`、`signals`（dual_drop、joint E_CF vs 控制组、info 正负），依据客观信号计算；`decision.verdict` 仍为冻结的 `distortion_exists`，**未改冻结判据**。
- 新 run metrics 中：MVP repro 三 seed 与 kdonly 均 `transfer_broken=false`；主验证对的 `transfer_broken=true` 在 `runs_index_errata.json` 中标注（旧 run 不可改，注在勘误层，正确）。`model_pair_corrected` 与 `verdict_unchanged` 字段齐全。主验证=true、MVP=false **属实**。
- 结论：R4 已闭环；下游须联合读取 `transfer_broken`，禁止只看 verdict 判「干净失真」。

### R2 审计补盲（第 1 轮：主要）→ **已闭环** ✅（附一个良性噪声）

- 扩展后的 `consistency_check.py` 确含：(a) `config.git_hash` 的 ancestry 检查 + 跑分代码相对 HEAD 一致性 + commit tree 含代码 + 工作区脏状态；(b) `model_pair` 与 teacher/student 路径、layer_map 层数一致性；(c) `protocol_version` / prereg 兼容。
- **检出能力实测**：旧主验证 run 被正确报出 `teacher path Qwen3-4B does not match qwen3-1.7b-to-0.6b`、`layer_map 28/36 != 28/28` 及 `run-producing code differs / commit tree lacks run code` → R1/R6 类缺陷现可被检出，假阳性消除。
- 7 个权威新 run 全部 `ok=true`。**良性噪声**：`reports/review/`（审稿目录）被扫描为「run」而报 6 项缺失；建议审计脚本按固定 `reports/runs/` 列表或排除 `review/` 目录，使 failed 计数精确为 8（仅 superseded）。此为工具整洁性问题，不影响权威 run 判定。

### R6 勘误（第 1 轮：次要 / 不阻塞）→ **已闭环** ✅

- `runs_index_errata.json`：3 个主验证 run 的 `model_pair_corrected="qwen3-4b-to-1.7b"` 附路径 + 36→28 layer_map 依据、`metrics_affected=false`；`runs_index.json` 对应条目亦写入该字段。原 `scores.jsonl`/`config.json` 未改（git diff 为空）。符合 PI §5.2。

### R5 bootstrap seed（第 1 轮：次要）→ **已闭环** ✅

- 审计脚本 `bootstrap_ci_report.py` 改为按各 run `experiment_config.bootstrap_seed` 取 seed；pipeline 写同字段。重算结果与 metrics 完全一致：repro seed0/1/2 = 1.968/1.934/2.123（CI 与第 1 轮报告值吻合），kdonly = 0.735 [0.552, 0.934]。第 1 轮 CI 端点差异消除。

### R7 / R8 → **已闭环 / 已更正** ✅

- R7：PI §6 裁定无需重跑，工程师维持披露（E0 尺度差异、one-shot 0.9993），第 1 轮已判充分。
- R8：`engineer_status.md §2.2` 已更正为 `info_attribution = 控制组 E_CF − joint E_CF`，符号口径与 metrics/论文一致。

### δ 锁定（新增关注项）→ **未闭环** ⛔（如实声明，不阻塞本轮对 P0/P1 的判定）

- `reports/huber_delta_lock.json`：status=`NOT_LOCKED_GRID_INCOMPLETE`。δ=0.5（val E_CF 2.750、dual 0.70、flip 1.0，满足非劣）；δ=1.0（1.597，但 dual 0.65<kd 0.70，违反第 2 优先级）；δ=2.0 仅 `config.json`、无 `metrics.json`/`scores.jsonl`（评测停滞 43 分钟）。
- 工程师**未据不完整网格锁定**，正确遵守「判据先写后跑」；未伪造锁定、未碰封存 test、未改 prereg。**判定：未闭环，且按 PI §10 构成 P2/P3 的硬阻塞**——不得因 δ=0.5 看似可用就事后锁定。

### pytest OOM → **待验证（不复现触发）** ⏳

- 当前 `nvidia-smi`：显存 23.6/24.6 GB 占用、GPU 利用率 0%——**GPU 仍被占满**，与工程师「争用导致 OOM」的说明一致。本轮**未强跑 pytest 以避免再触发 OOM**；仅做 `--collect-only`（测试可收集，无导入错误）。
- 处置：工程师声称「GPU 空闲时 53/53 通过」本轮**无法独立复核**，如实标注为「待 GPU 空闲后重跑验证」，不作为放行依据、也不否定其声明。此为次要项。

---

## 2. 闭环汇总表

| 编号 | 第 1 轮等级 | 第 2 轮状态 | 残余风险 |
|---|---|---|---|
| R1 可复现性 | 阻塞 | **已闭环** | 无（论文主表须换 repro run + commit 引用） |
| R2 审计补盲 | 主要 | **已闭环** | 次要：`review/` 目录误列入（工具整洁性） |
| R3 kd_only | 主要 | **部分闭环** | **主要**：单 seed + 预算不对等 + 主验证未补 |
| R4 verdict 口径 | 主要 | **已闭环** | 无 |
| R5 bootstrap seed | 次要 | **已闭环** | 无 |
| R6 model_pair 勘误 | 次要 | **已闭环** | 无 |
| R7 / R8 | 次要 | **已闭环** | 无 |
| δ 锁定 | （新增关注） | **未闭环** | **阻塞 P2/P3**（网格缺 δ=2.0） |
| pytest | （新增关注） | **待验证** | 次要（GPU 争用，未复核 53/53） |

---

## 3. kd_only 结果属于决策树哪个分支（PI §7 择支判断）

- **branch 1「强基线在反事实任务上已接近 Self → 转边界研究」：未触发。** kd_only 0.735 [0.552, 0.934] 相对 Self=0，CI 下界 0.552 远离 0，不构成「接近 Self / 消失」。
- **branch「强基线仍有 gap → 满足 RQ1 前提进 P2」：方向上部分满足，但证据强度不足。** 0.735 的 gap 在单 seed 上稳定不为 0，且 dual/flip 不退化、信息归因更强，方向上支持 H1；但仅 1 个 seed（协议要求 ≥3）且预算与参照不对等，**不足以支撑「稳定 gap」强结论**，不能据此批准 P2 启动。
- **branch 6「机制与方法均稳定优于强基线 → 投稿」：未触发**（无机制、无方法、无封存测试）。
- **综合**：当前既不满足「转边界研究」的强基线接近 Self 判据，也不满足「进 P2」的稳健 gap 判据，处于 **kd_only 证据不足的未定分支**。按 PI §3.3，kd 补跑的意图是二择一，但单 seed 结果未给出清晰择支信号。PI 需在（a）GPU 空闲后补齐 kd seed1/2 并同预算复核，与（b）基于现有单 seed 接受「方向性 gap、不作强结论」之间裁决。

---

## 4. 更新后的阶段放行建议

| 阶段 | 第 2 轮建议 | 理由 |
|---|---|---|
| **P0 / E0** | **GO（确认）** | E0 repro 数值 PASS（cosine 1.0、KL 0、EM 1.0、round-trip、zero-re-prefill、2.2e-16≪6.95）；R1 已闭环，可复现来源成立。 |
| **P1 — 证据 / 边界定位** | **GO** | 权威 repro run 可复现、联合报告齐全、broken-transfer 边界已正确标注。 |
| **P1 — 进 P2 的失真前提** | **条件 GO（仍受限）** | R1/R4 闭环，kd seed0 方向支持 gap 未消除；但单 seed + 预算不对等 + δ 未锁定 → 不足以放行 P2 主线。 |
| **P2 机制** | **NO-GO** | δ 未锁定（硬阻塞）+ kd 单 seed 不足以支撑稳健失真前提 + E2 未运行。 |
| **P3 方法** | **NO-GO** | P2 未闭环；δ 未锁定（严禁据不完整网格事后锁定）；封存测试未运行。 |
| **P4 泛化** | **NO-GO** | 上游未闭环；未见模板 / 真实文档 / 封存 test 未运行。 |
| **P5 成稿 / 投递** | **NO-GO** | 上游未闭环；论文主表仍引用 provisional 旧 run、贡献(1) 措辞与 repro 引用待同步（§4 写作者项）。 |

---

## 5. 给 PI 的最终建议

1. **R1/R2/R4/R5/R6/R7/R8 判定闭环**；P0/P1 证据层可放行，不再阻塞。**R3 部分闭环**，δ **未闭环**（阻塞 P2/P3），pytest **待验证**（次要）。
2. **择支**：kd_only 单 seed 0.735 [0.552, 0.934] 未接近 Self、也未构成稳健 gap；两条决策树分支均未被清晰触发。建议 **GPU 空闲后补齐 kd seed1/2（≥3 seed）并按同预算复核**，再正式择支；在此之前 P2 维持 NO-GO。
3. **δ**：不得据不完整网格锁定；须补齐 δ=2.0（必要时 q70 补充候选）、同预算复核后由 PI 以新增版本文件冻结，方可解锁 P2/P3。
4. **论文**：R1 已闭环，可按 PI §2.5 恢复 "reproducible" 并附 commit `458de18`；但须把主表数值引用由 provisional 旧 run 切换为 `*_repro_*` 权威 run，并在 §5.2 脚注/贡献(1) 补 kd_only 说明、贡献(2)(3) 维持 withheld、主验证仍为 broken-transfer 失败边界。
5. **工具**：请工程师将 `consistency_check` 的扫描限定为 `reports/runs/*`（排除 `reports/review/` 等），使 failed 计数精确；并重跑 pytest（GPU 空闲时）以复核 53/53。

## 6. 给工程师 / 写作者的遗留清单（本审稿人不自行执行）

- **工程师**：(a) 补 kd seed1/2 至 ≥3 seed、与 kd 参照同预算；(b) 完成 δ=2.0 网格（含 q70 必要时）后报 PI 锁定；(c) 主验证对补 kd_only（可选，PI §3.2）；(d) `consistency_check` 扫描限定 runs 目录；(e) GPU 空闲重跑 pytest 53/53。
- **写作者**：(a) 主表数值引用切换为 repro 权威 run + commit `458de18`，恢复 "reproducible" 措辞；(b) 贡献(1) 补 kd_only 结果说明（gap 缩小约 63% 但未消除、单 seed 限制）；(c) 保留 broken-transfer 与 P2–P5 未运行声明；(d) 维持贡献(2)(3) withheld、主终点未评估、P>0.05 不作等效。

---

## 7. 结论

第 1 轮的**唯一阻塞项 R1 已闭环**（新 commit `458de18` 含全部跑分代码，权威新 run provenance 齐全，旧 run 正确 superseded 且未改），R2/R4/R5/R6/R7/R8 均已闭环。**R3 部分闭环**——kd_only 补跑证实 gap 缩小约 63% 但未消除（CI 下界 0.552>0），方向支持 H1 前提，但**单 seed + 预算不对等不足以作强结论**，决策树两条分支均未被清晰触发。**δ 未闭环**（网格缺 δ=2.0），构成 P2/P3 硬阻塞；pytest 因 GPU 争用待验证。

据此：**P0 GO；P1 证据/边界层 GO，进 P2 前提仍受限；P2–P5 维持 NO-GO。** 第 2 轮为协议允许的最后复审轮，δ 锁定与 kd 三 seed 补齐问题若仍未解决，按 PI 裁决直裁，不进第 3 轮（审稿侧）。

**签署：reviewer（对抗性审阅），2026-11-23。**

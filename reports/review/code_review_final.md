# 实现一致性代码审查报告（独立复核 · 938f3a0..HEAD + 工作区）

> 审查人：code-reviewer（实现一致性）。日期：2026-11-23。
> 范围：`experiments/anchor_squad_gpu.py`、`scripts/{export_task_data,bootstrap_ci_report,consistency_check}.py`、`src/readkv/**`（runtime/context、stats/bootstrap、models/hooks）及 938f3a0..HEAD 的 src/experiments/scripts 变更（该区间内仅 `938f3a0` 引入 `anchor_squad_gpu.py`，其余为 docs/reports/configs）。
> 依据：`docs/protocol.md`、`docs/experiment_design_E0_E7.md`、`configs/prereg/{stats_convention_v2.3,external_validity_v2.4}.yaml`、`docs/decisions/research_scope_update.md`。
> 只读审查：未改代码/数据/判据/运行产物/论文。工作区 clean，HEAD=`9d80bce`。

---

## 0. 总体判定

> **阻塞问题：NONE。** 新评测路径（SQuAD 锚点）的 joint 臂确实实现 zero re-prefill；锚点 scores 仅 `anchor_squad_dev`，未读合成 test、未混算冻结 CI；v2.3 统计口径（template_family 主 CI + pair-level 敏感性 + min24 exploratory）实现正确；kd_clean 已纳入 bootstrap_summary；run_id 命名符合 v2.4；冻结判据未被篡改。
>
> 发现 **2 项主要**（均在审计脚本，属"审计盲点"而非当前结果错误）与 **6 项次要**（provenance 字段/可复现性/测试覆盖）。建议主要项在 P5 投递前修复或由 PI 显式接受风险；均不改变当前锚点/统计结论，不阻塞进入下一阶段。

---

## 1. 阻塞级（Blocking）

**NONE。**

---

## 2. 主要级（Major）

### M1. 新锚点评测代码未被 traceability 审计集合覆盖
- **位置**：`scripts/consistency_check.py:20-35`（`RUN_CODE_PATHS`），影响 `check_run` 的 `code_tracked` / `run_code_unchanged_vs_head`（`consistency_check.py:174-184`）。
- **问题**：`RUN_CODE_PATHS` 仅列 P0/P1 跑分代码（P0_gpu、P1_gpu、P1_kd_gpu、gpu_backend、hooks、cf_pipeline、kd_gpu、layer_map 等），**不含本轮新增的 `experiments/anchor_squad_gpu.py`**。因此两个锚点 run 的 `consistency_report.json` 报 `traceable=true / code_tracked=true / run_code_unchanged_vs_head=true`，实际上从未校验过真正产出它们的锚点评测代码。若日后 `anchor_squad_gpu.py` 被改动（含 zero-re-prefill 相关逻辑），该审计不会发现——直接削弱"新评测路径 zero-re-prefill 可追溯"这条硬约束的机器保障。
- **复现**：`grep -n anchor scripts/consistency_check.py` → 无命中；对比 `reports/consistency_report.json` 中 anchor run 的 `traceable=true` 与 `missing_code_paths=[]`。
- **建议**：将 `experiments/anchor_squad_gpu.py` 加入 `RUN_CODE_PATHS`；更稳妥做法是按 stage 分集合（anchor run 校验锚点代码，P0/P1 run 校验主验证代码），避免把无关历史 run 误判为代码漂移。修改后可重跑 `consistency_check` 复核两个锚点仍 `ok=true`。

### M2. `model_pair` 非法/缺失时审计静默放行（silent pass）
- **位置**：`scripts/consistency_check.py:101-110`（`_check_model_pair` 未知 pair 分支返回 `{"ok": False, "reason": ...}` 但**无 `problems` 键**）+ `scripts/consistency_check.py:188-190`（`problems.extend(pair_check.get("problems", []))`）。
- **问题**：当 `model_pair` 未知或为空时，`_check_model_pair` 返回的字典不含 `problems`，`check_run` 的 `problems.extend(...)` 为空操作，`ok` 仍为 `true`。当前两个锚点 run 的 `model_pair_check = {"ok": false, "reason": "unknown model_pair ''"}` 却 `ok=true`——锚点本就 N/A，尚可接受；但同一逻辑意味着任何主验证 run 若把 `model_pair` 拼错/写空，`consistency_check` 会**静默放行**，model_pair↔teacher/student↔层数一致性这道关卡形同虚设。
- **复现**：构造 `experiment_config.model_pair="typo"` 的 config，`check_run` 返回 `ok=true`（其他项正常时）。
- **建议**：对非锚点 run，未知/空 `model_pair` 应写入 `problems` 使 `ok=false`；对锚点 run 显式标注 `model_pair=N/A（external_anchor）` 并让 `model_pair_check.ok=true`，而不是依赖"缺键"造成的静默通过。（此点与既有 `anchor_eval_review.md` D4 同源，但根因在脚本逻辑，应修脚本而非只做披露。）

---

## 3. 次要级（Minor）

### m1. 锚点评测使用硬编码绝对路径（可复现性）
- **位置**：`experiments/anchor_squad_gpu.py:38`（`ANCHOR_FILE = Path("/root/readkv/data/anchors/squad/dev-v2.0.json")`）、`experiments/anchor_squad_gpu.py:196`（`reports_root=Path("/root/readkv/reports/_non_authoritative")`）。
- **问题**：路径绑死 `/root/readkv`。换工作目录/克隆位置即不可复现，与"确定性可复现"要求相悖（v2.4 §run_discipline 与 scope §3.5）。
- **建议**：改为相对 `Path(__file__).resolve().parents[1]` 解析；锚点文件 sha 在 `main()` 已校验，路径解耦不影响数据绑定。注：config 中记录的模型权重绝对路径属 provenance 转抄，可保留。

### m2. `zero_ok` 未作为硬门；config 的 `zero_re_prefill=True` 是先验写死
- **位置**：`experiments/anchor_squad_gpu.py:149,160,189,195,206-212`。
- **问题**：`zero_ok &= verify_zero_re_prefill(..., strict=False)` 仅累积布尔值，从不断言；`v2_context(... zero_re_prefill=True)` 在循环前即把 config 标为 True，而 metrics 才写 `bool(zero_ok)`。若任一臂验证失败，run 仍成功落盘、config 仍 `true`，只有 metrics 为 `false`——存在"config 声明 True 而实测 False"的潜在不一致（当前两 run 实测均为 True，无现实影响）。
- **建议**：`finalize()` 前 `assert zero_ok`（joint 臂可用 `strict=True`），并让写入 config 的 `zero_re_prefill` 取自实际验证结果而非字面常量。

### m3. `data_sha256` 仅嵌套于 `experiment_config`，且不在一致性审计必检键中
- **位置**：`experiments/anchor_squad_gpu.py:186`（写入 `experiment_config.data_sha256`）；`src/readkv/runtime/context.py:70-84`（config 顶层无 `data_sha256`）；`scripts/consistency_check.py:168`（必检键列表无 `data_sha256`）。
- **问题**：审查契约要求 config.json 含 `data_sha256`。锚点 config 中该字段**存在但位于 `experiment_config` 内**，非顶层；且 `check_run` 不校验该键。顶层实际字段为 run_id/protocol_version/git_hash/created_at/seed/device/dtype/kernel/zero_re_prefill/experiment_config/metadata。既有 `anchor_eval_review.md` §2.1 将其笼统记为"字段齐全"，未区分层级。
- **建议**：在 `v2_context`/锚点 config 顶层显式写 `data_sha256`（或文档明确嵌套位置为 canonical），并把 `data_sha256` 加入 `consistency_check` 必检键；不影响当前科学结论。

### m4. 锚点 config 缺 `bootstrap_seed`（v2.4 provenance 契约）
- **位置**：`experiments/anchor_squad_gpu.py:178-199`（config 构造未含 `bootstrap_seed`）；对照 `configs/prereg/external_validity_v2.4.yaml:130-132`。
- **问题**：v2.4 §run_discipline 要求每 run config 写 `.../bootstrap_seed/zero_re_prefill`。实测两个锚点 config 顶层与 `experiment_config` 均**无 `bootstrap_seed`**（`anchor_eval_review.md` §2.1 声称存在 `bootstrap_seed=0`，与实际 config 不符）。因锚点不计算 bootstrap，无科学影响，但属契约字段缺失。
- **建议**：在锚点 config 的 `experiment_config` 补 `bootstrap_seed=0`，与 v2.4 对齐；或由 PI 明示锚点臂豁免该字段。

### m5. v2.3 统计口径核心逻辑缺单元测试
- **位置**：`tests/test_bootstrap.py:1-27`（仅测 `readkv.stats.bootstrap` 底层函数）；未被覆盖的是 `scripts/bootstrap_ci_report.py:29-172` 的 `_fill_template_family` / `_cluster_labels` / `_dual_ci` / `summarize_run`（主终点与 pair 敏感性）。
- **问题**：v2.3 的 forbidden rule 是"不得把 pair-level 当主 CI""簇数<24 标 exploratory"。当前无任何测试锁定这些行为；若 `_cluster_labels` 回归为始终用 pair_id，或漏掉 `exploratory` 标记，`pytest` 不会失败。
- **建议**：新增测试断言：主 `cluster_unit="template_family"`、同时存在 `pair_level_sensitivity`、`n_clusters<24 ⇒ exploratory=true`、锚点 scores（无 E_CF）不进入 E_CF CI。scope §4.3 允许"缺键断言"类实现一致性修正。

### m6. 锚点 gold answer 仅取 `answers[0]`，与官方 SQuAD EM/F1 口径略有差异
- **位置**：`experiments/anchor_squad_gpu.py:89`（`"answer": qa["answers"][0]["text"]`）。
- **问题**：官方 SQuAD 对每个题取所有标注答案的 max EM/F1；本实现只用第一条。会低估绝对 EM/F1（当前全臂 EM=0，结论不受影响）。归一化函数本身（lower→去标点→去冠词→空白规整，:67-74）与官方一致。
- **建议**：在 `anchor_eval_summary.json` limitations 中补记"单 gold answer，仅作相对臂对照，非官方 SQuAD leaderboard 分数"；或改为 max-over-answers。

---

## 4. 合规确认（已核实为正确）

| 审查点 | 结论 | 证据 |
|---|---|---|
| joint 臂 zero re-prefill | ✅ | `anchor_squad_gpu.py:151-160`：教师 prefill 文档→`mapper.transform(t_cache)`→`inject_and_generate(sm, cache, q_tok)`，学生仅前向 query+解码；`hooks.py:419-425` 仅喂 `input_ids=query`，文档 K/V 全来自注入缓存；`verify_zero_re_prefill` 对两臂通过，metrics `zero_re_prefill=true`。未在 joint 路径读取 `C_S(d)` 或文档 token。 |
| anchor eval 正确性 | ✅ | `get_examples` 仅取 answerable、按文件序 `[:n]` 确定性；`main()` 先校验 sha `80a5225e…82d8`（:113-115）；EM/F1 归一化与 SQuAD 官方一致。 |
| 数据泄漏 / test 隔离 | ✅ | 两 run scores 共 960 行 `split` 全为 `anchor_squad_dev`；config `synthetic_test_used=false`；mapper 仅用合成 train（`split_pairs(...,"train")`，:131-141），未读合成 test；`data/anchors/squad/` 无衍生语料发布。 |
| 契约字段 | ✅（部分见 m3/m4） | 锚点 config 含 git_hash=`b7b9f50`、protocol_version、seed、dtype、kernel、zero_re_prefill；data_sha256 嵌套存在；两锚点 manifest 三文件 sha **逐项实测匹配**。 |
| run_id 命名 v2.4 | ✅ | `anchor_squad_affine_seed0` / `anchor_squad_kd_seed0` 与 v2.4 `anchor_{squad\|arc}_{affine\|kd}_seed0`（`external_validity_v2.4.yaml:124`）完全一致。 |
| v2.3 统计口径 | ✅ | `bootstrap_ci_report.py:46-75,123-135`：主聚类单元 `template_family`，pair-level sensitivity 同时报告，`n_clusters<24 ⇒ exploratory`；主终点为 `new_joint − joint` 成对差，改进判据 `ci[1]<0`（CI 上界<0）。本数据 8 族 exploratory，point=0、CI=[0,0]，`improved=false`，无假阳性。 |
| kd_clean 入汇总 | ✅ | `bootstrap_summary.json` 的 31 runs 含 `p1_kd_clean_mvp_seed{0,1,2}` 且 protocol=v2.0/stats=v2.3。 |
| pair-level 未冒充主 CI | ✅ | `_cluster_labels` 在无 template_family 时回退 `cluster-fallback` 并**显式标注** `cluster_unit`，不静默当作 template_family；端点主 CI 用簇级 `cluster_bootstrap`。 |
| 锚点未混算/未重算冻结 CI | ✅ | 锚点 scores 无 E_CF/gold_prob → bootstrap 报 `arms={}`、`protocol=v1.0`、`stats=n/a`；未进入任何合成 E_CF 主终点。 |
| 冻结判据未被篡改 | ✅ | `git diff 938f3a0..HEAD -- docs/protocol.md configs/prereg` 中 v2.1–v2.4/stats v2.3 均未改；v2.5/v2.6 为**新增且现已纳入 git 跟踪**（`git ls-files` 确认），非静默改冻结文件。 |
| 无 mock/smoke 混入正式证据 | ✅ | `bootstrap_summary.json`/`consistency_report.json` 对 "smoke/non_authoritative" 命中数=0；smoke 产物仅在 `reports/_non_authoritative/`，被两脚本的 glob 排除。 |
| E_CF 定义/τ/δ/统计口径未改 | ✅ | 938f3a0..HEAD 无任何 `src/readkv/**` 改动；`E_CF`、flip 口径（398, 排除 F5+F6）、δ=0.5 未被实现侧改动。 |
| 新课题一致性 | ✅ | 未发现 P2/P3/P4 重启、封存 test 触碰、贡献恢复或"跨源普适性/方法增益"措辞；`research_scope_update.md` §8.7 对 code-review 的授权边界被遵守。 |
| 确定性 seed | ✅ | `context.seed_everything`（random/numpy/torch/cuda/PYTHONHASHSEED）与 `default_rng(seed)` bootstrap；未启用 deterministic kernel（框架既有说明，非本轮回归）。 |

---

## 5. 给各角色的处置建议

- **给工程师**：优先修 M1、M2（改 `scripts/consistency_check.py`，不改判据、不改 run 产物）；可一并处理 m1–m4、m6。修 M1/M2 后重跑 `consistency_check`，确认锚点与 clean run 的 `ok` 判定不被误改。m5 建议补 `tests/test_bootstrap.py` 的口径锁定测试。
- **给高级工程师**：M1 是高风险点——新评测代码的机器可追溯性缺口，建议做一次深度审计确认零 re-prefill 结论不是只靠人工阅读保证。
- **给 PI**：**可合并 / 可进入下一阶段（P5 合规复核）**；无阻塞。建议在 P5 签 off 前确认 M1/M2 已修或书面接受风险，并落实 m3/m4 的 provenance 字段契约。所有修复不得改动已冻结判据、E_CF 定义或 `reports/runs/**` 不可变产物。

---

## 6. 结论

938f3a0..HEAD 及工作区的实现变更（核心为 `anchor_squad_gpu.py` 引入的 SQuAD 外部锚点评测）在 zero re-prefill、数据隔离、统计口径、产物契约与新课题一致性上总体合规，未发现阻塞问题。两项主要问题位于审计脚本（`consistency_check.py`），属"审计盲点"，不影响当前冻结结果但应在投递前收敛。其余为 provenance 字段/路径可复现性/测试覆盖的次要改进。

**阻塞：NONE。审查结论：通过（附 2 主要 + 6 次要整改项）。**

**签署：code-reviewer（实现一致性），2026-11-23。**

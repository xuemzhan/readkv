# 高级工程师 / Implementation Audit 终审报告（GPU hooks · 缓存注入 · 锚点 · 数据导出 · 统计）

> 审计人：senior-engineer（实现审计与技术把关）。日期：2026-11-23。
> 范围：`938f3a0..HEAD`（`b7b9f50`、`d0f54de`、`0fa65cc`、`4613200`、`9d80bce`）及审计时工作区。
> 依据：`docs/architecture.md`、`docs/gpu_handoff.md`、`docs/protocol.md` §2/§4/§9、`configs/prereg/{stats_convention_v2.3,external_validity_v2.4}.yaml`、`docs/decisions/research_scope_update.md`。
> 方法：**只读**。逐行阅读实现 + 对冻结 `scores.jsonl` 独立重算 + `git` 溯源 + `sha256sum` 实测。未改任何代码/数据/判据/运行产物/论文。
> 说明：审计期间检测到另一角色并发修改 `papers/readkv_v2_draft/main.tex`（`git status` 非 clean），与 run 产物无关，已忽略。

---

## 0. 总判定（先给结论）

| 问题 | 结论 | 严重度 |
|---|---|---|
| 1. SQuAD 锚点 zero-re-prefill 与数据哈希绑定是否工程可信 | **可信**：真实前向 + 真 hook 审计逐样本校验；数据哈希运行时校验且实测一致 | 无阻塞；2 项次要 |
| 1b. EM 全 0 是否实现 bug | **不是 bug**，是未微调 base 0.6B + 原始 prompt + 16-token 贪心 + 严格 EM 的预期结果；有 F1 分度与可读 `pred` 佐证 | 观察性限制（次要） |
| 2. 缓存 round-trip / teacher cache 加载数值稳定性（MVP 等深对） | **稳定**：E0 cosine≈1.0、KL=0、round-trip bit-identical、zero-re-prefill 全通过；RoPE/GQA/position_ids 无错配 | 无阻塞；2 项次要（潜在/非本轮路径） |
| 3. v2.3 pair_id→template_family 映射与 kd_clean CI 复算 | **正确且可复现**：逐 arm 全部数值从冻结 scores 精确重算一致；主口径确为 template_family 簇，pair-level 仅作敏感性并显式标注 | 无阻塞；1 项次要 |
| 4. 确定性/可复现性 | seed/git hash/config 指纹/manifest/数据哈希齐全；跑分代码全程受跟踪且与 HEAD 一致 | 无阻塞；3 项次要 |
| 5. 新课题工程边界 | **确认无越界**：本 commit 区间无任何 P2/P3/P4/G1/封存 test 代码或 run | 无 |

**放行建议：无阻塞级技术风险，可维持当前阶段结论。** 下列 M1/M2 为“契约书写方式”的潜在弱点（本轮未触发），建议作为工程改进项处理，不构成暂停理由。

---

## 1. SQuAD 锚点 run：zero-re-prefill 与哈希绑定可信度 + EM=0 归因

### 1.1 zero-re-prefill 是真实校验，不是“看起来合理”的旗标

- `experiments/anchor_squad_gpu.py:157-160`：每个样本、每个 arm 都调用 `inject_and_generate(...)` 并以 `verify_zero_re_prefill(res, expected_query_len=..., strict=False)` 校验；结果累积到 `zero_ok`，写入 `metrics.json:zero_re_prefill`（`anchor_squad_gpu.py:206`）。两个 run 的该字段实测均为 `true`。
- 校验依据是真 hook：`models/hooks.py:317-336` 在**学生顶层 forward** 注册 `register_forward_pre_hook(with_kwargs=True)`，逐次记录 `input_ids` 长度；`hooks.py:499-505` 断言「每次 forward token 数 ≤ query_len+decode」「喂给学生文档的 token 数 = total−query_len−decode = 0」「forward 次数 = 1+n_decode」。学生只处理 query；文档 K/V 全部来自注入缓存（`hooks.py:399-425`）。这是协议 §2 要求的真实 instrument，不是硬编码。
- **次要弱点（本轮未触发）**：`config.json` 里的 `zero_re_prefill` 是**声明式**——`anchor_squad_gpu.py:189,195` 无条件传 `True` 给 `v2_context`，不随 `zero_ok` 变化；`RunContext.__init__`（`runtime/context.py:70-84`）把该参数写进 config。当前 metrics 实测为 true 所以无害，但若未来出现违规，只看 config 的读者会被误导。**建议**：让 `v2_context` 的写入值来自实测 `zero_ok`，或在 config 中同时写 `zero_re_prefill_measured`（字典型，区分声明与实测）。

### 1.2 数据哈希绑定：运行时校验 + 实测一致，可信

- `anchor_squad_gpu.py:113-115`：run 启动即算 `sha256(ANCHOR_FILE.read_bytes())`，与硬编码 `ANCHOR_SHA256=80a5225e…82d8`（:39）不符则 `RuntimeError`。config/metrics/scores 的 `data_sha256`/`anchor_file_sha256` 均取此实测值。
- 审计复算：`sha256sum data/anchors/squad/dev-v2.0.json` = `80a5225e94905956a6446d296ca1093975c4d3b3260f1d6c8f68bc2ab77182d8`（4,370,528 B），与两个 run 的登记**逐字一致**。
- 子集确定性：`get_examples`（`anchor_squad_gpu.py:76-91`）取 answerable 子集前 n=240，按文件顺序，无随机采样；`seed=0` 已 `seed_everything`。锚点数据**不参与训练**：affine 用合成 train 闭式拟合（:132-137），kd 用合成 train 训 8 epoch（:140-142），`synthetic_test_used=false`。
- 对比：7 个 clean run 的 config **未内嵌** `data_sha256`，靠事后 `reports/data_hash_binding_erratum.json` 补绑（属溯源遗漏已如实披露）——锚点 run 的内嵌绑定明显更强，这一点工程上更可信。

### 1.3 EM 全 0：合理解释，非实现缺陷

- 复算（两个 run 各 480 行 = 240×2）：`self EM=0/240`、`joint EM=0/240`；`self mean F1=0.1975`、`joint F1` affine=0.0051 / kd=0.0014；**F1>0 且 `pred` 为可读文本**（如 `"France\nOkay, so the question is asking where Normandy is located. The answer"`、joint 为乱码串），说明候选 logits readout 与解码链路工作正常，并非取错位置/空输出。
- 归因：`em_f1`（`anchor_squad_gpu.py:98-107`）是标准 SQuAD normalize（去冠词/标点/小写/空白）+ token-F1，实现正确；prompt 为裸 `Question: …\nAnswer:`（:155），模型是 **base Qwen3-0.6B**（未指令微调、无 chat 模板），16-token 贪心生成不截断到短答案 → 严格 EM 必然触底。这是**评测设计限制**而非代码 bug。
- **次要限制（须披露，不可据此下绝对结论）**：EM floor 使跨臂只能靠 F1 分度；F1 绝对值受输出长度/格式影响，只能作相对对照（affine 2.6%、kd 0.7% of self F1）。这与 reviewer 的 D1 一致，我独立复算确认。
- 三情形判读：affine 失败方向复现但 kd 也坍塌、EM 触底、单 seed 240 例 → `exploratory_disclosure` 归类合理，未违反 v2.4 `hard_rule`，未恢复任何贡献。

---

## 2. 缓存 round-trip / identity 与 teacher cache 加载的数值稳定性

### 2.1 实现是真 GPU 前向，契约对齐 mock

- `capture_teacher_cache`（`hooks.py:221-309`）：`model(input_ids=doc, cache=DynamicCache, position_ids=…)` 真前向，逐层取 post-QK-Norm+post-RoPE 的 K/V（:279-280），在 **fp32** 中 de-RoPE（:283-288），落 `KVCache`(H_kv,T,d) fp32；两份文档各自调用、独立 prefill，无篡改缓存字节。符合协议 §2「两份缓存各自独立生成」。
- `inject_and_generate`（`hooks.py:345-451`）：内容空间 K 在 fp32 按 **doc 位置** re-RoPE 后写回 `DynamicCache`（:392-407），query 位置显式 `offset..offset+Q-1`（:393），首 token logits 取自 query 末位（:426），不在已推进 cache 上生成；`max_new_tokens` 解码位置逐个 +1（:431）。
- `_check_rope_compatible`（`hooks.py:204-214`）在注入前比对 `teacher_rope_theta/rope_type/max_position_embeddings/head_dim` 与当前模型，不一致即拒绝注入，避免 de/re-RoPE 不对消。

### 2.2 E0 数值证据（MVP 等深对，真实 GPU）

| run | min cosine | max KL | self-anchor min cos | round-trip | zero-re-prefill | em_agree | effect / tol |
|---|---|---|---|---|---|---|---|
| `e0_gpu_mvp_seed0` | 0.9999999999999998 | 0.0 | 0.9999999999999998 | bit-identical | all true | 1.0 | 20.86 / 6.95 |
| `e0_gpu_mvp_repro_seed0` | 同上 | 0.0 | 同上 | ✓ | ✓ | 1.0 | 20.86 / 6.95 |
| `e0_gpu_main_seed0` | 同上 | 0.0 | 同上 | ✓ | ✓ | 1.0 | 19.99 / 6.66 |
| `e0_clean_mvp_seed0` | 同上 | 0.0 | 同上 | ✓ | ✓ | 0.975 | 23.88 / 7.96 |

- Identity 注入与「学生原生两步路径」cosine≈1.0、KL=0，误差上限远低于效应/3，E0 `passed=true`、`release_to_P1=true`。这是**真 GPU 证据**，非 mock。
- one-shot（整段一次 prefill）cosine≈0.9991–0.9997，残差来自 sdpa kernel 路径差异（非实现误差），`P0_gpu.py:298` 已如实归因。符合 gpu_handoff §2「残差只来自 one-token query vs full-sequence prefill 的 attention kernel 路径」。

### 2.3 shape / position_ids / RoPE / GQA 逐项核对

- **RoPE 约定**：`_rotate_half`（`hooks.py:139-145`）为 half-split，与 Qwen3 一致；`_rope_cos_sin`（:120-136）用 fp32 dummy 取未舍入 cos/sin，de-RoPE `x*c − rot(x)*s`（:157-160）为 `_apply_rope` 的正交逆，可精确对消。`
- **广播**：`_apply_rope/_de_rope` 用 `unsqueeze(-3)` 兼容 (H,T,d) 与 (1,H,T,d)（`hooks.py:148-160`），cos/sin 形状 (1,T,d)→unsqueeze→(1,1,T,d)，与 (1,H,T,d) 广播正确。
- **position_ids**：capture 默认 `0..T-1`（:247-248），inject doc 段 `0..doc_len-1`、query 段 `offset..`（:392-393）对齐；`gpu_backend.py:100-119`、kd_gpu 的 `_gpu_candidate_logits`（:34-58）同样显式 `+doc_len`，三处口径一致。
- **GQA**：MVP 1.7B→0.6B 均为 8 KV heads、head_dim=128、28 层；cache (H_kv=8,T,128) 直接喂 `DynamicCache`，学生内部按 `num_key_value_heads` 处理，无头数错配；affine 逐 head `min(t_kv, s_kv)` 拟合（`representation.py:32-36`），等深对 8↔8 匹配。
- **层映射**：`LayerMap(identity)`（1.7B/0.6B 同 28 层），`_layer_map_entry`（`hooks.py:163-174`）注入侧查表一致。

### 2.4 次要/潜在问题

- **M1（潜在，非本轮路径）** `cache/identity_check.py:107`：回退分支写成 `max_kl <= max_kl`，局部量 `max_kl=float(max(kls))` 遮蔽了同名参数 `max_kl=1e-3`，恒真。**未影响 E0**：`P0_gpu.py:274-278` 独立计算 pass/fail 并于 :279 覆盖 `gate.passed`，且本轮 `effect_size_floor>0` 走另一分支。属死代码缺陷，建议改名 `max_kl_limit` 并补断言测试。
- **M2（潜在，调用方契约）** `AffineMapper.transform`（`representation.py:123-139`）按 teacher 层号直接查以 **student 层号**为键的矩阵；等深对（28↔28）无误。非等深 4B→1.7B（36→28）时 teacher 层 28–35 无矩阵会原样透传。transform 注释声明「调用方先按 layer_map 选好 teacher 层」，本锚点等深无需选层故不触发；非等深主验证对已被永久放弃，风险理论化。建议 transform 内部强制层映射或断言覆盖。

---

## 3. v2.3 统计脚本：pair_id→template_family 映射、kd_clean CI 复算、pair 冒主风险

### 3.1 映射正确且完整

- 冻结 `p1_kd_clean_mvp_seed0/scores.jsonl`（600 行）：每行带 `template_family`（8 个取值，如 `S-F1-person-C`）与 `cluster`（60 个，如 `val-S-F1-person-C-000`）。`self` arm 的 60 行缺 `template_family` 且 `E_CF=0`。
- `bootstrap_ci_report.py:29-43` `_fill_template_family` 用同文件其它 arm 的 `pair_id→template_family` 映射补齐缺失；`:46-51` `_cluster_labels` 仅在**所有**行都有 `template_family` 时用之，否则诚实标 `cluster-fallback`。补齐后 600/600 行均有该字段，主口径确为 `template_family`，`n_clusters=8`，`exploratory=true`（8<24）。
- 8 族 < 24 → v2.3 `min_clusters_for_inference` 规则正确触发，标探索性，符合 `stats_convention_v2.3.yaml:19-20`。

### 3.2 cluster-level paired bootstrap 实现正确

- `stats/bootstrap.py:40-61` `cluster_bootstrap` 以簇为重采样单位：`groups=[x[c==g]]`，每轮按簇有放回抽取后 `concatenate` 组内值取均值。主终点（`bootstrap_ci_report.py:109-135`）先按 pair_id 算 `new_joint − joint` 成对差，再以 `template_family` 聚簇重采样——即**簇级 paired bootstrap**，非逐对。
- `_dual_ci`（:54-75）同时给出 template_family 主 CI 与 `pair_id` 敏感性 CI，字段 `cluster_unit`/`n_clusters`/`exploratory`/`pair_level_sensitivity` 一应俱全。

### 3.3 kd_clean CI 独立复算：**精确一致**

从冻结 `scores.jsonl` 重跑 `summarize_run(n_resamples=10000, seed=run_seed)`，与 `reports/bootstrap_summary.json` 对比（三 seed × 10 arm × 主 CI + pair-level CI）：

```
p1_kd_clean_mvp_seed0  joint 6.388 [3.653, 8.814] == frozen ✓
p1_kd_clean_mvp_seed1  joint 6.479 [3.899, 8.798] == frozen ✓
p1_kd_clean_mvp_seed2  joint 7.210 [4.417, 9.799] == frozen ✓
10 arms × 3 seeds : 全部主 CI 与 pair-level CI 字符串逐字一致（ALL MATCH: True）
```

- `primary_endpoint`（new_joint − joint）三 seed 均为 `point=0, ci=[0,0], improved=false`（同 run 内两臂相同），**未伪造 CI 上界<0 的改善**。与主终点未评估、方法层取消的裁决一致。
- flip 分母：`bootstrap_summary.json.flip_denominator = {excludes:[F5,F6], recomputed_value:398}`，来自 `data/tasks/manifest.json::quality`，与 v2.3 `after_degenerate_fix:398` 一致。

### 3.4 pair-level 冒主 CI 风险：**实现层不存在**

- 主 CI 用 template_family、pair-level 只作 `E_CF_pair_level_sensitivity` 并显式标注 `cluster_unit=pair_id`；两者**都被报告**（v2.3 forbidden `reporting_only_pair_level_ci_without_template_family_ci` 未触发）。summary 顶层亦写 `cluster_bootstrap_convention.primary_cluster_unit=template_family`。
- **次要（展示层，非实现层）**：锚点 run 因只有 EM/F1 无 E_CF，被 `summarize_run` 走 V1 兼容分支，在 `bootstrap_summary.json` 留下 `arms={}, protocol=v1.0, stats_convention="n/a (v1 scores)"` 的空条目——不会伪造数字，但读者需注意别把它误读为“锚点做了 CI”。建议锚点 run 在非 E_CF 分支显式标 `not_applicable: external_anchor`。

---

## 4. 确定性 / 可复现性

- **seed**：`RunContext.seed_everything`（`runtime/context.py:88-98`）设 `random`/`numpy`/`PYTHONHASHSEED`/`torch.manual_seed`/`cuda.manual_seed_all`；未启用 deterministic kernel（:98 注释披露），梯度族按 ≥3 seed 报范围——与协议一致。
- **commit 跟踪**：`_git_hash()`（:27-33）在 run 创建时 `git rev-parse --short HEAD` 真取；锚点 run `git_hash=b7b9f50`。`consistency_report.json` 对两锚点：`traceable=true`、`code_tracked=true`、`git_hash_in_history=true`、`run_code_unchanged_vs_head=true`、`dirty_run_paths=[]`。
- **config 指纹**：E0 `P0_gpu.py:140` 用 `config_fingerprint(cfg_meta)` 写入 config（含 model revision/template/dtype/kernel/rope_scaling）；锚点 run 未写 config fingerprint，仅记 teacher/student 路径——**次要**：ModelScope 路径为快照目录名（含 `master`），未钉到具体 revision/commit，模型权重精确复现有轻微缺口。
- **manifest 哈希**：`RunContext.finalize`（:140-151）对 config/metrics/scores 逐文件 sha256；锚点 manifest 3/3 实测匹配。
- **未跟踪代码影响 run**：`git diff --name-only 938f3a0..HEAD | grep -E '^(src|scripts|experiments)/'` = 空；跑分代码自 `efc3ba3`/`6413ba0`/`938f3a0` 起未改，全部受跟踪且为当前 HEAD 的祖先。`consistency_check` 的 `run_code_unchanged_vs_head=true` 佐证。**无未跟踪代码影响 run。**
- **次要**：`consistency_check.py:22-38` 的 `RUN_CODE_PATHS` **不含** `experiments/anchor_squad_gpu.py`，故锚点“代码受跟踪”检查未覆盖其专用入口（该文件确已由 938f3a0 跟踪，结论不变）。建议补入集合。
- **次要**：锚点 config 无 `model_pair` 字段，`consistency_report` 中 `model_pair_check.ok=false`（`unknown model_pair ''`）但未计入 `problems`（reviewer D4）；建议对外部锚点显式标 `model_pair=N/A`，避免误读。

---

## 5. 新课题下的工程边界（P2/P3/P4/G1/封存 test）

**确认无越界，证据如下：**

1. `938f3a0..HEAD` 的代码 diff（`src/`、`scripts/`、`experiments/`）为**空**——本区间未新增任何机制/方法/泛化/封存评测代码。
2. 本区间新增 run 仅 `reports/runs/anchor_squad_{affine,kd}_seed0/` 两个，均为 `stage=external_anchor`、`gate=SQuAD_v2.0_dev`、`protocol_version=2.4`（experiment 字段）、`split=anchor_squad_dev`、`synthetic_test_used=false`。无 `P2/P3/G1/real/封存 test` run。
3. mapper 训练仅用合成 train：affine `cal_docs` 来自 `split_pairs(...,"train")`（`anchor_squad_gpu.py:131-137`），kd `train_kd_gpu(backend, trains, ...)`（:140）——不碰封存 test，不用锚点标签。
4. 与 `research_scope_update.md` §1.3/§3/§5 的不可变边界一致：贡献(1)(2) 撤回、贡献(3) withheld；P2/P3/P4 不重启；封存 test 不碰；G1 未启动；v2.6 为 not-activated 工作包（本区间新增的 v2.5/v2.6 prereg 文件仅文档，不触发实验）。
5. 唯一需提示：`configs/prereg/ai_generated_data_v2.6.yaml` 在锚点阶段曾被 reviewer 标为 untracked（D3）；本轮 `git diff --stat 938f3a0..HEAD` 显示它已作为新增文件纳入 938f3a0 之后的版本库，溯源缺口已消除。

---

## 6. 风险登记（按严重度）

### 阻塞（Blocking）
- **无。**

### 主要（Major）
- **M1**：`zero_re_prefill` 在锚点 config 中为无条件声明值（声明≠实测），存在“只看 config 被误导”的潜在契约风险；本轮 metrics 实测 true，未构成当前缺陷。修复：把实测 `zero_ok` 写入 config 或增加 `zero_re_prefill_measured` 字段。（§1.1）

### 次要（Minor）
- **m1** `identity_check.py:107` `max_kl <= max_kl` 遮蔽缺陷（死分支，E0 未受影响）。（§2.4）
- **m2** `AffineMapper.transform` 非等深层号透传风险（调用方契约未强制；等深锚点不触发）。（§2.4）
- **m3** 锚点被 `bootstrap_summary` 走 V1 兼容分支留下空条目，展示层需注明“不適用”。（§3.4）
- **m4** 锚点模型 revision 未钉到 commit（仅路径快照名）。（§4）
- **m5** `consistency_check.RUN_CODE_PATHS` 未含锚点专用入口 `anchor_squad_gpu.py`。（§4）
- **m6** 锚点 config 缺 `model_pair`，`model_pair_check.ok=false` 被静默放行。（§4）
- **m7** EM floor + F1 相对对照的解释边界（base 未微调、单 seed 240 例）须在论文如实披露。（§1.3）

---

## 7. 最小修复路径（按优先级，均不改冻结判据/产物/论文）

1. 工程：锚点评测入口让 config 的 `zero_re_prefill` 取 `zero_ok` 实测值（或补 `zero_re_prefill_measured`）。**（M1）**
2. 工程：`identity_check.py` 将参数改名 `max_kl_limit` 并加单测覆盖回退分支。（m1）
3. 工程：`consistency_check.RUN_CODE_PATHS` 补 `experiments/anchor_squad_gpu.py`；对无 `model_pair` 的锚点在报告中标 `model_pair=N/A`。（m5/m6）
4. 工程（若后续启用非等深映射）：`AffineMapper.transform` 内部按 layer_map 映射或断言层覆盖。（m2，当前非必做）
5. 展示：`bootstrap_summary` 对非 E_CF run 标 `not_applicable: external_anchor`。（m3）
6. 写作者（非我职责，转交）：披露 EM floor / F1 相对对照 / 240 例 / 单 seed / exploratory；不得升格贡献。（m7）
7. provenance（可选）：锚点 config 增加模型 revision 的具体 commit hash。（m4）

---

## 8. 给 PI 的放行建议

本审计范围内**未发现阻塞级正确性风险**。GPU hooks 为真实前向实现，zero-re-prefill 有真 hook 审计且实测通过，identity/round-trip 数值残差远低于效应下界，v2.3 簇级 CI 从冻结分数精确复现、pair-level 仅作敏感性，锚点数据哈希运行时校验且实测一致，EM 全 0 为 base 模型预期而非缺陷，新课题边界（P2/P3/P4/G1/封存 test 未实现未启动）经 git 与 run 清单双重确认。**建议维持当前阶段结论，无需暂停。** M1 为契约书写改进项，建议在下一次工程收尾中一并处理，不影响证据可信度。

**签署：senior-engineer（实现审计与技术把关）· 2026-11-23。**

# v3.0 G1 工程师实现报告（layer-map 修复 + E1 独立入口）

**日期：2026-11-25。角色：工程师。性质：实现 + CPU 自检 + 测试仪器修正 + pytest 全量回归；
本轮 GPU run = 0，实验结论 = 0。**

**依据**：`reports/review/v3_g1_feasibility_audit.md` §1.4（BLOCKER）/ §3.2（E1 入口规格）、
`configs/prereg/gpu_followup_v3.0.yaml`（FROZEN，只读）、`data/variants_v3/manifest.json`、
`reports/data/v3_e1_variant_audit.md`。

**未越界声明**：本实例未改 `configs/**`、`papers/**`、`docs/decisions/**`、`data/**`、
`reports/runs/**`；未创建任何 run 目录；未下载模型、未安装依赖、未运行 GPU 前向；
未产生 `scores.jsonl` 正式产物；未触碰 layer-0 K/V 捕获回归（独立工单）。
仓库中其他并行实例同期写入的文件（如 E2 入口、基线规格等）不属于本轮工作，
本报告不对其内容或状态作任何声明。

---

## 1. 本轮写入的文件（仅四份 + 本报告）

| 文件 | 变更 |
|---|---|
| `src/readkv/models/hooks.py` | 仅 layer-map 修复相关：把 `SOURCE_LAYER_MAP_KEY` / `resolve_injection_layer_map` 加入 `__all__`。接手时捕获端的 provenance 字段与注入端的恒等解析逻辑已存在（文件 mtime 晚于审计），本轮逐行复核其语义正确，未改动 proportional 公式、未改 capture 回归路径。 |
| `src/readkv/models/gpu_backend.py` | `score_candidate_sequence` 的同类修复：删除直接读 `meta["layer_map"]` 二次施加的分支，改为调用 `H.resolve_injection_layer_map(...)`；同步更新 `layer_map` 参数文档。`candidate_logits` 本来就未显式传 map，现经 hooks 的解析统一走恒等路径。 |
| `experiments/e1_variant_gpu.py` | 新建 E1 显式文件输入独立入口（详见 §3）。module-level 仅标准库，torch/transformers/numpy 全部惰性导入。 |
| `tests/test_layer_map_injection.py` | 新建 36→28 非等深注入回归（详见 §2）；本轮仅修正其中 `score_candidate_sequence` 一项的测试仪器（§2.3），未改生产代码、未放宽断言。 |
| `reports/review/v3_g1_engineer_implementation.md` | 本报告。 |

---

## 2. Task 1：非等深 layer-map 二次施加修复

### 2.1 根因与修复口径

审计 §1.4 的证据链：教师缓存（36 层）按 `LayerMap(28,36,"proportional")` 重索引成
28 层学生空间缓存后，metadata 仍透传 `{0:0,1:1,2:3,…,27:35}`；注入端若复用该 map，
读到的层号是 `mp[s] % 28`——只有 s=0,1 正确，s=2 读 3，s=22 回绕读 0……全部落在
0..27 合法范围内，因此不触发 KeyError，也不触发 zero-re-prefill 断言，是 silent corruption。

修复：

1. `hooks.resolve_injection_layer_map` 先以缓存深度判定层空间：`n_cache_layers <=
   n_student_layers` 即视为已重索引的学生空间，强制返回 `None`（恒等），不读 metadata
   中的 map；只有真正的教师缓存（深度更大）才允许使用捕获时记录的 map。
2. 捕获端把原 teacher→student 映射同时写入 `metadata["source_layer_map"]`
   （`SOURCE_LAYER_MAP_KEY`），只作溯源，注入端绝不施加；`metadata["layer_map"]`
   保留为兼容字段。
3. `_layer_map_entry` 不做静默取模，越界直接 `IndexError`（fail loud）。
4. `gpu_backend.score_candidate_sequence` 与 `inject_and_generate` 使用同一解析函数；
   此前它直接读 `meta["layer_map"]`，是非等深路径上残留的第二个入口。

**未改**：`LayerMap.source_for` 的 proportional 公式
`min(nt-1, round(s*nt/ns))`；`AffineMapper.fit/transform` 的学生层键；layer-0 K/V
捕获逻辑。

### 2.2 新增测试（tests/test_layer_map_injection.py）

- 前置条件断言：28 项 map 与 audit §1.3 一致，且错误实现 `mp[s]%28` 在多处与 s 不同
  （保证测试有判别力）。
- `resolve_injection_layer_map`：学生空间缓存（28 层）必须返回 `None`；教师缓存
  （36 层）才返回原 map；provenance 字段存在。
- `inject_and_generate`：构造 28 层学生空间缓存，用 V 常量给第 s 层打标记（V 不做
  RoPE），断言注入后学生第 s 层读到的标记 == s，而非 `mp[s]%28`；同时
  `verify_zero_re_prefill(strict=True)` 通过、`result.zero_re_prefill is True`。
- 全链路复刻：36 层教师缓存（V 标记教师层号）→ `LayerMappedMapper` 式 proportional
  重索引（metadata 原样透传，正是 bug 触发条件）→ 注入，断言学生层 s 读到的是教师
  `mp[s]`（即映射后缓存第 s 层），而不是二次施加的 `mp[mp[s]%28]`；两者在测试中
  明确可区分。
- `score_candidate_sequence`：在注入读取边界 `H._to_tensor_array` 记录被取用的 V
  数组标记（详见 §2.3 的测试仪器修正），逐层断言标记 == s，且
  `audit.zero_re_prefill is True`；`strict_audit=True` 保持不变。

**状态：PASS（5/5，CPU 前向，无 GPU）**。环境已具备 torch 2.11.0+cu130 /
transformers 5.24.0（与归档 `cache=` API 一致），`pytest` 可用。

### 2.3 测试仪器修正（仅测试，未改生产代码）

首次全量 pytest 中，`score_candidate_sequence` 一项失败：spy `DynamicCache.update`
捕获到的是模型在 query/candidate 前向里算出的 K/V（如 -0.013 / 0.003 / 0.16），
而不是注入 stamp。原因是 `SequenceScoreResult` 不暴露内部 cache，注入直接
`student_cache.update(...)`，而后续前向也会调用同一方法——spy 混入了模型值。
另外两项 `inject_and_generate` 路径均 PASS，证明生产修复本身正确；这是纯测试仪器 bug。

修正：改为 spy `H._to_tensor_array`（`score_candidate_sequence` 注入循环在此读取
`cache.values[t_layer]`），并把 V 用大 offset（1000.0）重打标、K 保持全零，
于是可按学生层顺序还原每层真正取用的 V stamp，且与模型计算值严格区分。
断言从逐层 stamp 相等（0..27）与 `len(observed)==2*28` 双向锁定；
`strict_audit=True` 与 `audit.zero_re_prefill` 断言未删未放宽。

---

## 3. Task 2：E1 独立入口（experiments/e1_variant_gpu.py）

### 3.1 CLI 与冻结值

`--run-id --variant(6) --panel(A|B) --train-path/--train-sha256 --val-path/--val-sha256
--manifest-path/--manifest-sha256 --seed(0|1|2) --model-pair --teacher/--student
--mapper(affine) --ridge-lambda(1e-3) --dtype(bfloat16) --kernel(sdpa) --device(cuda)
--n-resamples(10000) --smoke/--smoke-n-val(6) --out-dir` 全部实现；另加
`--cpu-selfcheck`、`--cpu-replay-only` + `--replay-logits-path/--replay-sha256`、
`--allow-input-change-gpu-forward`。改动 λ、dtype、kernel、seed 等冻结值直接 abort。

### 3.2 哈希绑定与隔离（硬约束逐条落地）

1. 运行时重算 train / val / manifest（及 replay）的 SHA-256，与传入期望逐一比对，
   **不符即 abort** 并写失败 `config.json`，绝不写 `scores.jsonl`/`metrics.json`。
2. 路径白名单：拒绝任何含 `test` 分量/文件名的路径，并额外拒绝原始
   `cf_pairs.jsonl`（含封存 test split 的全量导出）。
3. 未导入、未调用自动重建入口；CPU 自检对源码做静态扫描确认无相关调用。
4. 逐变体登记：`changed_attribute` / `scope` / `rule` / `caveat`、样本数、family 数、
   slice 计数、removed/added pair ids、`text_hash_changed` 计数、substitution_map、
   query_rewrites 数；构成变化或不同 commit 标 `version_difference_flag`。
   同一哈希可能命中多个变体（no-op 变体与 legacy 逐字节相同），Panel 角色检查按
   "期望变体是否在哈希候选集中" 判定，并记录全部候选，避免误拒绝。
5. `degenerate_only`：must-flip 退化对（candidate_A==candidate_B）不进入 ridge
   监督拟合（`fit_ready_pairs`），也不进入 CPU replay 重计分；提供
   `--cpu-replay-only`（哈希绑定的逐对 logits）模式，完全不加载模型。
6. 输入文本改变（entity/template disjoint 的 val）默认禁止 GPU 前向：必须显式传
   `--allow-input-change-gpu-forward`，并在 config/metrics 写
   `data_task_change=true`；此类变体禁止 CPU replay（原 logits 无效）。
7. 产物：smoke → `reports/_non_authoritative/`（或显式 `--out-dir`）；正式 → 新
   `reports/runs/v3_E1_.../`；`mkdir(exist_ok=False)` 不覆盖历史；四件套
   `config.json` / `scores.jsonl` / `metrics.json` / `manifest.json` 齐全并做 schema
   校验。`criteria_source=configs/prereg/gpu_followup_v3.0.yaml`、
   `sealed_test_read=false`、`zero_re_prefill=true`（replay 路径标注
   `basis=no_gpu_forward_cpu_replay`，不冒充前向审计）。

### 3.3 Panel 语义与统计

Panel A = 变体 train + 固定 clean v2.1 val；Panel B = 固定 clean v2.1 train + 变体
val；二者通过 manifest 哈希反查角色并强制校验。等深 28→28 identity 在 GPU 路径
强制断言（非等深/非 28 直接拒绝）。

逐对指标用与 `readkv.evaluate.counterfactual.PairCFRecord` 相同的公式（纯标准库实现，
便于 replay 在无科学栈环境运行）：g = logP(A|C,q)−logP(B|C,q)、D、E_CF、归一化
E_CF、双向成功率、方向一致率（含实际分母 `n_flip_evaluable`）、coverage。臂包含
self / identity / joint / k_only / v_only / control:mismatch / control:random /
control:zero；并列报告 L = Self − Joint、控制组差距。

Bootstrap：`template_family` 簇级百分位 bootstrap（主，10000 次）与 pair-level
敏感性区间并列；`n_families < 24` 标 `exploratory=true`。主终点口径仍为成对
E_CF 差异；本入口只产出逐对分数与描述统计，不做因果分解。

---

## 4. 本轮验证结果（全部为 CPU/wiring，非科学证据）

| 检查 | 结果 |
|---|---|
| `python3 -m experiments.e1_variant_gpu --cpu-selfcheck` | **PASS**：13 项检查全 true（CLI 冻结值、必填校验、哈希一致/篡改 abort、test 路径拒绝、裸 master 拒绝、文本改动显式授权与 data_task_change、产物 schema 正/反例、无自动重建调用）。 |
| 真实 manifest 角色校验（6 变体 × Panel A/B，只读） | PASS：Panel 期望角色全部命中；错误角色被拒绝；`input_text_changed` 在 A/B 的语义正确（template/entity 仅 Panel B 为 true）。 |
| 临时目录 CPU-replay 端到端接线（合成 logits，产物随即删除） | PASS：四件套齐全、schema 校验通过、replay basis 正确。**数字不报告，不作结论。** |
| `python3 -m py_compile` 三份 py 文件 | PASS。 |
| `.venv/bin/python -m pytest -q tests/test_layer_map_injection.py` | **PASS：5 passed**（退出码 0；verbose 显示 `5 passed in 8.26s`）。含修正后的 `score_candidate_sequence` 逐层 stamp 断言。 |
| `.venv/bin/python -m pytest -q`（全量） | **PASS：91 passed**（退出码 0；`91 passed in 16.44s`）。 |
| GPU forward / 显存 / 真实指标 | **未执行**；无可报告结果。 |

当前环境确认：`.venv` 已装 torch 2.11.0+cu130、transformers 5.24.0（`cache=` API
一致）、pytest 9.2.0；上述 pytest 均为 CPU 前向，未使用 CUDA。
系统 `python3` 仍无科学栈，故不带 `.venv` 的纯 stdlib 自检命令仍可用。

---

## 5. Blockers 与下一步（不在本轮权限内）

1. **环境版本仍待 PI 冻结**：当前 `.venv` 为 torch 2.11.0+cu130 / transformers 5.24.0，
   与归档记录的 torch 2.15.0+cu132 不同；虽 API 兼容（`cache=`）、全套 91 项单测在 CPU
   上通过，但**不能据此声称与归档环境字节级一致**。须由 PI 在 G1 放行文件冻结最终
   版本/驱动后，方可把后续 GPU 数字与归档合并。
2. **G2 pilot 尚未做**：4B→1.7B seed-0 小样本的模型加载、tokenizer、逐层映射核对、
   cache 形状、Self/Identity、zero-re-prefill、同卡显存实测（affine/kd_only 分列）。
   本修复把"错层"消除，但 pilot 是放行前置，不能以单测替代。
3. **E1 正式格未启动**：本入口只完成实现 + CPU 自检；需 G2 pilot PASS 与 PI G3
   授权后才可跑，且 seed 分开报告。
4. **E6 复现门 / E2 test 锁 / 模型 revision+文件 SHA 落盘**：属 PI / 数据工程师责任，
   本轮未触碰、未代决。
5. **layer-0 K/V 捕获回归**：审计 §5 的独立工单，本轮明确不修、不以 mock 掩盖。
6. 本入口为 CPU 自检过程中产生的临时文件均在 `/tmp/opencode/`，已删除；仓库内
   无新增 run 目录或实验产物。

**结论：两个工单的代码实现已完成；层映射回归测试与环境相关的 GPU 检查处于 pending；
本轮没有、也不声称任何 GPU 实验结果。**

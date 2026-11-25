# v3.0 G1 可行性审计（只读 · 高级工程师 / Implementation Auditor）

**日期：2026-11-25。性质：READ-ONLY G1 feasibility audit。本次未运行 GPU、未改代码、未改 prereg、未安装依赖、未新增实验。唯一写入文件：本报告。**

**依据**：`docs/audit/GPU_experiment_plan_2026-11-25.md`（§2 共用纪律、§3.4、§5、§6）、`docs/decisions/gpu_v3_scope_ruling.md`（真实 PI G0：E1/E2/E5/E6 全部授权；modelscope.cn 授权为模型/数据来源）、`configs/prereg/gpu_followup_v3.0.yaml`（FROZEN）、下列实现文件、`docs/reproducibility.md`、`reports/review/audit_of_third_party_review_sequence_b0_2026-11-24.md`（仅作背景）。

**审计结论速览**

| 项 | 结论 | 级别 |
|---|---|---|
| E5 模型可获取性 | 已联网确认 4B/1.7B 均在 modelscope.cn `Qwen/Qwen3-4B`、`Qwen/Qwen3-1.7B`，apache-2.0，可下载；但 API 只给 `master` 别名，必须自行钉 revision + 文件哈希 | 可通过（需补钉 revision） |
| E5 现有代码可行性 | **阻塞**：`experiments/P1_gpu.py` 的非等深链路在注入端**二次施加 proportional 层映射并对 28 取模**，把已重索引为学生层 0..27 的缓存映射到错误层；silent corruption（不报错） | **BLOCKER** |
| E5 显存 | 解析估算 ≈ 12–14 GiB（affine）/ 14–18 GiB（kd_only），32GB RTX 5090 理论上够；必须由 G2 pilot 实测，不得据此直接放行 | 需实测（非放行证据） |
| E6 复现门 | 现有证据**未通过**：两篇方法只到摘要级核验，无已核验的代码/权重/许可/完整训练目标；按 prereg §6.1 必须走明确命名的预算匹配内部对照 | G1 结论需落盘 |
| E1 独立入口 | `experiments/audit_2x2_gpu.py` 确认只支持 legacy/fixed 固定四路径 + 等深 identity，不能跑 E1 变体；需新入口 + 哈希绑定 | G1 阻塞项（未实现） |
| 环境 | 当前机器与归档环境不一致（Python 3.12.3 vs 3.13.11；.venv 空；driver CUDA 13.0 vs 记录 cu132；GPU 5090 32GB vs 记录 4090 24GB） | 需在 G1 冻结环境版本 |
| 两个历史敞开项 | 与 v3 研究**分离**，不得混为一谈；但 layer-0 失败测试是 G2 hook 接口前置条件，须单独修复取证 | 分离 + 前置 |

---

## 1. E5 可行性（第二模型对：Qwen3-4B → 1.7B）

### 1.1 模型可获取性与来源证据（联网核验，未下载、未安装）

通过 modelscope.cn 公开 API 直接核验（HTTP 200 / `Success:true`）：

| 项 | Qwen3-4B | Qwen3-1.7B |
|---|---|---|
| model id | `Qwen/Qwen3-4B` | `Qwen/Qwen3-1.7B` |
| `IsAccessible` / `IsOnline` / `IsPublished` | 1 / 1 / 1 | 1 / 1 / 1 |
| 许可 | `apache-2.0` | `apache-2.0` |
| `Architectures` | `Qwen3ForCausalLM` | `Qwen3ForCausalLM` |
| 层数 / GQA | 36 层；32 Q / 8 KV heads；head_dim 128 | 28 层；16 Q / 8 KV heads；head_dim 128 |
| 权重 dtype | BF16 | BF16 |
| `Revision` | `"master"`（**漂移别名**） | `"master"`（**漂移别名**） |
| `ModelRevisions` | `null`（该 API 不返回可钉的 commit） | `null` |
| 分片索引 sha256 | `6dc0981b8829fead746441f68f38f24c5ca4a3a66351f652c26c6df0efc43ab2` | `0d660e94b165eb912669a5249dff44b83188c4777a07ddb9611fb78d91b0578d` |
| 分片 sha256 | `328a91d3…`, `6cd087b3…`, `e4bf4369…` | `169ad53e…`, `912becff…` |
| 分片字节和（BF16 权重） | 8,044,982,000 B ≈ 7.49 GiB | 4,063,515,592 B ≈ 3.78 GiB |

结论：**可用性成立**；但 API 明确只到 `master` 别名，与 prereg §2 `fixed_before_run`「不得用漂移的 master 别名而不记实际文件 hash」和 `docs/reproducibility.md` §7.5（历史环境只记 `snapshots/master`，无法字节级保证）完全吻合。G1 必须通过 `modelscope_hub.snapshot_download(...)` 的返回值或等效途径取得**实际 commit/revision**，并对每个权重文件与 tokenizer 文件做 SHA-256 + 下载日期登记，写入 G1 放行文件。本机当前 `/root/.cache/modelscope/models/` **不存在**，两个模型都需新下载；下载命令见 §4.4（本审计未执行）。

### 1.2 精确 model-pair 配置（冻结值，不得临场调整）

- Teacher = `Qwen/Qwen3-4B`（36 层）→ Student = `Qwen/Qwen3-1.7B`（28 层）；**proportional layer map**，非 identity。
- 入口（prereg §5「可从 `experiments/P1_gpu.py` 的 `--model-pair qwen3-4b-to-1.7b` 开始」）：

```bash
.venv/bin/python -m experiments.P1_gpu \
  --run-id v3_E5_affine_s0 \
  --teacher <4B pinned snapshot dir> --student <1.7B pinned snapshot dir> \
  --model-pair qwen3-4b-to-1.7b --mapper affine \
  --seed 0 --dtype bfloat16 --kernel sdpa --device cuda \
  --n-resamples 10000
# 不传 --n-train / --n-val：默认 None => 冻结 sizes(train120, val60)，见 experiments/P1_gpu.py:41-43,61-65
# 不传 --eval-splits：P1_gpu.py 固定 eval_splits=("val",)（:108）；test 仅 E2 解锁后由 dedicated evaluator 使用
```

- `--model-pair` **只是标签**：真正决定模型对的是 `--teacher/--student` 路径（`experiments/P1_gpu.py:66-71`）。层映射由 `sm.config.num_hidden_layers` / `tm.config.num_hidden_layers` 自动推导（`:68-69`），即 `LayerMap(28, 36, kind="proportional")`。
- 数据：`cf_pairs_v2.1` 协议，train 120 / eval 60，三 seed（0/1/2），仅 validation。`build_cf_pairs(..., model_pair=...)` 中 `model_pair` 仅写入 `CFPair.model_pair` 元数据（`src/readkv/data/build_cf_pairs.py:361,474`），**不改变文本/split/label**——prereg §5 `prerequisite` 成立。注意 `run_cf_pipeline` 重建 eval pairs 时未传 model_pair（`src/readkv/evaluate/cf_pipeline.py:161`），eval 行该字段为空串；属元数据不一致，G1 须绑定数据 SHA 而非依赖该字段。
- 格数：affine 必选 → 3 格；kd_only 仅在 PI 批准**且** E6 复现门通过后追加 → 6 格（`configs/prereg/gpu_followup_v3.0.yaml:170-173`）。不得与 MVP 结果合并 seed 或 pooled CI（`:176-183`）。
- 硬边界：**P4 仍 NO-GO**（prereg §5 `status`、plan §5 line 124、G0 ruling §1）。E5 仅新增一个独立案例，写「在一个额外模型对复现/未复现该模式」，不写跨模型泛化，不删失败结果、不另选模型对。

### 1.3 36→28 proportional layer map 在当前代码中的实际行为

`src/readkv/models/layer_map.py:37-38`：`source_for(s) = min(nt-1, round(s*nt/ns))`。精确 28 项映射（`ns=28, nt=36`）：

```
student s :  0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27
teacher t :  0  1  3  4  5  6  8  9 10 12 13 14 15 17 18 19 21 22 23 24 26 27 28 30 31 32 33 35
```

- 被跳过的教师层：`{2, 7, 11, 16, 20, 25, 29, 34}`（8 层，正好 36−28）。
- `round` 无 `.5` 边界（9s/7 不可能为半整数），不存在 banker's rounding 歧义；`min(35, …)` 从未触发截断。
- 序列化：`hooks._serialize_layer_map`（`src/readkv/models/hooks.py:177-185`）把 `LayerMap` 落成显式 int 键字典 `{0:0, 1:1, …, 27:35}`，写入每个 teacher cache 的 `metadata["layer_map"]`（`:301`）。

### 1.4 【阻塞】注入端二次施加层映射 + 取模 → Joint/控制臂缓存错层

证据链（逐行）：

1. `experiments/P1_gpu.py:85-101` 的 `LayerMappedMapper.transform` 先用 `layer_map(s)` 从教师缓存取层，重建成**以学生层号 0..27 为键**的 `KVCache`（`:92-99`），metadata 原样保留（含 `layer_map` 的 0..35 映射）。
2. `src/readkv/mapper/representation.py:42-69` 的 `AffineMapper.transform` 输出的 K/V 仍以同一组键 0..27 索引，metadata 继续透传。
3. `src/readkv/evaluate/cf_pipeline.py:102-112,137-145` 把该映射缓存直接作为 `joint` 臂传给 `backend.candidate_logits`。
4. `src/readkv/models/gpu_backend.py:137-154` 的 `candidate_logits` 调用 `inject_and_generate(self.student, cache, q_t, ...)`——**未显式传 `layer_map`**。
5. `src/readkv/models/hooks.py:384-389` 于是从 `cache.metadata["layer_map"]` 取回 `{0:0,…,27:35}`；`:401-406` 对每个学生层调用 `_layer_map_entry(layer_map, s_layer, n_teacher)`，其中 `n_teacher = cache.n_layers = 28`（映射后缓存只有 28 层）。
6. `src/readkv/models/hooks.py:163-174` 的 Mapping 分支返回 `int(v) % n_teacher`。

于是注入时读取的层号是 `mp[s] % 28`，而正确应为 `s`。实际结果：

```
s:  0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27
读: 0  1  3  4  5  6  8  9 10 12 13 14 15 17 18 19 21 22 23 24 26 27  0  2  3  4  5  7
```

- **s=2..21**：读到偏大的学生层（如 s=2 读层 3）；**s=22..27**：`28..35 % 28` 回绕到 `0,2,3,4,5,7`。仅 s=0、1 正确。
- 因为所有结果都落在 0..27 内，**不会触发 KeyError，也不会触发 zero-re-prefill 断言**（输入长度/文档 token 数检查都通过）——这是 silent corruption，比崩溃更危险。
- 影响范围：E5 的 `joint`、`k_only`、`v_only`、`control:*` 臂全部错层；`self`/`identity` 臂不受影响（student 缓存 metadata 的 layer_map 为 `None`，走 `hooks.py:165-166` 的恒等分支）。
- 为什么 MVP 没暴露：等深 28→28 identity 时 `mp[s]=s`，`% 28` 是 no-op。**这是非等深路径特有缺陷**。
- 同样影响 `src/readkv/models/gpu_backend.py:440-445` 的 `score_candidate_sequence`（若未来用于非等深）；该入口在 `experiments/sequence_scoring_gpu.py:427` 强制等深，故 v2.8 未暴露。
- 不受影响：`gpu_backend.torch_candidate_logits`（`:109-115`）直接用 `mapped` 的键构造 cache，不读 metadata layer_map；因此 kd_only 训练（`src/readkv/train/kd_gpu.py:133-138`）的映射链路本身不走这个 bug，但其训练后的**评测**仍走 `candidate_logits`，同样受影响。

**最小修复路径（本审计不实施；须 PI 授权工程师修改并补测试）**：映射后的缓存已处于学生层空间，注入时应使用恒等映射（或在调用 `inject_and_generate` / `score_candidate_sequence` 时显式传 `{s:s}`），而不是复用教师捕获时记录的 teacher→student 映射；并删去/限定 `_layer_map_entry` 中无条件的 `% n_teacher`。必须新增非等深单测：断言 `mp` 的每一层注入都取到对应层；用 4B→1.7B 的 seed-0 小样本做 G2 pilot，先过层映射与 cache 形状审计再谈正式格。

### 1.5 4B + 1.7B 同卡显存估算（解析估算，非实测；G2 必须实测）

`experiments/P1_gpu.py:66-67` 用 `AutoModelForCausalLM.from_pretrained(...).to(device)` 同时把两个模型放到同一卡；`src/readkv/evaluate/pipeline.py:64-69` 的 `stack_caches` 逐文档 prefill 后在 **CPU numpy** 拼接；`hooks.capture_teacher_cache:283-289` 把 K/V 搬到 CPU fp32。因此 GPU 上常驻主要是权重，activation 是单文档量级。

| 分量 | 估算 | 依据 |
|---|---|---|
| Qwen3-4B BF16 权重 | ≈ 7.49 GiB | modelscope API 分片字节和 8,044,982,000 B |
| Qwen3-1.7B BF16 权重 | ≈ 3.78 GiB | 分片字节和 4,063,515,592 B |
| CUDA context / cuBLAS / SDPA workspace | ≈ 0.5–1.5 GiB | 经验值，须实测 |
| 单文档 prefill activation（batch=1，seq 数百） | < 0.5 GiB | inference_mode，逐文档调用 |
| GPU 上瞬时 DynamicCache（4B：36×8×128×T×2×2 B ≈ 0.14 MiB/token） | ~40–60 MiB（T≈300） | `hooks.py:263-272` |
| affine ridge 闭式解 | 0（CPU numpy） | `mapper/base.py` + `representation.py:24-40` |
| kd_only 额外（Adam 状态 ~88 MB + 梯度回传 activation） | 约 +1–4 GiB | `src/readkv/train/kd_gpu.py:97,133-152`（`grad_ok=True` 保留 activation） |

- **峰值估算：affine ≈ 12–14 GiB；kd_only ≈ 14–18 GiB。** RTX 5090 实测总显存 32,607 MiB ≈ 31.85 GiB，当前 0 MiB 占用（`nvidia-smi`，见 §4.1），理论有余量。
- 这是**上界式解析估算，不是承诺**。prereg §5 `tech_gate` 明确要求「4B+1.7B 同卡显存先实测；不得因 OOM 改精度或 kernel 后与主结果直接合并」。G2 pilot 用 `torch.cuda.max_memory_allocated()` 记录每格峰值、时间、forward 数与 cache 大小（plan §2.2.3）。
- 另注意 `.to(device)` 先把权重载入主机再搬卡，主机 RAM 需 ≥ 约 12 GiB 余量；这点未在本审计测量。

### 1.6 E5 所需代码变更汇总

| 优先级 | 变更 | 归属 |
|---|---|---|
| **BLOCKER** | 修复映射后缓存被二次层映射 + `% n_teacher` 错层（§1.4），补非等深单测 | 工程师，PI 授权后 |
| G1 | 把 `Qwen/Qwen3-4B` / `Qwen/Qwen3-1.7B` 的 commit/revision、每个权重与 tokenizer 的 SHA-256、下载日期落盘（当前只有 `master`） | 数据/工程师 |
| G1 | 校验 `build_cf_pairs` 在 `model_pair=qwen3-4b-to-1.7b` 下文本/split/label 与 MVP 一致（结构上成立，仍需哈希确认）；绑定独立 manifest | 数据工程师 |
| G1 | 决定 E5 是否含 kd_only（affine 3 格 or 含 kd 6 格），必须在 G2 前冻结；含 kd 须同时满足 E6 门 | PI |
| G2 | seed-0 小样本：模型加载、tokenizer、层映射逐层核对、cache 形状、Self/Identity、zero-re-prefill、峰值显存 | 工程师 |
| 不需改 | `LayerMap` 本身的 proportional 公式（§1.3 正确）；`AffineMapper.fit/transform` 的学生层键（§1.4 中游正确） | — |

---

## 2. E6 复现门与预算匹配内部对照

### 2.1 复现门评估（prereg §6.1 `gate.criteria`）

联网核验到摘要级事实（**仅摘要，不是全文**）：

- **KV-Lingo**（arXiv:2609.32610, "Learning KV-Cache Translators with Distillation", 2026-09-26）：摘要称「a collection of linear maps, typically one per layer of the target model, applied independently on all tokens' key and value representations」，训练目标为「distillation, minimising the divergence between the target model's predictions from its native cache and those from the translated cache」，训练数据是「a generic text corpus」，推理「a switch then costs a linear map and a single decoding step instead of a prefill」。
- **CacheLink**（arXiv:2610.15509, "Functional KV Transport for Zero-Prefill Cross-Model Context Handoff", 2026-10-11）：摘要称「learns a coupled K/V correction through the receiver behavior directly」，「four independently trained sender–receiver pairs and seven evaluation panels」。

评估：两篇的 mapper 结构只在摘要层级可辨（KV-Lingo：每层 per-token 线性 K/V 映射；CacheLink：「coupled K/V correction」，具体架构未给），**代码仓库/权重发布/许可/完整训练超参/训练语料/逐层映射细节均未核验**；本仓库 `docs/reproducibility.md` §7.8 也明说外部文献「只到标题/作者/摘要/日期级核验，章节级细节须投递前按 docs/protocol.md §9 全文核验」。此外 KV-Lingo 的「generic text corpus」与本项目合成 CF 语料不同，无法用现有数据直接对齐。

**判定：复现门未通过（NOT PASSED），不得称任一外部方法为 faithful baseline**（prereg §6 `if_fail`、G0 ruling §1 E6、plan §6.1）。本审计不把摘要里的结构描述当作可复现规格。若后续有人取得代码/权重，必须在 G1 里逐项核验：全文方法、代码/权重可用性与许可、mapper 结构、训练数据、训练目标、输入信息、推理是否严格 zero-re-prefill（可用 `verify_zero_re_prefill`，`hooks.py:467-518`），并在看到结果前冻结判定。

### 2.2 推荐的内部对照（明确命名，预声明架构/参数）

按 prereg §6.1 `fallback`，采用**预算匹配内部对照**，不称已发表方法基线。建议命名并在 G1 放行文件中冻结：

**`v3-BM-MLP-KD`（budget-matched per-layer K/V linear mapper, KD objective）**

预声明（在看到任何结果之前冻结；本审计不写入 prereg）：

- 架构：逐学生层、逐 KV head 的线性映射 `W ∈ R^{d×d}`（不加 bias，与现有 affine 的 closed-form ridge 区分开），K 与 V 各一套；层覆盖 28 层 × 8 KV heads × head_dim 128。
- 参数量：`128×128 × 2(K,V) × 8 heads × 28 layers = 7,340,032`，与现有 kd_only 的 `trainable_params=7,340,032`（`docs/reproducibility.md` §4.3 config）**刻意相等**，满足「参数匹配容差」的事先定义。
- 训练：与 kd_only 相同的 120 训练对、8 epochs、lr=1e-3、Adam、seed 0/1/2；目标为 KL(native Self logits ‖ mapped logits)，即 `src/readkv/train/kd_gpu.py:140-147` 的 `L_KD`（`lam_kd=1.0, lam_reg=1e-4, lam_cf=0`）；∇ 只回传映射缓存，学生权重冻结（`:93-96`）。
- 同模型对、同 train/val、同 3 seed、同 `zero_re_prefill=true`。
- **注意 prereg v3.0 §6.1 `internal_control.extra_mapper` 只写了「在 prereg 中明确架构/参数数量」这一要求，并未真正冻结任何具体架构/参数**。这是 G1 release 的缺口：PI 必须决定 (a) 只以现有 affine + kd_only 作为预算匹配内部基线并在放行文件写明，或 (b) 授权**新版本**判据/附录冻结上述 `v3-BM-MLP-KD` 规格。**不得直接改已冻结的 `gpu_followup_v3.0.yaml`**。

### 2.3 必须分项披露的清单（prereg §6）

每个 baseline（含复用的 affine/kd_only 与新增内部对照）逐项报告，缺一即为不合格：

1. **参数量**（trainable params，按层/通道分解），以及参数匹配容差定义；
2. **GPU 时间**（训练秒数 + 总墙钟；`P1_kd_gpu.py:85-92` 已记 `train_sec`，但需逐格落盘）；
3. **前向/反向次数**（每 epoch、每 seed 的 student forward 数与 backward 数；`src/readkv/train/kd_gpu.py:127-154` 可插桩计数）；
4. **显存**（峰值 `torch.cuda.max_memory_allocated()` + 已分配/保留区分）；
5. **训练目标**（闭式 ridge λ=1e-3 / L_KD 的 lam 组合 / 新对照的 KL 公式，写明文）；
6. 事前定义的：模型质量、训练预算、主指标、失败/中断处理、比较族；**即使排名不变也完整报告训练成本差异**（§6 `success_criteria`）。
7. 复用 affine/kd_only 权威结果时，须核验 data hash / checkpoint / code 绑定（§6.2 `reuse`）；否则三 seed 新跑。
8. 若纳入 E5 的 4B→1.7B，**分开报告**，不与 MVP affine 数值直接比较（§6.2 `e5_interaction`）。

---

## 3. 审计入口可行性（E1 前置）

### 3.1 现有入口确认：仅 legacy/fixed，不能跑 E1 变体

`experiments/audit_2x2_gpu.py`：

- `RIDGE_LAM=0.001` 与 `CELLS={A00:(legacy,legacy), A01:(legacy,fixed), A10:(fixed,legacy), A11:(fixed,fixed)}`（`:45-49`）；
- 必需参数为四路径 `--train-old / --val-old / --train-fixed / --val-fixed`（`:55-58`）；`--cell` choices 固定四格（`:59`）；`--cal-version/--val-version` 仅 `["legacy","fixed"]`（`:61-62`）；
- `path_key()` 把版本名硬编码为 `old/fixed` 后缀（`:155-161`）；
- 模型部分强制等深：`if n_s != n_t: raise ValueError("audit entry requires equal depth...")`，随后 `LayerMap(..., "identity")`（`:179-182`）；
- 产物 `criteria_source` 写死 v2.7（`:272`）。

因此**无法表达** prereg §3 的 `dedup_only / degenerate_only / entity_disjoint_only / template_disjoint_only / fully_repaired` 六种变体，也无法表达 Panel A / Panel B 的「校准变体 vs 验证变体」独立组合；与 plan §3.4 / prereg §3 `prerequisite` 的判断一致。旁证：`experiments/sequence_scoring_gpu.py` 也只有 `VERSIONS={legacy:A00, fixed:A11}`（`:55-61`）并在 `derive_paths` 拒绝 test、强制 `{dir}` 与 `seed` 匹配（`:113-130`），同样不能承载 E1。

### 3.2 新入口的精确 CLI / 签名要求（只给规格，本审计不实现）

建议新文件 `experiments/e1_variant_gpu.py`（或等价独立入口），函数签名 `main(argv: Sequence[str] | None = None) -> int`，argparse 至少包含：

```
--run-id                 必填；v3_E1_<variant>_s<seed>[_smoke]
--variant                必填；choices = 6 个注册名（legacy_bundle, dedup_only,
                         degenerate_only, entity_disjoint_only, template_disjoint_only, fully_repaired）
--panel                  必填；choices = [A, B]
--train-path             必填；显式校准 train JSONL（Panel A 用变体 train；Panel B 用固定 clean v2.1 train）
--train-sha256           必填；该 train 文件的冻结期望 SHA-256
--val-path               必填；显式评测 val JSONL（Panel A 用固定 clean v2.1 val；Panel B 用变体 val）
--val-sha256             必填；该 val 文件的冻结期望 SHA-256
--manifest-path / --manifest-sha256   必填；变体清单及期望哈希
--seed                   必填；choices=[0,1,2]
--model-pair             qwen3-1.7b-to-0.6b（标签）
--teacher / --student     pin 到具体 snapshot（禁止 master 裸别名）
--mapper                 affine；--ridge-lambda 1e-3（冻结）
--dtype bfloat16 --kernel sdpa --device cuda --n-resamples 10000
--smoke / --smoke-n-val 6 ; --out-dir（仅 smoke 允许指向 reports/_non_authoritative/）
```

建议核心函数：`load_pairs(path, expected_sha256) -> list[dict]`（读 JSONL、不过质量门、不调用 `build_cf_pairs`）、`fit_mapper_once(backend, train, lmap)`、`arm_caches(...)`、`v2_context(...)` 记录 `input_sha256` / `variant` / `panel` / `sealed_test_read=false` / `criteria_source="configs/prereg/gpu_followup_v3.0.yaml"`。

**哈希绑定与隔离要求（必须全部满足）**：

1. 运行时重算 `--train-path/--val-path/--manifest-path` 的 SHA-256 并与传入/冻结期望逐一比对，**不符即 abort**，写入失败 config；参照 `audit_2x2_gpu.py:74-75,153` 与 `sequence_scoring_gpu.py:100-101,414` 的现有做法但强制校验而非只记录。
2. 路径白名单：拒绝任何路径含 `test` 分量或文件名（照搬 `sequence_scoring_gpu.py:120-129` 的拒绝逻辑）；E1 不得读 test。
3. **绝不调用** `build_cf_pairs` / `run_cf_pipeline` 的自动重建与质量门路径（prereg §3 `data_entry`）；Panel B 的 mapper 训练样本与评测样本必须来自两个独立显式路径。
4. 逐变体登记改动样本/text/hash、样本数、替换/剔除规则、各 slice/family 数（prereg §3 `variant_registration`）；组成变化必须标为版本差异，不称纯单缺陷效应。
5. `degenerate_only` 的重计分先做 CPU replay，只有候选文本/输入上下文变化才追加 GPU 前向并单列「数据任务改变」（prereg §3 `degenerate_note`）。
6. 产物：smoke → `reports/_non_authoritative/`，正式 → 新 `reports/runs/v3_E1_.../`；不覆盖历史；`config.json`/`scores.jsonl`/`metrics.json`/`manifest.json` 齐全。
7. 等深 28→28 identity 与 bf16/sdpa/zero-re-prefill 固定；模板族重采样 + pair 敏感性并列，族数 <24 标 exploratory。

---

## 4. 环境（本次只读探测，未安装任何东西）

### 4.1 现场 tooling（实测输出）

```
which python3   -> /usr/bin/python3 ; python3 --version -> Python 3.12.3
which uv        -> /usr/bin/uv      ; uv --version      -> uv 0.9.17
which nvidia-smi-> /usr/bin/nvidia-smi
nvidia-smi      -> Driver Version 580.82.07, CUDA Version 13.0,
                   NVIDIA GeForce RTX 5090, 32607 MiB 总显存, 0 MiB 占用, 无运行进程
/root/readkv/.venv  -> Python 3.12.3, 无 torch（ModuleNotFoundError: No module named 'torch'），仅有 activate/python 基线
/root/.cache/modelscope/models/ -> 不存在（两模型均未缓存）
```

`scripts/reproduce.py` **不存在**（`scripts/` 无该文件）；仓库内唯一 `reproduce.py` 在 `papers/readkv_v2_tmlr_anonymous/reproduce.py`，是稿件侧一次性重算脚本，不是通用环境安装器——不要把它当作 v3 入口。

### 4.2 与归档环境的差异（G1 必须先冻结取舍）

| 项 | 归档记录（`reports/environment.json`、`docs/reproducibility.md` §1） | 当前机器 |
|---|---|---|
| Python | 3.13.11（uv 管理路径） | 系统 3.12.3；.venv 3.12.3 且空 |
| torch | 2.15.0+cu132 | 未安装 |
| transformers | 5.24.0 | 未安装 |
| CUDA toolkit | 13.2 | driver 上限 13.0（无 toolkit 安装确认） |
| GPU | RTX 4090 24GB | RTX 5090 32GB（sm_120/Blackwell） |
| 驱动版本 | 未记录 | 580.82.07（**新记录项**） |
| uv 版本 | 未记录 | 0.9.17（**新记录项**） |

**兼容性风险（G2 前必须验证）**：记录的 torch 是 `+cu132`，当前驱动只报 CUDA 13.0；同一 major 内 minor-version 兼容通常可用，但需在 pilot 里用 `torch.cuda.is_available()`、实际前向、SM 支持验证。若必须改用其他 CUDA 构建，属于环境变更，须先由 PI 在 G1 放行文件中冻结版本，再安装——不得临场换构建后仍与归档数字直接合并。

### 4.3 精确 uv 安装命令（**仅给出，未执行**）

```bash
# (0) 只读核验（已在本审计执行，见 §4.1）
which uv && uv --version && python3 --version && nvidia-smi

# (1) 用 uv 建立与归档一致的隔离 Python（固定 3.13.11）
uv python install 3.13.11
uv venv --python 3.13.11 .venv-v3

# (2) CUDA-enabled torch：按归档记录固定 +cu132 构建，走 PyTorch 官方索引
uv pip install --python .venv-v3/bin/python \
  --index-url https://download.pytorch.org/whl/cu132 \
  "torch==2.15.0+cu132"

# (3) 固定 transformers 与关键伴随包（版本取自 environment.json / reproducibility.md §1）
uv pip install --python .venv-v3/bin/python \
  "transformers==5.24.0" "numpy==2.5.5" "scipy==1.18.1" \
  "safetensors==0.8.0" "tokenizers==0.23.3" "pyyaml==6.0.4" \
  "tqdm==4.70.1" "huggingface-hub==2.4.0" \
  "modelscope==1.40.3" "modelscope-hub==0.7.1" "pytest==9.2.0"

# (4) 以 --no-deps 安装项目，避免上述固定版本被 pyproject.toml 的下界（torch>=2.1 / transformers>=4.44）改写
uv pip install --python .venv-v3/bin/python --no-deps -e ".[dev]"

# (5) 技术门（只读自检，不是科学证据）
.venv-v3/bin/python -m experiments.sequence_scoring_gpu --cpu-selfcheck
.venv-v3/bin/python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
```

### 4.4 记录 wheel 哈希与模型来源（**仅给出命令，未执行**）

```bash
# A) 生成带 sha256 的锁定 requirements（写到新的非冻结路径；实际落点须 PI 批准）
uv pip compile pyproject.toml \
  --python-version 3.13 --generate-hashes \
  --index-url https://download.pytorch.org/whl/cu132 \
  --extra-index-url https://pypi.org/simple \
  -o reports/_non_authoritative/v3_env/requirements.lock
# 该文件每行含 --hash=sha256:...，即 wheel 级来源证据

# B) 已安装包清单 + uv 缓存中的实际 wheel 字节哈希
uv pip freeze --python .venv-v3/bin/python > reports/_non_authoritative/v3_env/uv_freeze.txt
find "$(uv cache dir)" -type f -name '*.whl' -print0 \
  | xargs -0 sha256sum > reports/_non_authoritative/v3_env/wheel_sha256.txt
# 重点核对：torch-2.15.0+cu132-*.whl 与 transformers-5.24.0-*.whl 的索引来源 URL

# C) 模型：禁止用漂移 master 别名；先取得实际 commit 再下载与登记
.venv-v3/bin/python - <<'PY'
from modelscope_hub import snapshot_download
for mid in ("Qwen/Qwen3-4B", "Qwen/Qwen3-1.7B"):
    p = snapshot_download(mid)          # 返回值含实际 resolved revision
    print(mid, p)
PY
# 然后按上一步得到的 commit 固定 revision 下载（示意，revision 值不得编造）
.venv-v3/bin/modelscope download --model Qwen/Qwen3-4B   --revision <resolved-commit>
.venv-v3/bin/modelscope download --model Qwen/Qwen3-1.7B --revision <resolved-commit>
# 文件级 sha256 + 下载日期登记（G1 放行文件）
find /root/.cache/modelscope/models/Qwen--Qwen3-4B/snapshots/<resolved-commit> \
     /root/.cache/modelscope/models/Qwen--Qwen3-1.7B/snapshots/<resolved-commit> \
     -type f \( -name '*.safetensors' -o -name '*.json' -o -name '*.txt' \) -print0 \
  | xargs -0 sha256sum > reports/_non_authoritative/v3_env/model_file_sha256.txt
date -u +%Y-%m-%dT%H:%M:%SZ  # 与上述哈希一并登记
```

上述哈希与版本（含 driver 580.82.07、uv 0.9.17、modelscope commit、每个权重/tokenizer 文件 SHA-256、下载日期）须在 **G1 放行文件**落盘；prereg §2 `environment_setup` 与 plan §9 清单均要求可达此项。具体输出目录由 PI 指定，不得写入 `configs/prereg/**`、`reports/runs/**` 等冻结路径。

---

## 5. 两个历史敞开项与 v3 的关系（明确分离，不得混为一谈）

依据 `reports/review/audit_of_third_party_review_sequence_b0_2026-11-24.md` §3 表末两行与 §5「两条仍然敞开的实质问题」（原文 line 71、88）：

1. **postprocess Self E_CF 双写**：`experiments/sequence_scoring_gpu.py::postprocess`（`:286-304`，核心是 `:301-304` 的 `for row in (base, cur): row["E_CF"][r] = ecf`）。这是 **protocol-v2.8 序列评分产物**的字段语义问题；稿件侧由 `papers/.../reproduce.py` 的 `self_ecf = 0.0` 兜住，已发表数字不受影响。
2. **两条失败测试**：`tests/test_hooks.py::test_capture_inject_identity_matches_full_prefill`（`tests/test_hooks.py:33`）与 `tests/test_sequence_scoring.py::test_score_candidate_sequence_cpu_tiny`（`tests/test_sequence_scoring.py:119`），报错同为 `layer 0 has no K/V after prefill`；第三轮复审实测 74 收集 / 72 通过 / 2 失败。

**分离声明**：以上两项属于**此前 v2.8 / 稿件收尾审计**的敞开问题，**不是** E1/E2/E5/E6 的工作包，也不是 v3.0 prereg 的判据。本次 G1 审计**不修复、不改写、不把它们计入 v3 结论**，不得在 v3 运行产物中夹带这两项的「修正版」数字，也不得用它们解释 v3 的任何结果。

**技术前置提醒（与「分离」并不矛盾）**：第 2 项是**当前环境 hook 前向接口的回归**（DynamicCache 首层取不到 K/V）。E5 的 G2 pilot 必须通过 `capture_teacher_cache`（`hooks.py:221-309`）才能取缓存；若该回归在本机复现，G2 会直接失败。因此它应作为**独立的环境/实现修复工单**（另立证据、另行验收），在 v3 G2 之前完成；**不得**用 mock 或跳过 identity 检查来掩盖它，也不得把它塞进 v3 prereg 里当作 v3 的一个变体。第 1 项则与 v3 的 GPU 评测链路无关，可完全并行搁置。

---

## 6. G1 放行建议（给 PI）

**建议：G1 暂不放行；完成以下四项后再开 G2 pilot。**

| # | 阻塞项 | 责任方 | 放行证据 |
|---|---|---|---|
| 1 | 修复非等深注入错层 bug（§1.4）并补非等深单测 | 工程师（PI 授权） | 单测：逐学生层核对注入索引；seed-0 4B→1.7B pilot 的层映射/cache 形状审计 PASS |
| 2 | 两个模型钉 revision + 文件 SHA-256 + 下载日期落盘 | 数据/工程师 | G1 放行文件中的 model manifest |
| 3 | E6 复现门结论落盘；决定并冻结内部对照规格（或仅 affine+kd_only） | PI + 工程师 | 放行文件写明「不可复现 → 使用 v3-BM-MLP-KD / 现有基线」，规格与参数量事先冻结 |
| 4 | 新 E1 显式文件输入入口 + 哈希绑定实现与 CPU 自检 | 工程师 | CLI/拒绝 test/哈希不符 abort 的测试证据；未调用 `build_cf_pairs` |
| 附 | layer-0 K/V 失败测试单独修复（§5） | 工程师（独立工单） | `pytest` 全绿或明确的环境兼容说明，不以 mock 代替 |

**不可越界重申**：本次审计只写了本报告；未改 `src/**`、未改 `configs/**`、未改 `reports/runs/**`、未改论文、未运行任何 GPU 实验、未安装依赖。P4 仍 NO-GO；v2.1–v2.9 冻结判据与已签 off 结论保持原状。

# GPU 机器接续指南（V2.0 · 反事实功能保真）

本文档说明如何把 CPU mock 验证过的管线切换到 24GB GPU 机器。原则是**逐项替换、逐项回归**：每替换一个 mock 组件，就用同一阶段脚本与同一判据重跑，确认产物格式不变。判据细节见 `docs/protocol.md`，目标结构见 `docs/architecture.md`。V2.0 是待验证的研究计划，以下数字（除硬件 / 缓存体积的理论估算外）均为目标值，不是实验结论。

> **实现状态（已更新，2026-11-23）**：V2 全部功能已在 mock 后端落地；`models/hooks.py` 的真实 GPU 前向**已实现并通过 P0/E0 实现门**（`--backend gpu` 可用），单元测试 **53 passed**。本文下方为历史接续说明（目标值与理论估算，非当前结论）。当前权威 GPU run 的从零复现命令、环境版本与数据哈希见 **`docs/reproducibility.md`**。项目已 PIVOT 为失败边界 / 数据泄漏教训的负面实证研究（见 `docs/decisions/final_boundary_study_signoff.md`）；P2/P3/P4 取消、封存 test 未评测，不得据本文历史目标值启动已取消阶段。封存测试运行前须完成 `configs/prereg/` 预注册。

## 0. 环境

- 目标：单卡 4090 / 24GB；Qwen3 0.6B / 1.7B / 4B / 8B。
- 8B 只做离线 teacher 推理（bf16 约 16GB），离线生成缓存后卸载，不与训练同时驻留。
- 先 `python -m pip install -e ".[dev]"`，再 `python -m pytest` 确认 CPU 侧逻辑完好。
- 统一协议：Qwen3 的 QK-Norm 与模型专用聊天模板按真实结构实现；`/no_think` 或等价确定性答题模式固定为同一口径；文档切分、Query 拼接、位置偏置、RoPE、GQA 处理在对照之间完全一致。

## 1. 模型分层与缓存预算

| 层次 | 建议配置 | 目的与边界 |
|---|---|---|
| MVP（必须） | 教师 Qwen3-1.7B → 学生 Qwen3-0.6B；256—512 tokens | 等深、开销最低，先确定机制和训练目标 |
| 主验证（必须） | 教师 Qwen3-4B → 学生 Qwen3-1.7B；256—512 tokens | 非等深，直接与第一篇的主要模型对衔接 |
| 可选压力测试 | 教师 Qwen3-8B → 学生 Qwen3-0.6B，离线生成缓存后卸载教师 | 验证大尺度缺口；不与学生训练同时驻留 |
| 后续扩展 | 不同家族或 1K—4K 文本 | 仅当主线已确认成立再开展，需额外算力 / 存储 |

理论原始缓存体积（fp16/bf16 两通道 K/V，未计 Python 对象、padding、框架预分配、训练激活和 I/O 缓冲）：

- Qwen3-0.6B/1.7B：28 层、8 个 KV heads、head_dim=128 → ≈**112 KiB/token**。
- Qwen3-4B/8B：36 层、8 个 KV heads、head_dim=128 → ≈**144 KiB/token**。

示例：4B 教师对 360 对文档（720 份文档）、每份 512 token 离线缓存，总量约 **50.6 GiB**；保存相应学生 1.7B 原生缓存还需约 **39.4 GiB**。建议按 `pair_id` 按需加载、保留共享层映射所需中间特征、做 fp16 离线存储及配置指纹，避免全量驻留显存。

## 2. 必须先实现的接口（按优先级）

### 2.1 `src/readkv/models/hooks.py`

| 函数 | 契约 | 验收 |
|---|---|---|
| `capture_teacher_cache(model, tokens, layer_map, ...)` | 对一份文档 `d_A` 或 `d_B` Prefill 一次；按层取 K/V；keys 为 de-RoPE 内容空间；返回 `KVCache` | 同文档重复捕获 bit-identical；两份文档**分别**生成，绝不篡改缓存字节伪造 |
| `inject_and_generate(model, cache, query_tokens, ...)` | 用映射 cache 初始化 student；query 位置偏移显式传入；首 token 取自 prefill logits；不在已推进 query/gold 的 cache 上生成 | identity 注入与 full-prefill 的 Self EM 一致率 ≥0.929，首 token top-1 ≥0.929 |
| `verify_zero_re_prefill(...)` | instrument student forward，断言无上下文 token 进入；Oracle 干预路径不得进入 Joint 推理图 | 每个 run 的 `config.json` 中 `zero_re_prefill=true` |

注意 bf16 kernel path 残差：重复捕获、cache round-trip、显式 position offset 都应精确；残差只来自 one-token query vs full-sequence prefill 的 attention kernel 路径。E0 必须先测出测量误差上限，确认显著低于待研究效应。

### 2.2 `models/loader.py::resolve_layers`

适配 Qwen3 checkpoint 的 transformer block 列表；确认层容器属性名与 QK-Norm 位置；`loader.py` 已封装 `AutoModelForCausalLM.from_pretrained` 与冻结。

### 2.3 校准回调（替代 mock 的线性投影）

`evaluate/pipeline.py` 当前从 `MockBackend` 直接取：

- `query_states(layer, head, doc)`：学生真实 query（GQA 下同 KV head 的多个 query head 堆叠）；
- `attention_matrices(cache, doc)`：学生注意力分布，作为 consumer-space mapper 的 `A`；
- `answer_logits(cache, doc, arm)`：冻结学生读 cache 后的候选 A/B logits（用于 `g(C,q)`）。

GPU 后端应把这些换成真实前向，并保持返回形状不变：
`query_states` → `(T_q, d)`；`attention_matrices` → `{(layer, head): (T, T)}`；`answer_logits` → `(2,)`（单 token A/B 候选统一在同一生成位置提取）。多 token 自由回答须单独报告 corrected EM 与预定义序列概率评分，不能与 `g` 混合。

### 2.4 待补的 mapper / 诊断目标

| 位置 | 当前状态 | GPU 实现要求 |
|---|---|---|
| `mapper/consumer.py::WOAwareMapper.fit` | `NotImplementedError` | 按 GQA 组提供 `(A_S V_S W_O,q)` 目标，再调用 `consumer_solve` |
| `mapper/key_objectives.py::AttentionKLKeyMapper` | `NotImplementedError` | 可微学生 attention，KL / ranking 目标，SGD；对称 Key 前置实验的 E |
| `mapper/representation.py::TaskAwareMapper / RATMapper / TopKRidgeMapper` | `NotImplementedError` | 强行为基线族，需要下游 loss / 两模型投影与词表对齐 / top-k 源层选择 |
| `mapper/hidden_state.py::HiddenStateMapper.transform` | `NotImplementedError` | 映射 hidden state 后经学生 W_K/W_V 投影，先做小规模探针；效果不优于直接 KV 映射则停止 |
| `mapper/adapter.py::apply_adapter_to_model` | `NotImplementedError` | 把 rank-8 修正挂到 o_proj / v_proj / q_proj,k_proj；作为改变接收端的对照，参数开销单列 |
| 新增 `models/cf_rct.py` / `train/cf_rct.py` | 待实现 | 冻结学生；成对 `L_CF = Huber(D_trans − D_self)`；`L_local` 固定局部 Query 的 routing / W_O 消费一致；seed、Forward 次数、参数量记账；`CF-RCT-lite` 与 `CF-RCT-mech` 两版本 |
| 新增 `diagnostics/route_value.py` | 待实现 | K/V 四臂；局部分解 `(Â−A_S)V_S W_O + Â(V̂−V_S)W_O`；层 / 头 / Token Oracle 移植；机制选择规则只用训练 / 验证集 |

## 3. 数据与目录准备

- 反事实对：`data/build_cf_pairs.py` 生成 `u=(q,d_A,d_B,a,b,m)`，六类切片 F1—F6（F5 为非翻转负控、F6 为长度 / 位置条件扰动），候选顺序随机交换，按实体 / 来源 / 模板簇隔离 split。规模建议：探针 32—48 对、训练 / 验证 120/60、封存 240—360（≥24 独立模板 / 主题簇 + 未见模板子集）、真实文档扩展 80—150。
- 标准 QA 保留旧 `data/qa.py` / `data/synthetic.py` 作普通任务报告，防止“反事实指标改善但常规任务退化”。
- 目标目录（见 architecture §4）：`configs/{protocol,models,eval}.yaml`、`data/build_cf_pairs.py`、`cache/offline_prefill.py`、`cache/identity_check.py`、`models/{ridge,consumer,cf_rct}.py`、`diagnostics/route_value.py`、`train/{kd,cf_rct}.py`、`eval/{quality,counterfactual,controls,stats}.py`、`reports/{runs,figures,ledgers}/`。当前旧模块按 architecture §10 映射逐步归并。

## 4. 离线缓存与实现门

```powershell
# 对 d_A、d_B 分别独立生成；先 dry-run 确认体积后去掉 --dry-run
python -m scripts.gen_teacher_cache --pair 4b_to_17b --n-pairs 360 --tokens-per-doc 512 --dry-run
# 需先实现 hooks.capture_teacher_cache
python -m scripts.gen_teacher_cache --pair 4b_to_17b --n-pairs 360 --tokens-per-doc 512
```

缓存落盘到 `data/cache/`（npz，按 `pair_id` 索引），teacher 随即卸载；后续 mapper 实验只加载 student。记录 shape / position_ids / 层映射 / RoPE 元数据 / 文件哈希。磁盘吞吐可能先于显存成为瓶颈，早期实测读写速度；只存需要的层可进一步压缩。

实现门（P0 / E0）：`cache/identity_check.py` 验证 Self / Identity / full-prefill 路径一致性与数值残差；E0 判据为“测量误差上限显著低于待研究效应”。`logit cosine ≥0.9998` 为 V1 继承的 identity 锚点一致性参考值，不作为 V2.0 主终点阈值。未通过 E0 不得进入 P1。

## 5. 训练与机制诊断

- 配对训练（`train/`）：加载冻结学生与 Mapper；每 batch 载入两份教师缓存 + 离线 Self 目标；两次 Query Forward；计算 `L_KD/L_CF/L_local/L_reg`；反向传播只更新 Mapper。对齐可训练参数、Forward 预算、训练步数、学习率调参次数，并单独报告超参搜索成本。τ、Huber 阈值、标签平衡在验证集固定。
- 机制诊断（`diagnostics/`）：对称 Key 四目标（per-head ridge / attention-mass 加权 / pre-softmax score 回归 / attention KL-ranking）；K/V 四臂（Self / K-only / V-only / Joint）；局部 Routing/Consumption 分解；层 / 头 / Token Oracle 移植。Oracle 依赖学生原生 Prefill，**只用于离线诊断 / 训练期**；推理期预算分配预测器只能依赖教师缓存、映射状态、学生当前 Query 等可观测量。

## 6. 阶段重跑顺序与判据（P0—P5）

1. `P0` 基座：校正评测器 + identity + 缓存持久化 + 双文档 Query 格式；先确认 E0 实现门通过。
2. `P1` 基准：反事实数据 + 真实小样本；复现 ridge / consumer / KD 等强基线。放行判据：确认是否存在未被强基线消除的反事实失真；否则按决策树转向边界研究。
3. `P2` 机制：K score 目标、K/V 四臂、层 / 头移植。放行判据：机制诊断在验证集有预测价值；产出机制报告与候选公式。
4. `P3` 方法：训练 KD-only、CF-lite、CF-mech；严格配平预算并做消融。放行判据：相对强基线有非偶然改进；否则停止扩大模型。
5. `P4` 泛化：非等深 pair、未见模板 / 真实文档，最终封存测试；报告跨设置稳定性、CI、失败边界与不利结果。
6. `P5` 成稿：运行耗时与显存核算、统一图表、投稿文本。

运行后重算与审计：

```powershell
python -m scripts.bootstrap_ci_report      # 从 scores.jsonl 重算 E_CF 终点与簇级 CI
python -m scripts.consistency_check        # 检查 git hash / 协议版本 / zero-reprefill / 哈希无交叉
python -m scripts.measure_reconstruction_r2 --cache-root data/cache ...   # 仅作 cache 层诊断
```

## 7. 注意事项

- 对比实验必须同 dtype、同 kernel；bf16 小效应噪声不可事后忽略。
- 梯度训练族（MLP / adapter / CF-RCT）按 ≥3 seed 报告范围，不把单次结果当点估计。
- 主终点为封存测试上新方法与最强行为基线的**成对 `E_CF` 差异**；多重比较用 Holm；`P>0.05` 不等于等效。
- 普通 QA 与反事实 QA 同报；Full-Prefill / Self / Identity 仅作锚点，不计可部署性能；只对 Joint 严格零重 Prefill 主报告。
- 封存测试运行前完成预注册：`docs/protocol.md §9` 的固定项 + `configs/prereg/` 的机器可读 `conditions`，之后不按测试结果调超参。
- mock 阶段产生的 `reports/*mock*` 目录不是科学结果，正式实验使用新的 run_id（置于 `reports/runs/`）。

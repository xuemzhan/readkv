# readkv 项目架构（V2.0 · 反事实功能保真）

> 状态：Accepted（设计目标稿，按 V2.0 研究方案修订）。需求来源：`docs/raw/跨模型KV迁移_第三篇论文研究方案_V2.0_详细版.pdf`（修订 2026-11-22）；基础论文：`docs/raw/Cache Translation Across Model Scale.pdf`、`docs/raw/Beyond Representation Fidelity.pdf`、`docs/raw/跨模型 KV 迁移：后续研究方向.pdf`。
> 本文描述代码结构、依赖方向、状态归属与失败模式；**具体门限与判据见 `docs/protocol.md`**。本文描述的是目标架构，已实现部分与迁移路径见 §10；GPU 接续见 `docs/gpu_handoff.md`。
> V2.0 是**待验证的研究计划**：论文题目、指标名（`E_CF`）、算法名（`CF-RCT`）均为工作版本，不将拟议结果写成已成立事实。

---

## 1. 需求定位

readkv 不是一个“训一个更强 mapper”的项目，而是一个**可复现的跨模型 KV 迁移实验平台**。V2.0 的主线是：

> 两篇现有论文的审计与机制结论 → 反事实功能响应评测 → Key/Value 局部机制定位 → 冻结接收端的定向恢复 → 严格零重 Prefill 下的泛化与成本审查。

核心问题不再是“表示误差是否等于任务质量”，而是：即使 Mapper 在常规 QA / teacher-forced likelihood / 平均预测分布上接近学生原生缓存，**是否保留文档事实发生受控变化时学生输出应出现的对应变化**。

三个研究问题及可证伪假设（H1—H4）见 `protocol.md §1`。三个贡献层次与门槛：

| 层次 | 交付 | 成立条件 |
|---|---|---|
| ①评价层 | 可复现的成对反事实任务 + 预先固定的审计 | 可重复、未被强基线消除的失真现象 |
| ②机制层 | Routing / Consumption 在 `E_CF` 上的可解释诊断 | 在独立数据上有预测价值，而非事后热图 |
| ③方法层 | 机制约束 `CF-RCT` 在配平预算下改善保真 | 同预算胜过 KD / CE / contrastive / 强行为基线 |

硬约束：单卡 4090 / 24GB；teacher 缓存一次性离线生成落盘后卸载；8B 只做离线推理；不做 4K/8K 长上下文、不做大规模非线性架构搜索；判据先写后跑；主方法不修改学生主干权重。

---

## 2. 现状事实

- `E:\Workspace\readkv` 原先只有 `docs/raw/` 下三个 PDF，无任何代码；当前仓库已有一版**按 V1 三道门 / `stage0..4` 搭建的骨架**，本架构为向 V2.0 演进的目标结构，按 §10 映射逐步迁移，不要求一次性重命名。
- 本机环境：Windows / PowerShell，Python 3.14，torch 2.14（CPU build）、transformers 5.17、numpy 2.5、scipy 1.18、PyYAML 6、pytest 9。目标运行环境为带 24GB GPU 的机器，代码须设备无关。
- 沿用论文 1 的命名分区：`experiments/`（编排）、`scripts/`（离线工具）、`reports/`（逐样本产物）；阶段从 `stage0..4` 改为 V2.0 的 `P0..P5`（§7）。

---

## 3. 总体分层与依赖方向

```
docs/raw（需求与论文，只读）
       ↓ 蒸馏
docs/protocol.md + configs/{protocol,models,eval}.yaml + configs/prereg/（预注册：门限、decision rule、evidence tier）
       ↓ 被读取
src/readkv（runtime / models / cache / data / diagnostics / train / eval / stats）
       ↓ 被调用
experiments/P0..P5（薄编排层）
       ↓ 产出
reports/runs/<run_id>/（不可变：config、逐样本分数、输入 hash、protocol version、zero-re-prefill flag）
       ↓ 被消费
reports/figures/ + reports/ledgers/ + scripts/ + tests/（bootstrap 重算、一致性检查、R2 测量、回归测试）
```

依赖方向严格单向：`experiments` / `train` 依赖核心库；核心库不反向依赖实验脚本；`stats` 只读归档分数，不加载模型。`mapper`（`models/{ridge,consumer,cf_rct}`）只写参数，不判定门限；`eval` 只产出分数与诊断，不拟合 mapper；`diagnostics` 的 Oracle 干预只在训练 / 诊断期调用 `C_S(d)`，**不得进入 `train` 的推理图或 `eval` 的 Joint 臂**。

---

## 4. 模块边界与职责

目标模块（与 V2.0 方案 §9.3 建议目录对齐）：

| 模块 | 负责 | 明确不负责 |
|---|---|---|
| `runtime/` | RunContext：run_id、种子列表、dtype/kernel、git hash、协议版本、zero-re-prefill 标志、产物写入 | 科学结论 |
| `models/` | 模型加载 / 冻结、KV 捕获与注入、de-RoPE/re-RoPE、层映射、GQA 处理、Qwen3 QK-Norm 与模板；`ridge.py` / `consumer.py` / `cf_rct.py` 定义 mapper 与低秩残差、参数量统计 | 映射质量判断 |
| `cache/` | KV 数据结构、npz 落盘 / 加载、层子集、体积估算、`identity_check`、pair_id 索引、配置指纹 | 评测与判定 |
| `data/` | `build_cf_pairs.py`：六类反事实文档对、合法性检查、标签交换、分组拆分；真实文档扩展；保留旧 QA / 合成域作基线 | 模型推理 |
| `diagnostics/` | `route_value.py`：四臂、局部 Routing/Consumption 分解、层 / 头 / Token Oracle 干预、对称 Key 前置实验 | 训练主方法、判定门限 |
| `train/` | `kd.py` / `cf_rct.py`：冻结学生、固定训练预算、成对损失（`L_KD/L_CF/L_local/L_reg`）、seed 与预算记账 | 评测、科研叙事 |
| `eval/` | `quality.py` / `counterfactual.py` / `controls.py` / `stats.py`：修正 EM、`g`/`D`/`E_CF` 族、正 / 负控制、簇级 bootstrap 与 CI | 拟合 mapper、判定科研叙事 |
| `stats/` | paired/cluster bootstrap、max-family bootstrap、Holm 调整、Wilcoxon、秩相关 | 访问模型或缓存 |
| `experiments/P0..P5` | 按配置编排阶段、调用上述模块 | 内嵌统计或指标实现 |
| `scripts/` | 离线缓存生成、报告重算、一致性审计、R2 测量 | 新的科学逻辑 |

---

## 5. 数据流与状态归属

一次运行的生命周期：

1. **构造反事实对**（`data/build_cf_pairs.py`）：生成 `u=(q,d_A,d_B,a,b,m)`，六类切片 F1—F6，候选顺序随机交换，按实体 / 来源 / 模板簇隔离 split；产出附录 A schema 的 pair 表。
2. **离线教师缓存**（`cache/offline_prefill.py`）：对 `d_A`、`d_B` **各自独立 Prefill** → 选定层 K/V → de-RoPE → 按 `pair_id` 落盘 → 记录文件哈希 → 卸载 Teacher。早期实测磁盘吞吐（I/O 可能先于显存成为瓶颈）。理论体积：0.6B/1.7B ≈112 KiB/token；4B/8B ≈144 KiB/token（fp16，需实测）。
3. **实现正确性**（`cache/identity_check.py`）：Self / Identity / full-prefill 路径一致性与数值残差；E0 的测量误差上限必须显著低于待研究效应。
4. **机制前置**（`diagnostics/route_value.py`）：对称 Key 四目标（A—E）、K/V 四臂、局部输出分解、层 / 头 / Token Oracle 移植；机制选择规则只在训练 / 验证集学习。
5. **配对训练**（`train/{kd,cf_rct}.py`）：加载冻结学生与 Mapper → 按小 Batch 加载两份教师缓存 + 学生原生 Self 目标 → 两次学生 Query Forward → 计算 `L_KD/L_CF/L_local/L_reg` → 反向传播**只更新 Mapper**；记录 seed、Forward 次数与参数量。
6. **注入与打分**（`eval/`）：只加载最终 Mapper、教师缓存与学生；Joint 严格禁止学生处理文档 token；每个评测单元运行 Correct / Mismatch / Random / Zero / Shuffled-target 控制；产出 `g`、`D_self`、`D_trans`、`E_CF`、`flip_consistency`、`dual_correct`、`coverage` 等逐对记录。
7. **统计与判定**（`eval/stats.py` + `stats/`）：从逐对记录重算主终点（新方法与最强基线的成对 `E_CF` 差异）与 95% 簇级 paired bootstrap；≥3 seed；多重比较用 Holm；`gates.py` 输出实现门 / 替代门 / 反事实结果与证据分级。
8. **归档**：`reports/runs/<run_id>/{config.json,scores.jsonl,metrics.json,manifest.json}`、`reports/figures/`、`reports/ledgers/`；论文数字只能从此处重算。

状态唯一 owner：

| 状态 | owner | 生命周期 | 持久化 |
|---|---|---|---|
| 反事实 pair 表 | `data/` | 构造 → 冻结 → 后续实验只读 | `data/pairs/*.jsonl` |
| Teacher KV 缓存 | `cache/` | 离线生成 → 落盘 → 后续实验只读 | `data/cache/*.npz` |
| mapper / 低秩残差参数 | `models/` + `train/` | 训练拟合 → 随 run 归档 | `reports/runs/<run_id>/mapper.pt` |
| 逐对分数 | `eval/` | 每次推理追加 | `reports/runs/<run_id>/scores.jsonl` |
| 统计结论 | `stats/` | 由归档分数重算，不落第二次 | `reports/runs/<run_id>/metrics.json` |
| 判据与协议版本 | `runtime/` + `configs/prereg/` | 冻结后只读 | `reports/runs/<run_id>/config.json` |

禁止多个模块同时持有同一份缓存 / 分数；跨边界一律通过显式参数或归档文件传递。

---

## 6. 失败模式与降级

| 风险 | 后果 | 应对 |
|---|---|---|
| 24GB OOM（4B/8B teacher） | 实验中断 | Teacher 离线、只加载 student；bf16 + 小 batch + gradient checkpointing；8B 仅一次缓存生成后卸载 |
| bf16 kernel path 残差 | 小效应噪声、假阳性 | E0 先测残差上限；对比实验同 dtype / 同 kernel；残差归因写入协议 |
| 磁盘 / I/O 瓶颈 | 缓存读取拖垮迭代 | 早期实测吞吐；只存需要的层；文档 256–512 token；按 pair 加载；fp16 离线存储 + 配置指纹 |
| `D_self` 近零导致 `E_CF` 退化 | 恒定输出也低误差 | 必须联合报告双向成功率、方向一致率、coverage、与无信息控制的差距；预注册 Self 有效子集 |
| 反事实对构造不纯 | 把位置 / 模板效应误判为事实失真 | F5 负控制、F6 长度 / 位置控制、token 长度匹配、来源 / 实体 / 模板簇隔离、人工抽检 |
| Oracle 信号泄漏进推理 | 虚假的“零重 Prefill”结果 | Oracle 只在离线诊断 / 训练期；verify_zero_re_prefill 断言；Joint 臂禁止读取 `C_S(d)` |
| `τ` / Huber 阈值 / 标签平衡按测试调 | 主终点被污染 | 全部在验证集固定并写入 `configs/prereg/`；封存测试只读 |
| 梯度训练种子方差 | 单次数字不可复现 | ≥3 seed 报范围；簇级 bootstrap；单次 MLP 不当点估计 |
| 机制诊断只有事后相关 | 无法支撑 H2 / 贡献② | 三层诊断中 C 层必须有独立文档预测价值；降级为现象报告 |
| CF 改善 `E_CF` 但常规任务退化 | 不可写成方法贡献 | 普通 QA 与反事实 QA 同报；按决策树重新调整多目标或如实报告权衡 |
| 效果仅在合成域成立 | 过度宣称通用性 | 未见模板 / 同义实体 / 位置偏移 / 真实文档扩展；按决策树限定适用域 |
| 强基线已接近 Self | 主线前提失效 | 按决策树转边界 / 失败条件研究，不坚持“所有方法反事实失真” |

---

## 7. 阶段计划、闸门与交付（V2.0 P0—P5）

| 阶段 | 计划窗口* | 工作任务 | 放行条件 / 产出 |
|---|---|---|---|
| P0 基座 | 第1—2 周 | 整合校正评测器、identity 与 cache 持久化；确定双文档 Query 格式；建立实现门 | 形状 / 位置 / 数值一致性全部通过；输出协议 V1 和可复现最小样本 |
| P1 基准 | 第3—4 周 | 建立反事实数据、真实数据小样本；复现 ridge / consumer / KD 等强基线 | 确认是否存在未被强基线消除的反事实失真；否则及时转向 |
| P2 机制 | 第5—6 周 | K score 目标、K/V 四臂及层 / 头移植，形成错误归因候选 | 机制诊断在验证集有预测价值；产出机制报告和候选公式 |
| P3 方法 | 第7—9 周 | 训练 KD-only、CF-lite、CF-mech；严格配平预算并作消融 | 新方法相对强基线有非偶然改进；否则停止扩大模型 |
| P4 泛化 | 第10—11 周 | 非等深 pair、未见模板 / 真实文档，最终封存测试 | 报告跨设置稳定性、CI、失败边界与不利结果 |
| P5 成稿 | 第12 周及后续 | 运行耗时与显存核算、统一图表、投稿文本 | 完成方法 / 实验 / 复现附录；是否投稿取决于结果质量 |

\*窗口仅为有现有代码和足够存储条件的排期估算，不是工作完成承诺；实际训练时间、统计检验规模、强基线实现可用性将影响排期。每阶段的“不通过”分支按 `protocol.md §8` 决策树执行，不事后改判据。

---

## 8. 关键取舍

- **反事实保真为一级指标 vs 仅报替代能力**：选前者。常规 EM / gold-prob 接近 Self 不等于事实变化响应被保留；但 `E_CF` 单独下降也可能退化，必须联合报告一组指标（见 §6 与 protocol §4.3）。
- **统一底座 vs 阶段独立脚本**：选统一底座。同 dtype / 同 kernel / 同 split / 同 Query 协议才可比较；代价是 P0 需 1—2 周。
- **Teacher 在线 vs 离线落盘**：选离线。24GB 下 8B 无法与学生训练共存；代价是磁盘占用与 I/O 管理；按 `pair_id` 加载、分层报告长度差异。
- **consumer-space vs representation-space 默认**：默认 consumer-space。representation 族与对称 Key 目标仅作机制基线；不把 raw error / `R²` 当任务质量。
- **closed-form vs SGD key 目标**：先 de-RoPE 闭式近似，再 SGD 对照；把“近似是否足够”作为明确结果报告；Key 侧不论正负都写入论文。
- **CF-RCT-lite vs CF-RCT-mech**：先 lite 再 mech；机制选择规则只用训练 / 验证集；只有 mech 对 lite 与最强公共基线均有增益，才把“机制引导”写成核心创新。
- **PyTorch 模型层 vs 自维护 cache 数据结构**：选自维护数据结构 + hook 捕获。transformers 5.x 的 cache API 变化较快，接口放在 `models/hooks.py`，便于按版本适配而不污染评测与 mapper 代码。

---

## 9. Mock 后端与 CPU 可运行管线

为了让没有 GPU 的机器也能验证整条逻辑，保留并扩展 `src/readkv/models/mock_backend.py` 与 `src/readkv/evaluate/pipeline.py`：

- `MockBackend` 用确定性的线性“模型”把文档内容向量映射成 teacher/student KV，再用注意力读出得到候选 logits。需**新增反事实能力**：对同一 `q` 的两个文档 `d_A`/`d_B` 独立生成缓存，并可选择性复刻/注入三类现象供判据接线测试——①identity 注入保真；②映射 V 可被 consumer-space mapper 恢复；③两文档事实位点变化时 `D_trans` 与 `D_self` 可能出现偏离。mock 仅用于接线回归，**不预设实验结论**（即不预设强基线一定存在或不存在反事实失真）。
- `run_pipeline` 统一编排：pair 构造 → 缓存 → mapper → 四臂 + 内容控制 + 探针 → 逐对分数 → `E_CF` 族 → 门限与决策树 → 报告落盘。决策规则由 `configs/prereg/` 的机器可读 `conditions` 字段匹配，不做事后解释。
- 阶段脚本默认 `--backend mock`，可在 CPU 上完整运行；`--backend gpu` 保留给目标机器，并要求先实现 `models/hooks.py` 契约。
- **mock 产生的所有数字都不是科学证据**，只用于接线回归、判据触发与报告格式验证。

V2.0 最小自动测试（对应方案 §9.3）：

1. 相同学生缓存的 round-trip 一致；
2. 每个反事实对正确关联两个文档与答案（含 F5 非翻转负控）；
3. query-only 生成不含文档 token（零重 Prefill 断言）；
4. 长度不匹配能显式报错；
5. 临时打乱映射应造成预期失真（`E_CF` 上升 / 方向一致率下降）；
6. 关闭全部新损失时回归基础 KD 结果（`CF-RCT-lite` 退化为 KD-only 行为）；
7. 训练 / 测试缓存哈希无交叉，且机制选择规则不使用封存标签。

---

## 10. V1 → V2 迁移映射（当前代码 → 目标结构）

**实现状态（已更新）**：V2.0 目标结构已全部实现并通过 51 个测试（V1 35 + V2 16）。下表保留为 V1→V2 的对应参考；旧模块继续服务回归与行为基线，**但旧指标（CHG / 三道门）不得当 V2.0 主终点**。GPU 后端仍需实现 `models/hooks.py` 的真实前向（接口契约与 mock 一致）。

| 现有（V1） | 目标（V2.0） | 迁移动作 |
|---|---|---|
| `configs/gates.yaml`（三道门 H1/H2/H3） | `configs/protocol.yaml` + `configs/prereg/` | 保留 identity 门与替换门形式；H3 exploitability 改为信息归因对照；新增 `E_CF` 终点与 τ/Huber 阈值 |
| `configs/stage1_key.yaml`、`stage2_audit.yaml`、`stage3_behavioral.yaml` | `configs/{protocol,models,eval}.yaml` | 模型对保留 1.7B→0.6B / 4B→1.7B；新增反事实 pair、CF-RCT 与公平基线配置 |
| `data/synthetic.py`、`data/qa.py`、`data/splits.py` | `data/build_cf_pairs.py` | 扩展为六类切片的成对构造；保留旧数据作标准 QA 报告 |
| `evaluate/probes.py`、`controls.py` | `diagnostics/route_value.py` + `eval/controls.py` | fraction/window/octant 探针降级为信息归因控制；四臂与 Oracle 移植独立成 diagnostics |
| `evaluate/evaluator.py`、`pipeline.py` | `eval/quality.py`、`eval/counterfactual.py`、`eval/stats.py` | 新增 `g`/`D`/`E_CF` 族、`flip_consistency`、`dual_correct`、`coverage`；主终点改为成对 `E_CF` 差异 |
| `mapper/behavioral.py` | `models/cf_rct.py` + `train/cf_rct.py` | 重构为 `CF-RCT-lite` / `CF-RCT-mech`；加入 `L_CF`、`L_local` 与公平基线 |
| `mapper/key_objectives.py`、`consumer.py`、`representation.py` | `models/ridge.py`、`models/consumer.py` | 保留为机制前置实验 / 强基线；`NotImplementedError` 按 GPU 接续清单实现 |
| `mapper/hidden_state.py` | `models/cf_rct.py` 的候补分支 | 保留为高风险探针，默认不进主线 |
| `experiments/stage0..4` | `experiments/P0..P5` | 阶段语义按 §7 重排；stage0→P0，stage1→P2（机制），stage2→P1（基准），stage3→P3，stage4→P4/P5 |
| `reports/<run_id>/` | `reports/runs/<run_id>/` + `figures/` + `ledgers/` | 逐对记录新增附录 A 字段；图表只读冻结结果文件 |
| `scripts/measure_reconstruction_r2.py` | 保留 | `R²` 只作 cache 层诊断，不得作任务质量结论 |

---

## 11. GPU 机器接续清单

详细步骤见 `docs/gpu_handoff.md`。摘要：

1. 实现 `models/hooks.py` 的 `capture_teacher_cache` / `inject_and_generate` / `verify_zero_re_prefill`，按当次 pinned transformers 版本适配；确认 Qwen3 QK-Norm、聊天模板与 `/no_think` 协议；
2. 把 `models/loader.py` 的 `resolve_layers` 适配到 Qwen3 checkpoint；
3. 为真实 `query_states` 与 `attention_matrices`（GQA 按 KV head 堆叠 query head）提供回调，替换 mock 的线性投影；
4. 实现 `models/consumer.py` 的 `W_O,q` 目标与 attention KL / ranking 目标；`models/cf_rct.py` 的成对 `L_CF` 与 `L_local`；
5. 用 `scripts/gen_teacher_cache` 对 `d_A`、`d_B` 各自独立离线生成并落盘 teacher 缓存，之后卸载 teacher；
6. 先以 `--backend gpu` 重跑 P0，确认 E0 实现门（cosine ≥0.9998，残差上限显著低于效应）再继续；
7. 按 §9 的七条自动测试补回归，封存测试运行前完成 `protocol.md §9` 预注册。

---

## 12. 未决问题（实现后）

1. **GPU 后端适配（唯一剩余阻塞）**：`models/hooks.py` 的 `capture_teacher_cache` / `inject_and_generate` / `verify_zero_re_prefill` 仍是接口桩；`gen_teacher_cache --backend gpu` 与所有阶段脚本的 `--backend gpu` 在适配前显式报错。mock 后端已完整覆盖全部 V2 功能。
2. 主模型对保持不变：MVP `1.7B→0.6B`（等深）、主验证 `4B→1.7B`（非等深），8B 仅离线压力测试（`configs/eval.yaml`）。
3. CacheLink / KV-Lingo 是否有可运行官方实现；若无，按公开文档实现并明确报告偏差，不假定原作者结果可直接复现。
4. τ、Huber 阈值、标签平衡、最小有意义差异已写入 `configs/protocol.yaml`；封存测试前须冻结 `configs/prereg/` 的 decision rule，运行后不可更改。
5. 真实文档扩展（`real` split，80—150 对）需人工核验出处与事实扰动，当前默认为 0。

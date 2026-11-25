# GPU 实验方案（审稿后续项；需 PI 另行批准）

**日期：2026-11-25**  
**用途：**把审稿意见中仍可能需要 GPU 的实验单列，作为后续决策方案。  
**状态：提案，不是运行授权；本文件不修改冻结判据，也不启动任何实验。**

## 0. 决策边界

本计划所针对的当前稿件是单一等深模型对上的失败边界 / 基准审计研究。现有 2×2 版本对照（`configs/prereg/gpu_followup_v2.7.yaml`）已经完成；**不重跑 A00/A01/A10/A11**。

当前冻结记录对后续实验有明确限制：

- v2.7 将单缺陷实验列为“本轮不做、不建议在本文做”。
- v2.7 明确规定不读取封存 test。
- `docs/decisions/final_boundary_study_signoff.md` 将 P2/P3/P4 收口；`docs/decisions/human_decisions.md` 的既有 GPU 授权仅覆盖 2×2。
- v2.1 数据文件把 train/val/test 都放在 `data/tasks/cf_pairs.jsonl` 中。因此 test 是**此前未评测的 held-out split**，但不应在没有独立保管和访问控制证据时称为技术上“封存”的 test。

所以 E1、E2、E5、E6 **均须先有真实 PI 新裁决和新版本预注册**（建议另立 `configs/prereg/gpu_followup_v3.0.yaml`；此文件尚未创建），再决定是否纳入当前稿或新研究。不得以本方案替代 PI 签核，不得回写 v2.1–v2.8，不得运行后再改判据。

## 1. 研究问题与优先级

| 编号 | GPU 工作包 | 优先级 | 主要回答 | 对当前论文的状态 |
|---|---|---:|---|---|
| E1 | 单缺陷干预筛查 | 高，但需新课题/新裁决 | 哪类基准修改可能改变 affine 的观测结果？ | 当前冻结决定不做；未获新批准前不执行 |
| E2 | clean held-out split 评测 | 高，但需解锁授权 | 现有 validation 结论在此前未评测的 test split 是否复现？ | v2.7 禁止触碰；需新 prereg 与访问门 |
| E5 | 第二模型对复验（Qwen3-4B→1.7B） | 中 | 相同失败方向是否在一个额外模型对出现？ | P4 已 NO-GO；只能作为新授权的有限复验，不可直接声称普遍泛化 |
| E6 | 强/预算匹配基线 | 中 | 结论是否依赖 affine 与 KD 预算不对称？ | 先完成方法全文/代码核验；有可信实现才做 GPU 对比 |

排序建议：**先审批并冻结方案 → E2 是否允许 → E1 是否另立研究 → E6 基线选择/可复现性门 → E5**。E1/E2/E5/E6 的数据、估计量和研究主张不同，不应事后合并成一个新的“强叙事”。

## 2. 共用运行纪律（只有新裁决批准后适用）

### 2.1 固定项

- 运行前固定模型权重 revision、tokenizer 指纹、代码 commit、数据 SHA-256、软件/CUDA/驱动版本、dtype、kernel、layer map、mapper 参数及 seed。
- 延续 BF16、SDPA、严格 `zero_re_prefill=true`；记录每次 student forward 的输入长度与 cache/position 审计。
- 逐 seed 报 Self 和 Joint 双侧正确率、`L = Self − Joint`（百分点）、`E_CF`、coverage、方向一致率及其实际分母；不能只报 E_CF。
- template-family 为主重采样单位，pair-level 仅作敏感性。族数不足 24 时标 `exploratory=true`，不做强推断；所有 seed 分开报告。
- 逐对 `scores.jsonl`、`config.json`、`metrics.json`、数据指纹和 `manifest.json` 写入**新的** `reports/runs/<run_id>/`。不覆盖历史目录。
- 所有运行串行。先用一个 seed/小样本走技术门；技术门失败则停止扩展，不把烟测数字用作科学结果。

### 2.2 通用技术门

1. 输入 split 和 pair 数正确；候选/gold、template family、样本哈希与预期 manifest 对齐。
2. Self/Identity 锚点通过；检查 zero re-prefill、K/V 捕获和注入、位置偏移与样本顺序。
3. 测量 peak GPU memory、每格 elapsed time、前向数和缓存大小；据实更新预算。
4. Smoke run 和正式 run 使用独立 run ID；正式运行需在新 prereg 中规定停止条件。
5. GPU 工具或模型版本不兼容时先修复并复验；禁止为得到预期方向而变更评分、样本、seed 或阈值。

## 3. E1：单缺陷干预筛查（新研究；不属于当前冻结实验）

### 3.1 目标与边界

目标是估计单类基准修改与 mapper 结果变化之间的**受控关联**，不是直接证明“泄漏制造了假发现”。仅做单缺陷逐项干预无法识别缺陷之间的交互；若要定量分解交互，需要另行预注册完整 factorial 设计，不能从 one-at-a-time 结果外推。

先由数据工程师制作可审计的候选语料，不运行 GPU。每个变体从同一 legacy 基线派生，并只改一个明确定义的数据属性：

1. `legacy_bundle`：原始版本，仅作为历史参照；
2. `dedup_only`：只处理预先定义的重复/重叠组；
3. `degenerate_only`：只处理 must-flip 但候选相同的记录；
4. `entity_disjoint_only`：只让规定 split 间的实体池互斥；
5. `template_disjoint_only`：只让规定 split 间的模板骨架互斥；
6. `fully_repaired`：当前 v2.1 全修复版本。

每个变体须记录改变了哪些 sample/text/hash、样本数是否改变、替换/剔除规则、各 slice/family 数及质量审计。样本数和切片构成变化无法匹配时，应将它报告为版本差异，不得声称纯粹的单缺陷效应。

**设计限制：**must-flip 退化对主要是评测标签/任务有效性缺陷，不进入 ridge 的标签监督拟合。因此，对“退化对改变拟合 mapper”的 GPU 因果解释不成立；其对预测指标的重算应优先用已存 logits/逐对分数做 CPU 复核。只有当候选文本或输入上下文本身需要改变时，才需要新增 GPU 前向，并应单列“数据任务改变”。

### 3.2 建议的最小 GPU 矩阵

若 PI 批准，先做两个独立 panel，避免把训练与验证端变化混为一谈。

**Panel A：校准集干预，固定 clean validation。**  
每个 seed 分别用 legacy、各单缺陷 calibration 变体和 fully repaired train 拟合 affine mapper；所有 mapper 均在同一 v2.1 validation 上评分。

| Calibration train | Seed 0 | Seed 1 | Seed 2 | 评测集 |
|---|---:|---:|---:|---|
| legacy | 1 格 | 1 格 | 1 格 | 固定 v2.1 val |
| dedup-only | 1 格 | 1 格 | 1 格 | 固定 v2.1 val |
| entity-disjoint-only | 1 格 | 1 格 | 1 格 | 固定 v2.1 val |
| template-disjoint-only | 1 格 | 1 格 | 1 格 | 固定 v2.1 val |
| fully repaired | 1 格 | 1 格 | 1 格 | 固定 v2.1 val |

共 **15 个 mapper-fit/evaluation 格**；若归档的 legacy 与 fully repaired 对角结果通过 checkpoint、代码、tokenizer、输入指纹核验，可复用为历史锚点，否则增跑对应的桥接格。dedup 变体须明确是训练集内去重还是 train–validation overlap 清理，两者不能混称。

**Panel B：验证集干预，固定 clean calibration mapper。**  
用固定 v2.1 train 拟合 mapper，再在预先构造的 validation 变体上评分；同一模型/seed 的 calibration 与 mapper 不变。只在任务定义有效、gold 标签可审计的样本上比较。若变体导致样本组成变化，使用预先定义的共同样本集与全样本描述性结果并列报告。

Panel B 同样最多 15 个格，但不是 Panel A 的替代；两者回答不同问题。Panel B 中“修复退化标签”对原始 logits 的重新计分应先做 CPU replay，只有输入文档/候选内容发生变化才追加 GPU 前向。

### 3.3 指标、判读和停止规则

- 主结果：逐 seed 的 Self、Joint dual correctness 和 `L`；同时列出每种变体的实际有效 pair/family 数。
- 次结果：`E_CF`、coverage、flip/direction consistency 和旧版/clean 之间的逐对变化；不能把 E_CF 单独当作效用。
- 不预设“哪一个缺陷应解释最大差距”，也不根据结果挑选主缺陷。报告所有六种版本条件。
- 结果只能支持“在给定生成器/样本构造下，某种单一改动与指标变化相关”。单因素矩阵不识别多缺陷交互，也不自动证明真实数据泄漏造成普遍假阳性。
- 若目标仍是因果比例归因，须另立完整析因设计（例如缺陷因素的 factorial），独立冻结判据；不能将本 6 条件筛查改名为“因果贡献分解”。

### 3.4 工程和算力

新增 CPU 数据构造/审计是前置门槛；现有 `experiments/audit_2x2_gpu.py` 只支持 legacy/fixed 两套 train/val，**不能直接执行这些单缺陷变体**。需先实现显式文件输入的独立入口及版本哈希绑定。

当前 2×2 方案的历史预算为 12 个格约 1–2 单卡 GPU 小时。Panel A/B 合计最多 30 个格，初始仅作**约 3–6 GPU 小时的线性估算**（非实测承诺）；先跑 seed 0 冒烟和一个完整格，再依据实际耗时/显存决定是否继续。单缺陷语料设计/人工核验的人日不包含在 GPU 小时内。

## 4. E2：此前未评测的 held-out test（解锁门；当前禁止运行）

### 4.1 先更正“封存”状态

v2.1 的 520 对数据在 `data/tasks/cf_pairs.jsonl` 中可读，manifest 显示 test=300 对、16 个 template family。除非证实 test 文件由独立保管者控制且研究者此前无法访问，否则建议在稿件与方案中称为**“此前未评测的 held-out split”**，不要称“sealed”。本计划不读取该 split 内容，也不授权任何新 test scoring。

### 4.2 PI 新批准后才可进行的流程

1. 先锁定 test 的数据 SHA、分析代码 commit、模型/checkpoint/tokenizer、输出指标、seed、所有排除规则和统计脚本。
2. 确认验证集不再用于选参；固定 affine 和 kd_only 配置，不做 test 上调参、阈值选择、错误样本返修或多轮查看后再跑。
3. 由授权者一次性运行 dedicated test evaluator；现有 `P1_gpu.py` 默认只评 val，`P1_kd_gpu.py` 可接受 `--eval-splits test`，但在批准前不得使用该参数。需加入 test-only 的显式路径/哈希/锁检查，避免误把 val/test 混跑。
4. 当前 `data/tasks/manifest.json` 记录的是一个 seed-0 生成的 300 对 test split，而不是三个独立 test seed。若授权跨三个训练 seed，应在**同一固定 test 集**上评估 affine 与 kd_only 各 seed，共 **6 个评测格**；这些是 mapper/calibration seeds，不是 3 份独立 test 样本。
5. 对同一 test 集分别报告各 mapper seed 的 Self/Joint dual、L、E_CF、coverage、flip 及 template-family 区间；16 个 template family 仍低于冻结的 24 family 参考线，结果仍标 exploratory。不得把三次评分当成 3 个独立 test replicate 合并推断。
6. test 结果只验证固定配置的外推表现，不作模型/域的普遍泛化结论。若 test 上失败，照实报告，不返回验证集调整后再次声称为独立 test。

**预算：**六个评测格的耗时需由 seed 0 pilot 实测；test split 有 300 对，不能直接按 60 对 validation 的单格时间等同估算。若在 24GB 单卡上出现 OOM，先按样本分批、保持相同的固定配置和输出协议；不得通过缩减 test 样本选择结果。

## 5. E5：第二模型对复验（新范围；P4 当前 NO-GO）

**问题：**在 Qwen3-4B→1.7B（36→28 层，proportional layer map）上，clean-data affine 行为是否与 1.7B→0.6B 方向一致。它只能增加一个独立案例，不足以支持“跨模型普遍成立”。

**建议设计：**

- 数据：相同 `cf_pairs_v2.1` 生成协议；先检查 model-pair 配置不会改变文本、split 或标签。若生成器的 pair 参数会改变数据，固定并绑定独立 manifest。
- 系统：affine 为必须；若经 PI 批准且论文保留强基线比较，再加入现有 kd_only，形成 2 mapper × 3 seeds = **6 个正式格**。
- 入口：可从 `experiments/P1_gpu.py` 的 `--model-pair qwen3-4b-to-1.7b` 开始，但需在新 prereg 中冻结 proportional layer mapping、数据规模、校准/评测 split 和参数。训练 120、评测 60 与主 MVP 保持一致，评估仍只跑 validation，除非 E2 单独获批。
- 对照：报告同一方法在原模型对的现有权威结果与新模型对结果，不合并 seed 或 pooled CI；解释 layer-depth 不匹配带来的差别。
- 指标：Self/Joint dual correctness 和 L 为首要，E_CF/coverage/方向指标为次要；template-family CI、pair 敏感性、探索性标记均保留。
- 技术门：先做 seed 0 的模型加载、tokenizer、层映射、cache 形状、Self/Identity 和 zero-re-prefill 审计。4B+1.7B 在线同卡显存需先测；不得因 OOM 改精度或 kernel 后仍与主结果直接合并。

**判读：**同方向只能写成“在一个额外模型对复现/未复现该模式”；不称跨模型泛化。若失败，不可删去该模型对或选择另一对替代。

## 6. E6：基线公平性与外部方法

### 6.1 先过方法复现门（非 GPU）

在任何训练前选定一个基线，并核验全文方法、代码/权重可用性、许可、mapper 结构、训练数据、训练目标、输入信息及推理是否严格 zero-re-prefill。若 KVLingo、CacheLink 或其他发表方法没有足够代码/模型细节，不得只按摘要重实现后称为“faithful baseline”。

若没有可忠实复现的外部方法，采用明确命名的**预算匹配内部对照**，不称已发表方法基线：

- 同模型对、同 train/val 样本、同三 seed、同 zero-re-prefill；
- affine ridge：现有闭式解与 λ=1e-3；
- kd_only：现有 8 epochs、lr=1e-3、训练对数 120；
- 追加一个在 prereg 中明确架构/参数数量的可训练线性或仿射 mapper，对齐训练样本与优化步数；报告参数、GPU 时间、前向/反向次数、显存和训练目标。参数量相似不等于算力/目标公平，必须分项披露。

### 6.2 GPU 矩阵

- 首选主对 Qwen3-1.7B→0.6B，三 seed；同一 clean train/val 上逐对评测所有 baseline。
- 若只跑现有 affine + kd_only，前两组已有权威结果可复用，但须核验其 data hash/checkpoint/code 绑定；新内部基线需三 seed 新跑。
- 若另纳入 E5 的 4B→1.7B，属于额外模型对，须分开报告；不能为了省预算只在该模型对跑 baseline 却把结果与 MVP 的 affine 数值直接比较。
- 外部方法必须在代码/参数/目标复现通过后才能进入正式矩阵；不通过则记录为“不可复现/不具备公平比较条件”，不要拼凑实验。

**成功标准：**在看到运行结果之前，定义模型质量、参数匹配容差、训练预算、主指标、失败/中断处理及比较族。即使 affine/KD 排名不变，也完整报告训练成本差异。

## 7. 建议执行顺序与审批门

| 阶段 | 工作 | 放行条件 | 预算方式 |
|---|---|---|---|
| G0 | 研究范围裁决 | PI 明确 E1/E2/E5/E6 是否纳入当前论文或另立后续研究；针对 test 解锁另行签核 | 不占 GPU |
| G1 | 新 prereg + CPU 数据/基线审计 | 新版本文件冻结；数据哈希、变体清单、模型来源、判读分支全部完成 | 不占 GPU |
| G2 | 技术 pilot | 单 seed/小样本通过 Self/Identity、层映射、zero-re-prefill、显存与时间门 | 按 pilot 实测 |
| G3 | 核心批准实验 | E1/E2/E5/E6 按各自矩阵运行，串行、不混 run ID、不覆盖归档 | 每格实测时间 × 格数 + 明确缓冲 |
| G4 | 统计和独立审阅 | family bootstrap + pair 敏感性；各 seed 和失败 run 全部入账；确认没有事后择支 | 不占 GPU |

**首轮建议：**若 PI 批准，先做 E6 的基线复现可行性审计和 E1 的 CPU 数据变体审计；两者没通过前不提交 GPU 队列。E2 放在最后且仅在完整锁定后一次性评测。E5 属跨模型范围扩张，当前稿若维持单模型对边界定位，不是必须跑。

## 8. 不纳入本方案的事项

- 已完成的 v2.7 2×2 与已完成的 A00/A11 序列评分不重跑。
- 不做 P2/P3/P4 阶段恢复，不重算旧主终点，不把 E1/E2/E5/E6 结果包装为方法增益。
- 不将 ARC/HellaSwag/SQuAD、真实文档采集或 AI 生成数据混入本 GPU 矩阵。
- 不以“GPU 方案已写”为开始运行、访问 held-out split、修改论文因果措辞或改变投稿决策的授权。

## 9. 交付与复核清单（获批后）

- [ ] PI 新裁决明确范围、当前稿或新研究的去向、test split 是否解锁。
- [ ] 新版本 prereg 在任何新 GPU run 前冻结；不回改旧版本文件。
- [ ] 每个输入/模型/tokenizer/代码/环境均有指纹；模型 revision 不使用漂移的 `master` 别名而不记录实际文件 hash。
- [ ] smoke gate 通过，完整日志和 zero-re-prefill 审计落盘。
- [ ] 所有 seed、所有对照和失败 run 均报告；统计脚本从 `scores.jsonl` 重建，不人工改数字。
- [ ] 结论用词只达到本设计实际识别的范围；单缺陷 screening 不声称交互分解，第二模型对不声称普遍泛化。
- [ ] 独立审稿后再更新论文与投稿材料。

# 数据就绪性复核报告（科学家视角：P0–P5 与可投稿性）

> 角色：科学家（算法与机制设计）。日期：2026-11-23。
> 任务：与数据工程师并行，独立复核当前数据是否支撑 P0–P3 并足以发论文。
> 边界：**只写本 `docs/` 文档**；不重算统计、不改数据、不改 `configs/prereg/**`、不改论文/代码/运行产物；所有数值均引用既有冻结产物或文档，凡本报告自行观察到的事实均标注「复核观察」并给出可追溯的 pair_id / 行号。凡属推断均标注「判断」而非「证据」。
> 数据来源：`data/tasks/manifest.json`、`data/tasks/cf_pairs.jsonl`、`configs/{protocol,pairs}.yaml`、`configs/prereg/**`、`docs/protocol.md`、`docs/gpu_handoff.md §3`、`docs/experiment_design_E0_E7.md`、`docs/decisions/{final_signoff,contribution2_final_form,p3_task_plan}.md`、`docs/p3_resource_estimate.md`、`papers/readkv_v2_draft/{main.tex,notes.md}`。

---

## 0. 独立复核结果：PI 给出的数据事实逐项确认

| 事实（PI 给定） | 复核方法与结论 |
|---|---|
| 520 对：probe 40 / train 120 / val 60 / test 300；real 0 | ✅ 确认。`manifest.json sizes` + `by_split` 一致；`cf_pairs.jsonl` 共 520 行，`"split":"test"` 精确 300 条，`real` 无记录。`configs/protocol.yaml data_sizes.real=0`。 |
| 切片 F1 130 / F2 67 / F3 130 / F4 67 / F5 63 / F6 63 | ✅ 确认，与 `manifest.json quality.by_slice` 一致。 |
| test 仅 8 个模板族、300 个唯一 source_doc_id/cluster | ✅ 确认。通读 test 全 300 行，`template_family` 取值恰为 8 个：`T-F1-person-D`、`T-F1-city-D`、`T-F2-alias-D`、`T-F3-direction-D`、`T-F3-negation-D`、`T-F4-distractor-D`、`T-F5-paraphrase-D`、`T-F6-position-D`；`source_doc_id` 形如 `test-<slice>-NNNN-doc`，逐行唯一（300 个），`cluster` 同样逐行唯一。 |
| train 16 个模板族；template_overlap_train_eval 为空 | ✅ 部分确认。train 有 16 个 `template_family` 取值，但它们是 **8 个基础模板 × {A,B} 两个后缀变体**（如 `T-F1-person-A`/`T-F1-person-B`）；test 用后缀 `D`、val 用 `C`、probe 用 `P`。`template_overlap_train_eval=[]`（`manifest.json`）只在**后缀字面**层面成立，**结构上 train/test 是同一批 8 个句式模板**（详见 §3.2 与 §5.4）。 |
| length_mismatch 39；flip_denominator 394 | ✅ 确认。`manifest.json` 记录 39；`"must_flip":true` 精确 394 条（= F1+F2+F3+F4 = 130+67+130+67），F5/F6 全部 `must_flip=false`。 |
| 指南建议封存测试 ≥24 独立模板/主题簇 + 未见模板子集、真实文档 80–150 对，均未满足 | ✅ 确认。`protocol.md §3.3`、`gpu_handoff.md §3` 给出建议；当前 base 模板仅 8 个、real=0。 |

### 0.1 复核新增发现（PI 清单未列，均给出可追溯证据）

1. **结构性「未见模板」不成立（判断，影响 E4）**：test 的 8 个模板族与 train 的 8 个基础模板**句式完全相同**，仅后缀字母 `-D` 与 `-A/-B` 不同（对照 `data/tasks/cf_pairs.jsonl` line 41 `train-F1-0000` 与 line 221 `test-F1-0000`：均为「项目 X 的[角色]是[姓名]。该项目已于[日期]完成评审。」）。`template_overlap_train_eval=[]` 是**后缀标记造成的字面空集**，不是语言形式上真正未见。`experiment_design_E0_E7.md E4` 的「未见模板子集」与 `protocol.md §3.3` 的「另设未见模板子集」在数据层无对应实体。
2. **存在语义退化的「空翻转」对，却标 `must_flip=true`（复核观察，影响 E1/P1 的 flip/dual 指标与 P3 联合报告）**：若干 F2/F3/F4 样本 `candidate_A == candidate_B` 且 `context_A` 与 `context_B` 在答案位上无有效差异，逻辑上无法「翻转正确」，却被计入 `flip_denominator=394`。可追溯样例：
   - F3 direction：`test-F3-0074`（line 295，「赵六向赵六汇报…赵六审批」两文档相同，候选均「赵六」）、`test-F3-0226`（line 447）、`val-F3-0002`（line 163）、`val-F3-0010`（line 171）、`probe-F3-0026`（line 27）。
   - F4 distractor：`test-F4-0067`（line 288，「张三→张三」两文档相同）、`test-F4-0115`（line 336）、`test-F4-0251`（line 472）、`train-F4-0007`（line 48）、`train-F4-0039`（line 80）、`probe-F4-0019`（line 20）。
   - F2 alias（换组不换人，答案不变）：`test-F2-0121`（line 342，组C/孙七→组K/孙七）、`test-F2-0129`（line 350，组C/张三→组J/张三）、`val-F2-0009`（line 170）、`val-F2-0017`（line 178）、`train-F2-0050`（line 91）、`train-F2-0051`（line 92）。
   上述为按具名实体的抽样枚举，**不是完整普查**；建议数据工程师用脚本做全量审计（`context_A` 与 `context_B` 在答案位是否真不同、`candidate_A==candidate_B && must_flip==true` 的条数与分 split 分布）。这类样本会系统性压低 `dual_correct`/`flip_consistency`，并可能污染 `D_self`（若两文档等价则 `D_self≈0`，进入不了 Self 有效子集 yet 仍占翻转分母）。注意 F5 的 `candidate_A==candidate_B` 是**设计使然且 `must_flip=false`**（正确），不要与上述缺陷混为一谈。
3. **簇级 bootstrap 的聚类单元存在口径歧义（判断，影响 P3 主终点 CI）**：`configs/protocol.yaml statistics.cluster_unit="template_or_source_doc"`；`notes.md §4` 写「template/source-cluster paired bootstrap」。但 test 的 `source_doc_id` 每条唯一（300 个），若按 source doc 为簇，**等价于逐对重采样，未对 8 个模板的相关性做任何处理**；若按 template_family 为簇，**只有 8 个簇**，bootstrap CI 极不稳定、检验效力很低。两条路都有问题，需在 P3 封存测试前由 PI 明确并冻结（本报告不改判据，只提出风险）。

---

## 1. 数据对已完成阶段（P0/E0、P1、P2）的支撑性判断

判断尺度针对**内部效度**：E0 门是否可测、gap 是否可检出且不被混淆解释、机制 held-out 是否可能成立。以下结论均指「数据层能否支撑该推断」，不对数值本身重新计算。

| 阶段 | 判定 | 理由（可追溯） |
|---|---|---|
| **P0 / E0（实现门）** | **支撑** | E0 用探针 40 对（`probe`，不少于 6 模板族，实际 8）做 identity / round-trip / kernel 一致性，判据为数值残差与 EM 一致率（`e0_gpu_mvp_repro_seed0`：cosine 1.0、KL 0、EM 1.0、`2.2e-16`，`notes.md §0.5`）。此门测的是实现与测量误差上限，与数据语义多样性无关；合成短模板（18–40 token）+ 单 token A/B 候选恰使「bit-identical / 机器精度」判据可判定。**数据对 E0 的内部效度充分**。E0 尺度差异（多 token logprob ≈17–20 vs 主终点 2 维 logit）已由 `notes.md §4` 备案，不影响门判定。 |
| **P1（基准 / 失真存在性 E1）** | **部分支撑** | 支撑面：train 120 / val 60 覆盖 F1–F6 六类切片、候选顺序左右平衡（`swap_candidates` roughly 50/50）、实体/来源/split 隔离（train 用 -A/-B、val 用 -C、test 用 -D），足以在**受控合成域内**检出「强基线相对 Self 的 gap」；kd 三 seed 的 E_CF 0.735/1.034/1.539、CI 下界均>0、`distortion_present=true`（`final_signoff.md §1 R3`、`notes.md §0.5`）说明在该合成域内 gap 可被稳定检出。不支撑面：① 8 个结构模板使「gap 不是模板记忆」无法排除（无未见结构模板对照）；② §0.1(2) 的空翻转样本会压低 flip/dual，使 `quality_pass`/`dual_correct` 的解释被数据质量污染；③ `main.tex §5.4` 已把 4B→1.7B 主验证对定性为 `broken-transfer` 失败边界、不计入 H1 正向证据，故 H1 的正向证据**仅限 MVP 等深对**。结论：足以得出「在这 8 类合成模板、该 mapper 范围内 gap 存在」，**不足以得出跨模板/跨域的普遍失真现象**。 |
| **P2（机制 / E2 held-out）** | **部分支撑** | 支撑面：P2 的三判据（分解残差≈0、repair-vs-random CI 下界>0、方向一致>0.5）在 train 8 对选 U、val 40 对零重叠、未碰 test 的设计下成立（`notes.md §0.5`/`§4`；4/5 核心单元跨 seed 稳定）；`d_A`、`d_B` 分别诊断后取差（`protocol.md §5.3`）在数据层可执行——F1–F4/F6 每对都有两份独立文档，满足分别诊断的最小条件。不支撑面：① held-out 只在 **val 同分布模板**上验证（val 是 train 的 -C 后缀同 8 模板），未验证到结构未见模板，故「机制可外推到新模板」无数据支撑；② Oracle 单元 U 来自 8 个训练对（`notes.md §0.5`），样本基数极小，第 5 单元已出现跨 seed 漂移；③ 机制证据仅来自 MVP 等深对（`contribution2_final_form.md §2.2 条件 1`）。结论：足以支撑「限定于 MVP 等深对、同分布合成模板的受控干预定位」，**不足以支撑跨模板/跨对因果机制**。 |

**小结**：E0 充分支撑；P1、P2 在「受控合成域 + MVP 对 + 8 模板」边界内部分支撑，且这一边界已被 `final_signoff.md`、`notes.md` 和论文实际措辞（强形式仅限 MVP 对、禁用 across model pairs/causal 等）正确遵守——从**诚实披露**角度看，未越界声明；但从**证据强度**看，边界正是数据本身造成的。

---

## 2. 数据对 P3（主终点）的支撑性判断

主终点（冻结）：封存 test 300 对上 CF-RCT 与 `kd_only` 的**成对 E_CF 差异**，模板/来源簇级 paired bootstrap 95% CI **上界<0**（`configs/protocol.yaml`、`experiment_design_E0_E7.md §0.1`、`phase3_method_decision.yaml`）。

| 维度 | 判定 | 理由 |
|---|---|---|
| 数据是否到位 | **支撑（形式）** | test 300 对已封存、train/val 可用于训练调参，F1–F6 全覆盖，F5 排除翻转分母、F6 单列长度/位置层；与主终点的最低数据契约相符。 |
| 统计效力 | **部分支撑 / 偏弱** | 成对设计下 300 对可提供中等效力（判断），但方向不利：δ 网格三个值的 val joint E_CF（2.7496/1.5968/2.7625）**全部高于** kd_only（0.735）（`phase3_loss_config_v2.2.yaml grid_results`），这是来自 val 的真实信号，提示 CF 方法方向可能为负；P3 探路门已预告 `no_method_gain` 为高概率合法结论（`p3_task_plan.md §1.1`、`p3_resource_estimate.md §5`）。**数据规模不是主要瓶颈，效应方向才是**——但效应方向属实验结果，本报告不预判，仅指出数据不足以「保证」正结果。 |
| 簇级 bootstrap 的独立性风险 | **不支撑（需先修口径）** | 见 §0.1(3)：300 个唯一 source doc 使「以 pair 为簇」退化为逐对 bootstrap，忽略 8 模板的簇内相关 → CI 可能过窄、假阳性上界<0 的风险；若改以 template 为簇则只有 8 簇 → 效力极低、CI 不稳。**这是当前数据对主终点统计效度的最大内部威胁**，且与 `min_training_seeds=3`、Holm 等冻结设计叠加后，多重比较下 8 簇的 bootstrap 几乎不可能给出稳健的 CI 上界<0。建议 PI 在封存测试前明确并冻结聚类单元，必要时补充结构独立的模板以扩大有效簇数。 |
| F5 / F6 处理是否到位 | **部分支撑** | F5 作非翻转负控、排除翻转分母：配置层正确（`flip_denominator_excludes:[F5]`、`must_flip=false`），**到位**。但 `info_gap` 逐对字段为空、控制组仅作独立臂聚合（`notes.md §4`），故 `protocol.md §4.1` 要求的「与无信息控制组的净差」只以聚合 `info_attribution` 形式报告，未逐对入主终点联合报告——**部分到位**。F6 作长度/位置控制：数据自带 `token_count_A/B`、`position_gap`、`length_matched` 字段，可分层报告（39 对 length_mismatch 已记录），**到位**；但需注意 config 只声明排除 F5，而 F6 实际也 `must_flip=false`（不进翻转分母），config 声明与数据 flag 之间存在**文档不一致**，须由工程师在 P3 评测脚本中确认口径一致（本报告不改判据）。 |

**P3 判定**：数据满足 P3 的**最低运行契约**，但在「主终点的统计可信度」上**不支撑无保留放行**——聚类单元口径未定、有效独立模板仅 8 个、F2/F3/F4 空翻转样本污染联合报告指标，三者都可能在真实运行后使 CI/联合指标的解释失效。若要在 P3 得到**可被审稿人接受的主终点结论**，须先解决这三点（见 §4「投稿前必须」）。

---

## 3. 能否发论文：按 `protocol.md §10` 贡献门槛逐层判断

论文现状（`main.tex` / `notes.md`）：贡献(1) 全claim、贡献(2) 强形式（限定 MVP 等深对）已解禁、贡献(3) withheld，定位 boundary/empirical study，`final_signoff.md`、`contribution2_final_form.md` 已据此签 off。

| 贡献层 | §10 门槛 | 当前证据与数据支撑 | 判断（证据强度） |
|---|---|---|---|
| **贡献 1（评价层）**：可复现 gap | 独立测试集 + ≥3 seed 上 gap 可重复且未被强基线消除 | kd 三 seed CI 下界>0、`distortion_present=true`（`final_signoff.md R3`）；commit `458de18` 可复现。**但 gap 限定在 8 个合成模板、MVP 等深对、affine/ridge/kd_only mapper 范围内**。 | **达标（限定范围）**。可写「在这批受控合成模板上发现可重复的 gap」；不能写「普遍现象」。 |
| **贡献 2（机制层）**：localize 到 V 消费 | 受控干预 + held-out 预测价值，≥3 seed，跨样本稳定 | P2 三 seed、repair 0.275–0.350 CI 下界>0、4/5 核心单元稳定、分解残差≈0（`contribution2_final_form.md §1`）。**但 held-out 是同分布 val（同 8 模板）、仅 MVP 对、局部固定 Q 恒等式、Oracle 离线**；三判据非独立（2 信号+1 门槛，见 `notes.md §0.5`）。 | **达标（强形式，附强制条件）**：范围限定 MVP 对、禁 causal/sole cause/across pairs、强制披露 F4/F6 与第 5 单元漂移。数据支撑的是「受控干预下的定位」，非「因果分解」。 |
| **贡献 3（方法层）**：机制约束 Mapper 降低 gap | 主终点成对 E_CF vs kd_only CI 上界<0 + flip/dual≥0.7 + ≥3 seed + Holm + mech>lite + 普通 QA 不退化 + 跨模型(E5)/成本(E6) | **完全缺位**：CF-RCT 未训练、封存测试未跑、主终点未评估、δ 网格三值均不优于 kd_only（`final_signoff.md §3 P3=NO-GO`、`notes.md §0.5`）。 | **withheld（不可写）**。当前数据**不支撑任何方法增益表述**。 |

### 3.1 ≤ 结论：可投稿，但只能定位为边界/实证研究

- **按 §10 与决策树 §8**：当前证据 = 贡献(1) + 贡献(2) 强形式，缺贡献(3)，**必须**定位为 boundary/empirical study；这与 `final_signoff.md §4`、`contribution2_final_form.md §4` 的签 off 一致。就该定位而言，**可以投稿**，前提是诚实披露已记录的全部边界。
- **若目标是方法论文（贡献3 完整）**：当前数据**不可发**——缺主终点、缺跨模型、缺成本证据，且三 δ 负值预警。

### 3.2 对外投稿时审稿人最可能攻击的数据弱点（按攻击强度排序）

1. **合成模板 + 模板多样性不足（最致命）**：全部 520 对为模板生成，仅 8 个基础句式，变量只有人名（8 个）、城市、日期、编号、组字母。审稿人会质疑「gap 是模型对这套人工句式的过拟合，而非 KV 迁移的普遍功能失真」；`main.tex §5.5` 已自认「applicability boundary」，但**自认边界不等于消除质疑**——若投稿到强会议/期刊，这条往往直接决定接收档位。
2. **「未见模板」名不副实**：`template_overlap_train_eval=[]` 是后缀造成的字面空集，结构模板 8 个贯穿所有 split（§0.1(1)）。若论文/回复声称做过 unseen-template 泛化，会被逐行对照 `cf_pairs.jsonl` 击穿。
3. **无真实文档 / 无外部基准**：real=0，未用 HellaSwag/ARC/SQuAD 等（`manifest.json limitations`）；当前 `E_CF` 是自己定义的新指标，缺「新指标与标准 QA 一致性」的外部锚点，审稿人会问「E_CF 下降到底对应什么真实能力」。
4. **单域、单模型对的正向证据**：所有正向 gap/机制证据来自 MVP 1.7B→0.6B 等深对；主验证对 4B→1.7B 是失败边界（`main.tex §5.4`）。审稿人会质疑跨架构/跨尺度外推——恰是 `contribution2_final_form.md` 明令禁用 "across model pairs" 的原因。
5. **Self 锚点本身不完美 + 空翻转样本**：MVP dual_correct 0.617–0.667<0.7（`notes.md §2`），且存在 must_flip=true 却无法翻转的样本（§0.1(2)）。审稿人会质疑 `flip_consistency`/`dual_correct` 的分母与定义，尤其在 P3 若触发 `tradeoff` 分支时。
6. **簇级 bootstrap 口径歧义**（§0.1(3)）：300 唯一 doc 使 pair 级 bootstrap 忽略 8 模板相关；若审稿人要求按模板聚类，只 8 簇使所有 CI 站不住。
7. **引用占位**：KV-Lingo / CacheLink 仍是 `[PLACEHOLDER]`（`notes.md §4`、`main.tex` bibliography），投递前必须核实版本/日期/口径（`protocol.md §9`），否则有学术规范风险。

---

## 4. 最小补足方案（区分「投稿前必须」与「接收后/未来工作」）

> 原则：补足目标不是「把每条都做成真实世界泛化」，而是**让 boundary/empirical study 的证据无可挑剔**，并为方法层留门。以下为设计级建议，不构成对冻结判据的修改；任何新判据须由 PI 另立版本。

### 4.1 投稿前必须（不做则维持现状可投，但对强 venue 风险高）

| 项 | 最小量 | 目的 | 预算/时间量级（判断） |
|---|---|---|---|
| **全量审计空翻转样本** | 脚本遍历 520 对，输出 `candidate_A==candidate_B && must_flip=true`（及两文档答案位等价）的条数与分 split 分布；把逻辑上不可翻转的样本从翻转分母剔除或重新标注 | 修复 §0.1(2) 对 flip/dual 分母的污染；这是**正确性**问题，优先级最高 | 1–2 h 工程 + 重新生成 manifest（数据工程师） |
| **冻结聚类单元口径** | PI 明确 `cluster_unit`：建议对主终点按 **template_family 聚类并在报告中同时给出 pair-level 敏感性分析**；若坚持 pair 级，须在论文论证「8 模板内效应同质」 | 修复 §0.1(3) 的 CI 效度威胁 | 0.5 h 裁决 + 评测脚本相应改动 |
| **补结构未见模板的最小测试子集** | 新增 ≥16 个**句式结构不同**的模板（每类 F1–F6 至少 2 种新句式），在 test 内划出「结构未见」子集（约 60–100 对），不重训、只评测 | 把 E4「未见模板」从字面做成结构真实；也是 §3.2 弱点 2 的唯一硬修复 | 数据构造 0.5–1 天 + 评测 0.5 h |
| **真实文档最小集** | 80–150 对（`gpu_handoff.md §3` 建议下限），人工核验出处与事实扰动、避免实体泄漏；作为**独立域**只评测不训练 | 回应弱点 3/4，给出「合成域结论在真实文本上是否成立」的第一手证据 | 人工构造/核验 2–5 天（视来源） |
| **引用核验** | KV-Lingo / CacheLink 正式版本、日期、口径 | 学术规范 | 0.5 h |
| **补外部锚点实验（最小）** | 在标准 QA（如 HellaSwag/ARC 子集）上报告 Joint 与 kd_only 的常规质量，证明「新指标下降≠常规退化」 | 部分回应弱点 3 | 0.5–1 天（若已有 QA 管线则更快） |

> 说明：若真实资源无法在投稿前完成「真实文档 + 结构未见模板」，**保守选择是维持当前 empirical/boundary 定位投稿并在 limitation 中明确缺少这两项**（现状已如此），而不是硬塞弱证据。

### 4.2 应加入的实验（把缺口映射到 E4–E6）

- **E4（泛化，投稿前强烈建议至少做「结构未见模板」臂）**：分组 E_CF + 95% CI，分别报告 (a) 同域未见实体、(b) 结构未见模板、(c) 真实文档扩展。当前 (b)(c) 完全缺；(a) 因实体名仅 8 个且 train/test 后缀隔离，实质是「未见实体名」而非未见实体结构。
- **E5（跨结构/尺度）**：非等深 4B→1.7B 已有但为失败边界；补一组**成功方向**的非等深证据（或明确报告「无跨对正向证据」并把贡献(2) 永久限定在 MVP 对）。这是解禁贡献(3)「跨模型」措辞的必要条件（`p3_task_plan.md §6.4`）。
- **E6（成本）**：实测 Joint 端到端 TTFT/延迟/显存 vs 学生重 Prefill；这是解禁贡献(3)「without target-side re-prefill」系统侧措辞的必要条件。**投稿前非必需**（贡献3 withheld），接收后/方法论文必需。
- **E3/P3 方法主实验**：仅在 δ 网格负值预警被排除、且聚类口径与空翻转样本修复后启动；门控按 `p3_task_plan.md`（探路 2×3 seed ≈2.5–3 h，全量 9 run ≈5–7 h GPU 串行）。

### 4.3 接收后 / 未来工作（不阻断当前投稿）

- 多域真实文档（新闻、百科、代码等）扩展至 200+ 对；多模型家族（非 Qwen3）；1K–4K 长上下文（`pairs.yaml long_context=false` 当前明确不做）。
- 把 E_CF 与外部标准 QA 指标的相关性做成方法论文级的效度论证。
- 公开数据构造脚本与外部可复现基准；E7 hidden-state 候补分支（只在稳定超过直接 KV 映射时继续）。
- 贡献(3) 完整措辞的四条件（`p3_task_plan.md §6.4`：主终点 + E5 + E6 + 统计/代码/叙事）全部满足后再升级方法论文。

---

## 5. 最终判定

> **当前数据：可支撑「任务 P0/E0（充分）+ P1（部分）+ P2（部分）」；对 P3 仅满足最低运行契约、主终点统计效度不支撑无保留放行；可以「边界/实证研究」定位投稿（贡献1 + 贡献2 强形式），不可发方法论文（贡献3 withheld）。**

具体边界：

1. **可支撑**：受控合成域内、MVP 等深对上、8 类模板的「gap 存在性评价层发现」与「V 消费路径的受控干预定位」——前提是论文维持已约定的范围限定、禁用词表、不利结果披露与不确定性声明（`final_signoff.md §4`、`contribution2_final_form.md §2.2`）。
2. **不足以支撑（缺什么）**：
   - 跨结构/跨家族/真实世界的**普遍失真**主张（缺结构未见模板、缺真实文档、缺外部基准）；
   - **P3 主终点的稳健 CI 上界<0**（缺明确的簇级聚类口径、有效独立模板仅 8 个、空翻转样本污染联合指标）；
   - **贡献(3) 方法增益的全部措辞**（缺主终点评估、缺 E5 正向、缺 E6 成本，且 δ 网格三值均为负向预警）。
3. **投稿前最低动作**：全量审计并修复空翻转样本（§0.1(2)）、冻结聚类单元口径（§0.1(3)）、至少补一个「结构未见模板」评测臂、完成引用核验；若后两项来不及，维持 boundary/empirical 定位并在 limitation 明确披露（现状已具备此退路）。
4. **策略选项（属真实 PI 拍板，本报告只列不决）**：(A) 维持 boundary/empirical 定位尽快投稿；(B) 先补结构未见模板 + 真实文档最小集并修复数据质量，再以更强实证版本投稿；(C) 待 P3 主终点结果决定升级方法论文——但 δ 网格负值使 (C) 成功概率不高，且须先解决 §2 的统计口径问题。

**签署：科学家（数据就绪性复核 · 2026-11-23）。本复核未修改任何数据、判据、论文、代码或运行产物。**

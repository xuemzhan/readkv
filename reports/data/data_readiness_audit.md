# 数据就绪性独立审计报告（P0–P3 / 投稿充分性）

- 审计角色：数据工程师（独立复核，不沿用 PI 摘要结论）
- 审计日期：2026-11-23
- 审计对象：
  - `data/tasks/cf_pairs.jsonl`、`data/tasks/manifest.json`
  - `src/readkv/data/build_cf_pairs.py`、`configs/protocol.yaml`、`configs/pairs.yaml`
  - `docs/protocol.md`（§4.3/§4.4/§5）、`docs/gpu_handoff.md` §3
  - `reports/runs/**/config.json`（22 个 run 配置）
- 审计方式：独立重算哈希/行数/schema、独立重建数据集、独立做跨 split 重叠与模板骨架检查、独立统计 22 个 run 的实际 split 与规模。
- 写入边界：仅写本报告；**未修改** `cf_pairs.jsonl`、`manifest.json`、任何冻结判据或已有运行产物。

---

## 0. 结论摘要（先给判定）

| 维度 | 判定 |
|---|---|
| 数据完整性与可复现性 | **通过**：manifest 哈希/行数/质量门与文件逐字节一致；seed=0 重建字节级一致 |
| 泄漏与隔离 | **不通过**：存在跨 split 完全相同的文档（train↔test）、实体全共享、模板骨架跨 split 完全相同（"未见模板"仅名称后缀）；18 个不可翻转的退化对污染 flip 分母 |
| 统计设计充分性 | **不通过**：cluster 退化为逐对唯一（300 簇），仅 8 个模板结构，cluster bootstrap 会低估方差、CI 偏窄 |
| 支撑 P0–P3 | P0 **可支撑**；P1 **部分支撑（可跑但科学证据弱）**；P2 **部分支撑（规模过小）**；P3 **数据存在但从未运行主终点，且数据本身有污染** |
| 能否发论文（数据角度） | **否（投稿前不达标）**。当前资产是"合成接线/探针数据集"，不是可发表级基准 |

---

## 1. 数据完整性与可复现性

### 1.1 manifest 与实际文件逐项核对（全部一致）

| 项 | manifest 声明 | 独立实测 | 一致 |
|---|---|---|---|
| sha256 | `6058fd6d46c4ca10562f48f3446bb8ee396ad5ca8f582183b21fdcb7618d1887` | 同 | ✅ |
| 文件大小 | 439734 B | 439734 B | ✅ |
| 行数 | 520 | 520 | ✅ |
| sizes | probe40/train120/val60/test300/real0 | 完全一致 | ✅ |
| by_slice | F1 130/F2 67/F3 130/F4 67/F5 63/F6 63 | 完全一致 | ✅ |
| length_mismatch | 39 | 39 | ✅ |
| f5_negative_controls | 63 | 63 | ✅ |
| flip_denominator | 394 | 394 | ✅ |
| template_overlap_train_eval | `[]` | `[]` | ✅ |
| quality_gate | pass | 按现有代码逻辑重算 pass | ✅ |

PI 摘要中列出的所有计数均经独立复核成立。

### 1.2 确定性重建（通过）

用 `build_cf_pairs(seed=0)` 重建并写到 `/tmp/opencode/cf_pairs_rebuild.jsonl`：

- 重建文件 sha256 = 原文件 sha256 = `6058fd6d…d1887`
- 520 行逐行比对，差异行数 = 0
- 结论：**确定性可复现，seed=0 可完全重建**。

### 1.3 schema 字段检查

- 29 个字段在 520 条记录中**全部存在、无缺失**；无完全重复记录。
- 派生字段 `token_count_A/B` 与 `token_count_A` / `token_count_B` 在所有记录中一致（0 处不符）。
- `must_flip`、`length_matched`、`swap_candidates` 均为布尔且与 slice 语义一致。
- **异常（构造缺陷，非 schema 缺失）**：18 条 `must_flip=True` 记录出现 `candidate_A == candidate_B`（见 §2.4），标签 `correct_A`/`correct_B` 仍分别为 A/B，语义上不可判定。

### 1.4 manifest 溯源规范缺口

- manifest **无 license / source / 来源 URL / 生成脚本 commit hash / manifest 自身哈希** 字段；`docs/data/` 不存在，无数据卡。
- 因 `real=0`、数据全为模板合成，未违反"外部数据必须记录来源/许可"的硬约束；但缺少合成方法学数据卡，不满足可审计数据资产的标准。

---

## 2. 泄漏与隔离

### 2.1 名义隔离（通过）

- `template_overlap_train_eval`（train vs val+test）独立重算为空；train 16 模板族（8 基础族 × A/B 后缀），val/test 各 8 族（C/D 后缀）。
- `cluster`、`source_doc_id`、`pair_id` 全局均唯一（520/520）；test 300 个唯一 source_doc_id / 300 个唯一 cluster。
- `length_mismatch`（39）全部落在 **F5**（因同义改写替换不同长度的 role 词，如 负责人→技术负责人）；按 split 分布 probe2/train9/val4/test24，**可分层报告**。F5 为负控且不计入 flip 分母，对主指标影响有限。

### 2.2 模板内容隔离 —— 名义通过、实质失败（重要）

`build_cf_pairs.py` 中 `SPLIT_VARIANTS` 只把 `t.family` 改为带后缀的族名（`t.family + "-A/B/C/D"`），而 `query_fmt` / `context_fmt` 原样复用。实体槽位抽空后的骨架比对结果：

| 基础族 | train 骨架 | test 骨架 | 共有骨架 |
|---|---|---|---|
| T-F1-person | 2 | 2 | **2（100%）** |
| T-F3-direction | 1 | 1 | **1（100%）** |
| T-F5-paraphrase | 2 | 2 | **2（100%）** |

结论：**train/test 的模板文本结构完全相同**。`template_overlap_train_eval=[]` 只是比较了带后缀的族名字符串，并不代表真正的模板隔离。`docs/protocol.md` §4.4 / §5（E4）与 `docs/gpu_handoff.md` §3 要求的"未见模板子集 / ≥24 独立模板或主题簇"在实质层面未满足。

### 2.3 实体与文档级隔离 —— 不通过（真实泄漏）

- **实体全共享**：8 个姓名实体（张三…郑十）在 probe/train/val/test 中**全部出现**（train∩test = 全部 8 个）。无按实体隔离。
- **跨 split 完全相同文档**：独立扫描发现 7 组 `context_A` 和 8 组 `context_B` 在不同 split 逐字相同，其中涉及 train↔test 的：
  - `train-F3-0014` 与 `test-F3-0015`：context_A、context_B **均完全相同**（仅候选顺序与 correct 标签不同）——**一整对从 train 泄漏到 test**；
  - `train-F1-0096` ≡ `test-F5-0276`（context_A，跨切片）；
  - `train-F2-0067` ≡ `test-F2-0105`、`train-F2-0114` ≡ `test-F2-0209`（context_B）。
  - 其余涉及 probe/val↔test 的重复见审计脚本输出；合计至少 15 组。
- 成因：NAMES/PROJECTS/CITIES/DATES/NUMBERS 池仅 8 个取值且在全部 split 复用，520 对大规模抽样必然碰撞。这违反"按实体/来源/模板簇隔离"的硬约束，并使 test 主终点被训练集污染。

### 2.4 退化对（构造缺陷）—— 不通过

候选被独立抽取而未强制相异（`_fact_slots` 中 `name_a`/`name_b` 独立 `choice`，F4 的 `name_a`/`name_b` 未走 `_distinct`），导致：

| 指标 | 数量 | 说明 |
|---|---|---|
| `candidate_A == candidate_B`（全库） | 81 | 其中 F5 63 条为设计使然（correct="A/B"） |
| **must_flip 且候选相同的退化对** | **18** | F2 6 / F3 5 / F4 7；按 split：probe2/train5/val4/**test7** |
| 其中 `context_A == context_B` | 12 | 文档对无任何差异，例如 `test-F4-0067`（张三→张三）、`test-F3-0074`（赵六向赵六汇报） |

这些对 `must_flip=True`、进入 flip 分母，但**物理上不可能翻转**，且 correct_A=A / correct_B=B 与相同候选相互矛盾。名义 flip 分母 394 中至少 18 条无效（若剔除则 376）。这会系统性污染 flip-consistency、dual_correct 与 E_CF 的成对比较。

### 2.5 F5 负控与 flip 分母语义

- F5：63 条，`must_flip=False`、`correct_A=correct_B="A/B"`、`candidate_A==candidate_B` —— **正确标记为非翻转负控，未计入 flip 分母** ✅。
- flip 分母 394 = F1(130)+F2(67)+F3(130)+F4(67)，F6(63) 同样被排除（代码 `SEMANTIC_SLICES=F1–F4`）。
- **口径不一致**：`configs/protocol.yaml` 写 `flip_denominator_excludes: [F5]`，按该配置 F6 应计入、分母应为 457。代码实现与冻结配置口径冲突，需 PI 裁决并在报告中明示 F6 的排除理由。

---

## 3. 统计设计充分性

### 3.1 cluster bootstrap 的簇定义失效（高风险）

- `configs/protocol.yaml`: `bootstrap: cluster_paired`, `cluster_unit: "template_or_source_doc"`, `n_resamples` 10000（部分 run 用 2000）。
- 实际 `cluster = f"{split}-{template.family}-{pair_id[-3:]}"` 对每条记录唯一（520/520；test 300/300）。`source_doc_id = f"{pair_id}-doc"` 也逐对唯一。
- 因此"按模板/来源文档的簇级 bootstrap"**退化为逐对 i.i.d. bootstrap**：test 名义 300 簇，但真正独立的模板结构只有 8 个。同一模板内的实体/句式/位置高度相关，pair 级重采样忽略簇内相关 → **CI 系统性偏窄、显著性被夸大**。这是 PI 摘要所担心风险的独立证实。

### 3.2 未见模板子集

- 名义上 test 后缀族 D 不在 train（A/B）、val（C）中；实质模板文本与 train 完全一致（§2.2）。**不存在真正的未见模板子集**，无法支撑 E4"是否仅记住合成模板"的检验。

### 3.3 切片分布与规模

| 项 | 现状 | 指南要求 | 判定 |
|---|---|---|---|
| test 总量 | 300 | 240–360 | ✅ 数量达标 |
| test 独立模板/主题簇 | 8（名义后缀族，实质 6 基础结构） | ≥24 | ❌ |
| 未见模板子集 | 无（仅后缀） | 必须有 | ❌ |
| 真实文档 | 0 | 80–150 | ❌ |
| 候选顺序随机交换 | 有 `swap_candidates` 字段 | 必须 | ✅ |
| F5 排除分母 | 是 | 必须 | ✅（但 F6 口径待裁决） |
| ≥3 训练种子 | P1 有 seed 0/1/2 | 必须 | ✅（仅 P1；P2 为 3 个单种子 run） |

切片在 test 内分布：F1/F3 各约 1/4，F2/F4/F5/F6 各约 1/10；虽 six slices 均覆盖，但 F5/F6 每 split 数偏少（如 val F5 仅 8 条），小切片分层后统计功效不足。

---

## 4. 逐阶段数据支撑判定（P0–P3）

| 阶段 | 实际使用的数据 | 数据层判定 | 理由 |
|---|---|---|---|
| **P0 / E0 实现门** | `n_probes=40`（probe split）；identity/KL/EM 容差 | **✅ 支撑** | E0 门为测量误差上限，不需要反事实标签语义；probe 40 对存在且确定可重建。注：probe 含 2 条退化对，但对 identity/round-trip 判据影响很小。 |
| **P1 检出失真（反事实基准）** | train120/val60，3 seeds；`eval_splits=["val"]` | **⚠️ 部分支撑** | 数据机械上可跑，且确已跑出信号；但 val 仅有 8 基础模板、4 条退化对、与 test 的文档泄漏、length_mismatch 未分层、模板内容无隔离。只支持"合成域内信号检测"，不足以支撑可发表的泛化/主结论。3 个 delta_lock run 实际只用 train=60（`n_train_pairs=60`），与 manifest 声明的 120 不一致，需注意可复现性。 |
| **P2 机制（held-out）** | `n_select_pairs=8`, `n_heldout_pairs=40`, candidate forward=400；val 派生 | **⚠️ 部分支撑** | 8 条选择对、40 条 held-out 规模过小；配置 `quality_pass_scope="data_quality_gate_only"`，"通过"仅指数据质量门，不构成机制科学结论的放行。held-out 与 train 间存在文档泄漏（§2.3），可能抬高机制预测的表观成绩。 |
| **P3 封存 test 主终点** | test 300 对（数据存在且封存） | **❌ 现阶段不支撑** | 22 个 run 配置中 **P0=3 / P1=15 / P2=4，P3=0**；`eval_splits` 全部为 `["val"]` 或无，**没有任何 run 在 test 上评测过**。主终点从未产生结果。即便现在跑，test 含 7 条退化对、至少 4 条 train↔test 泄漏对、仅 8 个模板结构、0 真实文档 → CI 偏窄且数据被污染。 |

补充：22 个 run 中 16 个用标准 sizes，3 个 delta_lock run 用 train=60，3 个 P0 无 sizes；`p1_gpu_main_*` 的 `model_pair` 元数据写 `1.7b-to-0.6b` 但实际 teacher=4B/student=1.7B，属元数据漂移（不影响数据本身，但影响溯源）。

---

## 5. 能否发论文（数据角度判定与最小补足清单）

### 5.1 明确判定

**不能发（投稿前数据不达标）。** 当前 `cf_pairs.jsonl` 是一个确定性、可复现、schema 干净的**合成接线/探针数据集**，适合 P0–P2 的内部信号核验；但它不具备作为论文主终点基准的四项必要条件：

1. 封存 test 主终点从未运行（无结果可发表）；
2. 模板/实体隔离为名义隔离，缺乏真实 OOD / 未见模板证据；
3. 真实文档 = 0，无外部效度；
4. 18 条不可翻转对 + 跨 split 完全相同的文档污染指标；cluster 定义退化使 CI 偏窄。

若强行投稿，最可能的致命审稿意见是"benchmark 构造存在泄漏与退化样本、bootstrap 簇单位错误、无真实数据、主结果未在封存集上给出"。

### 5.2 投稿前必须（MUST）

| # | 补足项 | 目标状态 | 责任方 |
|---|---|---|---|
| M1 | 修复生成器：`_fact_slots` 中 `name_a`/`name_b`、F4 的 `name_a`/`name_b` 强制 `_distinct` | 退化对（must_flip 且候选相同）= 0 | 工程师（数据管线），PI 确认后重建 |
| M2 | 跨 split 去重：对归一化 context 做哈希，确保 train/val/test 无完全相同文档 | 跨 split context 泄漏 = 0 | 数据工程 |
| M3 | 真实隔离：split 使用不相交的实体池（姓名/项目/城市）；test 使用**全新 query_fmt/context_fmt**（≥24 独立模板/主题簇） | 模板骨架 overlap = 0；实体 overlap = 0；≥24 族 | 数据工程 + 科学家设计 |
| M4 | 真实文档扩展 80–150 对，人工核验出处/编辑类型/许可 | `real` split 非空，含 source/license/hash/date/抽检字段 | 数据工程（需合规评估） |
| M5 | 重建后更新 manifest：加入 license/source、生成脚本 commit hash、manifest 自身哈希；新增 `docs/data/` 数据卡；length_mismatch 分层报告 | 可审计数据资产 | 数据工程 |
| M6 | 修正 bootstrap 簇定义：按模板族（≥24 簇）而非逐对重采样，预注册后重算 CI | CI 不再因簇过细而偏窄 | 科学家 + reviewer |
| M7 | PI 裁决 flip_denominator 口径（F6 是否计入），统一代码与 `configs/protocol.yaml` | 口径一致、分母可解释 | PI |
| M8 | 在修复后的封存 test 上运行 P3 主终点（≥3 seeds，预注册，禁止按结果调参） | 产出 `scores.jsonl` 与主终点结果 | 工程师 |
| M9 | 用修复后数据重跑 P0–P2（至少 P1 三 seed、P2 机制） | 结论基于干净数据 | 工程师 |

注意：M1–M5 会改变 `cf_pairs.jsonl` 的内容与哈希。按审计边界，本报告**不执行**这些改动；应由 PI 授权后、工程师/数据工程在数据目录下重建并同步更新 manifest（禁止原地手改既有文件而不重建哈希）。

### 5.3 未来工作（NICE-TO-HAVE，不阻断投稿）

- 接入公开真实基准（HellaSwag / ARC / SQuAD 类）的合规子集，作为跨域外部验证；
- 不等深模型对（4B→1.7B、8B→0.6B）在封存 test 上的一次性核验；
- 长上下文 / 位置压力子集；
- 更大规模真实文档的半自动构造与人工抽检流水线。

### 5.4 工作量与时间量级估计（单数据工程师 + GPU 机）

| 工作包 | 人日 | 备注 |
|---|---|---|
| M1+M2 生成器修复、重建、哈希/质量门复验 | 0.5–1 | 纯本地，快 |
| M3 ≥24 新模板设计 + 不相交实体池 + 去重 | 2–3 | 需科学家共同设计模板语义 |
| M5 manifest/数据卡规范化 | 0.5–1 | |
| M6+M7 统计口径修正与预注册 | 1–2 | 需 PI/reviewer 裁决 |
| 修复后重跑 P0–P2（机器时间 + 分析） | 1–2 人日 + GPU 数小时 | |
| M8 P3 主终点（预注册 + 3 seeds + bootstrap） | 2–4 人日 + GPU 数小时 | |
| **小计（不含真实文档）** | **约 7–11 人日（≈1.5–2.5 人周）** | |
| M4 真实文档 80–150（采集 2–3 + 人工核验 3–6 + 许可评估 1） | **5–10 人日** | 视来源可得性，风险最高、建议尽早启动 |

- **投稿前总量级**：若保留真实文档要求，约 **12–20 人日（≈2.5–4 人周）**；若 PI 决定降级定位为"受限合成域研究"并明示无外部效度，则约 **7–11 人日**可完成数据+统计侧补足。
- GPU 机时相对充裕；关键路径是 **M3 模板设计** 与 **M4 真实文档/许可**（后者可能成为进度瓶颈，建议立即启动许可预评估）。

---

## 6. 合规声明

- 本次审计**只写** `reports/data/data_readiness_audit.md`；未修改 `data/tasks/cf_pairs.jsonl`、`data/tasks/manifest.json`、`configs/**`、`docs/protocol.md` 或 `reports/runs/**`。
- 所有数字均由独立脚本现场重算，未采用 PI 摘要中的结论作为证据。
- 审计报告中所有"问题"均给出可复核证据（记录 ID / 字段名 / 计数），建议修复动作交由 PI 授权后执行；涉及真实数据的许可风险按硬约束须上报 PI 裁决后方可进入主实验。

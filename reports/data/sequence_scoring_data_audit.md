# 完整候选答案评分 · CPU 数据审计报告

> 执行角色：数据工程师 · 日期：**2026-11-24**（CPU only，未跑 GPU）
> 治理依据：`configs/prereg/full_candidate_scoring_v2.8.yaml`（冻结）、`refine-logs/GPU_SEQUENCE_SCORING_PLAN.md`（方案）、`docs/decisions/full_candidate_scoring_ruling.md`
> 边界：只读既有 `data/audit_2x2/{legacy,fixed}/**`；新建 `data/audit_2x2/sequence/**` 与本报告；**不改**既有数据/`data/tasks/**`/代码/冻结判据/论文/`reports/runs/**`。
> 一句话结论：既有 2×2 数据准备全部验收通过；A00/A11 六格索引已建；用当前私有 tokenizer（Qwen3-0.6B）按固定边界独立复算，主分析分母 **旧版 42/42/41、修复版 46/46/46 与方案完全一致**；token 边界不一致 **0**，候选互为前缀仅出现在“候选文本相同”的样本上。

---

## 1. 既有 2×2 数据准备复述与核验（任务 1）

生成器版本：legacy = `458de18`（旧语料，含历史缺陷）、fixed = `efc3ba3`（修复版）。导出时 sizes = `{probe:0, train:120, val:60, test:0, real:0}`，各 split 独立 RNG `Random(f"{seed}-{split}")`。样本身份：`sample_hash = sha256(query|context_A|context_B|candidate_A|candidate_B)`（= 归档 Joint 行 `cache_hash`）；`sample_id = "<version_tag>|<sample_hash[:16]>"`。

对本审计**实际读取**的全部 12 个文件逐字节复算（LF 行数、`\r\n` 计数、逐行 `sample_hash`/`sample_id` 一致性）：

| 版本/split/seed | 路径 | LF 行数 | SHA-256（实测，LF） | sample_hash 校验 | sample_id 校验 |
|---|---|---|---|---|---|
| legacy train s0 | `data/audit_2x2/legacy/train_seed0.jsonl` | 120 | `81da04a041a4e7757caa02e502c10ca9a9236d7f98da5419fb226ca95a02b00a` | 120/120 | 120/120 |
| legacy train s1 | `data/audit_2x2/legacy/train_seed1.jsonl` | 120 | `7385245c6b2db4e4f78abc837aaa31817cd7025eaa23dc099b2dc92c9f4a793e` | 120/120 | 120/120 |
| legacy train s2 | `data/audit_2x2/legacy/train_seed2.jsonl` | 120 | `3ad49eea2a41ff0e0ffd516b0fb1b8dc5282dce9a8336d7f371bf28adc97bb11` | 120/120 | 120/120 |
| legacy val s0 | `data/audit_2x2/legacy/val_seed0.jsonl` | 60 | `24a5077bec11657c70d8eeddeed6fbe4871253d6d141daf16989903d1ebccaaa` | 60/60 | 60/60 |
| legacy val s1 | `data/audit_2x2/legacy/val_seed1.jsonl` | 60 | `6f5c2b553832bdb2e03dd56ab39a7e6b2a6e4b5ec726448692f9fae1ebb849ff` | 60/60 | 60/60 |
| legacy val s2 | `data/audit_2x2/legacy/val_seed2.jsonl` | 60 | `df24f7cf9d6fae8ce2e8a7af9b2a68aefe040a447534d30119aed99cd7f0c759` | 60/60 | 60/60 |
| fixed train s0 | `data/audit_2x2/fixed/train_seed0.jsonl` | 120 | `9b03522746825f3fe0794c7f62ec7b1fb430f46734bb175b90a55a788d91e953` | 120/120 | 120/120 |
| fixed train s1 | `data/audit_2x2/fixed/train_seed1.jsonl` | 120 | `024a69e9f35c777ad1030227eed37ef8f3dd43a82fb0a905a569e9150a37633f` | 120/120 | 120/120 |
| fixed train s2 | `data/audit_2x2/fixed/train_seed2.jsonl` | 120 | `53258777ab214fb9226b85389673672c9c4b1b17c8cb9d07cf1a97beddcf3e6e` | 120/120 | 120/120 |
| fixed val s0 | `data/audit_2x2/fixed/val_seed0.jsonl` | 60 | `19e9839e4e27b584c53d30242411ab14a659ac5cc487849b205928f5caa3c595` | 60/60 | 60/60 |
| fixed val s1 | `data/audit_2x2/fixed/val_seed1.jsonl` | 60 | `b4f9587fc7e28a780b923c7e4a3e1aec96ddf6cde3c63a50fd0cc4b8423e7921` | 60/60 | 60/60 |
| fixed val s2 | `data/audit_2x2/fixed/val_seed2.jsonl` | 60 | `5633a8bf052f33c44ec694704baef64c96898a1548fc313abc2fb537a5e5b475` | 60/60 | 60/60 |

- 全部 12 文件：`\r\n` 计数 = 0（规范 LF）；行数 train=120 / val=60；SHA-256 与 `data/audit_2x2/manifest.json`、各 `_index.json` 登记值**逐字一致**；每行 `sample_hash`/`sample_id` 均按定义复算通过（命中率 100%）。
- **封存 test 未读取**：本审计只打开上述 train/val 12 个文件（train 仅用于本任务 1 核验，不进入任何评分）；未打开 `data/tasks/test*` 或任何 test split。

## 2. 完整候选评分样本索引（任务 2）

按方案固定边界：`query` 与候选**分别** tokenize，两侧均 `add_special_tokens=False`；候选 token 序列 = `encode(candidate, add_special_tokens=False)`；不追加 EOS。主评分对象 = `query_token_ids + candidate_token_ids`。

索引文件（每格每 seed 一个，各 60 行；A00 = legacy/legacy，A11 = fixed/fixed）：

| 文件 | 行数 | SHA-256 |
|---|---|---|
| `data/audit_2x2/sequence/A00_seed0.jsonl` | 60 | `31fdb0fef597b9c1b46baa903a35b4b996c44c16bdddf546b6576c4e7045638c` |
| `data/audit_2x2/sequence/A00_seed1.jsonl` | 60 | `9cb21930e4316ea0c481547b82a4aecb576236ce929d47506e26ae95d94e9d1d` |
| `data/audit_2x2/sequence/A00_seed2.jsonl` | 60 | `2b1e892d9af41c08ef0c6e3d43860955f1c915e10517c260b6668648f70b85d3` |
| `data/audit_2x2/sequence/A11_seed0.jsonl` | 60 | `57d01382ead6dadca5bdfa4684277826cf6209b3c6c2daf2f991f0e5f40d8c05` |
| `data/audit_2x2/sequence/A11_seed1.jsonl` | 60 | `6afce4e046bfbb700be6bdcd4bcedf1f002796361929944511e0f93d76f73a8f` |
| `data/audit_2x2/sequence/A11_seed2.jsonl` | 60 | `3b7de1b592300372a65e2140140f727121217f509265544a395150e744fa0835` |

每条记录字段：
- 身份/源：`cell`、`source_version`、`split`、`seed`、`pair_id`、`sample_hash`、`sample_id`、`slice_id`、`template_family`、`cluster`。
- 文本：`query`、`context_A`、`context_B`、`candidate_A`、`candidate_B`、`correct_A`、`correct_B`。
- token（固定边界，Qwen3-0.6B 私有 tokenizer）：`query_token_ids`/`query_token_count`、`candidate_A_token_ids`/`candidate_A_token_count`、`candidate_B_token_ids`/`candidate_B_token_count`。
- 判定布尔：`candidate_texts_differ`（候选文本是否不同）、`candidate_token_seqs_differ`、`is_f1_f4`、`gold_labels_swapped`、`f1_f4_gold_swapped`（是否 F1–F4 且金标签在 A/B 间交换）、`primary_analysis`（主分析分母成员）。
- 边界审计布尔：`boundary_consistent_A/B/pair`、`candidates_identical`、`candidates_prefix_related`、`candidates_prefix_related_distinct_only`。

> 提醒工程师：源 JSONL 自带的 `token_count_A/B` 是 `_tokens(context)` 的**文档长度代理（非空白字符数）**，不是候选 token 数；候选 token 数一律用索引中的 `candidate_{A,B}_token_count`。

## 3. 主分析分母独立核对（任务 3）

私有 tokenizer 物理路径 `/root/.cache/modelscope/models/Qwen--Qwen3-0.6B/snapshots/master`（`Qwen2Tokenizer`，fast，`add_bos_token=false`，`bos_token=null`）；关键文件 SHA-256：`tokenizer.json=aeb13307…4492dae4`、`tokenizer_config.json=d5d09f07…acd8101`、`vocab.json=ca10d7e9…a894a…`（完整值见 manifest）。主分析定义：F1–F4 中候选文本不同 **且** 两侧金标签在 A/B 间交换。

| 格 | seed | 全部对 | F5 | F6 | 相同候选 | flip 分母(排除 F5+F6) | F1–F4 金标签交换 | F1–F4 文本不同 | **主分析分母（文本/token 两口径一致）** | 主分析模板族数 |
|---|---|---|---|---|---|---|---|---|---|---|
| A00 旧 | 0 | 60 | 7 | 7 | 11 | 46 | 46 | 42 | **42** | 6 |
| A00 旧 | 1 | 60 | 7 | 7 | 11 | 46 | 46 | 42 | **42** | 6 |
| A00 旧 | 2 | 60 | 7 | 7 | 12 | 46 | 46 | 41 | **41** | 6 |
| A11 修复 | 0 | 60 | 7 | 7 | 7 | 46 | 46 | 46 | **46** | 6 |
| A11 修复 | 1 | 60 | 7 | 7 | 7 | 46 | 46 | 46 | **46** | 6 |
| A11 修复 | 2 | 60 | 7 | 7 | 7 | 46 | 46 | 46 | **46** | 6 |

- **与方案完全一致**：旧版 42/42/41、修复版 46/46/46；每格主分析 6 个 template_family（<24，按 v2.8 标 exploratory）。
- 文本口径与 token 口径在全部 6 格给出**相同**分母（`f1_f4_primary_tok_level` 与 `f1_f4_primary` 相等）：不存在“文本不同但 token 序列相同”的候选对。
- 差异来源（如实说明，非凑数）：旧版每个 val 的 F1–F4 共 46 对，金标签 46/46 均交换；但旧生成器对 F2/F3/F4 的候选名未强制相异（`_fact_slots` 独立抽 `name_a`/`name_b`），造成 4/4/5 个 F1–F4 对 `candidate_A == candidate_B`，按“候选文本不同”剔除后剩 42/42/41；修复版 `efc3ba3` 对全部切片强制 `_distinct`，46/46/46 全部合格。这与既有诊断（`data/audit_2x2/diagnostics.json`、`reports/data/audit_2x2_data_prep.md` §5）中旧版 must_flip 退化对的记录一致。
- F5=7、F6=7 在每格每 seed 恒定；“相同候选”= F5 的 7 个 + 旧版 F1–F4 退化对（旧 s0/s1 各 4、s2 为 5）；F5/F6 与相同候选均**不计入**主分析分母（F5 负控制不计“必须翻转”分母，沿用 v2.3 口径）。

## 4. token 边界检查（任务 4）

对每个候选比较 `encode(query + candidate, add_special_tokens=False)` 与 `encode(query)+encode(candidate)`（两段分别 `add_special_tokens=False` 后拼接）：

| 格 | seed | 边界不一致候选数 | 边界不一致对数 | 候选互为前缀对数（含文本相同） | 其中候选文本不同但互为前缀 | 候选文本相同对数 |
|---|---|---|---|---|---|---|
| A00 | 0 | 0 | 0 | 11 | 0 | 11 |
| A00 | 1 | 0 | 0 | 11 | 0 | 11 |
| A00 | 2 | 0 | 0 | 12 | 0 | 12 |
| A11 | 0 | 0 | 0 | 7 | 0 | 7 |
| A11 | 1 | 0 | 0 | 7 | 0 | 7 |
| A11 | 2 | 0 | 0 | 7 | 0 | 7 |

- **`encode(query+candidate)` 与两段拼接不一致的样本数 = 0**（全部 6 格、每格 60 对 × 2 候选）：该私有 tokenizer 在“问号句 + 中文候选/政策词/两位数字”边界上不发生跨边界合并，固定边界与整串编码等价。
- **候选互为前缀的样本数**：11/11/12（旧）、7/7/7（修复）。逐条核查发现**全部来自 `candidate_A == candidate_B`（token 序列完全相同，互为平凡前缀）**；候选文本不同的对中互为前缀数 = 0（字符级与 token 级均 0）。
- 给工程师：按当前 tokenizer 与这批 val，边界不一致不构成风险，主口径可直接用 `query_token_ids + candidate_token_ids`；若需要满足 v2.8 §4 `token_boundary.sensitivity`，仍可用“同一新答案分隔符”做两读数边界敏感性，但本审计未发现必须触发的边界异常。互为前缀仅出现在相同候选（F5/退化对），这些样本本就不在主分析分母内。

## 5. manifest 与产物位置（任务 5）

- manifest：`data/audit_2x2/sequence/manifest.json`（含 6 个索引文件路径/sha256/行数、每格分母、源 val sha256、生成器 commit 458de18/efc3ba3、本脚本 `build_sequence_index.py` 的 sha256 `86d7aa81…40f`、生成脚本运行所在 repo HEAD `a05e9b355d0f338d79fe0f92356fbb61d6e66c32`、tokenizer 指纹、审计日期 2026-11-24）。
- 复现脚本：`data/audit_2x2/sequence/build_sequence_index.py`（`.venv/bin/python data/audit_2x2/sequence/build_sequence_index.py` 可重建全部索引与 manifest；纯 CPU）。
- 本报告：`reports/data/sequence_scoring_data_audit.md`。
- HEAD `a05e9b3` 为冻结基线；v2.8 配置与裁决文档为本次新增的未跟踪文件（已在任何 `audit_seq_*` GPU run 前冻结），本审计未改动它们。

## 6. 口径与范围声明（任务 6）

- **old/repaired 是两套验证样本**：seed0 的 legacy/fixed val 共享 60 个相同 `pair_id` 字符串，但 **sample_hash 60/60 全部不同**（0 碰撞）。关联样本必须用 `version_tag + sample_hash`，不得仅用 `pair_id`。
- **不混算**：同一格内 first 与 full（及 length-normalized）三种读数必须使用**同一批**样本；A00 只用 legacy val、A11 只用 fixed val，跨版本不混。
- **无封存 test**：未读取、未评测；无 P2/P3 重启；无 A01/A10（本轮不做）；本实验不重算主终点、不恢复贡献、不构成方法贡献。
- **未伪造**：所有 sha256/计数/token 序列均由脚本对实际字节与本地 tokenizer 计算；token 边界异常见 §4 如实披露（为 0）。

---

## 7. 交付回填

- 各格主分析分母：A00 旧版 **42 / 42 / 41**；A11 修复版 **46 / 46 / 46**（与方案预期一致）。
- token 边界异常计数：边界不一致候选 **0**（全部格）；候选互为前缀 **11/11/12（旧）、7/7/7（修复）**，且全部因候选文本相同，候选不同者 0。
- 索引：`data/audit_2x2/sequence/A00_seed{0,1,2}.jsonl`、`A11_seed{0,1,2}.jsonl`；manifest：`data/audit_2x2/sequence/manifest.json`。
- 是否与方案预期一致：**一致**（分母、每格 6 族、F5/F6/相同候选计数均吻合）。

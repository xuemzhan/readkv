# 2×2 GPU 补充实验 · CPU 数据准备报告

> 执行角色：数据工程师 · 日期：2026-11-23
> 依据：`refine-logs/EXPERIMENT_PLAN.md` §1（数据准备）、PI 指令（真实 PI 拍板 2×2 GPU 补充实验，v2.7 由 PI 冻结中）
> 范围：**仅 CPU 数据准备；未跑任何 GPU 实验**；不改 `data/tasks/cf_pairs.jsonl`、manifest、`configs/prereg/**`（含 v2.7）、代码、`reports/runs/**`、论文。
> 结论：6 组 train + 6 组 val 全部导出并验收通过；val 样本哈希与归档 Joint 行 EXACT 匹配；旧版缺陷已量化登记。

## 1. 生成器版本与隔离方式

| 版本 | commit | 代码来源（未改仓库代码） | 导出目录 |
|---|---|---|---|
| 旧版 legacy | `458de18` | `git show 458de18:src/readkv/data/build_cf_pairs.py` 抽到 `/tmp/opencode/gen_old/readkv/data/`，独立 PYTHONPATH 导入 | `data/audit_2x2/legacy/` |
| 修复版 fixed | `efc3ba3` | `git show efc3ba3:src/readkv/data/build_cf_pairs.py` 抽到 `/tmp/opencode/gen_new/readkv/data/`，独立 PYTHONPATH 导入 | `data/audit_2x2/fixed/` |

- 导出时 sizes = `{probe:0, train:120, val:60, test:0, real:0}`（其他 split 设 0）；各 split 用独立 RNG `Random(f"{seed}-{split}")`，故其他 split 置 0 不影响 train/val 的生成序列。
- 每次导出脚本打印并断言实际加载的模块路径（确认未误用工作区当前代码），见导出日志。

## 2. 导出文件清单（12 个，逐文件真实 LF SHA-256）

| 版本/split/seed | 路径 | 行数 | SHA-256（实测） |
|---|---|---|---|
| legacy train seed0 | `data/audit_2x2/legacy/train_seed0.jsonl` | 120 | `81da04a041a4e7757caa02e502c10ca9a9236d7f98da5419fb226ca95a02b00a` |
| legacy train seed1 | `data/audit_2x2/legacy/train_seed1.jsonl` | 120 | `7385245c6b2db4e4f78abc837aaa31817cd7025eaa23dc099b2dc92c9f4a793e` |
| legacy train seed2 | `data/audit_2x2/legacy/train_seed2.jsonl` | 120 | `3ad49eea2a41ff0e0ffd516b0fb1b8dc5282dce9a8336d7f371bf28adc97bb11` |
| legacy val seed0 | `data/audit_2x2/legacy/val_seed0.jsonl` | 60 | `24a5077bec11657c70d8eeddeed6fbe4871253d6d141daf16989903d1ebccaaa` |
| legacy val seed1 | `data/audit_2x2/legacy/val_seed1.jsonl` | 60 | `6f5c2b553832bdb2e03dd56ab39a7e6b2a6e4b5ec726448692f9fae1ebb849ff` |
| legacy val seed2 | `data/audit_2x2/legacy/val_seed2.jsonl` | 60 | `df24f7cf9d6fae8ce2e8a7af9b2a68aefe040a447534d30119aed99cd7f0c759` |
| fixed train seed0 | `data/audit_2x2/fixed/train_seed0.jsonl` | 120 | `9b03522746825f3fe0794c7f62ec7b1fb430f46734bb175b90a55a788d91e953` |
| fixed train seed1 | `data/audit_2x2/fixed/train_seed1.jsonl` | 120 | `024a69e9f35c777ad1030227eed37ef8f3dd43a82fb0a905a569e9150a37633f` |
| fixed train seed2 | `data/audit_2x2/fixed/train_seed2.jsonl` | 120 | `53258777ab214fb9226b85389673672c9c4b1b17c8cb9d07cf1a97beddcf3e6e` |
| fixed val seed0 | `data/audit_2x2/fixed/val_seed0.jsonl` | 60 | `19e9839e4e27b584c53d30242411ab14a659ac5cc487849b205928f5caa3c595` |
| fixed val seed1 | `data/audit_2x2/fixed/val_seed1.jsonl` | 60 | `b4f9587fc7e28a780b923c7e4a3e1aec96ddf6cde3c63a50fd0cc4b8423e7921` |
| fixed val seed2 | `data/audit_2x2/fixed/val_seed2.jsonl` | 60 | `5633a8bf052f33c44ec694704baef64c96898a1548fc313abc2fb537a5e5b475` |

- 全部以 **LF** 换行写入（`newline="\n"`，已核验无 `\r`）；machine-readable 清单见 `data/audit_2x2/manifest.json`（其 SHA-256 `31918e2c…23beb23`），每版本 `_index.json` 亦记录。
- 行数验收：6 组 train 各 120 ✅；6 组 val 各 60 ✅。

## 3. 样本指纹方法（防跨版本 pair_id 误配）

每条记录新增两个字段：
- `sample_hash = sha256(query|context_A|context_B|candidate_A|candidate_B)` —— 与两版生成器的 `stable_hash(pair)` 完全一致，因此**等于归档 scores.jsonl 中 Joint 行的 `cache_hash`**。
- `sample_id = "<version_tag>|<sample_hash[:16]>"` —— 版本限定的稳定身份键。

**关键证据**：跨版本 `pair_id` 字符串相同但样本不同——以 val seed0 为例，60 个共享 pair_id（如 `val-F1-0000`）**60/60 的 sample_hash 不同**（legacy `a659c1c3…` vs fixed `a987ce93…`）。因此 2×2 入口必须按 `version+sample_hash` 关联样本，**不得仅按 pair_id**（方案 §1 特别强调）。详见 `data/audit_2x2/diagnostics.json` 的 `cross_version_pairid_collision`。

## 4. 验收：val 样本哈希 vs 归档 Joint 行（EXACT）

| 导出 val | 匹配的归档 run（Joint val 60 行 cache_hash 集合） | 结果 |
|---|---|---|
| legacy seed0 | `p1_gpu_main_seed0`(53e9bc5)、`p1_gpu_mvp_seed0`(53e9bc5)、`p1_gpu_mvp_repro_seed0`(458de18)、`p1_gpu_kdonly_mvp_seed0`(458de18)、`delta_lock_v2p1_{0p5,1p0,2p0}` | 60/60 EXACT |
| legacy seed1 | `p1_gpu_main_seed1`、`p1_gpu_mvp_seed1`、`p1_gpu_mvp_repro_seed1`、`p1_gpu_kdonly_mvp_seed1_par` | 60/60 EXACT |
| legacy seed2 | `p1_gpu_main_seed2`、`p1_gpu_mvp_seed2`、`p1_gpu_mvp_repro_seed2`、`p1_gpu_kdonly_mvp_seed2_fast` | 60/60 EXACT |
| fixed seed0 | `p1_clean_mvp_seed0`(efc3ba3)、`p1_kd_clean_mvp_seed0`(6413ba0) | 60/60 EXACT |
| fixed seed1 | `p1_clean_mvp_seed1`、`p1_kd_clean_mvp_seed1` | 60/60 EXACT |
| fixed seed2 | `p1_clean_mvp_seed2`、`p1_kd_clean_mvp_seed2` | 60/60 EXACT |

6/6 val 集与对应归档 Joint 行样本哈希**完全一致**（集合相等），符合方案“val 样本哈希与已归档 Joint 行一致（旧版对旧 run、修复版对 clean run）”的验收要求。

## 5. 旧版诊断格（缺陷量化证据，来自 `data/audit_2x2/diagnostics.json`）

对旧版（legacy）每个 seed 的 train+val（180 对）统计：

| seed | 重复文本组 | must_flip 候选退化对（candidate_A==B） | must_flip 双文档全同 | train–val 逐字重叠（context_A / context_B / query / edited_span） |
|---|---|---|---|---|
| legacy seed0 | 0 | **9** | **5** | ctxA=1（train-F5-0073 ≡ val-F1-0040）, ctxB=1, query=23, edited=11 |
| legacy seed1 | **1** | **7** | **5** | ctxA=0, ctxB=0, query=20, edited=8 |
| legacy seed2 | 0 | **9** | **7** | ctxA=0, ctxB=1, query=26, edited=11 |

修复版（fixed）三个 seed 全部为 0（重复文本/退化对/双文档全同/train-val 逐字重叠均为 0）——与 M1/M2 修复预期一致。

说明：本诊断基于 train+val-only 导出（方案约定的 2×2 输入），故重叠数小于全 520 对数据集的审计值（全库 train↔test 等）；它量化的是**本次 2×2 实际喂入的 train/val 中存在的旧缺陷**，正是补实验要分离的因素。逐条重叠/退化 pair_id 与内容存于 `diagnostics.json`。

## 6. 边界与合规

- `data/tasks/cf_pairs.jsonl` 未改（sha256 仍 `f910f1f1…a894a`）；`data/tasks/manifest.json` 未改（`874826e9…`）。
- 未改 `configs/prereg/**`（含 PI 正在冻结的 v2.7）、任何代码、`reports/runs/**`、论文。
- 未启动任何 GPU 实验；本工作全部在 CPU 完成。
- 所有 sha256 均由 `sha256sum`/`hashlib` 对实际字节计算，无编造。

## 7. 给工程师的审计入口数据

- 数据根：`data/audit_2x2/`
- 版本目录：`legacy/`（458de18）、`fixed/`（efc3ba3）；每目录 `train_seed{0,1,2}.jsonl`（120 行）、`val_seed{0,1,2}.jsonl`（60 行）。
- 逐文件哈希/行数/字节：`data/audit_2x2/manifest.json`（及每版本 `_index.json`）。
- 旧版缺陷明细 + 跨版本 pair_id 碰撞：`data/audit_2x2/diagnostics.json`。
- 关联键：用 `version_tag + sample_hash`（**不要**用 pair_id）；`sample_hash` 即 scores 的 `cache_hash`，便于与归档 Joint 行逐对核对。
- 四格 A00/A01/A10/A11 由工程师用独立审计入口显式接收两份 train 与两份 val（方案 §1），本角色只提供数据，未实现/运行评测。

## 8. 说明

- v2.7 判据由 PI 冻结中，本报告不依赖也不修改其内容；评测口径（L、bootstrap、阈值等）由工程师/v2.7 定义。
- 旧版历史样本保留（legacy/），以支持复现历史对角格与核对历史 Joint 逐对结果。

# E2 test split 锁文件（G1 · CPU-only）

**性质：** 数据哈希与锁定清单；**本文件不读取 test 内容用于评分、不产生任何预测、不报告任何 test 性能数字**。无 GPU、无模型推理。

**日期：** 2026-11-25　**角色：** data-engineer　**状态：** 数据层锁定项已落盘；模型/代码/评测器锁定项须由授权者在一次性评测前补齐。

## 1. 命名与解锁状态

本 split 为 **previously unevaluated held-out split**（此前未评测的 held-out split），**不称 "sealed"**。PI 已在 `docs/decisions/gpu_v3_scope_ruling.md` §1 明确解锁 E2；`configs/prereg/gpu_followup_v3.0.yaml` §4 冻结了设计与判读分支。本文件只做锁定，不构成评测授权。

## 2. 数据哈希（已锁定）

| 对象 | SHA-256 | 方法 |
|---|---|---|
| 整文件 `data/tasks/cf_pairs.jsonl` | `f910f1f1196a21041765834654af8233d216ef4bf4f28f4c60abbd0641aa894a` | 文件字节；与 `data/tasks/manifest.json` 记录一致 |
| test split（300 对） | `c5450013bc9fc9b84dec286a653207f2dde8168d0df74a24896218d32769a7a2` | 抽取 `split=="test"` 的 300 行，按 `json.dumps(ensure_ascii=False)+LF` 规范序列化后取字节 SHA-256；与原始行字节拼接法结果一致 |

## 3. 计数（来自 `data/tasks/manifest.json`，未重新解释任务内容）

- 整文件：`520` 行；split 计数 probe=40 / train=120 / val=60 / **test=300**。
- test template-family 数：**16**（低于冻结参考线 24，判读标记 `exploratory=true`）。
- test slice 结构计数（仅元数据）：F1=57, F2=57, F3=57, F4=57, F5=36, F6=36。
- 全数据 template-family 总数 56；test 未评测。

## 4. 锁定清单（Lock checklist）

| # | 锁定项 | 当前值 / 要求 | 状态 |
|---|---|---|---|
| 1 | **数据 SHA** | 整文件 `f910f1f1196a21041765834654af8233d216ef4bf4f28f4c60abbd0641aa894a`；test split `c5450013bc9fc9b84dec286a653207f2dde8168d0df74a24896218d32769a7a2` | **已锁定（本文件）** |
| 2 | **代码 commit / 入口哈希** | 当前工作目录不是 git 仓库，无法提供 git commit；已记录脚本 SHA-256：`experiments/P1_gpu.py` `97043a318fc0ed8928cafa4891887ddd0c522bc5b67dba98b3d6c975429884f5`、`experiments/P1_kd_gpu.py` `533a185ea6377c4a56cf2f16a509a5f1bc7f338324731afa8503fb090efc1c0d`。授权者须在评测前冻结实际执行的 commit/入口哈希并写入 run manifest；不得用漂移别名。 | 部分（文件哈希已记；git commit 待授权者冻结） |
| 3 | **模型 / checkpoint / tokenizer** | 必须在评测前锁定 modelscope snapshot/revision、权重文件 SHA-256、tokenizer SHA-256；不得使用未记录实际文件 hash 的 `master` 别名。G1 为 CPU 数据工作，本项**未确定、未伪造**。 | 待授权者锁定 |
| 4 | **输出指标** | 逐 mapper seed 的 Self/Joint dual correctness、`L=Self−Joint`、`E_CF`、coverage、flip/direction consistency 及 template-family 区间；不得只报 `E_CF`（冻结 prereg §2/§4）。 | 已在 prereg 冻结 |
| 5 | **seeds / 格数** | mapper seeds `[0,1,2]`，mappers `affine` + `kd_only` → **6 个评测格**；同一固定 300 对 test split，三次评分是 mapper/calibration seeds，**不是 3 份独立 test replicate**，不得合并推断。 | 已在 prereg 冻结 |
| 6 | **排除规则** | flip 分母排除 F5+F6（`configs/prereg/stats_convention_v2.3.yaml`，sha `e44c6acb...`）；F5 negative control 不计入 must-flip 分母；length-mismatch 单独分层报告。 | 已冻结并记录 |
| 7 | **统计脚本** | 主统计为 template_family 簇级 bootstrap（10000 次）+ pair-level 敏感性并列；候选脚本 SHA-256：`scripts/bootstrap_ci_report.py` `3545ada7b3b6d819164b69dad64b4e58c6ee64d5d6dada1dbc4f3310f2c8b23d`、`scripts/consistency_check.py` `37b282fea1d1633e6f74b63e78c3ea9d734a8d8ccc17ec254424048dd285b8b3`。统计须从 `scores.jsonl` 重建，不人工改数字。 | 候选脚本哈希已记；须绑定实际执行版本 |
| 8 | **一次性 dedicated evaluator** | 必须是 test-only，带显式路径/哈希/锁检查，禁止 val/test 混跑；`experiments/P1_gpu.py` 默认只评 val，`experiments/P1_kd_gpu.py` 的 `--eval-splits test` 仅在锁完成后由 dedicated evaluator 使用。只运行一次，不覆盖历史 run。 | 待工程师实现并由授权者执行 |
| 9 | **无调参 / 无返修 / 无多轮查看** | 验证集不再用于选参；固定 affine 与 kd_only 配置；不在 test 上选阈值、不做错误样本返修、不多轮查看后再跑；test 上失败照实报告，不返回 val 调整后再声称独立 test。 | 冻结禁令（prereg §4 prohibitions） |

## 5. 本轮边界

- 未读取 test 条目的任务内容做判定，未运行任何 evaluator，未生成 `scores.jsonl` / 预测 / 指标。
- 未修改 `configs/**`、`reports/runs/**`、`src/**`、`experiments/**` 或任何冻结判据。
- 下游须以本报告两个 SHA 作为 test 数据绑定值；若 `cf_pairs.jsonl` 字节变化则锁失效，必须重新走 G0/G1 授权，不得静默续跑。
